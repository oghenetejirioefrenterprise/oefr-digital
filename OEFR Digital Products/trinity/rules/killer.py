"""Apply kill rules to the product roster.

Pure Python — runs without LLM. The agent loop cannot rationalize past
this. Reads roster, applies thresholds, transitions statuses, returns
a structured report.

Phase 0 behavior:
- Detects products that hit kill thresholds → moves to sunset-pending
- Sunset-pending products past grace period → moved to dead
- `maintain` status is respected (TJ override) — no auto-sunset
- `meta` status is ignored (e.g., gumroad-products directory)
- Actual unlisting from Etsy/Gumroad is OUT OF SCOPE for Phase 0
  (queued for Phase 1 sunset-executor cycle with browser automation)
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Optional

from .roster import (
    Product,
    Status,
    SUNSET_GRACE_DAYS,
    PORTFOLIO_MAX,
    load_roster,
    save_roster,
    append_postmortem,
)


@dataclass
class KillerAction:
    product: str
    from_status: str
    to_status: str
    reason: str


@dataclass
class KillerReport:
    actions: list[KillerAction] = field(default_factory=list)
    portfolio_size_before: int = 0
    portfolio_size_after: int = 0
    skipped_overrides: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = ["# Killer Loop Report", f"Date: {dt.date.today().isoformat()}", ""]
        lines.append(f"Portfolio: {self.portfolio_size_before} → {self.portfolio_size_after} active")
        lines.append("")
        if self.actions:
            lines.append(f"## Actions ({len(self.actions)})")
            for a in self.actions:
                lines.append(f"- **{a.product}**: {a.from_status} → {a.to_status} ({a.reason})")
        else:
            lines.append("## Actions\nNo state transitions today.")
        if self.skipped_overrides:
            lines.append("")
            lines.append(f"## Skipped (manual maintain override): {len(self.skipped_overrides)}")
            for name in self.skipped_overrides:
                lines.append(f"- {name}")
        return "\n".join(lines)


# ── Kill rule evaluation ────────────────────────────────────────

# Format: "metric < threshold in N d [AND ...]"
_RULE_CLAUSE = re.compile(
    r"(?P<metric>\w+(?:_\w+)*)\s*(?P<op><|<=|>|>=|==)\s*(?P<value>\d+(?:\.\d+)?)\s*in\s*(?P<window>\d+)\s*d",
    re.IGNORECASE,
)


# Sentinel for clauses whose metric has no sensor yet. Phase 0 treats these
# as "skip" rather than "fail" so a rule like "sales<1 AND views<50" can
# still trigger on the sales clause alone until Phase 1 view sensors land.
UNMEASURABLE = object()


def _eval_clause(product: Product, metric: str, op: str, value: float, window_days: int,
                 today: Optional[dt.date] = None):
    """Evaluate one rule clause against a product.

    Returns True/False if the clause can be evaluated, or UNMEASURABLE
    sentinel if the metric has no sensor in Phase 0. The caller decides
    how to combine results (skip vs. fail).
    """
    today = today or dt.date.today()

    if metric.lower() == "sales":
        # Approximate from revenue: revenue_30d > 0 implies ≥ 1 sale in 30d.
        # Window mismatch is handled conservatively (we use whatever data we have).
        sales_in_window = 1 if product.revenue_value() > 0 else 0
        return _compare(sales_in_window, op, value)

    if metric.lower() == "revenue":
        return _compare(product.revenue_value(), op, value)

    if metric.lower() == "views":
        # Phase 1 sensors will populate this. For Phase 0, mark as skip.
        return UNMEASURABLE

    # Unknown metric — skip rather than fail.
    return UNMEASURABLE


def _compare(actual: float, op: str, expected: float) -> bool:
    if op == "<":
        return actual < expected
    if op == "<=":
        return actual <= expected
    if op == ">":
        return actual > expected
    if op == ">=":
        return actual >= expected
    if op == "==":
        return actual == expected
    return False


def _rule_matches(product: Product, today: Optional[dt.date] = None) -> tuple[bool, str]:
    """Return (should_sunset, reason). Joins all clauses with AND."""
    rule = product.kill_rule.strip().lower()
    if not rule or rule in ("manual", "n/a", "—", "-"):
        return False, "no automated rule"

    clauses = [c.strip() for c in re.split(r"\band\b", rule)]
    matched_descs = []
    skipped_descs = []
    for clause in clauses:
        m = _RULE_CLAUSE.search(clause)
        if not m:
            # Could not parse this clause — fail safe, don't kill.
            return False, f"unparseable clause: {clause!r}"
        metric = m.group("metric")
        op = m.group("op")
        value = float(m.group("value"))
        window = int(m.group("window"))
        verdict = _eval_clause(product, metric, op, value, window, today=today)
        if verdict is UNMEASURABLE:
            skipped_descs.append(f"{metric}{op}{value:g} in {window}d (no sensor)")
            continue
        if not verdict:
            return False, f"clause not satisfied: {metric}{op}{value:g} in {window}d"
        matched_descs.append(f"{metric}{op}{value:g} in {window}d")

    # Need at least one measurable clause that fired. If every clause was
    # unmeasurable, we have no basis to kill — fail safe.
    if not matched_descs:
        return False, f"no measurable clauses (skipped: {', '.join(skipped_descs)})"

    desc = " AND ".join(matched_descs)
    if skipped_descs:
        desc += f" (skipped Phase 0: {', '.join(skipped_descs)})"
    return True, desc


# ── Main entry ──────────────────────────────────────────────────

def apply_kill_rules(today: Optional[dt.date] = None) -> KillerReport:
    """Scan roster, apply rules, transition statuses, return report.

    Side effects: writes updated roster, appends post-mortems for any
    transitions to dead.
    """
    today = today or dt.date.today()
    products = load_roster()

    report = KillerReport()
    report.portfolio_size_before = sum(
        1 for p in products
        if p.status not in (Status.DEAD, Status.META)
    )

    for p in products:
        # Skip non-actionable statuses.
        if p.status in (Status.DEAD, Status.META):
            continue

        # Manual maintain override — log skip, do not auto-sunset.
        if p.status == Status.MAINTAIN:
            report.skipped_overrides.append(p.name)
            continue

        # Sunset-pending: check grace period expiration.
        if p.status == Status.SUNSET_PENDING:
            # If the product launched more than (grace + window) days ago and still
            # has no signal, kill it. We approximate "time in sunset-pending" using
            # days_since_signal (or days_since_launch if never signaled).
            ref_days = p.days_since_signal(today) or p.days_since_launch(today)
            if ref_days is not None and ref_days >= SUNSET_GRACE_DAYS:
                # Re-check the rule. If a positive signal arrived during grace,
                # the rule will no longer match and we skip the kill (resurrection).
                still_failing, reason = _rule_matches(p, today)
                if still_failing:
                    p.status = Status.DEAD
                    report.actions.append(KillerAction(
                        product=p.name,
                        from_status=Status.SUNSET_PENDING,
                        to_status=Status.DEAD,
                        reason=f"grace period elapsed ({ref_days}d ≥ {SUNSET_GRACE_DAYS}d), still failing: {reason}",
                    ))
                    append_postmortem(
                        p,
                        cause=reason,
                        lesson="No validation pre-build; consider validation gate before next product in this category",
                    )
                else:
                    # Positive signal arrived — bump back to producing.
                    p.status = Status.PRODUCING
                    report.actions.append(KillerAction(
                        product=p.name,
                        from_status=Status.SUNSET_PENDING,
                        to_status=Status.PRODUCING,
                        reason=f"new signal during grace period: {reason}",
                    ))
            continue

        # Active states: producing / scaling / validating / candidate.
        # Apply the kill rule.
        should_sunset, reason = _rule_matches(p, today)
        if should_sunset:
            prev_status = p.status
            p.status = Status.SUNSET_PENDING
            report.actions.append(KillerAction(
                product=p.name,
                from_status=prev_status,
                to_status=Status.SUNSET_PENDING,
                reason=reason,
            ))

    report.portfolio_size_after = sum(
        1 for p in products
        if p.status not in (Status.DEAD, Status.META)
    )

    # Persist any state transitions.
    if report.actions:
        save_roster(products)

    return report
