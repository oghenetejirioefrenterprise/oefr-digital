#!/usr/bin/env python3
"""Customer sweep: polls Stripe for new purchases/subscriptions,
sends welcome emails, day-3 check-ins, and subscription refresh emails.

Designed to run every 2 hours via the Trinity scheduler's customer_sweep cycle.
Can also be invoked manually: python scripts/customer_sweep.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import stripe

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure the project root is importable even when this file is run directly as
# `python scripts/customer_sweep.py` (sys.path[0] would otherwise be scripts/,
# making `import scripts.email_sender` fail). `python -m scripts.customer_sweep`
# already puts the root on the path; this makes the documented direct
# invocation work too.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

STATE_DIR = PROJECT_ROOT / "state"
CUSTOMERS_DIR = STATE_DIR / "customers"
CURSOR_FILE = STATE_DIR / "stripe-poll-cursor.json"
PRODUCTS_DIR = STATE_DIR / "products"
REFRESH_LOG_DIR = STATE_DIR / "subscription-refresh-log"

# Ensure directories exist
CUSTOMERS_DIR.mkdir(parents=True, exist_ok=True)
REFRESH_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------
SIGNATURE = (
    "\n\n---\n"
    "DataStructured\n"
    "Curated public data, delivered as products.\n"
    "https://oefr-digital.vercel.app\n"
)


def _product_display_name(slug: str) -> str:
    """Convert slug to human-readable product name."""
    return slug.replace("-", " ").replace("2026 05", "(May 2026)").title()


def welcome_onetime_email(product_name: str, download_url: str) -> tuple[str, str]:
    """Return (subject, body) for one-time purchase welcome."""
    subject = f"Your DataStructured purchase -- {product_name}"
    body = (
        f"Thanks for purchasing {product_name} from DataStructured.\n\n"
        f"Download your data here:\n{download_url}\n\n"
        "If you have any questions or need help with the data, just reply to this email.\n"
        f"{SIGNATURE}"
    )
    return subject, body


def welcome_subscription_email(product_name: str, download_url: str) -> tuple[str, str]:
    """Return (subject, body) for subscription welcome."""
    subject = f"Welcome to DataStructured -- {product_name} subscription"
    body = (
        f"Thanks for subscribing to {product_name} on DataStructured.\n\n"
        f"Download your first data drop here:\n{download_url}\n\n"
        "Your next refresh arrives approximately quarterly. "
        "We'll email you with a fresh download link each time.\n\n"
        "Questions? Just reply to this email.\n"
        f"{SIGNATURE}"
    )
    return subject, body


def day3_checkin_email(product_name: str) -> tuple[str, str]:
    """Return (subject, body) for day-3 check-in."""
    subject = f"Quick check-in -- anything broken with {product_name}?"
    body = (
        f"Hey -- just checking in on your {product_name} purchase.\n\n"
        "Three quick questions:\n"
        "1. Were you able to open and use the data?\n"
        "2. Was it what you expected?\n"
        "3. Anything that would make it more useful for you?\n\n"
        "No upsell, just want to make sure it works.\n"
        f"{SIGNATURE}"
    )
    return subject, body


def refresh_email(product_name: str, quarter: str, gist_url: str, notes: str) -> tuple[str, str]:
    """Return (subject, body) for subscription refresh."""
    subject = f"Fresh data -- {product_name} ({quarter})"
    body = (
        f"Your {quarter} refresh for {product_name} is ready.\n\n"
        f"Download here:\n{gist_url}\n\n"
    )
    if notes:
        body += f"What changed since last quarter: {notes}\n\n"
    body += f"Questions? Reply to this email.\n{SIGNATURE}"
    return subject, body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def email_safe(email: str) -> str:
    """Convert email to filesystem-safe filename."""
    return email.replace("@", "_at_").replace("+", "_plus_")


def load_json(path: Path) -> dict:
    """Load JSON from path, return empty dict if missing."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    """Atomically write JSON to path."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.rename(path)


def now_iso() -> str:
    """Current UTC timestamp as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def build_product_map() -> dict[str, dict]:
    """Build stripe_product_id -> {slug, download_url, has_subscription} map from launch reports."""
    product_map = {}
    for product_dir in PRODUCTS_DIR.iterdir():
        if not product_dir.is_dir():
            continue
        lr_path = product_dir / "launch-report.json"
        if not lr_path.exists():
            continue
        lr = load_json(lr_path)
        slug = lr.get("slug", product_dir.name)
        download_url = lr.get("asset_gist_url") or lr.get("asset_raw_url") or lr.get("stripe_payment_link_url") or ""

        stripe_pid = lr.get("stripe_product_id")
        if stripe_pid and stripe_pid != "None":
            product_map[stripe_pid] = {
                "slug": slug,
                "download_url": download_url,
                "display_name": _product_display_name(slug),
            }

        stripe_sub_pid = lr.get("stripe_subscription_product_id")
        if stripe_sub_pid and stripe_sub_pid != "NONE" and stripe_sub_pid != "None":
            product_map[stripe_sub_pid] = {
                "slug": slug,
                "download_url": download_url,
                "display_name": _product_display_name(slug),
                "is_subscription": True,
            }

    return product_map


def load_customer(email: str) -> dict:
    """Load or initialize a customer record."""
    path = CUSTOMERS_DIR / f"{email_safe(email)}.json"
    if path.exists():
        return load_json(path)
    return {
        "email": email,
        "first_purchase_at": None,
        "purchases": [],
        "subscriptions": [],
        "emails_sent": {
            "welcome": None,
            "day3": None,
        },
    }


def save_customer(customer: dict) -> None:
    """Save customer record."""
    path = CUSTOMERS_DIR / f"{email_safe(customer['email'])}.json"
    save_json(path, customer)


# ---------------------------------------------------------------------------
# Stripe polling
# ---------------------------------------------------------------------------
def poll_stripe(product_map: dict, cursor_ts: int) -> dict:
    """Poll Stripe for charges and subscriptions since cursor.

    Returns dict of stats: {new_customers, charges_found, subscriptions_found, skipped}.
    """
    stats = {"new_customers": 0, "charges_found": 0, "subscriptions_found": 0, "skipped": 0}

    # --- Poll charges ---
    try:
        charges = stripe.Charge.list(
            created={"gte": cursor_ts},
            limit=100,
            expand=["data.customer"],
        )
    except stripe.error.StripeError as e:
        print(f"[ERROR] Stripe Charge.list failed: {e}", file=sys.stderr)
        return stats

    for charge in charges.auto_paging_iter():
        if charge.status != "succeeded":
            continue
        stats["charges_found"] += 1

        # Extract email
        email = None
        if charge.billing_details and charge.billing_details.email:
            email = charge.billing_details.email.lower().strip()
        elif charge.customer and hasattr(charge.customer, "email") and charge.customer.email:
            email = charge.customer.email.lower().strip()
        elif isinstance(charge.customer, str):
            # Customer not expanded, try to fetch
            try:
                cust = stripe.Customer.retrieve(charge.customer)
                email = (cust.email or "").lower().strip()
            except Exception:
                pass

        if not email:
            print(f"[WARN] Charge {charge.id}: no email found, skipping")
            stats["skipped"] += 1
            continue

        # Determine product from payment intent -> line items or invoice
        product_id = None
        slug_info = None

        # Try via invoice line items
        if charge.invoice:
            invoice_id = charge.invoice if isinstance(charge.invoice, str) else charge.invoice.id
            try:
                invoice = stripe.Invoice.retrieve(invoice_id, expand=["lines.data"])
                for line in invoice.lines.data:
                    if line.price and line.price.product:
                        pid = line.price.product if isinstance(line.price.product, str) else line.price.product.id
                        if pid in product_map:
                            product_id = pid
                            slug_info = product_map[pid]
                            break
            except Exception as e:
                print(f"[WARN] Invoice fetch failed for charge {charge.id}: {e}")

        # Try via payment intent metadata or checkout session
        if not slug_info and charge.payment_intent:
            pi_id = charge.payment_intent if isinstance(charge.payment_intent, str) else charge.payment_intent.id
            try:
                sessions = stripe.checkout.Session.list(payment_intent=pi_id, limit=1)
                for session in sessions.data:
                    line_items = stripe.checkout.Session.list_line_items(session.id, limit=10)
                    for item in line_items.data:
                        if item.price and item.price.product:
                            pid = item.price.product if isinstance(item.price.product, str) else item.price.product.id
                            if pid in product_map:
                                product_id = pid
                                slug_info = product_map[pid]
                                break
                    if slug_info:
                        break
            except Exception as e:
                print(f"[WARN] Session lookup failed for charge {charge.id}: {e}")

        if not slug_info:
            print(f"[WARN] Charge {charge.id} for {email}: cannot map to product, skipping")
            stats["skipped"] += 1
            continue

        # Update customer record
        customer = load_customer(email)
        charge_ids = {p["stripe_charge_id"] for p in customer.get("purchases", [])}
        if charge.id not in charge_ids:
            customer["purchases"].append({
                "slug": slug_info["slug"],
                "type": "one_time",
                "stripe_charge_id": charge.id,
                "purchased_at": datetime.fromtimestamp(charge.created, tz=timezone.utc).isoformat(),
                "product_name": slug_info["display_name"],
                "download_url": slug_info["download_url"],
            })
            if not customer.get("first_purchase_at"):
                customer["first_purchase_at"] = datetime.fromtimestamp(charge.created, tz=timezone.utc).isoformat()
                stats["new_customers"] += 1

        save_customer(customer)

    # --- Poll subscriptions ---
    try:
        subscriptions = stripe.Subscription.list(
            created={"gte": cursor_ts},
            limit=100,
            status="all",
            expand=["data.items.data"],
        )
    except stripe.error.StripeError as e:
        print(f"[ERROR] Stripe Subscription.list failed: {e}", file=sys.stderr)
        return stats

    for sub in subscriptions.auto_paging_iter():
        stats["subscriptions_found"] += 1

        # Extract email
        email = None
        try:
            cust = stripe.Customer.retrieve(sub.customer if isinstance(sub.customer, str) else sub.customer.id)
            email = (cust.email or "").lower().strip()
        except Exception:
            pass

        if not email:
            print(f"[WARN] Subscription {sub.id}: no email, skipping")
            stats["skipped"] += 1
            continue

        # Determine product
        slug_info = None
        for item in sub["items"]["data"]:
            pid = item.price.product if isinstance(item.price.product, str) else item.price.product.id
            if pid in product_map:
                slug_info = product_map[pid]
                break

        if not slug_info:
            print(f"[WARN] Subscription {sub.id}: cannot map to product, skipping")
            stats["skipped"] += 1
            continue

        customer = load_customer(email)
        sub_ids = {s["stripe_subscription_id"] for s in customer.get("subscriptions", [])}
        if sub.id not in sub_ids:
            customer["subscriptions"].append({
                "slug": slug_info["slug"],
                "stripe_subscription_id": sub.id,
                "started_at": datetime.fromtimestamp(sub.created, tz=timezone.utc).isoformat(),
                "status": sub.status,
                "product_name": slug_info.get("display_name", slug_info["slug"]),
                "download_url": slug_info["download_url"],
            })
            if not customer.get("first_purchase_at"):
                customer["first_purchase_at"] = datetime.fromtimestamp(sub.created, tz=timezone.utc).isoformat()
                stats["new_customers"] += 1

        save_customer(customer)

    return stats


# ---------------------------------------------------------------------------
# Email dispatch
# ---------------------------------------------------------------------------
def send_welcome_emails() -> int:
    """Send welcome emails to customers who haven't received one. Returns count sent."""
    from scripts.email_sender import send_email

    sent = 0
    for f in CUSTOMERS_DIR.glob("*.json"):
        customer = load_json(f)
        if customer.get("emails_sent", {}).get("welcome"):
            continue  # Already sent

        email = customer.get("email")
        if not email:
            continue

        # Determine what to send based on most recent purchase/subscription
        purchases = customer.get("purchases", [])
        subscriptions = customer.get("subscriptions", [])

        if subscriptions:
            latest = subscriptions[-1]
            subject, body = welcome_subscription_email(
                latest.get("product_name", latest["slug"]),
                latest.get("download_url", ""),
            )
        elif purchases:
            latest = purchases[-1]
            subject, body = welcome_onetime_email(
                latest.get("product_name", latest["slug"]),
                latest.get("download_url", ""),
            )
        else:
            continue  # No purchases at all

        try:
            send_email(email, subject, body)
            customer.setdefault("emails_sent", {})["welcome"] = now_iso()
            save_customer(customer)
            sent += 1
            print(f"[OK] Welcome email sent to {email}")
        except Exception as e:
            print(f"[ERROR] Welcome email to {email} failed: {e}", file=sys.stderr)

    return sent


def send_day3_checkins() -> int:
    """Send day-3 check-in emails. Returns count sent."""
    from scripts.email_sender import send_email

    sent = 0
    now = datetime.now(timezone.utc)
    for f in CUSTOMERS_DIR.glob("*.json"):
        customer = load_json(f)
        if customer.get("emails_sent", {}).get("day3"):
            continue  # Already sent

        first_purchase = customer.get("first_purchase_at")
        if not first_purchase:
            continue

        purchase_dt = datetime.fromisoformat(first_purchase)
        hours_since = (now - purchase_dt).total_seconds() / 3600

        # Eligible between 72 and 96 hours after first purchase
        if not (72 <= hours_since <= 96):
            continue

        email = customer.get("email")
        if not email:
            continue

        purchases = customer.get("purchases", [])
        subscriptions = customer.get("subscriptions", [])
        if subscriptions:
            product_name = subscriptions[0].get("product_name", subscriptions[0]["slug"])
        elif purchases:
            product_name = purchases[0].get("product_name", purchases[0]["slug"])
        else:
            continue

        subject, body = day3_checkin_email(product_name)
        try:
            send_email(email, subject, body)
            customer.setdefault("emails_sent", {})["day3"] = now_iso()
            save_customer(customer)
            sent += 1
            print(f"[OK] Day-3 check-in sent to {email}")
        except Exception as e:
            print(f"[ERROR] Day-3 check-in to {email} failed: {e}", file=sys.stderr)

    return sent


def send_refresh_emails() -> int:
    """Send subscription refresh emails when refresh logs exist. Returns count sent."""
    from scripts.email_sender import send_email

    sent = 0
    for refresh_file in REFRESH_LOG_DIR.glob("*.json"):
        refresh = load_json(refresh_file)
        slug = refresh.get("slug")
        quarter = refresh.get("quarter")
        gist_url = refresh.get("gist_url", "")
        notes = refresh.get("notes", "")

        if not slug or not quarter:
            continue

        refresh_key = f"refresh_{quarter.replace('-', '_').replace('Q', 'Q')}"

        for cust_file in CUSTOMERS_DIR.glob("*.json"):
            customer = load_json(cust_file)
            email = customer.get("email")
            if not email:
                continue

            # Check for active subscription matching slug
            has_active_sub = any(
                s.get("slug") == slug and s.get("status") in ("active", "trialing")
                for s in customer.get("subscriptions", [])
            )
            if not has_active_sub:
                continue

            if customer.get("emails_sent", {}).get(refresh_key):
                continue  # Already notified

            product_name = _product_display_name(slug)
            subject, body = refresh_email(product_name, quarter, gist_url, notes)
            try:
                send_email(email, subject, body)
                customer.setdefault("emails_sent", {})[refresh_key] = now_iso()
                save_customer(customer)
                sent += 1
                print(f"[OK] Refresh email ({quarter}) sent to {email}")
            except Exception as e:
                print(f"[ERROR] Refresh email to {email} failed: {e}", file=sys.stderr)

    return sent


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------
def run_sweep() -> dict:
    """Execute the full customer sweep. Returns summary dict."""
    # Source env
    stripe.api_key = os.environ.get("STRIPE_SECRET") or os.environ.get("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        print("[FATAL] STRIPE_SECRET / STRIPE_SECRET_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Load cursor
    cursor_data = load_json(CURSOR_FILE)
    if cursor_data.get("last_polled_at"):
        cursor_dt = datetime.fromisoformat(cursor_data["last_polled_at"])
        cursor_ts = int(cursor_dt.timestamp())
    else:
        # First run: look back 90 days
        cursor_ts = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp())
        print(f"[INFO] First run -- looking back 90 days from {datetime.fromtimestamp(cursor_ts, tz=timezone.utc).isoformat()}")

    print(f"[INFO] Polling Stripe since {datetime.fromtimestamp(cursor_ts, tz=timezone.utc).isoformat()}")

    # Capture the cursor for the NEXT run BEFORE polling begins, with a small
    # overlap buffer. Stripe `created` timestamps and list visibility are not
    # perfectly monotonic, and the poll + three email phases take time; stamping
    # the cursor with now() only after all phases would skip any charge/sub
    # created during this run, permanently losing those paying-customer events.
    OVERLAP_BUFFER_SECONDS = 300  # 5 min
    next_cursor_dt = datetime.now(timezone.utc) - timedelta(seconds=OVERLAP_BUFFER_SECONDS)

    # Build product map
    product_map = build_product_map()
    print(f"[INFO] Product map: {len(product_map)} Stripe products mapped")

    # Phase 1: Poll Stripe
    poll_stats = poll_stripe(product_map, cursor_ts)
    print(f"[INFO] Stripe poll: {poll_stats['charges_found']} charges, "
          f"{poll_stats['subscriptions_found']} subscriptions, "
          f"{poll_stats['new_customers']} new customers, "
          f"{poll_stats['skipped']} skipped")

    # Phase 2: Send welcome emails
    welcome_sent = send_welcome_emails()

    # Phase 3: Send day-3 check-ins
    day3_sent = send_day3_checkins()

    # Phase 4: Send refresh emails
    refresh_sent = send_refresh_emails()

    # Advance cursor ONLY after all phases succeed. Use the timestamp captured
    # BEFORE polling (minus overlap buffer), not now(), so events created during
    # this run are re-scanned next time instead of being skipped.
    save_json(CURSOR_FILE, {"last_polled_at": next_cursor_dt.isoformat()})

    # Count total customers on file
    total_customers = len(list(CUSTOMERS_DIR.glob("*.json")))

    summary = {
        "timestamp": now_iso(),
        "cursor_advanced": True,
        "stripe_charges_found": poll_stats["charges_found"],
        "stripe_subscriptions_found": poll_stats["subscriptions_found"],
        "new_customers": poll_stats["new_customers"],
        "skipped": poll_stats["skipped"],
        "welcome_emails_sent": welcome_sent,
        "day3_checkins_sent": day3_sent,
        "refresh_emails_sent": refresh_sent,
        "total_emails_sent": welcome_sent + day3_sent + refresh_sent,
        "total_customers_on_file": total_customers,
        "errors": 0,
    }

    return summary


def main():
    print("=" * 60)
    print("CUSTOMER SWEEP")
    print(f"Started: {now_iso()}")
    print("=" * 60)

    try:
        summary = run_sweep()
    except Exception as e:
        print(f"\n[FATAL] Sweep failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SWEEP SUMMARY")
    print("=" * 60)
    print(f"  Stripe charges found:    {summary['stripe_charges_found']}")
    print(f"  Stripe subs found:       {summary['stripe_subscriptions_found']}")
    print(f"  New customers:           {summary['new_customers']}")
    print(f"  Skipped (unmapped):      {summary['skipped']}")
    print(f"  Welcome emails sent:     {summary['welcome_emails_sent']}")
    print(f"  Day-3 check-ins sent:    {summary['day3_checkins_sent']}")
    print(f"  Refresh emails sent:     {summary['refresh_emails_sent']}")
    print(f"  Total emails sent:       {summary['total_emails_sent']}")
    print(f"  Customers on file:       {summary['total_customers_on_file']}")
    print(f"  Errors:                  {summary['errors']}")
    print(f"  Cursor advanced:         {summary['cursor_advanced']}")
    print("=" * 60)

    # Exit 0 on success
    sys.exit(0)


if __name__ == "__main__":
    main()
