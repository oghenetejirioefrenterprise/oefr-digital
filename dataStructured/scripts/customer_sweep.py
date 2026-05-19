"""Customer sweep — Stripe polling + welcome/day-3/refresh email dispatch.

Runs every 2 hours via the trinity scheduler `customer_sweep` cycle.

Algorithm:
1. Read cursor from `state/stripe-poll-cursor.json` (default: now - 90 days).
2. Pull charges + subscriptions from Stripe since the cursor.
3. For each, resolve product slug via launch-report.json mapping.
4. Create/update `state/customers/<email-safe>.json` (idempotent by stripe id).
5. Send welcome email if not yet sent for this customer.
6. Scan all customer files for day-3 check-in candidates (72-96h window).
7. Scan `state/subscription-refresh-log/*.json` for fresh data → email
   active subscribers who haven't been notified for that quarter.
8. Advance the cursor ONLY if the Stripe pull completed without exceptions.

Idempotency:
- Welcome / day-3 / refresh emails are each keyed on a flag in the customer
  file. Re-running a cycle never spams.
- SMTP failures DO NOT mark the email as sent; the next cycle retries.

Standalone usage:
    source ~/.profile && python scripts/customer_sweep.py

Output (last line, stdout):
    new_customers=N welcome_sent=N day3_sent=N refresh_sent=N affiliate_matches=N errors=N
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import stripe

# Make sibling module importable both as `scripts.email_sender` and when run
# directly (`python scripts/customer_sweep.py`).
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.email_sender import send_plain  # noqa: E402


# ── Paths ───────────────────────────────────────────────────────────
STATE_DIR = _REPO_ROOT / "state"
CURSOR_PATH = STATE_DIR / "stripe-poll-cursor.json"
CUSTOMERS_DIR = STATE_DIR / "customers"
PRODUCTS_DIR = STATE_DIR / "products"
REFRESH_LOG_DIR = STATE_DIR / "subscription-refresh-log"
STOREFRONT_BASE = "https://data.oefrenterprise.com/products"


# ── Email templates ─────────────────────────────────────────────────
WELCOME_ONE_TIME_SUBJECT = "Your DataStructured purchase — {product_name}"
WELCOME_ONE_TIME_BODY = (
    "Hi,\n\n"
    "Thanks for buying {product_name}. Here's your download:\n\n"
    "{download_url}\n\n"
    "This dataset is exactly what's on data.oefrenterprise.com — every row is "
    "source-cited to the public record it came from. If a row looks off, you "
    "can audit it.\n\n"
    "If you ever need to reach a human, just reply to this email. We read "
    "every one.\n\n"
    "— DataStructured\n"
    "oefrenterprise.com\n"
)

WELCOME_SUBSCRIPTION_SUBJECT = "Welcome to DataStructured — {product_name}"
WELCOME_SUBSCRIPTION_BODY = (
    "Hi,\n\n"
    "Thanks for subscribing to {product_name}. Your first download:\n\n"
    "{download_url}\n\n"
    "Your next refresh arrives ~quarterly (every ~90 days). We'll email the "
    "new download link automatically.\n\n"
    "Cancel anytime from your Stripe receipt. No commitment.\n\n"
    "Reply to this email if you need anything.\n\n"
    "— DataStructured\n"
    "oefrenterprise.com\n"
)

DAY3_SUBJECT = "Quick check-in — {product_name}"
DAY3_BODY = (
    "Hi,\n\n"
    "It's been a few days since you bought {product_name}. Quick check:\n\n"
    "- Did the data work for what you needed?\n"
    "- Anything broken, confusing, or missing?\n\n"
    "We're an autonomous-agent shop, but the founder reads every reply. Two "
    "lines is enough.\n\n"
    "— DataStructured\n"
)

REFRESH_SUBJECT = "Fresh data — {product_name} ({quarter})"
REFRESH_BODY = (
    "Hi,\n\n"
    "Your Q{quarter_num} refresh is ready:\n\n"
    "{download_url}\n\n"
    "What changed since last quarter:\n"
    "{delta_notes}\n\n"
    "— DataStructured\n"
)


# ── Helpers ─────────────────────────────────────────────────────────
def utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    """Format a datetime as ISO-8601 with Z suffix (UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    """Parse an ISO-8601 string (with Z or offset) into a UTC datetime."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def email_safe(email: str) -> str:
    """Filesystem-safe stem for a customer email."""
    return email.lower().replace("@", "_at_").replace("+", "_plus_")


def quarter_key(dt: datetime) -> tuple[str, int]:
    """Return (`YYYY_Qn`, quarter_num) for the given UTC datetime."""
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}_Q{q}", q


def atomic_write_json(path: Path, payload: dict) -> None:
    """Write JSON atomically (tmp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    tmp.replace(path)


def read_json(path: Path) -> dict | None:
    """Read a JSON file, returning None if it doesn't exist."""
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ── Cursor ──────────────────────────────────────────────────────────
def read_cursor() -> datetime:
    """Read the last-polled cursor, defaulting to now - 90 days."""
    data = read_json(CURSOR_PATH)
    if data and "last_polled_at" in data:
        return parse_iso(data["last_polled_at"])
    return utcnow() - timedelta(days=90)


def write_cursor(dt: datetime) -> None:
    """Persist the cursor atomically."""
    atomic_write_json(CURSOR_PATH, {"last_polled_at": iso(dt)})


# ── Product mapping ─────────────────────────────────────────────────
def load_product_map() -> dict[str, tuple[str, str, str | None]]:
    """Map Stripe product_id → (slug, product_name, gist_url).

    Scans every `state/products/<slug>/launch-report.json` and registers both
    `stripe_product_id` (one-time) and `stripe_subscription_product_id`
    (recurring). gist_url is best-effort — falls back to None if missing.
    """
    mapping: dict[str, tuple[str, str, str | None]] = {}
    if not PRODUCTS_DIR.exists():
        return mapping
    for report_path in PRODUCTS_DIR.glob("*/launch-report.json"):
        try:
            report = json.loads(report_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        slug = report.get("slug") or report_path.parent.name
        name = report.get("product_name") or slug.replace("-", " ")
        gist = report.get("gist_url")
        one_time_pid = report.get("stripe_product_id")
        sub_pid = report.get("stripe_subscription_product_id")
        if one_time_pid:
            mapping[one_time_pid] = (slug, name, gist)
        if sub_pid:
            mapping[sub_pid] = (slug, name, gist)
    return mapping


def download_url_for(slug: str, gist_url: str | None) -> str:
    """Return the download URL to deliver in welcome emails.

    Prefer the launch-report's gist_url; fall back to the storefront product
    page (engineer should backfill gist_url — see engineer identity TODO).
    """
    if gist_url:
        return gist_url
    return f"{STOREFRONT_BASE}/{slug}"


# ── Customer file ───────────────────────────────────────────────────
def customer_path(email: str) -> Path:
    """Path to the per-customer state file."""
    return CUSTOMERS_DIR / f"{email_safe(email)}.json"


def load_or_create_customer(email: str, first_seen: datetime) -> tuple[dict, bool]:
    """Return (customer_dict, created_now)."""
    path = customer_path(email)
    existing = read_json(path)
    if existing is not None:
        existing.setdefault("purchases", [])
        existing.setdefault("subscriptions", [])
        existing.setdefault("emails_sent", {"welcome": None, "day3": None})
        return existing, False
    return (
        {
            "email": email,
            "first_purchase_at": iso(first_seen),
            "purchases": [],
            "subscriptions": [],
            "emails_sent": {"welcome": None, "day3": None},
        },
        True,
    )


def add_purchase(customer: dict, slug: str, charge_id: str, ts: datetime) -> bool:
    """Append a one-time purchase if not already recorded. Returns True if added."""
    if any(p.get("stripe_charge_id") == charge_id for p in customer["purchases"]):
        return False
    customer["purchases"].append({
        "slug": slug,
        "type": "one_time",
        "stripe_charge_id": charge_id,
        "purchased_at": iso(ts),
    })
    return True


def add_subscription(customer: dict, slug: str, sub_id: str, ts: datetime, status: str) -> bool:
    """Append/update a subscription. Returns True if newly added."""
    for s in customer["subscriptions"]:
        if s.get("stripe_subscription_id") == sub_id:
            s["status"] = status
            return False
    customer["subscriptions"].append({
        "slug": slug,
        "stripe_subscription_id": sub_id,
        "started_at": iso(ts),
        "status": status,
    })
    return True


# ── Stripe pulls ────────────────────────────────────────────────────
def ensure_stripe_key() -> None:
    """Set the Stripe API key from STRIPE_SECRET in the environment."""
    key = os.environ.get("STRIPE_SECRET")
    if not key:
        raise RuntimeError("STRIPE_SECRET not set in environment")
    stripe.api_key = key


def iter_charges(since: datetime) -> Iterable[Any]:
    """Iterate Stripe charges created at-or-after `since`."""
    ts = int(since.timestamp())
    params = {"created": {"gte": ts}, "limit": 100}
    return stripe.Charge.list(**params).auto_paging_iter()


def iter_subscriptions(since: datetime) -> Iterable[Any]:
    """Iterate Stripe subscriptions created at-or-after `since`."""
    ts = int(since.timestamp())
    params = {"created": {"gte": ts}, "limit": 100, "status": "all"}
    return stripe.Subscription.list(**params).auto_paging_iter()


def charge_email(charge: Any) -> str | None:
    """Best-effort email extraction from a Stripe Charge object."""
    bd = getattr(charge, "billing_details", None)
    if bd and getattr(bd, "email", None):
        return bd.email
    return getattr(charge, "receipt_email", None) or None


def charge_product_id(charge: Any) -> str | None:
    """Resolve the Stripe product_id for a charge via its payment intent + invoice.

    Returns None if we cannot determine it without extra API calls (and the
    metadata route also yielded nothing).
    """
    # Some Payment Link charges carry the product_id in metadata
    md = getattr(charge, "metadata", None)
    if md and md.get("product_id"):
        return md["product_id"]
    # Try invoice line items if present
    inv = getattr(charge, "invoice", None)
    if isinstance(inv, str) and inv:
        try:
            inv_obj = stripe.Invoice.retrieve(inv, expand=["lines.data.price.product"])
            for line in inv_obj.lines.data:
                price = getattr(line, "price", None)
                if price and getattr(price, "product", None):
                    return price.product if isinstance(price.product, str) else price.product.id
        except Exception:
            pass
    # Fall back: look up payment intent for charges resulting from a Payment Link
    pi = getattr(charge, "payment_intent", None)
    if isinstance(pi, str) and pi:
        try:
            pi_obj = stripe.PaymentIntent.retrieve(pi, expand=["latest_charge"])
            md_pi = getattr(pi_obj, "metadata", None)
            if md_pi and md_pi.get("product_id"):
                return md_pi["product_id"]
        except Exception:
            pass
    return None


def subscription_email(sub: Any) -> str | None:
    """Best-effort email extraction from a Stripe Subscription via its Customer."""
    cust = getattr(sub, "customer", None)
    if isinstance(cust, str) and cust:
        try:
            c = stripe.Customer.retrieve(cust)
            return getattr(c, "email", None) or None
        except Exception:
            return None
    if cust and getattr(cust, "email", None):
        return cust.email
    return None


def subscription_product_id(sub: Any) -> str | None:
    """First item's product_id from a Stripe Subscription."""
    items = getattr(sub, "items", None)
    if not items or not getattr(items, "data", None):
        return None
    for item in items.data:
        price = getattr(item, "price", None)
        if price and getattr(price, "product", None):
            return price.product if isinstance(price.product, str) else price.product.id
    return None


# ── Email actions ───────────────────────────────────────────────────
def send_welcome_one_time(customer: dict, product_name: str, download_url: str) -> None:
    """Send the one-time-purchase welcome email and stamp emails_sent.welcome."""
    subject = WELCOME_ONE_TIME_SUBJECT.format(product_name=product_name)
    body = WELCOME_ONE_TIME_BODY.format(product_name=product_name, download_url=download_url)
    send_plain(customer["email"], subject, body)
    customer["emails_sent"]["welcome"] = iso(utcnow())


def send_welcome_subscription(customer: dict, product_name: str, download_url: str) -> None:
    """Send the subscription welcome email and stamp emails_sent.welcome."""
    subject = WELCOME_SUBSCRIPTION_SUBJECT.format(product_name=product_name)
    body = WELCOME_SUBSCRIPTION_BODY.format(product_name=product_name, download_url=download_url)
    send_plain(customer["email"], subject, body)
    customer["emails_sent"]["welcome"] = iso(utcnow())


def send_day3(customer: dict, product_name: str) -> None:
    """Send the day-3 check-in email and stamp emails_sent.day3."""
    subject = DAY3_SUBJECT.format(product_name=product_name)
    body = DAY3_BODY.format(product_name=product_name)
    send_plain(customer["email"], subject, body)
    customer["emails_sent"]["day3"] = iso(utcnow())


def send_refresh(customer: dict, product_name: str, quarter: str,
                 quarter_num: int, download_url: str, delta_notes: str) -> None:
    """Send the subscription refresh email and stamp emails_sent.refresh_<q>."""
    subject = REFRESH_SUBJECT.format(product_name=product_name, quarter=quarter)
    body = REFRESH_BODY.format(
        quarter_num=quarter_num,
        download_url=download_url,
        delta_notes=delta_notes or "(no notes provided)",
    )
    send_plain(customer["email"], subject, body)
    key = f"refresh_{quarter.replace('-', '_')}"
    customer["emails_sent"][key] = iso(utcnow())


# ── Main sweep ──────────────────────────────────────────────────────
def process_charges(product_map: dict[str, tuple[str, str, str | None]],
                    since: datetime, counters: dict[str, int]) -> list[Any]:
    """Pull charges since `since` and dispatch welcome emails.

    Returns the list of charges pulled this cycle so downstream steps
    (e.g. affiliate reconciliation) can re-use them without a second API call.
    """
    pulled: list[Any] = []
    for ch in iter_charges(since):
        pulled.append(ch)
        if getattr(ch, "paid", False) is not True:
            continue
        email = charge_email(ch)
        if not email:
            continue
        pid = charge_product_id(ch)
        if not pid or pid not in product_map:
            continue
        slug, product_name, gist_url = product_map[pid]
        ts = datetime.fromtimestamp(ch.created, tz=timezone.utc)
        customer, created = load_or_create_customer(email, ts)
        if created:
            counters["new_customers"] += 1
        added = add_purchase(customer, slug, ch.id, ts)
        path = customer_path(email)
        atomic_write_json(path, customer)
        if added and customer["emails_sent"].get("welcome") is None:
            try:
                send_welcome_one_time(customer, product_name,
                                      download_url_for(slug, gist_url))
                atomic_write_json(path, customer)
                counters["welcome_sent"] += 1
            except Exception as e:
                counters["errors"] += 1
                print(f"[error] welcome one_time send to {email}: {e}",
                      file=sys.stderr)
    return pulled


def reconcile_affiliates(charges: list, workspace: Path) -> int:
    """For each new charge, check client_reference_id against utm-links registry.

    Append matches to state/partnerships/sales-log.json and rebuild per-partner
    aggregates in state/partnerships/active.json. Returns count of matches
    newly added this cycle.

    Idempotent: charges already present in sales-log (by stripe_charge_id) are
    skipped. active.json aggregates are rebuilt from sales-log on every call so
    they remain correct under re-runs.
    """
    links_file = workspace / "state" / "partnerships" / "utm-links.json"
    sales_log = workspace / "state" / "partnerships" / "sales-log.json"
    active_file = workspace / "state" / "partnerships" / "active.json"

    if not links_file.exists():
        return 0
    registry = json.loads(links_file.read_text())
    ref_to_link = {l["client_reference_id"]: l for l in registry.get("links", [])}
    if not ref_to_link:
        return 0

    log_data: dict = {"version": 1, "sales": []}
    if sales_log.exists():
        log_data = json.loads(sales_log.read_text())
    existing_charge_ids = {s["stripe_charge_id"] for s in log_data["sales"]}

    matched = 0
    for charge in charges:
        # Stripe may surface the client_reference_id in several places depending
        # on whether the charge originated from a Payment Link, Checkout
        # Session, or PaymentIntent. Try each.
        ref = None
        # 1. Top-level attribute (Checkout Session-derived charges)
        ref = (getattr(charge, "client_reference_id", None)
               if not isinstance(charge, dict)
               else charge.get("client_reference_id"))
        # 2. Payment intent dict (when expanded)
        if not ref:
            pi = (getattr(charge, "payment_intent", None)
                  if not isinstance(charge, dict)
                  else charge.get("payment_intent"))
            if isinstance(pi, dict):
                ref = pi.get("client_reference_id")
        # 3. Metadata (manual tagging fallback)
        if not ref:
            md = (getattr(charge, "metadata", None)
                  if not isinstance(charge, dict)
                  else charge.get("metadata"))
            if md:
                ref = md.get("client_reference_id") if hasattr(md, "get") else None
        if not ref or ref not in ref_to_link:
            continue
        charge_id = (getattr(charge, "id", None)
                     if not isinstance(charge, dict)
                     else charge.get("id"))
        if charge_id in existing_charge_ids:
            continue
        amount = (getattr(charge, "amount", 0)
                  if not isinstance(charge, dict)
                  else charge.get("amount", 0)) or 0
        created = (getattr(charge, "created", None)
                   if not isinstance(charge, dict)
                   else charge.get("created"))
        link = ref_to_link[ref]
        commission = round(amount * link["commission_pct"] / 100 / 100, 2)
        log_data["sales"].append({
            "stripe_charge_id": charge_id,
            "amount_usd": amount / 100,
            "client_reference_id": ref,
            "partner": link["partner"],
            "product_slug": link["product_slug"],
            "commission_pct": link["commission_pct"],
            "commission_owed_usd": commission,
            "charged_at": created,
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
            "paid_to_partner": False,
        })
        existing_charge_ids.add(charge_id)
        matched += 1

    sales_log.parent.mkdir(parents=True, exist_ok=True)
    sales_log.write_text(json.dumps(log_data, indent=2) + "\n")

    # Rebuild per-partner aggregates fresh from the full log so re-runs and
    # manual edits (e.g. flipping paid_to_partner) stay consistent.
    fresh_aggregates: dict[str, dict] = {}
    for sale in log_data["sales"]:
        p = sale["partner"]
        fresh_aggregates.setdefault(p, {
            "total_referred_usd": 0,
            "total_commission_owed_usd": 0,
            "total_commission_paid_usd": 0,
            "sale_count": 0,
        })
        fresh_aggregates[p]["total_referred_usd"] += sale["amount_usd"]
        fresh_aggregates[p]["total_commission_owed_usd"] += sale["commission_owed_usd"]
        if sale.get("paid_to_partner"):
            fresh_aggregates[p]["total_commission_paid_usd"] += sale["commission_owed_usd"]
        fresh_aggregates[p]["sale_count"] += 1
    # Round float sums to cents to keep file readable
    for p, agg in fresh_aggregates.items():
        agg["total_referred_usd"] = round(agg["total_referred_usd"], 2)
        agg["total_commission_owed_usd"] = round(agg["total_commission_owed_usd"], 2)
        agg["total_commission_paid_usd"] = round(agg["total_commission_paid_usd"], 2)
    active = {"version": 1, "partners": fresh_aggregates}
    active_file.write_text(json.dumps(active, indent=2) + "\n")

    return matched


def process_subscriptions(product_map: dict[str, tuple[str, str, str | None]],
                          since: datetime, counters: dict[str, int]) -> None:
    """Pull subscriptions since `since` and dispatch subscription welcomes."""
    for sub in iter_subscriptions(since):
        email = subscription_email(sub)
        if not email:
            continue
        pid = subscription_product_id(sub)
        if not pid or pid not in product_map:
            continue
        slug, product_name, gist_url = product_map[pid]
        ts = datetime.fromtimestamp(sub.created, tz=timezone.utc)
        status = getattr(sub, "status", "unknown")
        customer, created = load_or_create_customer(email, ts)
        if created:
            counters["new_customers"] += 1
        added = add_subscription(customer, slug, sub.id, ts, status)
        path = customer_path(email)
        atomic_write_json(path, customer)
        if added and customer["emails_sent"].get("welcome") is None:
            try:
                send_welcome_subscription(customer, product_name,
                                          download_url_for(slug, gist_url))
                atomic_write_json(path, customer)
                counters["welcome_sent"] += 1
            except Exception as e:
                counters["errors"] += 1
                print(f"[error] welcome subscription send to {email}: {e}",
                      file=sys.stderr)


def process_day3(product_map: dict[str, tuple[str, str, str | None]],
                 counters: dict[str, int]) -> None:
    """Scan customers for day-3 check-in eligibility and send."""
    if not CUSTOMERS_DIR.exists():
        return
    now = utcnow()
    for cust_path in CUSTOMERS_DIR.glob("*.json"):
        try:
            customer = json.loads(cust_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if customer.get("emails_sent", {}).get("day3"):
            continue
        first_str = customer.get("first_purchase_at")
        if not first_str:
            continue
        try:
            first = parse_iso(first_str)
        except ValueError:
            continue
        age = now - first
        if not (timedelta(hours=72) <= age <= timedelta(hours=96)):
            continue
        # Use the first recorded purchase's slug for the product_name
        purchases = customer.get("purchases") or []
        subscriptions = customer.get("subscriptions") or []
        slug = (purchases[0].get("slug") if purchases else
                (subscriptions[0].get("slug") if subscriptions else None))
        if not slug:
            continue
        # Find product_name by reverse-scanning the map
        product_name = slug.replace("-", " ")
        for _pid, (mslug, mname, _g) in product_map.items():
            if mslug == slug:
                product_name = mname
                break
        try:
            send_day3(customer, product_name)
            atomic_write_json(cust_path, customer)
            counters["day3_sent"] += 1
        except Exception as e:
            counters["errors"] += 1
            print(f"[error] day3 send to {customer.get('email')}: {e}",
                  file=sys.stderr)


def process_refresh(product_map: dict[str, tuple[str, str, str | None]],
                    counters: dict[str, int]) -> None:
    """Scan refresh logs and email matching active subscribers."""
    if not REFRESH_LOG_DIR.exists() or not CUSTOMERS_DIR.exists():
        return
    for log_path in REFRESH_LOG_DIR.glob("*.json"):
        try:
            log = json.loads(log_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        slug = log.get("slug")
        quarter = log.get("quarter")  # e.g. "2026-Q3"
        gist_url = log.get("gist_url")
        delta_notes = log.get("notes", "")
        if not (slug and quarter and gist_url):
            continue
        try:
            quarter_num = int(quarter.split("-Q")[-1])
        except (ValueError, IndexError):
            continue
        flag_key = f"refresh_{quarter.replace('-', '_')}"
        # Resolve product_name via the map (best-effort)
        product_name = slug.replace("-", " ")
        for _pid, (mslug, mname, _g) in product_map.items():
            if mslug == slug:
                product_name = mname
                break
        for cust_path in CUSTOMERS_DIR.glob("*.json"):
            try:
                customer = json.loads(cust_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if customer.get("emails_sent", {}).get(flag_key):
                continue
            has_active = any(
                s.get("slug") == slug and s.get("status") == "active"
                for s in customer.get("subscriptions", [])
            )
            if not has_active:
                continue
            try:
                send_refresh(customer, product_name, quarter, quarter_num,
                             gist_url, delta_notes)
                atomic_write_json(cust_path, customer)
                counters["refresh_sent"] += 1
            except Exception as e:
                counters["errors"] += 1
                print(f"[error] refresh send to {customer.get('email')}: {e}",
                      file=sys.stderr)


def main() -> int:
    """Run one sweep cycle. Returns 0 on success, 1 on hard failure."""
    counters = {
        "new_customers": 0,
        "welcome_sent": 0,
        "day3_sent": 0,
        "refresh_sent": 0,
        "affiliate_matches": 0,
        "errors": 0,
    }

    ensure_stripe_key()
    CUSTOMERS_DIR.mkdir(parents=True, exist_ok=True)
    REFRESH_LOG_DIR.mkdir(parents=True, exist_ok=True)

    product_map = load_product_map()
    cursor = read_cursor()
    sweep_started_at = utcnow()

    stripe_pull_ok = True
    charges_pulled: list[Any] = []
    try:
        charges_pulled = process_charges(product_map, cursor, counters)
        process_subscriptions(product_map, cursor, counters)
    except Exception:
        stripe_pull_ok = False
        counters["errors"] += 1
        print("[error] Stripe pull failed:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    # Day-3 + refresh sweeps are independent of cursor; run regardless.
    process_day3(product_map, counters)
    process_refresh(product_map, counters)

    # Affiliate reconciliation: silent bookkeeping for the founder's monthly
    # review. Matches incoming Stripe charges back to a partner via
    # client_reference_id (set when partner shared their UTM-tagged link).
    try:
        counters["affiliate_matches"] = reconcile_affiliates(
            charges_pulled, _REPO_ROOT
        )
    except Exception as e:
        counters["errors"] += 1
        print(f"[error] affiliate reconciliation failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    if stripe_pull_ok:
        write_cursor(sweep_started_at)

    print(
        "new_customers={new_customers} welcome_sent={welcome_sent} "
        "day3_sent={day3_sent} refresh_sent={refresh_sent} "
        "affiliate_matches={affiliate_matches} "
        "errors={errors}".format(**counters)
    )
    return 0 if counters["errors"] == 0 and stripe_pull_ok else 1


if __name__ == "__main__":
    sys.exit(main())
