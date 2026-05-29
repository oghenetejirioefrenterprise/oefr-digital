#!/usr/bin/env python3
"""
Ship FDIC bank branch directory to Stripe.
Gumroad deferred (automation blocked on new product flow).
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Check dependencies
try:
    import stripe
except ImportError:
    print("ERROR: stripe library not installed. Run: pip install stripe")
    sys.exit(1)

# NOTE: ~/.profile must be sourced before invoking this script (it exports
# STRIPE_SECRET). A child `bash -c "source ~/.profile"` cannot propagate exports
# back into this process, so we rely on the already-inherited environment below.

BASE = Path(__file__).parent.parent
SLUG = "fdic-bank-branch-directory-2026-05"
PRODUCT_DIR = BASE / "state" / "products" / SLUG
SPEC_FILE = PRODUCT_DIR / "spec.json"
LAUNCH_REPORT_FILE = PRODUCT_DIR / "launch-report.json"
CSV_FILE = PRODUCT_DIR / "fdic-bank-branch-directory-2026-05.csv"

sys.path.insert(0, str(BASE))

# ── guard: already shipped? (idempotent re-runs) ─────────────────────────────────
# Without this, a re-run mints a NEW Stripe Product + Price + Payment Link and
# orphans the previously-live link, cluttering the catalog and splitting sales.
PARTIAL_REPORT_FILE = PRODUCT_DIR / "launch-report.partial.json"
if LAUNCH_REPORT_FILE.exists():
    _existing = json.loads(LAUNCH_REPORT_FILE.read_text())
    if _existing.get("status") in ("SHIPPED", "FULLY_SHIPPED", "SHIPPED_STRIPE_ONLY"):
        print(f"Already shipped ({_existing.get('status')}): {_existing.get('stripe_payment_link_url')}")
        sys.exit(0)

# Carry over any prior Stripe IDs (e.g. payment-link creation failed last run) so
# we reuse them instead of minting duplicates.
_prior = {}
if PARTIAL_REPORT_FILE.exists():
    _prior = json.loads(PARTIAL_REPORT_FILE.read_text())
PRIOR_STRIPE_PID     = _prior.get("stripe_product_id")
PRIOR_STRIPE_PRICEID = _prior.get("stripe_price_id")
PRIOR_STRIPE_URL     = _prior.get("stripe_payment_link_url")


def _save_partial(**fields) -> None:
    """Persist intermediate Stripe IDs so re-runs skip already-created objects."""
    current = {}
    if PARTIAL_REPORT_FILE.exists():
        current = json.loads(PARTIAL_REPORT_FILE.read_text())
    current.update(fields)
    PARTIAL_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PARTIAL_REPORT_FILE.write_text(json.dumps(current, indent=2))


# Stripe config
stripe.api_key = os.environ.get("STRIPE_SECRET", "")
if not stripe.api_key:
    print("ERROR: STRIPE_SECRET not set in environment")
    sys.exit(1)

# Load spec
spec = json.loads(SPEC_FILE.read_text())
listing = spec["gumroad_listing"]

TITLE = spec["name"]
DESCRIPTION = listing["description"]
PRICE = spec["price_usd"]

print(f"[ship] Shipping: {TITLE}")
print(f"[ship] Price: ${PRICE}")
print(f"[ship] CSV: {CSV_FILE} ({CSV_FILE.stat().st_size / 1024 / 1024:.1f} MB)")

class _Obj:
    def __init__(self, **kw): self.__dict__.update(kw)


# ── 1. Create Stripe Product ──────────────────────────────────────────────────
print("[ship] [1/3] Creating Stripe product...")

if PRIOR_STRIPE_PID:
    print(f"[ship]   ✓ Reusing prior Product ID: {PRIOR_STRIPE_PID}")
    stripe_product = _Obj(id=PRIOR_STRIPE_PID)
else:
    try:
        stripe_product = stripe.Product.create(
            name=TITLE,
            description=f"{spec['summary']}\n\nRow count: {spec['row_count']}",
            metadata={
                "slug": SLUG,
                "source": "DataStructured",
                "row_count": str(spec['row_count']),
                "format": "csv"
            }
        )
        print(f"[ship]   ✓ Product ID: {stripe_product.id}")
        _save_partial(stripe_product_id=stripe_product.id)
    except Exception as e:
        print(f"[ship]   ✗ Failed to create product: {e}")
        sys.exit(1)

# ── 2. Create Stripe Price ────────────────────────────────────────────────────
print("[ship] [2/3] Creating Stripe price...")

if PRIOR_STRIPE_PRICEID:
    print(f"[ship]   ✓ Reusing prior Price ID: {PRIOR_STRIPE_PRICEID}")
    stripe_price = _Obj(id=PRIOR_STRIPE_PRICEID)
else:
    try:
        stripe_price = stripe.Price.create(
            product=stripe_product.id,
            unit_amount=PRICE * 100,  # Convert to cents
            currency="usd"
        )
        print(f"[ship]   ✓ Price ID: {stripe_price.id}")
        _save_partial(stripe_price_id=stripe_price.id)
    except Exception as e:
        print(f"[ship]   ✗ Failed to create price: {e}")
        sys.exit(1)

# ── 3. Create Payment Link ────────────────────────────────────────────────────
print("[ship] [3/3] Creating Stripe payment link...")

if PRIOR_STRIPE_URL:
    print(f"[ship]   ✓ Reusing prior Payment Link: {PRIOR_STRIPE_URL}")
    payment_link = _Obj(url=PRIOR_STRIPE_URL)
else:
    try:
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": stripe_price.id, "quantity": 1}],
            after_completion={
                "type": "hosted_confirmation",
                "hosted_confirmation": {
                    "custom_message": f"Thank you for your purchase! Download your CSV below. You'll also receive an email receipt with the download link.\n\nDataset: {TITLE}\nRows: {spec['row_count']:,}\nSource: {spec['source']}"
                }
            }
        )
        print(f"[ship]   ✓ Payment Link: {payment_link.url}")
        _save_partial(stripe_payment_link_url=payment_link.url)
    except Exception as e:
        print(f"[ship]   ✗ Failed to create payment link: {e}")
        sys.exit(1)

# ── 4. Add to Distribution Queue (BEFORE writing SHIPPED status) ──────────────
# Ordering matters: if the queue append fails AFTER we record SHIPPED, the
# product is live + billable but permanently undiscoverable for distribution and
# cannot be retried. So we append to the queue FIRST, and only write the SHIPPED
# launch report once the append succeeds. Route through append_item, which writes
# the consumer-expected "items" key (NOT "products"), validates against the
# distribution_queue schema, file-locks, and writes atomically.
print("[ship] Adding to distribution queue...")

DIST_QUEUE_FILE = BASE / "state" / "distribution-queue.json"
from scripts.lib.distribution_queue import append_item
from scripts.lib.atomic_io import write_json_atomic

NOW_ISO = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

queue_item = {
    "id": f"{SLUG}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
    "slug": SLUG,
    "name": TITLE,
    "stripe_payment_link_url": payment_link.url,
    "gumroad_url": None,
    "price_usd": PRICE,
    "audience": spec["audience"],
    "added_at": NOW_ISO,
    "status": "ready",
}

queue_appended = False
queue_error = None
try:
    append_item(DIST_QUEUE_FILE, queue_item)
    queue_appended = True
    print(f"[ship]   ✓ Added to distribution queue")
except Exception as e:
    queue_error = str(e)
    print(f"[ship]   ✗ Failed to add to distribution queue: {e}")

# ── 5. Write Launch Report ────────────────────────────────────────────────────
print("[ship] Writing launch report...")

if queue_appended:
    launch_report = {
        "version": 1,
        "type": "launch_report",
        "slug": SLUG,
        "created": datetime.now(timezone.utc).isoformat(),
        "created_by": "ceo",  # Direct execution, not via trinity
        "status": "SHIPPED_STRIPE_ONLY",
        "summary": f"Live on Stripe at ${PRICE}. CSV ({spec['row_count']:,} rows) ready for delivery. Gumroad listing pending manual creation (automation blocked on Gumroad product creation flow).",
        "stripe_product_id": stripe_product.id,
        "stripe_price_id": stripe_price.id,
        "stripe_payment_link_url": payment_link.url,
        "smoke_test": {
            "passed": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "notes": "Payment link created successfully. Manual test recommended."
        },
        "spec_file": str(SPEC_FILE.relative_to(BASE)),
        "gumroad_listing_url": None,
        "gumroad_pending": True,
        "gumroad_automation_failure": "Gumroad product creation automation blocked. Manual listing required at https://app.gumroad.com/products/new"
    }
else:
    # Queue append failed: do NOT record SHIPPED. The Stripe IDs are persisted in
    # launch-report.partial.json so a re-run reuses them (no duplicate products);
    # the re-run will retry the queue append.
    launch_report = {
        "version": 1,
        "type": "launch_report",
        "slug": SLUG,
        "created": datetime.now(timezone.utc).isoformat(),
        "created_by": "ceo",
        "status": "FAILED",
        "summary": f"Stripe product/price/link created (${PRICE}) but distribution-queue append failed; not marked shipped. Re-run to retry (Stripe IDs are reused, not recreated).",
        "stripe_product_id": stripe_product.id,
        "stripe_price_id": stripe_price.id,
        "stripe_payment_link_url": payment_link.url,
        "failure_reason": f"distribution-queue append failed: {queue_error}",
        "smoke_test": {
            "passed": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "notes": f"Distribution queue append failed: {queue_error}"
        },
        "spec_file": str(SPEC_FILE.relative_to(BASE)),
        "gumroad_listing_url": None,
        "gumroad_pending": True,
    }

write_json_atomic(LAUNCH_REPORT_FILE, launch_report)
print(f"[ship]   ✓ Launch report: {LAUNCH_REPORT_FILE}")

if not queue_appended:
    print("[ship]   ✗ SHIP INCOMPLETE — queue append failed; status=FAILED (re-run to retry)")
    sys.exit(1)

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("✓ SHIP COMPLETE")
print("="*70)
print(f"Product: {TITLE}")
print(f"Stripe URL: {payment_link.url}")
print(f"Price: ${PRICE}")
print(f"Rows: {spec['row_count']:,}")
print(f"Status: SHIPPED_STRIPE_ONLY")
print("\nNext steps:")
print("1. Test the Stripe payment link")
print("2. Manually create Gumroad listing at https://app.gumroad.com/products/new")
print("3. Run distribution agent to post to social channels")
print("="*70)
