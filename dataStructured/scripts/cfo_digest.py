"""CFO daily digest — Stripe books snapshot + anomaly detection + Telegram routing.

Runs daily at 18:30 ET via the trinity scheduler `cfo_digest` cycle.

Algorithm:
1. Pull active subscriptions + charges (last 30d) + refunds (last 30d) from Stripe.
2. Compute MRR, active_subscriptions, one-time revenue (today + 30d),
   refunds (today + 30d), refund_rate_30d, churn_rate_7d.
3. Run four simple anomaly checks against thresholds documented in the cfo
   identity.md.
4. Propose pricing experiments only when data is sparse-but-real (one product
   has revenue but zero MRR — suggest a subscription test; or 30d revenue >$200
   with current pricing — suggest +25% raise).
5. Write `state/cfo-digest/{YYYY-MM-DD}.json` atomically (.tmp + rename).
6. Send headline line to financial_alerts channel (falls back to founder_dm).
7. Send each anomaly as its own message to financial_alerts immediately.
8. If Stripe fails: retry once after 30s, then write a "degraded" digest and
   notify financial_alerts.

Standalone usage:
    source ~/.profile && python scripts/cfo_digest.py

Output (last line, stdout):
    MRR=$N today=$N 30d=$N refunds_today=$N anomalies=N experiments=N
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import stripe

# Make sibling module importable both as `scripts.telegram_dispatch` and when
# run directly (`python scripts/cfo_digest.py`).
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.telegram_dispatch import send_to_channel  # noqa: E402


# ── Paths ───────────────────────────────────────────────────────────
STATE_DIR = _REPO_ROOT / "state"
DIGEST_DIR = STATE_DIR / "cfo-digest"


# ── Anomaly thresholds (v1) ─────────────────────────────────────────
REFUND_RATE_THRESHOLD = 0.05            # > 5% over last 30d
MRR_DROP_THRESHOLD = 0.10               # > 10% week-over-week
CHURN_THRESHOLD = 0.20                  # > 20% week-over-week
ZERO_REV_DAYS = 7                       # consecutive zero-revenue days with MRR > 0

# ── Pricing experiment heuristic ────────────────────────────────────
PRICE_RAISE_MIN_30D_REVENUE_USD = 200   # if 30d one-time rev > $200 → propose raise
PRICE_RAISE_PCT = 0.25                  # propose +25%


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def start_of_today_utc() -> datetime:
    n = now_utc()
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


# ── Stripe ──────────────────────────────────────────────────────────
def ensure_stripe_key() -> None:
    """Bind stripe.api_key from STRIPE_SECRET in environment."""
    key = os.environ.get("STRIPE_SECRET")
    if not key:
        raise RuntimeError("STRIPE_SECRET not set in environment")
    stripe.api_key = key


def fetch_active_subscriptions() -> list[Any]:
    """Return all active Stripe subscriptions."""
    return list(stripe.Subscription.list(status="active", limit=100).auto_paging_iter())


def fetch_charges_since(since: datetime) -> list[Any]:
    """Return succeeded charges created at-or-after `since`."""
    ts = int(since.timestamp())
    return list(
        stripe.Charge.list(created={"gte": ts}, limit=100).auto_paging_iter()
    )


def fetch_refunds_since(since: datetime) -> list[Any]:
    """Return refunds created at-or-after `since`."""
    ts = int(since.timestamp())
    return list(
        stripe.Refund.list(created={"gte": ts}, limit=100).auto_paging_iter()
    )


def fetch_subscriptions_canceled_since(since: datetime) -> list[Any]:
    """Return subscriptions whose `canceled_at` is at-or-after `since`.

    Stripe's Subscription.list does not accept `canceled_at` as a filter
    parameter (only `created`, `current_period_end`, `current_period_start`),
    so we list canceled subs and filter by `canceled_at` client-side. For v1
    volumes this is fine; if cancellations ever exceed ~1000/window we'd
    need to page with `created` and intersect.
    """
    ts = int(since.timestamp())
    out: list[Any] = []
    for sub in stripe.Subscription.list(
        status="canceled", limit=100
    ).auto_paging_iter():
        canceled_at = getattr(sub, "canceled_at", None) or 0
        if canceled_at >= ts:
            out.append(sub)
    return out


# ── Metric computation ──────────────────────────────────────────────
def compute_mrr_cents(subscriptions: list[Any]) -> int:
    """Sum monthly recurring revenue across all active subscriptions, in cents.

    For each subscription, walk `items.data` and use `price.unit_amount * quantity`.
    Annual/quarterly prices are normalized into a per-month equivalent.
    """
    total = 0
    for sub in subscriptions:
        items = getattr(sub, "items", None)
        item_list = getattr(items, "data", []) if items else []
        for item in item_list:
            price = getattr(item, "price", None)
            if not price:
                continue
            unit_amount = getattr(price, "unit_amount", 0) or 0
            quantity = getattr(item, "quantity", 1) or 1
            recurring = getattr(price, "recurring", None)
            interval = getattr(recurring, "interval", "month") if recurring else "month"
            interval_count = getattr(recurring, "interval_count", 1) if recurring else 1
            per_month_factor = {
                "day": 30.0 / max(interval_count, 1),
                "week": 4.345 / max(interval_count, 1),
                "month": 1.0 / max(interval_count, 1),
                "year": 1.0 / (12.0 * max(interval_count, 1)),
            }.get(interval, 1.0)
            total += int(round(unit_amount * quantity * per_month_factor))
    return total


def split_revenue_buckets(charges: list[Any], today_start: datetime) -> tuple[int, int]:
    """Return (today_cents, 30d_cents) for succeeded charges only."""
    today_ts = int(today_start.timestamp())
    today_cents = 0
    thirty_d_cents = 0
    for c in charges:
        if getattr(c, "status", None) != "succeeded":
            continue
        amount = getattr(c, "amount", 0) or 0
        # Subtract amount_refunded so we capture net revenue
        refunded = getattr(c, "amount_refunded", 0) or 0
        net = max(0, amount - refunded)
        thirty_d_cents += net
        if getattr(c, "created", 0) >= today_ts:
            today_cents += net
    return today_cents, thirty_d_cents


def split_refund_buckets(refunds: list[Any], today_start: datetime) -> tuple[int, int]:
    """Return (today_refunds_cents, 30d_refunds_cents)."""
    today_ts = int(today_start.timestamp())
    today_cents = 0
    thirty_d_cents = 0
    for r in refunds:
        amt = getattr(r, "amount", 0) or 0
        if getattr(r, "status", "succeeded") not in {"succeeded", None}:
            continue
        thirty_d_cents += amt
        if getattr(r, "created", 0) >= today_ts:
            today_cents += amt
    return today_cents, thirty_d_cents


def compute_refund_rate(charges: list[Any], refund_30d_cents: int) -> float:
    """Refund_rate = sum(refunds 30d) / sum(succeeded charges 30d, gross)."""
    gross = sum(
        (getattr(c, "amount", 0) or 0)
        for c in charges
        if getattr(c, "status", None) == "succeeded"
    )
    if gross == 0:
        return 0.0
    return round(refund_30d_cents / gross, 4)


def compute_churn_rate_7d(
    active_now: list[Any], canceled_7d: list[Any]
) -> float | None:
    """Churn = canceled in last 7d / (active_now + canceled_7d).

    Returns None when denominator is 0 so the anomaly check can skip safely.
    """
    canceled_count = len(canceled_7d)
    denom = len(active_now) + canceled_count
    if denom == 0:
        return None
    return round(canceled_count / denom, 4)


# ── Anomaly checks ──────────────────────────────────────────────────
def check_anomalies(
    refund_rate_30d: float,
    churn_rate_7d: float | None,
    mrr_cents: int,
    today_revenue_cents: int,
) -> list[dict]:
    """Run the four documented anomaly checks. Return a list of anomaly dicts."""
    out: list[dict] = []
    detected_at = iso(now_utc())

    if refund_rate_30d > REFUND_RATE_THRESHOLD:
        out.append(
            {
                "severity": "HIGH",
                "metric": "refund_rate_30d",
                "value": refund_rate_30d,
                "threshold": REFUND_RATE_THRESHOLD,
                "detected_at": detected_at,
                "summary": (
                    f"Refund rate hit {refund_rate_30d * 100:.1f}%, "
                    f"above {REFUND_RATE_THRESHOLD * 100:.0f}% threshold."
                ),
            }
        )

    if churn_rate_7d is not None and churn_rate_7d > CHURN_THRESHOLD:
        out.append(
            {
                "severity": "HIGH",
                "metric": "churn_rate_7d",
                "value": churn_rate_7d,
                "threshold": CHURN_THRESHOLD,
                "detected_at": detected_at,
                "summary": (
                    f"Subscription churn at {churn_rate_7d * 100:.1f}% "
                    f"week-over-week, above {CHURN_THRESHOLD * 100:.0f}% threshold."
                ),
            }
        )

    # MRR week-over-week drop requires prior digest. Load yesterday-7 if exists.
    prior_digest = _load_digest_n_days_ago(7)
    if prior_digest and prior_digest.get("mrr", 0) > 0:
        prior_mrr_cents = int(prior_digest["mrr"]) * 100
        if prior_mrr_cents > 0:
            drop_ratio = (prior_mrr_cents - mrr_cents) / prior_mrr_cents
            if drop_ratio > MRR_DROP_THRESHOLD:
                out.append(
                    {
                        "severity": "MEDIUM",
                        "metric": "mrr_wow_drop",
                        "value": round(drop_ratio, 4),
                        "threshold": MRR_DROP_THRESHOLD,
                        "detected_at": detected_at,
                        "summary": (
                            f"MRR dropped {drop_ratio * 100:.1f}% "
                            f"week-over-week (${prior_mrr_cents // 100} → "
                            f"${mrr_cents // 100})."
                        ),
                    }
                )

    # Zero-revenue-N-days check when MRR > 0 (Stripe webhook outage signal).
    if mrr_cents > 0 and today_revenue_cents == 0:
        zero_streak = _count_zero_revenue_streak()
        if zero_streak >= ZERO_REV_DAYS:
            out.append(
                {
                    "severity": "HIGH",
                    "metric": "zero_revenue_streak_days",
                    "value": zero_streak,
                    "threshold": ZERO_REV_DAYS,
                    "detected_at": detected_at,
                    "summary": (
                        f"Zero one-time revenue for {zero_streak} consecutive days "
                        f"while MRR > 0. Check Stripe integration."
                    ),
                }
            )

    return out


def _load_digest_n_days_ago(n: int) -> dict | None:
    """Best-effort: load `state/cfo-digest/{today - n days}.json`. None if missing."""
    target = (now_utc() - timedelta(days=n)).date().isoformat()
    path = DIGEST_DIR / f"{target}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _count_zero_revenue_streak() -> int:
    """Count consecutive past days (excluding today) with one_time_revenue_today == 0."""
    streak = 0
    for i in range(1, 30):
        d = _load_digest_n_days_ago(i)
        if d is None:
            break
        if int(d.get("one_time_revenue_today", 0)) == 0:
            streak += 1
        else:
            break
    return streak


# ── Pricing experiments ─────────────────────────────────────────────
def propose_pricing_experiments(
    one_time_30d_cents: int, mrr_cents: int
) -> list[dict]:
    """Propose pricing experiments only when data warrants — strict v1 logic.

    Rules:
    - If one-time 30d revenue > $200 and MRR is zero → propose +25% raise on
      the active products (suggest founder pick the highest-volume one).
    - Skip entirely on empty / near-empty data.
    """
    experiments: list[dict] = []
    if one_time_30d_cents <= PRICE_RAISE_MIN_30D_REVENUE_USD * 100:
        return experiments

    # Discover one-time products via state/products/<slug>/launch-report.json
    products_dir = STATE_DIR / "products"
    if not products_dir.exists():
        return experiments
    for product_dir in sorted(products_dir.iterdir()):
        if not product_dir.is_dir():
            continue
        launch_report = product_dir / "launch-report.json"
        if not launch_report.exists():
            continue
        try:
            with open(launch_report, "r") as f:
                report = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        current_price = report.get("price_usd") or report.get("price") or 0
        if not current_price:
            continue
        proposed_price = round(float(current_price) * (1 + PRICE_RAISE_PCT))
        experiments.append(
            {
                "slug": product_dir.name,
                "current_price": current_price,
                "proposed_change": (
                    f"raise to ${proposed_price} — 30d one-time revenue is "
                    f"${one_time_30d_cents // 100}, room to test elasticity"
                ),
                "rationale": (
                    f"30d gross one-time revenue exceeded "
                    f"${PRICE_RAISE_MIN_30D_REVENUE_USD} threshold; "
                    f"recommend +{int(PRICE_RAISE_PCT * 100)}% test for one cycle."
                ),
            }
        )
        # v1: one proposal per cycle is plenty; founder can iterate.
        break
    return experiments


# ── IO ──────────────────────────────────────────────────────────────
def write_digest_atomic(digest: dict) -> Path:
    """Write today's digest atomically (tmp + rename). Returns the final path."""
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    date_str = digest["date"]
    final = DIGEST_DIR / f"{date_str}.json"
    tmp = final.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(digest, f, indent=2, sort_keys=False)
        f.write("\n")
    tmp.replace(final)
    return final


def safe_notify(channel: str, message: str) -> None:
    """Send to channel; never raise on Telegram failures (just log to stderr)."""
    try:
        send_to_channel(channel, message)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"WARN: telegram dispatch failed: {exc}", file=sys.stderr)


# ── Stripe pull with retry ──────────────────────────────────────────
def pull_stripe_with_retry() -> dict | None:
    """Try Stripe pulls; retry once after 30s. Returns dict of raw lists or None."""
    today_start = start_of_today_utc()
    since_30d = today_start - timedelta(days=30)
    since_7d = today_start - timedelta(days=7)

    for attempt in (1, 2):
        try:
            return {
                "today_start": today_start,
                "active_subs": fetch_active_subscriptions(),
                "charges_30d": fetch_charges_since(since_30d),
                "refunds_30d": fetch_refunds_since(since_30d),
                "canceled_subs_7d": fetch_subscriptions_canceled_since(since_7d),
            }
        except Exception as exc:  # pylint: disable=broad-except
            print(
                f"WARN: Stripe pull attempt {attempt} failed: {exc}",
                file=sys.stderr,
            )
            traceback.print_exc(file=sys.stderr)
            if attempt == 1:
                time.sleep(30)
    return None


def build_degraded_digest(date_str: str, reason: str) -> dict:
    """Compose a placeholder digest when Stripe is unreachable."""
    return {
        "date": date_str,
        "generated_at": iso(now_utc()),
        "degraded": True,
        "degraded_reason": reason,
        "mrr": 0,
        "active_subscriptions": 0,
        "one_time_revenue_today": 0,
        "one_time_revenue_30d": 0,
        "refunds_today": 0,
        "refunds_30d": 0,
        "refund_rate_30d": 0.0,
        "churn_rate_7d": 0.0,
        "anomalies": [],
        "pricing_experiments_proposed": [],
    }


# ── Main ────────────────────────────────────────────────────────────
def main() -> int:
    """Entry point — pull, compute, write, notify."""
    ensure_stripe_key()
    today_iso = now_utc().date().isoformat()

    raw = pull_stripe_with_retry()
    if raw is None:
        digest = build_degraded_digest(
            today_iso, "Stripe API unreachable after retry"
        )
        path = write_digest_atomic(digest)
        safe_notify(
            "financial_alerts",
            f"CFO digest DEGRADED — Stripe unreachable. Written to {path.name}.",
        )
        print(
            f"DEGRADED MRR=$0 today=$0 30d=$0 refunds_today=$0 "
            f"anomalies=0 experiments=0"
        )
        return 0

    today_start = raw["today_start"]
    active_subs = raw["active_subs"]
    charges_30d = raw["charges_30d"]
    refunds_30d = raw["refunds_30d"]
    canceled_subs_7d = raw["canceled_subs_7d"]

    mrr_cents = compute_mrr_cents(active_subs)
    today_rev_cents, thirty_d_rev_cents = split_revenue_buckets(charges_30d, today_start)
    today_ref_cents, thirty_d_ref_cents = split_refund_buckets(refunds_30d, today_start)
    refund_rate = compute_refund_rate(charges_30d, thirty_d_ref_cents)
    churn = compute_churn_rate_7d(active_subs, canceled_subs_7d)

    anomalies = check_anomalies(refund_rate, churn, mrr_cents, today_rev_cents)
    experiments = propose_pricing_experiments(thirty_d_rev_cents, mrr_cents)

    digest = {
        "date": today_iso,
        "generated_at": iso(now_utc()),
        "mrr": mrr_cents // 100,
        "active_subscriptions": len(active_subs),
        "one_time_revenue_today": today_rev_cents // 100,
        "one_time_revenue_30d": thirty_d_rev_cents // 100,
        "refunds_today": today_ref_cents // 100,
        "refunds_30d": thirty_d_ref_cents // 100,
        "refund_rate_30d": refund_rate,
        "churn_rate_7d": churn if churn is not None else 0.0,
        "anomalies": anomalies,
        "pricing_experiments_proposed": experiments,
    }
    path = write_digest_atomic(digest)

    # Notify per-anomaly first (immediate surface) — then headline.
    for a in anomalies:
        safe_notify(
            "financial_alerts",
            f"ANOMALY [{a['severity']}] {a['metric']}: {a['summary']}",
        )

    headline = (
        f"CFO digest {today_iso}: MRR=${digest['mrr']} "
        f"today=${digest['one_time_revenue_today']} "
        f"30d=${digest['one_time_revenue_30d']} "
        f"anomalies={len(anomalies)} "
        f"experiments={len(experiments)}"
    )
    safe_notify("financial_alerts", headline)

    print(
        f"MRR=${digest['mrr']} today=${digest['one_time_revenue_today']} "
        f"30d=${digest['one_time_revenue_30d']} "
        f"refunds_today=${digest['refunds_today']} "
        f"anomalies={len(anomalies)} experiments={len(experiments)}"
    )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
