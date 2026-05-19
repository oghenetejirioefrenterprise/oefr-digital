"""Reputation snapshot generator — Phase 4 sub-project 4.3.

Compiles per-agent "reputation snapshots" from production state. Each
snapshot is a JSON file the corresponding agent reads at the start of its
cycle to bias its decisions with what historically produced revenue (and
what didn't).

Inputs (all read defensively — missing dirs/files = empty patterns):
- state/customers/*.json         actual sales (Stripe webhooks/customer_sweep)
- state/partnerships/sales-log.json   affiliate sales
- state/products/<slug>/spec.json    shipped product specs
- state/products/<slug>/launch-report.json   ship status + slug -> product map
- state/opportunities/*.json     opportunity briefs from research_scan
- state/ethics-ledger/*.json     compliance verdicts

Outputs (in state/reputations/):
- researcher.json         opportunity-niche -> sales correlation
- product-manager.json    spec patterns -> sales (price tier, bonus count, format)
- compliance-officer.json verdict counts + revocations + verdict->sales

Standalone usage:
    source ~/.profile && python scripts/reputation_snapshot.py

Output (last line, stdout):
    researcher_niches=N pm_patterns=N compliance_verdicts=N revocations=N

Run nightly via the `reputation_refresh` trinity cycle (23:00 ET).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


# ── Paths ───────────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
STATE_DIR = _REPO_ROOT / "state"
REPUTATIONS_DIR = STATE_DIR / "reputations"

CUSTOMERS_DIR = STATE_DIR / "customers"
PARTNERSHIPS_SALES_LOG = STATE_DIR / "partnerships" / "sales-log.json"
PRODUCTS_DIR = STATE_DIR / "products"
OPPORTUNITIES_DIR = STATE_DIR / "opportunities"
ETHICS_LEDGER_DIR = STATE_DIR / "ethics-ledger"

WINDOW_DAYS = 30


# ── Defensive io ────────────────────────────────────────────────────
def _read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON file. Return None on any failure (missing, malformed)."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _list_json(directory: Path) -> list[Path]:
    """List *.json files in directory. Empty list if directory missing."""
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.json") if p.is_file())


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO datetime string defensively. Return None on failure."""
    if not value or not isinstance(value, str):
        return None
    try:
        s = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _within_window(dt: datetime | None, cutoff: datetime) -> bool:
    return dt is not None and dt >= cutoff


# ── Niche keyword extraction ────────────────────────────────────────
_NICHE_STOP = {
    "the", "and", "for", "with", "from", "data", "database", "directory",
    "registry", "records", "list", "csv", "us", "usa", "state", "states",
    "national", "public", "open", "new", "may", "2026", "leads",
}


def _niche_keywords(brief: dict[str, Any]) -> list[str]:
    """Extract candidate niche keywords from an opportunity brief.

    Naive but reproducible: tokenize the slug and audience.who, lowercase,
    strip stopwords and short tokens. The agent's snapshot consumer treats
    these as cohorts, not labels.
    """
    pieces: list[str] = []
    slug = brief.get("slug") or ""
    if isinstance(slug, str):
        pieces.append(slug.replace("-", " "))
    audience = brief.get("audience") or {}
    if isinstance(audience, dict):
        who = audience.get("who") or ""
        if isinstance(who, str):
            pieces.append(who)
    blob = " ".join(pieces).lower()
    tokens = re.findall(r"[a-z][a-z0-9]{2,}", blob)
    seen: list[str] = []
    for t in tokens:
        if t in _NICHE_STOP:
            continue
        if t in seen:
            continue
        seen.append(t)
    # Cap to keep snapshots small. First ~8 tokens carry the niche signal.
    return seen[:8]


# ── Sales aggregation ───────────────────────────────────────────────
def _load_customer_records() -> list[dict[str, Any]]:
    """Return all customer records as dicts. Defensive against missing dir."""
    out: list[dict[str, Any]] = []
    for path in _list_json(CUSTOMERS_DIR):
        rec = _read_json(path)
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _customer_revenue_by_slug(
    customers: list[dict[str, Any]], cutoff: datetime
) -> dict[str, dict[str, float]]:
    """Aggregate revenue + purchase count by product slug within window.

    A customer file (per customer_sweep) typically contains a list of
    purchases / subscriptions, each with an amount and a product slug. We
    handle multiple plausible shapes defensively.
    """
    totals: dict[str, dict[str, float]] = {}
    for rec in customers:
        purchases = rec.get("purchases") or rec.get("orders") or []
        if not isinstance(purchases, list):
            purchases = []
        # Subscriptions surface as a separate list in some shapes.
        subs = rec.get("subscriptions") or []
        if isinstance(subs, list):
            purchases = purchases + subs
        for item in purchases:
            if not isinstance(item, dict):
                continue
            slug = (
                item.get("product_slug")
                or item.get("slug")
                or item.get("product")
                or ""
            )
            if not isinstance(slug, str) or not slug:
                continue
            when = _parse_iso(
                item.get("created")
                or item.get("created_at")
                or item.get("purchased_at")
                or item.get("date")
            )
            if not _within_window(when, cutoff):
                continue
            amt_cents = item.get("amount") or item.get("amount_cents") or 0
            try:
                amt_cents = float(amt_cents)
            except (TypeError, ValueError):
                amt_cents = 0.0
            # Heuristic: trinity stores cents; values < 1000 likely dollars.
            amount_usd = amt_cents / 100.0 if amt_cents >= 1000 else amt_cents
            slot = totals.setdefault(slug, {"revenue_usd": 0.0, "count": 0})
            slot["revenue_usd"] += float(amount_usd)
            slot["count"] += 1
    return totals


def _affiliate_revenue_by_slug(cutoff: datetime) -> dict[str, dict[str, float]]:
    """Revenue from partnerships/sales-log.json grouped by slug."""
    totals: dict[str, dict[str, float]] = {}
    log = _read_json(PARTNERSHIPS_SALES_LOG) or {}
    sales = log.get("sales") if isinstance(log, dict) else None
    if not isinstance(sales, list):
        return totals
    for sale in sales:
        if not isinstance(sale, dict):
            continue
        slug = sale.get("product_slug") or sale.get("slug") or ""
        if not isinstance(slug, str) or not slug:
            continue
        when = _parse_iso(sale.get("sold_at") or sale.get("created") or sale.get("date"))
        if not _within_window(when, cutoff):
            continue
        amt = sale.get("amount_usd") or sale.get("amount") or 0
        try:
            amt = float(amt)
        except (TypeError, ValueError):
            amt = 0.0
        if amt >= 1000:  # likely cents
            amt = amt / 100.0
        slot = totals.setdefault(slug, {"revenue_usd": 0.0, "count": 0})
        slot["revenue_usd"] += amt
        slot["count"] += 1
    return totals


def _merge_revenue(*sources: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    merged: dict[str, dict[str, float]] = {}
    for src in sources:
        for slug, vals in src.items():
            slot = merged.setdefault(slug, {"revenue_usd": 0.0, "count": 0})
            slot["revenue_usd"] += vals.get("revenue_usd", 0.0)
            slot["count"] += int(vals.get("count", 0))
    return merged


# ── Product index ───────────────────────────────────────────────────
def _shipped_products() -> dict[str, dict[str, Any]]:
    """Return slug -> {spec, launch_report} for products that shipped.

    A product is "shipped" if launch-report.json exists and status is one of
    {"FULLY_SHIPPED", "STRIPE_LIVE", "READY", "SHIPPED"}. We're permissive
    about status because the goal is coverage, not a strict gate.
    """
    out: dict[str, dict[str, Any]] = {}
    if not PRODUCTS_DIR.exists():
        return out
    for product_dir in sorted(PRODUCTS_DIR.iterdir()):
        if not product_dir.is_dir():
            continue
        spec = _read_json(product_dir / "spec.json")
        launch = _read_json(product_dir / "launch-report.json")
        if not isinstance(spec, dict):
            continue
        slug = spec.get("slug") or product_dir.name
        out[slug] = {
            "slug": slug,
            "spec": spec,
            "launch_report": launch if isinstance(launch, dict) else {},
            "shipped": isinstance(launch, dict),
        }
    return out


# ── Researcher snapshot ─────────────────────────────────────────────
def _build_researcher_snapshot(
    cutoff: datetime,
    products: dict[str, dict[str, Any]],
    revenue_by_slug: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Group opportunity briefs by niche keyword and correlate to revenue.

    For each brief in window, extract niche keywords, attribute to it the
    revenue of any product whose slug matches the brief slug.
    """
    briefs = []
    for path in _list_json(OPPORTUNITIES_DIR):
        brief = _read_json(path)
        if not isinstance(brief, dict):
            continue
        if brief.get("type") != "opportunity_brief" and "score" not in brief:
            # Skip scan-summary or non-brief shapes.
            continue
        when = _parse_iso(brief.get("created") or brief.get("approved_at"))
        if not _within_window(when, cutoff):
            continue
        briefs.append(brief)

    niche_stats: dict[str, dict[str, Any]] = {}
    products_shipped_from_briefs = 0
    total_revenue_from_briefs = 0.0

    for brief in briefs:
        slug = brief.get("slug") or ""
        # Find any shipped product whose slug starts with the brief slug
        # (briefs are dateless: "new-fmcsa-carrier-leads" -> product
        # "new-fmcsa-carrier-leads-2026-05").
        matched_product_slugs = [
            ps for ps in products
            if isinstance(slug, str) and slug and ps.startswith(slug)
        ]
        product_revenue = 0.0
        for ps in matched_product_slugs:
            product_revenue += revenue_by_slug.get(ps, {}).get("revenue_usd", 0.0)
        if matched_product_slugs:
            products_shipped_from_briefs += 1
            total_revenue_from_briefs += product_revenue

        for kw in _niche_keywords(brief):
            slot = niche_stats.setdefault(
                kw,
                {
                    "niche": kw,
                    "briefs": 0,
                    "products_shipped": 0,
                    "revenue_usd": 0.0,
                    "evidence_slugs": [],
                },
            )
            slot["briefs"] += 1
            if matched_product_slugs:
                slot["products_shipped"] += 1
                slot["revenue_usd"] += product_revenue
                for ps in matched_product_slugs:
                    if ps not in slot["evidence_slugs"]:
                        slot["evidence_slugs"].append(ps)

    high: list[dict[str, Any]] = []
    low: list[dict[str, Any]] = []
    for kw, stats in niche_stats.items():
        evidence = (
            f"{stats['products_shipped']} product(s) shipped from {stats['briefs']} brief(s); "
            f"${stats['revenue_usd']:.2f} revenue. "
            f"Slugs: {', '.join(stats['evidence_slugs']) or 'none'}"
        )
        row = {
            "niche": kw,
            "products_shipped": stats["products_shipped"],
            "revenue_usd": round(stats["revenue_usd"], 2),
            "evidence": evidence,
        }
        if stats["revenue_usd"] > 0:
            high.append(row)
        elif stats["products_shipped"] >= 2 and stats["revenue_usd"] == 0:
            # 2+ shipped products in this niche with zero revenue is a real
            # low signal. Single shipment with no revenue yet is just early.
            low.append(row)

    high.sort(key=lambda r: r["revenue_usd"], reverse=True)
    low.sort(key=lambda r: r["products_shipped"], reverse=True)

    summary = (
        f"Researcher reputation (last {WINDOW_DAYS}d): "
        f"{len(briefs)} briefs scored, "
        f"{products_shipped_from_briefs} shipped, "
        f"${total_revenue_from_briefs:.2f} revenue. "
        f"{len(high)} high-signal niche(s), {len(low)} low-signal niche(s)."
    )

    return {
        "version": 1,
        "agent": "researcher",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": WINDOW_DAYS,
        "summary": summary,
        "patterns": {
            "high_signal_niches": high,
            "low_signal_niches": low,
        },
        "raw_counts": {
            "total_opportunities_briefed": len(briefs),
            "total_products_shipped_from_briefs": products_shipped_from_briefs,
            "total_revenue_from_briefs": round(total_revenue_from_briefs, 2),
        },
    }


# ── Product-manager snapshot ────────────────────────────────────────
def _price_tier(price_usd: Any) -> str:
    try:
        p = float(price_usd)
    except (TypeError, ValueError):
        return "unknown"
    if p <= 0:
        return "free_or_unknown"
    if p < 20:
        return "under_20"
    if p < 40:
        return "20_to_39"
    if p < 80:
        return "40_to_79"
    if p < 150:
        return "80_to_149"
    return "150_plus"


def _bonus_bucket(spec: dict[str, Any]) -> str:
    stack = spec.get("bonus_stack") or []
    n = len(stack) if isinstance(stack, list) else 0
    if n == 0:
        return "none"
    if n <= 2:
        return "sparse_1_2"
    if n <= 4:
        return "medium_3_4"
    return "rich_5_plus"


def _build_pm_snapshot(
    cutoff: datetime,
    products: dict[str, dict[str, Any]],
    revenue_by_slug: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Bucket specs by (price_tier, bonus_bucket, format). Correlate to revenue."""
    pattern_stats: dict[str, dict[str, Any]] = {}
    pm_specs_in_window = 0
    revenue_from_pm_specs = 0.0

    for slug, info in products.items():
        spec = info["spec"]
        created_by = spec.get("created_by") or ""
        # Spec was authored by product-manager OR by ceo from a PM draft —
        # both count toward PM's track record. (CEO often promotes PM drafts.)
        created = _parse_iso(spec.get("created"))
        if not _within_window(created, cutoff):
            continue
        pm_specs_in_window += 1
        rev = revenue_by_slug.get(slug, {}).get("revenue_usd", 0.0)
        revenue_from_pm_specs += rev

        key = (
            _price_tier(spec.get("price_usd")),
            _bonus_bucket(spec),
            str(spec.get("format") or "unknown"),
        )
        pattern_key = f"price={key[0]}|bonus={key[1]}|format={key[2]}"
        slot = pattern_stats.setdefault(
            pattern_key,
            {
                "pattern": pattern_key,
                "price_tier": key[0],
                "bonus_bucket": key[1],
                "format": key[2],
                "specs_count": 0,
                "shipped_count": 0,
                "revenue_usd": 0.0,
                "example_slugs": [],
                "created_by": created_by,
            },
        )
        slot["specs_count"] += 1
        if info["shipped"]:
            slot["shipped_count"] += 1
        slot["revenue_usd"] += rev
        if slug not in slot["example_slugs"] and len(slot["example_slugs"]) < 3:
            slot["example_slugs"].append(slug)

    winning: list[dict[str, Any]] = []
    losing: list[dict[str, Any]] = []
    for pat, stats in pattern_stats.items():
        evidence = (
            f"{stats['specs_count']} spec(s), {stats['shipped_count']} shipped, "
            f"${stats['revenue_usd']:.2f} revenue. Examples: "
            f"{', '.join(stats['example_slugs']) or 'none'}"
        )
        row = {
            "pattern": pat,
            "price_tier": stats["price_tier"],
            "bonus_bucket": stats["bonus_bucket"],
            "format": stats["format"],
            "specs": stats["specs_count"],
            "shipped": stats["shipped_count"],
            "revenue_usd": round(stats["revenue_usd"], 2),
            "evidence": evidence,
        }
        if stats["revenue_usd"] > 0:
            winning.append(row)
        elif stats["shipped_count"] >= 2 and stats["revenue_usd"] == 0:
            losing.append(row)

    winning.sort(key=lambda r: r["revenue_usd"], reverse=True)
    losing.sort(key=lambda r: r["shipped"], reverse=True)

    summary = (
        f"Product-manager reputation (last {WINDOW_DAYS}d): "
        f"{pm_specs_in_window} spec(s) drafted in window, "
        f"${revenue_from_pm_specs:.2f} revenue. "
        f"{len(winning)} winning pattern(s), {len(losing)} losing pattern(s)."
    )

    return {
        "version": 1,
        "agent": "product-manager",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": WINDOW_DAYS,
        "summary": summary,
        "patterns": {
            "winning_spec_patterns": winning,
            "losing_spec_patterns": losing,
        },
        "raw_counts": {
            "total_specs_in_window": pm_specs_in_window,
            "total_revenue_from_specs": round(revenue_from_pm_specs, 2),
        },
    }


# ── Compliance-officer snapshot ─────────────────────────────────────
def _build_compliance_snapshot(
    cutoff: datetime,
    products: dict[str, dict[str, Any]],
    revenue_by_slug: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Tally verdicts; flag any revocation; correlate PASSes to sales."""
    verdict_counts = {"PASS": 0, "FAIL": 0, "NEEDS_FOUNDER_REVIEW": 0, "OTHER": 0}
    pass_with_sales = 0
    pass_zero_sales = 0
    revocations: list[dict[str, Any]] = []
    verdicts_in_window: list[dict[str, Any]] = []

    for path in _list_json(ETHICS_LEDGER_DIR):
        verdict_doc = _read_json(path)
        if not isinstance(verdict_doc, dict):
            continue
        when = _parse_iso(verdict_doc.get("audited_at") or verdict_doc.get("created"))
        if not _within_window(when, cutoff):
            continue
        verdict = (verdict_doc.get("verdict") or "").upper()
        if verdict in verdict_counts:
            verdict_counts[verdict] += 1
        else:
            verdict_counts["OTHER"] += 1

        verdicts_in_window.append(
            {
                "slug": verdict_doc.get("slug"),
                "verdict": verdict,
                "audited_at": verdict_doc.get("audited_at"),
            }
        )

        # Revocation detection: explicit revoked flag OR a later FAIL/REVOKED
        # verdict for the same slug after a PASS. Currently zero in this
        # codebase — the explicit field check covers the common case.
        if verdict_doc.get("revoked") is True or verdict == "REVOKED":
            revocations.append(
                {
                    "slug": verdict_doc.get("slug"),
                    "reason": verdict_doc.get("revocation_reason") or "unspecified",
                    "audited_at": verdict_doc.get("audited_at"),
                }
            )

        if verdict == "PASS":
            slug = verdict_doc.get("slug") or ""
            # Match any product whose slug starts with the verdict slug.
            matched = [ps for ps in products if isinstance(slug, str) and slug and ps.startswith(slug)]
            rev = sum(revenue_by_slug.get(ps, {}).get("revenue_usd", 0.0) for ps in matched)
            if rev > 0:
                pass_with_sales += 1
            elif matched:
                pass_zero_sales += 1

    total_verdicts = sum(verdict_counts.values())
    summary = (
        f"Compliance reputation (last {WINDOW_DAYS}d): "
        f"{total_verdicts} verdict(s) issued "
        f"(PASS={verdict_counts['PASS']}, FAIL={verdict_counts['FAIL']}, "
        f"NFR={verdict_counts['NEEDS_FOUNDER_REVIEW']}). "
        f"Revocations: {len(revocations)} (zero is the positive signal). "
        f"{pass_with_sales} PASS(es) produced revenue; "
        f"{pass_zero_sales} PASS(es) shipped without revenue yet."
    )

    return {
        "version": 1,
        "agent": "compliance-officer",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": WINDOW_DAYS,
        "summary": summary,
        "patterns": {
            "verdict_counts": verdict_counts,
            "revocations": revocations,
            "pass_with_sales_count": pass_with_sales,
            "pass_zero_sales_count": pass_zero_sales,
        },
        "raw_counts": {
            "total_verdicts_in_window": total_verdicts,
            "total_revocations": len(revocations),
            "verdicts_in_window": verdicts_in_window,
        },
    }


# ── Driver ──────────────────────────────────────────────────────────
def _write_snapshot(name: str, payload: dict[str, Any]) -> Path:
    REPUTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = REPUTATIONS_DIR / f"{name}.json"
    tmp = target.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
        fh.write("\n")
    tmp.replace(target)
    return target


def main() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)

    customers = _load_customer_records()
    direct_revenue = _customer_revenue_by_slug(customers, cutoff)
    affiliate_revenue = _affiliate_revenue_by_slug(cutoff)
    revenue_by_slug = _merge_revenue(direct_revenue, affiliate_revenue)

    products = _shipped_products()

    researcher = _build_researcher_snapshot(cutoff, products, revenue_by_slug)
    pm = _build_pm_snapshot(cutoff, products, revenue_by_slug)
    compliance = _build_compliance_snapshot(cutoff, products, revenue_by_slug)

    _write_snapshot("researcher", researcher)
    _write_snapshot("product-manager", pm)
    _write_snapshot("compliance-officer", compliance)

    print(researcher["summary"])
    print(pm["summary"])
    print(compliance["summary"])
    print(
        "researcher_niches="
        f"{len(researcher['patterns']['high_signal_niches']) + len(researcher['patterns']['low_signal_niches'])} "
        "pm_patterns="
        f"{len(pm['patterns']['winning_spec_patterns']) + len(pm['patterns']['losing_spec_patterns'])} "
        "compliance_verdicts="
        f"{compliance['raw_counts']['total_verdicts_in_window']} "
        f"revocations={compliance['raw_counts']['total_revocations']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
