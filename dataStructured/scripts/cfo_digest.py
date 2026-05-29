#!/usr/bin/env python3
"""CFO Daily Digest — pulls Stripe data, computes financial KPIs,
runs anomaly detection, proposes pricing experiments, writes state,
and routes the headline + anomalies to Telegram.

Designed to run once daily via scheduler.
Can also be invoked manually: python scripts/cfo_digest.py
"""

import json
import os
import sys
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import stripe

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = PROJECT_ROOT / "state"
DIGEST_DIR = STATE_DIR / "cfo-digest"
PRODUCTS_DIR = STATE_DIR / "products"

DIGEST_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
# "Making Cheddar" group is the financial channel; fall back to founder DM
MAKING_CHEDDAR_CHAT_ID = "-1003850599483"
FOUNDER_DM_CHAT_ID = "1366707521"


def send_telegram(message: str, chat_id: str | None = None) -> bool:
    """Send a message to Telegram. Returns True on success."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("[WARN] TELEGRAM_BOT_TOKEN not set — skipping Telegram", file=sys.stderr)
        return False

    target = chat_id or MAKING_CHEDDAR_CHAT_ID
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": target,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=15)
        if resp.status_code == 200 and resp.json().get("ok"):
            print(f"[OK] Telegram message sent to {target}")
            return True
        else:
            # Retry with founder DM on group failure
            if target != FOUNDER_DM_CHAT_ID:
                print(f"[WARN] Telegram group send failed ({resp.status_code}), retrying with founder DM")
                return send_telegram(message, chat_id=FOUNDER_DM_CHAT_ID)
            print(f"[ERROR] Telegram send failed: {resp.status_code} — {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[ERROR] Telegram send error: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.rename(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cents_to_dollars(cents: int) -> float:
    return round(cents / 100, 2)


# ---------------------------------------------------------------------------
# Stripe data pull
# ---------------------------------------------------------------------------
def get_active_subscriptions() -> list[dict]:
    """Fetch all active subscriptions with expanded price/product info."""
    subs = []
    try:
        for sub in stripe.Subscription.list(
            status="active",
            limit=100,
            expand=["data.items.data.price"],
        ).auto_paging_iter():
            subs.append(sub)
    except stripe.error.StripeError as e:
        print(f"[ERROR] Subscription.list failed: {e}", file=sys.stderr)
    return subs


def compute_mrr(subscriptions: list[dict]) -> float:
    """Compute MRR from active subscriptions."""
    mrr_cents = 0
    for sub in subscriptions:
        for item in sub["items"]["data"]:
            price = item["price"]
            amount = price.get("unit_amount", 0) or 0
            interval = price.get("recurring", {}).get("interval", "month")
            interval_count = price.get("recurring", {}).get("interval_count", 1)

            if interval == "month":
                mrr_cents += amount / interval_count
            elif interval == "year":
                mrr_cents += amount / (12 * interval_count)
            elif interval == "week":
                mrr_cents += amount * (52 / 12) / interval_count
            elif interval == "day":
                mrr_cents += amount * (365 / 12) / interval_count

    return cents_to_dollars(int(mrr_cents))


def get_charges_in_range(start_ts: int, end_ts: int) -> list:
    """Fetch succeeded charges in a time range."""
    charges = []
    try:
        for charge in stripe.Charge.list(
            created={"gte": start_ts, "lt": end_ts},
            limit=100,
        ).auto_paging_iter():
            if charge.status == "succeeded":
                charges.append(charge)
    except stripe.error.StripeError as e:
        print(f"[ERROR] Charge.list failed: {e}", file=sys.stderr)
    return charges


def get_refunds_in_range(start_ts: int, end_ts: int) -> list:
    """Fetch refunds in a time range."""
    refunds = []
    try:
        for refund in stripe.Refund.list(
            created={"gte": start_ts, "lt": end_ts},
            limit=100,
        ).auto_paging_iter():
            refunds.append(refund)
    except stripe.error.StripeError as e:
        print(f"[ERROR] Refund.list failed: {e}", file=sys.stderr)
    return refunds


def get_churned_subscriptions_in_range(start_ts: int, end_ts: int) -> list:
    """Fetch subscriptions that were canceled in a time range."""
    churned = []
    try:
        for sub in stripe.Subscription.list(
            status="canceled",
            limit=100,
            created={"gte": start_ts - 365 * 86400},  # subscriptions created within the last year
        ).auto_paging_iter():
            # Check if canceled_at falls within our range
            canceled_at = sub.get("canceled_at")
            if canceled_at and start_ts <= canceled_at < end_ts:
                churned.append(sub)
    except stripe.error.StripeError as e:
        print(f"[ERROR] Subscription.list (canceled) failed: {e}", file=sys.stderr)
    return churned


def sum_charge_revenue(charges: list) -> float:
    """Sum revenue from charges in dollars."""
    total = sum(c.get("amount", 0) for c in charges)
    return cents_to_dollars(total)


def sum_refund_amount(refunds: list) -> float:
    """Sum refund amounts in dollars."""
    total = sum(r.get("amount", 0) for r in refunds)
    return cents_to_dollars(total)


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------
def load_recent_digests(days: int = 7) -> list[dict]:
    """Load the last N days of digest data for trend analysis."""
    digests = []
    today = datetime.now(timezone.utc).date()
    for i in range(1, days + 1):
        d = today - timedelta(days=i)
        path = DIGEST_DIR / f"{d.isoformat()}.json"
        data = load_json(path)
        if data:
            digests.append(data)
    return digests


def detect_anomalies(digest: dict, history: list[dict]) -> list[dict]:
    """Run anomaly checks against historical data. Returns list of anomaly dicts."""
    anomalies = []

    # 1. Refund spike — refund rate > 10% in 30d window
    if digest["refund_rate_30d"] > 10.0:
        anomalies.append({
            "type": "refund_spike",
            "severity": "high",
            "message": f"30-day refund rate at {digest['refund_rate_30d']:.1f}% (threshold: 10%)",
        })

    # 2. Any refund today when historically none
    if digest["refunds_today"] > 0:
        historical_refunds = [h.get("refunds_today", 0) for h in history]
        if all(r == 0 for r in historical_refunds):
            anomalies.append({
                "type": "first_refund",
                "severity": "medium",
                "message": f"First refund detected: ${digest['refunds_today']:.2f} today (no prior refunds in last {len(history)} days)",
            })

    # 3. Revenue drop — today's revenue dropped > 50% vs 7-day average
    if history:
        avg_daily = statistics.mean([h.get("one_time_revenue_today", 0) for h in history])
        if avg_daily > 0 and digest["one_time_revenue_today"] < avg_daily * 0.5:
            anomalies.append({
                "type": "revenue_drop",
                "severity": "medium",
                "message": f"Today's revenue ${digest['one_time_revenue_today']:.2f} is >{50}% below 7-day avg ${avg_daily:.2f}",
            })

    # 4. Revenue spike — today's revenue > 2x the 7-day average (positive anomaly)
    if history:
        avg_daily = statistics.mean([h.get("one_time_revenue_today", 0) for h in history])
        if avg_daily > 0 and digest["one_time_revenue_today"] > avg_daily * 2:
            anomalies.append({
                "type": "revenue_spike",
                "severity": "info",
                "message": f"Revenue spike: ${digest['one_time_revenue_today']:.2f} today is >2x the 7-day avg ${avg_daily:.2f}",
            })

    # 5. Churn alert — any churn when we have active subscriptions
    if digest["churn_rate_7d"] > 0:
        anomalies.append({
            "type": "churn_detected",
            "severity": "high",
            "message": f"7-day churn rate: {digest['churn_rate_7d']:.1f}% — {digest.get('churned_7d', 0)} subscription(s) canceled",
        })

    # 6. MRR change — MRR differs from yesterday
    if history:
        yesterday_mrr = history[0].get("mrr", 0)
        if yesterday_mrr != digest["mrr"]:
            direction = "up" if digest["mrr"] > yesterday_mrr else "down"
            delta = abs(digest["mrr"] - yesterday_mrr)
            severity = "info" if direction == "up" else "medium"
            anomalies.append({
                "type": f"mrr_{direction}",
                "severity": severity,
                "message": f"MRR moved {direction}: ${yesterday_mrr:.2f} -> ${digest['mrr']:.2f} (delta: ${delta:.2f})",
            })

    return anomalies


# ---------------------------------------------------------------------------
# Pricing experiments
# ---------------------------------------------------------------------------
def propose_pricing_experiments(digest: dict, history: list[dict]) -> list[dict]:
    """Propose pricing experiments based on observed patterns."""
    proposals = []
    product_count = len(list(PRODUCTS_DIR.iterdir())) if PRODUCTS_DIR.exists() else 0

    # 1. Zero-revenue for extended period with products live
    if product_count > 0 and digest["one_time_revenue_30d"] == 0 and digest["mrr"] == 0:
        days_zero = 0
        for h in history:
            if h.get("one_time_revenue_today", 0) == 0 and h.get("mrr", 0) == 0:
                days_zero += 1
            else:
                break

        if days_zero >= 5:
            proposals.append({
                "experiment": "bundle_discount_test",
                "rationale": f"{days_zero + 1}+ consecutive days of $0 revenue across {product_count} products. Consider: (a) 3-product bundle at 20% savings, (b) free sample rows on landing page, (c) limited-time 'launch week' pricing on newest 3 products.",
                "priority": "high",
            })

        if days_zero >= 3:
            proposals.append({
                "experiment": "distribution_channel_audit",
                "rationale": f"{days_zero + 1}+ days at $0. Verify distribution channels are actually driving traffic — check Stripe payment link click-through, Reddit/X post impressions, and whether links are reachable.",
                "priority": "high",
            })

    # 2. High refund rate — price-value mismatch signal
    if digest["refund_rate_30d"] > 5.0:
        proposals.append({
            "experiment": "value_audit",
            "rationale": f"Refund rate {digest['refund_rate_30d']:.1f}% suggests price-value mismatch. Review: data quality, preview availability, product descriptions accuracy.",
            "priority": "medium",
        })

    # 3. Revenue with zero subscriptions — upsell opportunity
    if digest["one_time_revenue_30d"] > 0 and digest["active_subscriptions"] == 0:
        proposals.append({
            "experiment": "subscription_conversion",
            "rationale": f"${digest['one_time_revenue_30d']:.2f} in one-time sales but 0 subscriptions. Consider post-purchase email offering quarterly subscription at 30% less per refresh vs. one-time re-purchase.",
            "priority": "medium",
        })

    return proposals


# ---------------------------------------------------------------------------
# Digest builder
# ---------------------------------------------------------------------------
def build_digest() -> dict:
    """Pull all Stripe data and build the daily digest."""
    now = datetime.now(timezone.utc)
    today = now.date()

    # Time boundaries
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    today_start_ts = int(today_start.timestamp())
    now_ts = int(now.timestamp())

    thirty_days_ago_ts = int((now - timedelta(days=30)).timestamp())
    seven_days_ago_ts = int((now - timedelta(days=7)).timestamp())

    print(f"[INFO] Building digest for {today.isoformat()}")
    print(f"[INFO] Time range: today={today_start.isoformat()} | 30d={datetime.fromtimestamp(thirty_days_ago_ts, tz=timezone.utc).isoformat()}")

    # --- Active subscriptions + MRR ---
    print("[INFO] Fetching active subscriptions...")
    active_subs = get_active_subscriptions()
    mrr = compute_mrr(active_subs)
    print(f"[INFO] Active subscriptions: {len(active_subs)} | MRR: ${mrr:.2f}")

    # --- Today's charges ---
    print("[INFO] Fetching today's charges...")
    today_charges = get_charges_in_range(today_start_ts, now_ts)
    today_revenue = sum_charge_revenue(today_charges)
    print(f"[INFO] Today's charges: {len(today_charges)} | Revenue: ${today_revenue:.2f}")

    # --- 30-day charges ---
    print("[INFO] Fetching 30-day charges...")
    charges_30d = get_charges_in_range(thirty_days_ago_ts, now_ts)
    revenue_30d = sum_charge_revenue(charges_30d)
    print(f"[INFO] 30-day charges: {len(charges_30d)} | Revenue: ${revenue_30d:.2f}")

    # --- Today's refunds ---
    print("[INFO] Fetching today's refunds...")
    today_refunds = get_refunds_in_range(today_start_ts, now_ts)
    refund_today = sum_refund_amount(today_refunds)
    print(f"[INFO] Today's refunds: {len(today_refunds)} | Amount: ${refund_today:.2f}")

    # --- 30-day refunds ---
    print("[INFO] Fetching 30-day refunds...")
    refunds_30d = get_refunds_in_range(thirty_days_ago_ts, now_ts)
    refund_30d = sum_refund_amount(refunds_30d)
    refund_rate_30d = (refund_30d / revenue_30d * 100) if revenue_30d > 0 else 0.0
    print(f"[INFO] 30-day refunds: {len(refunds_30d)} | Amount: ${refund_30d:.2f} | Rate: {refund_rate_30d:.1f}%")

    # --- 7-day churn ---
    print("[INFO] Fetching 7-day churn...")
    churned_7d = get_churned_subscriptions_in_range(seven_days_ago_ts, now_ts)
    total_subs_base = len(active_subs) + len(churned_7d)
    churn_rate_7d = (len(churned_7d) / total_subs_base * 100) if total_subs_base > 0 else 0.0
    print(f"[INFO] Churned (7d): {len(churned_7d)} | Churn rate: {churn_rate_7d:.1f}%")

    # --- Build digest dict ---
    digest = {
        "date": today.isoformat(),
        "generated_at": now.isoformat(),
        "mrr": mrr,
        "active_subscriptions": len(active_subs),
        "one_time_revenue_today": today_revenue,
        "one_time_revenue_30d": revenue_30d,
        "refunds_today": refund_today,
        "refunds_30d": refund_30d,
        "refund_rate_30d": round(refund_rate_30d, 2),
        "churn_rate_7d": round(churn_rate_7d, 2),
        "churned_7d": len(churned_7d),
        "total_charges_today": len(today_charges),
        "total_charges_30d": len(charges_30d),
        "total_refunds_today": len(today_refunds),
        "total_refunds_30d": len(refunds_30d),
    }

    # --- Anomaly detection ---
    print("[INFO] Running anomaly detection...")
    history = load_recent_digests(7)
    anomalies = detect_anomalies(digest, history)
    digest["anomalies"] = anomalies
    if anomalies:
        for a in anomalies:
            print(f"[ANOMALY] [{a['severity'].upper()}] {a['message']}")
    else:
        print("[INFO] No anomalies detected")

    # --- Pricing experiments ---
    print("[INFO] Evaluating pricing experiments...")
    experiments = propose_pricing_experiments(digest, history)
    digest["pricing_experiments_proposed"] = experiments
    if experiments:
        for exp in experiments:
            print(f"[EXPERIMENT] [{exp['priority'].upper()}] {exp['experiment']}: {exp['rationale'][:80]}...")
    else:
        print("[INFO] No pricing experiments proposed")

    return digest


# ---------------------------------------------------------------------------
# Telegram message formatter
# ---------------------------------------------------------------------------
def format_telegram_message(digest: dict) -> str:
    """Format the digest as a concise Telegram message."""
    date = digest["date"]
    anomaly_count = len(digest.get("anomalies", []))
    experiment_count = len(digest.get("pricing_experiments_proposed", []))

    lines = [
        f"*CFO Daily Digest -- {date}*",
        "",
        f"MRR: ${digest['mrr']:.2f}  |  Subs: {digest['active_subscriptions']}",
        f"Revenue today: ${digest['one_time_revenue_today']:.2f}  |  30d: ${digest['one_time_revenue_30d']:.2f}",
        f"Refunds today: ${digest['refunds_today']:.2f}  |  30d: ${digest['refunds_30d']:.2f}  ({digest['refund_rate_30d']:.1f}%)",
        f"Churn (7d): {digest['churn_rate_7d']:.1f}%",
    ]

    if anomaly_count > 0:
        lines.append("")
        lines.append(f"*Anomalies ({anomaly_count}):*")
        for a in digest["anomalies"]:
            icon = {"high": "🔴", "medium": "🟡", "info": "🔵"}.get(a["severity"], "⚪")
            lines.append(f"  {icon} {a['message']}")

    if experiment_count > 0:
        lines.append("")
        lines.append(f"*Pricing Experiments ({experiment_count}):*")
        for exp in digest["pricing_experiments_proposed"]:
            lines.append(f"  - {exp['experiment']}: {exp['rationale'][:120]}")

    if anomaly_count == 0 and experiment_count == 0:
        lines.append("")
        lines.append("No anomalies. No experiments proposed.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("CFO DAILY DIGEST")
    print(f"Started: {now_iso()}")
    print("=" * 60)

    # Init Stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET") or os.environ.get("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        print("[FATAL] STRIPE_SECRET / STRIPE_SECRET_KEY not set", file=sys.stderr)
        sys.exit(1)

    try:
        digest = build_digest()
    except Exception as e:
        print(f"\n[FATAL] Digest build failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # --- Write state ---
    today = digest["date"]
    output_path = DIGEST_DIR / f"{today}.json"
    save_json(output_path, digest)
    print(f"\n[OK] Digest written to {output_path}")

    # --- Send to Telegram ---
    message = format_telegram_message(digest)
    anomaly_count = len(digest.get("anomalies", []))

    if anomaly_count > 0:
        # Anomalies: send to both Making Cheddar and founder DM
        print("[INFO] Anomalies detected — routing to Making Cheddar + founder DM")
        send_telegram(message, chat_id=MAKING_CHEDDAR_CHAT_ID)
        send_telegram(message, chat_id=FOUNDER_DM_CHAT_ID)
    else:
        # Clean digest: just Making Cheddar
        print("[INFO] Clean digest — routing to Making Cheddar")
        send_telegram(message, chat_id=MAKING_CHEDDAR_CHAT_ID)

    # --- Summary ---
    print("\n" + "=" * 60)
    print("DIGEST SUMMARY")
    print("=" * 60)
    print(f"  MRR:                     ${digest['mrr']:.2f}")
    print(f"  Active subscriptions:    {digest['active_subscriptions']}")
    print(f"  Revenue today:           ${digest['one_time_revenue_today']:.2f}")
    print(f"  Revenue 30d:             ${digest['one_time_revenue_30d']:.2f}")
    print(f"  Refunds today:           ${digest['refunds_today']:.2f}")
    print(f"  Refunds 30d:             ${digest['refunds_30d']:.2f}")
    print(f"  Refund rate 30d:         {digest['refund_rate_30d']:.1f}%")
    print(f"  Churn rate 7d:           {digest['churn_rate_7d']:.1f}%")
    print(f"  Anomalies:               {anomaly_count}")
    print(f"  Experiments proposed:     {len(digest.get('pricing_experiments_proposed', []))}")
    print(f"  State written:           {output_path}")
    print("=" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()
