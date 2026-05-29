#!/usr/bin/env python3
"""
Ship sbir-sttr-award-recipients product end-to-end.

Build sequence (Engineer role):
1. Read spec
2. Stripe: product + price + Payment Link
3. GitHub Gist: upload final CSV
4. Gumroad: create listing (optional)
5. Smoke test
6. Append to distribution-queue.json
7. Write launch-report.json
8. Git commit + push (triggers Vercel deploy)
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[1]
SLUG = "sbir-sttr-award-recipients"
PRODUCT_DIR = BASE / "state" / "products" / SLUG
SPEC_FILE = PRODUCT_DIR / "spec.json"
LAUNCH_REPORT_FILE = PRODUCT_DIR / "launch-report.json"
FINAL_CSV = PRODUCT_DIR / "clean-final.csv"
QUEUE_FILE = BASE / "state" / "distribution-queue.json"

sys.path.insert(0, str(BASE))

# ── guard: already shipped? (idempotent re-runs) ─────────────────────────────────
# Without this, a re-run mints a NEW Stripe Product + Price + Payment Link and
# orphans the previously-live link, cluttering the catalog and splitting sales.
if LAUNCH_REPORT_FILE.exists():
    _existing = json.loads(LAUNCH_REPORT_FILE.read_text())
    if _existing.get("status") in ("SHIPPED", "FULLY_SHIPPED", "SHIPPED_STRIPE_ONLY"):
        print(
            f"Already shipped ({_existing.get('status')}): "
            f"{_existing.get('stripe_payment_link_url')} / {_existing.get('gumroad_listing_url')}"
        )
        sys.exit(0)

# ── Load environment ───────────────────────────────────────────────────────────
STRIPE_SECRET = os.environ.get("STRIPE_SECRET", "")
GUMROAD_USER = os.environ.get("GUMROAD_USERNAME", "")
GUMROAD_PASS = os.environ.get("GUMROAD_PASSWORD", "")

if not STRIPE_SECRET:
    sys.exit("ERROR: STRIPE_SECRET not set in environment")
if not GUMROAD_USER or not GUMROAD_PASS:
    print("WARNING: Gumroad credentials not set. Gumroad listing will be skipped.")

# ── Load spec ──────────────────────────────────────────────────────────────────
if not SPEC_FILE.exists():
    sys.exit(f"ERROR: spec.json not found at {SPEC_FILE}")

spec = json.loads(SPEC_FILE.read_text())

if spec.get("status") != "READY_TO_SHIP":
    sys.exit(f"ERROR: Product status is '{spec.get('status')}', expected 'READY_TO_SHIP'")

if not FINAL_CSV.exists():
    sys.exit(f"ERROR: Final CSV not found at {FINAL_CSV}")

TITLE = spec["name"]
SUMMARY = spec["summary"]
PRICE = spec["price_usd"]
ROW_COUNT = spec["row_count_final"]

print("="*70)
print(f"SHIPPING: {TITLE}")
print("="*70)
print(f"Price: ${PRICE}")
print(f"Rows: {ROW_COUNT:,}")
print(f"CSV: {FINAL_CSV.name} ({FINAL_CSV.stat().st_size / 1024 / 1024:.1f} MB)")
print()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Upload CSV to GitHub Gist
# ─────────────────────────────────────────────────────────────────────────────
print("[1/7] Uploading CSV to GitHub Gist...")

try:
    # Create public gist
    result = subprocess.run(
        ["gh", "gist", "create", str(FINAL_CSV), "--public",
         "--desc", f"DataStructured: {TITLE}"],
        capture_output=True,
        text=True,
        timeout=180
    )

    if result.returncode != 0:
        sys.exit(f"  ✗ Gist upload failed: {result.stderr.strip()}")

    gist_url = result.stdout.strip()
    # Convert gist URL to raw download URL. Resolve the gist owner dynamically
    # (gh authenticated login) rather than hardcoding a username — a wrong login
    # produces a 404 download link in the Stripe receipt for paying customers.
    gist_id = gist_url.rstrip("/").split("/")[-1]
    gh_user = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True, text=True, timeout=30
    ).stdout.strip()
    if not gh_user:
        sys.exit("  ✗ Could not resolve GitHub login via `gh api user` — aborting to avoid a 404 download link")
    raw_download_url = f"https://gist.githubusercontent.com/{gh_user}/{gist_id}/raw/{FINAL_CSV.name}"

    print(f"  ✓ Gist created: {gist_url}")
    print(f"  ✓ Raw download: {raw_download_url}")
except Exception as e:
    sys.exit(f"  ✗ Failed to create gist: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Stripe: product + price + Payment Link
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/7] Creating Stripe product...")

try:
    import stripe
    stripe.api_key = STRIPE_SECRET

    from scripts.stripe_helpers import create_price, create_payment_link

    # Create product
    # NOTE: left inline (not migrated to stripe_helpers.create_product) because this
    # metadata carries extra keys (slug, row_count, format) that the shared helper's
    # fixed metadata={"product_id","lob"} would silently drop.
    stripe_product = stripe.Product.create(
        name=TITLE,
        description=f"{SUMMARY[:400]}...",
        metadata={
            "product_id": f"dsl_{SLUG.replace('-', '_')}",
            "lob": "datastructured",
            "slug": SLUG,
            "row_count": str(ROW_COUNT),
            "format": "csv"
        }
    )
    print(f"  ✓ Product ID: {stripe_product.id}")

    # Create price
    stripe_price = create_price(
        stripe_product.id,
        PRICE,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_price",
    )
    print(f"  ✓ Price ID: {stripe_price.id}")

    # Create Payment Link with download URL in success message
    success_message = (
        f"Thank you for your purchase!\n\n"
        f"Download your SBIR/STTR Award Database here:\n"
        f"{raw_download_url}\n\n"
        f"Dataset: {ROW_COUNT:,} awards (FY2023-2025)\n"
        f"Source: SBIR.gov public data portal\n\n"
        f"You'll also receive this link via email receipt."
    )

    stripe_link = create_payment_link(
        stripe_price.id,
        success_message,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_link",
    )
    print(f"  ✓ Payment Link: {stripe_link.url}")

except Exception as e:
    sys.exit(f"  ✗ Stripe creation failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Gumroad listing (optional, via Playwright)
# ─────────────────────────────────────────────────────────────────────────────
gumroad_url = None

if GUMROAD_USER and GUMROAD_PASS:
    print("\n[3/7] Creating Gumroad listing...")

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        def create_gumroad_listing():
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = context.new_page()

                # Login
                print("  [3a] Logging in to Gumroad...")
                page.goto("https://gumroad.com/login", timeout=30000)
                time.sleep(2)

                page.fill("input[type='email']", GUMROAD_USER)
                page.fill("input[type='password']", GUMROAD_PASS)
                page.click("button:has-text('Login')")

                try:
                    page.wait_for_url("**app.gumroad.com/**", timeout=30000)
                except PWTimeout:
                    print("  ⚠ Login timeout - skipping Gumroad")
                    browser.close()
                    return None

                # Create product
                print("  [3b] Creating product...")
                page.goto("https://app.gumroad.com/products/new", timeout=30000)
                time.sleep(3)

                # Fill form (selectors may need adjustment based on current UI)
                page.fill("input[placeholder*='name' i]", TITLE)
                page.fill("textarea[placeholder*='description' i]", SUMMARY)
                page.fill("input[placeholder*='price' i]", str(PRICE))

                # Upload file
                page.set_input_files("input[type='file']", str(FINAL_CSV))
                time.sleep(2)

                # Submit
                page.click("button:has-text('Create')")
                page.wait_for_url("**app.gumroad.com/products/**", timeout=60000)

                # Get public URL
                public_url = page.url.replace("app.gumroad.com/products/", "gumroad.com/l/")

                browser.close()
                return public_url

        gumroad_url = create_gumroad_listing()

        if gumroad_url:
            print(f"  ✓ Gumroad URL: {gumroad_url}")
        else:
            print("  ⚠ Gumroad listing creation failed - continuing without it")

    except Exception as e:
        print(f"  ⚠ Gumroad error: {e} - continuing without Gumroad listing")
else:
    print("\n[3/7] Skipping Gumroad (credentials not set)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Smoke Test
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/7] Running smoke test...")

smoke_test_passed = True
smoke_test_notes = []

# Test 1: Stripe Payment Link loads
try:
    result = subprocess.run(
        ["curl", "-fsSL", "-o", "/dev/null", "-w", "%{http_code}", stripe_link.url],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.stdout.strip() == "200":
        print("  ✓ Stripe Payment Link loads (HTTP 200)")
        smoke_test_notes.append("Stripe Payment Link: OK")
    else:
        print(f"  ✗ Stripe Payment Link returned {result.stdout.strip()}")
        smoke_test_passed = False
        smoke_test_notes.append(f"Stripe Payment Link: HTTP {result.stdout.strip()}")
except Exception as e:
    print(f"  ✗ Stripe Payment Link test failed: {e}")
    smoke_test_passed = False
    smoke_test_notes.append(f"Stripe Payment Link: FAILED ({e})")

# Test 2: Gist raw download URL is accessible
try:
    result = subprocess.run(
        ["curl", "-fsSL", "-o", "/dev/null", "-w", "%{http_code}", raw_download_url],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.stdout.strip() == "200":
        print("  ✓ Gist download URL accessible (HTTP 200)")
        smoke_test_notes.append("Gist download: OK")
    else:
        print(f"  ✗ Gist download URL returned {result.stdout.strip()}")
        smoke_test_passed = False
        smoke_test_notes.append(f"Gist download: HTTP {result.stdout.strip()}")
except Exception as e:
    print(f"  ✗ Gist download test failed: {e}")
    smoke_test_passed = False
    smoke_test_notes.append(f"Gist download: FAILED ({e})")

# Test 3: Gumroad (if created)
if gumroad_url:
    try:
        result = subprocess.run(
            ["curl", "-fsSL", "-o", "/dev/null", "-w", "%{http_code}", gumroad_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout.strip() == "200":
            print("  ✓ Gumroad listing accessible (HTTP 200)")
            smoke_test_notes.append("Gumroad listing: OK")
        else:
            print(f"  ⚠ Gumroad listing returned {result.stdout.strip()}")
            smoke_test_notes.append(f"Gumroad listing: HTTP {result.stdout.strip()}")
    except Exception as e:
        print(f"  ⚠ Gumroad test failed: {e}")
        smoke_test_notes.append(f"Gumroad listing: FAILED ({e})")

print(f"\n  Smoke test: {'✓ PASSED' if smoke_test_passed else '✗ FAILED'}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Append to distribution-queue.json (only if smoke test passed)
# ─────────────────────────────────────────────────────────────────────────────
queue_appended = False
if smoke_test_passed:
    print("\n[5/7] Appending to distribution-queue.json...")

    from scripts.lib.distribution_queue import append_item

    # Build the item with ALL distribution_queue schema-required fields:
    # id, slug, name, price_usd, audience, added_at, status (valid enum).
    queue_item = {
        "id": f"{SLUG}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "slug": SLUG,
        "name": TITLE,
        "stripe_payment_link_url": stripe_link.url,
        "gumroad_url": gumroad_url,
        "price_usd": PRICE,
        "audience": spec.get("audience", SUMMARY),
        "added_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "ready",
    }

    try:
        append_item(QUEUE_FILE, queue_item)
        queue_appended = True
        print("  ✓ Added to distribution queue")
    except Exception as e:
        # A queue-append failure must NOT leave a SHIPPED-but-unqueued product
        # that can never be distributed or retried. Fail loud and mark not-shipped.
        print(f"  ✗ Failed to append to queue: {e}")
        smoke_test_passed = False
        smoke_test_notes.append(f"Distribution queue append: FAILED ({e})")
else:
    print("\n[5/7] Skipping distribution queue (smoke test failed)")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Write launch-report.json
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6/7] Writing launch-report.json...")

status = "FULLY_SHIPPED" if (smoke_test_passed and gumroad_url) else \
         "SHIPPED_STRIPE_ONLY" if smoke_test_passed else \
         "FAILED"

launch_report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": datetime.now(timezone.utc).isoformat(),
    "created_by": "engineer",
    "status": status,
    "summary": (
        f"{'✓' if smoke_test_passed else '✗'} Shipped to Stripe at ${PRICE}. "
        f"{'Gumroad listing created. ' if gumroad_url else 'Gumroad listing skipped. '}"
        f"CSV ({ROW_COUNT:,} rows) delivered via GitHub Gist."
    ),
    "stripe_product_id": stripe_product.id,
    "stripe_price_id": stripe_price.id,
    "stripe_payment_link_url": stripe_link.url,
    "gumroad_listing_url": gumroad_url,
    "gist_url": gist_url,
    "asset_raw_url": raw_download_url,
    "smoke_test": {
        "passed": smoke_test_passed,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "notes": " | ".join(smoke_test_notes)
    },
    "spec_file": str(SPEC_FILE.relative_to(BASE)),
    "final_csv": str(FINAL_CSV.relative_to(BASE)),
    "row_count": ROW_COUNT
}

LAUNCH_REPORT_FILE.write_text(json.dumps(launch_report, indent=2))
print(f"  ✓ Launch report written: {LAUNCH_REPORT_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Git commit + push (triggers Vercel deploy)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[7/7] Committing and pushing to trigger Vercel deploy...")

try:
    subprocess.run(
        ["git", "add", str(PRODUCT_DIR.relative_to(BASE))],
        cwd=BASE,
        check=True
    )

    subprocess.run(
        ["git", "commit", "-m",
         f"ship(dataStructured): {SLUG} launched\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"],
        cwd=BASE,
        check=True
    )

    subprocess.run(
        ["git", "push"],
        cwd=BASE,
        check=True
    )

    print("  ✓ Pushed to git - Vercel deploy will auto-trigger")

except subprocess.CalledProcessError as e:
    print(f"  ⚠ Git operations failed: {e}")
    print("  → Manual push required: cd ~/apps/dataStructured && git push")

# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("✓ SHIP COMPLETE" if smoke_test_passed else "⚠ SHIP PARTIAL")
print("="*70)
print(f"Product: {TITLE}")
print(f"Status: {status}")
print(f"Stripe: {stripe_link.url}")
if gumroad_url:
    print(f"Gumroad: {gumroad_url}")
print(f"Download: {raw_download_url}")
print(f"Price: ${PRICE}")
print(f"Rows: {ROW_COUNT:,}")
print("="*70)

if not smoke_test_passed:
    print("\n⚠ WARNING: Smoke test failed. Review launch-report.json for details.")
    sys.exit(1)

sys.exit(0)
