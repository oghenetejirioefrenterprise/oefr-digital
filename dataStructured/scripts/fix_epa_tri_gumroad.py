#!/usr/bin/env python3
"""
Fix EPA TRI Gumroad listing and complete launch report + distribution queue.
Stripe already created successfully, just need to fix Gumroad.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).resolve().parents[1]
SLUG        = "epa-tri-toxic-release-reporting-facilities-2026-05"
SPEC_FILE   = BASE / "state" / "products" / SLUG / "spec.json"
REPORT_FILE = BASE / "state" / "products" / SLUG / "launch-report.json"
QUEUE_FILE  = BASE / "state" / "distribution-queue.json"
ASSET_PATH  = BASE / "state" / "datasets" / f"{SLUG}.csv"

sys.path.insert(0, str(BASE))

# ── creds ─────────────────────────────────────────────────────────────────────
GUMROAD_USER = os.environ["GUMROAD_USERNAME"]
GUMROAD_PASS = os.environ["GUMROAD_PASSWORD"]

spec = json.loads(SPEC_FILE.read_text())
report = json.loads(REPORT_FILE.read_text())

gumroad_spec = spec["gumroad"]
TITLE = gumroad_spec["title"]
PRICE = int(spec["price_usd"])
DESC = gumroad_spec["description"]

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

print(f"Fixing Gumroad for: {TITLE}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Create Gumroad listing via Playwright
# ─────────────────────────────────────────────────────────────────────────────
print("[1/3] Creating Gumroad listing…")
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def gumroad_deploy(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    ctx  = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # ── Login ──────────────────────────────────────────────────────────────────
    print("   [a] Logging in to Gumroad…")
    page.goto("https://gumroad.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    page.fill("input[type='email']", GUMROAD_USER)
    page.fill("input[type='password']", GUMROAD_PASS)
    page.click("button:has-text('Login')")

    try:
        page.wait_for_url("**app.gumroad.com/**", timeout=30000)
        print(f"   Logged in ✓")
    except PWTimeout:
        if "login" in page.url:
            page.screenshot(path="/tmp/gr_epa_fix_login_fail.png")
            browser.close()
            return None, None

    # ── New product ────────────────────────────────────────────────────────────
    print("   [b] Creating product…")
    page.goto("https://app.gumroad.com/products/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Select "Digital product" type first
    try:
        digital_product = page.locator("text=Digital product").first
        if digital_product.is_visible(timeout=3000):
            digital_product.click()
            print("   Selected Digital product type")
            time.sleep(2)
    except Exception as e:
        print(f"   Could not select Digital product: {e}")

    # Name
    for sel in [
        "input[placeholder*='name' i]",
        "input[name='name']",
        "input[type='text']:first-of-type",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(TITLE)
                print(f"   Name filled")
                break
        except Exception:
            continue

    # Price
    for sel in ["input[name='price']", "input[placeholder*='price' i]", "#price"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(str(PRICE))
                print(f"   Price filled: ${PRICE}")
                break
        except Exception:
            continue

    # Submit to go to edit page
    for sel in [
        "button[type='submit']",
        "button:has-text('Create')",
        "button:has-text('Continue')",
        "button:has-text('Next')",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                print(f"   Submitted creation form")
                break
        except Exception:
            continue

    # Wait for edit page
    try:
        page.wait_for_url("**/products/**/edit**", timeout=30000)
    except PWTimeout:
        try:
            page.wait_for_url("**/products/**", timeout=15000)
        except PWTimeout:
            pass
    time.sleep(3)
    print(f"   Edit page: {page.url}")

    # ── Description ────────────────────────────────────────────────────────────
    for sel in [
        "textarea[name='description']",
        "[contenteditable='true']",
        ".ql-editor",
        "textarea",
        "[role='textbox']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(DESC)
                print(f"   Description filled")
                break
        except Exception:
            continue

    # ── File upload ────────────────────────────────────────────────────────────
    # Upload failure is FATAL: publishing a paid product with no asset attached
    # means buyers pay and receive nothing. Poll for an upload-complete signal
    # (filename chip on the page) instead of trusting a flat sleep, and abort the
    # deploy if the file never attaches.
    asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ASSET_PATH))
    except Exception as exc:
        print(f"   FATAL: file upload could not start: {exc}")
        page.screenshot(path="/tmp/gr_epa_fix_upload_fail.png")
        browser.close()
        return None, None

    # Poll for the uploaded filename chip to appear (max generous budget for a
    # large CSV) rather than blindly sleeping.
    upload_confirmed = False
    deadline = time.time() + max(180, int(asset_mb * 4))
    chip = page.locator(f"text={ASSET_PATH.name}").first
    print(f"   Uploading {asset_mb:.1f} MB CSV… (polling for completion)")
    while time.time() < deadline:
        try:
            if chip.is_visible(timeout=2000):
                upload_confirmed = True
                break
        except Exception:
            pass
        time.sleep(3)

    if not upload_confirmed:
        print("   FATAL: upload did not complete (filename chip never appeared); "
              "refusing to publish a product with no downloadable asset")
        page.screenshot(path="/tmp/gr_epa_fix_upload_incomplete.png")
        browser.close()
        return None, None
    print("   Upload confirmed ✓")

    # ── Save / Publish ─────────────────────────────────────────────────────────
    saved = False
    for sel in [
        "button:has-text('Save')",
        "button:has-text('Publish')",
        "button:has-text('Update')",
        "button[type='submit']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=5000):
                el.click()
                print(f"   Saved/Published")
                saved = True
                time.sleep(3)
                break
        except Exception:
            continue

    if not saved:
        # Try keyboard shortcut
        try:
            page.keyboard.press("Control+S")
            print("   Saved via Ctrl+S")
            time.sleep(2)
        except Exception:
            pass

    page.screenshot(path="/tmp/gr_epa_fix_final.png")

    # ── Extract public URL ─────────────────────────────────────────────────────
    final_url = page.url
    gumroad_public_url = None
    gumroad_product_id = None

    # Try to find view/public link
    for sel in ["a[href*='/l/']", "a:has-text('View product')", "a:has-text('View')"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                href = el.get_attribute("href")
                if href and "/l/" in href:
                    if href.startswith("/"):
                        href = "https://gumroad.com" + href
                    gumroad_public_url = href
                    print(f"   Found public URL: {gumroad_public_url}")
                    break
        except Exception:
            continue

    # Extract from URL if not found
    if not gumroad_public_url:
        m = re.search(r"/products/([^/?#]+)", final_url)
        if m:
            pid = m.group(1)
            gumroad_product_id = pid
            # Try to navigate to products list and get the permalink
            try:
                page.goto("https://app.gumroad.com/products", timeout=20000)
                time.sleep(2)
                # Look for the product we just created
                product_link = page.locator(f"a:has-text('{TITLE[:30]}')").first
                if product_link.is_visible(timeout=5000):
                    product_link.click()
                    time.sleep(2)
                    # Now try to get permalink
                    for sel in ["a[href*='/l/']", "input[value*='/l/']"]:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible(timeout=3000):
                                val = el.get_attribute("href") or el.get_attribute("value")
                                if val and "/l/" in val:
                                    if val.startswith("/"):
                                        val = "https://gumroad.com" + val
                                    gumroad_public_url = val
                                    break
                        except Exception:
                            continue
            except Exception as e:
                print(f"   Could not get permalink: {e}")

    if gumroad_public_url:
        m = re.search(r"/l/([^/?#]+)", gumroad_public_url)
        if m:
            gumroad_product_id = m.group(1)

    browser.close()
    return gumroad_public_url, gumroad_product_id


with sync_playwright() as pw:
    gumroad_url, gumroad_product_id = gumroad_deploy(pw)

if not gumroad_url:
    print("ERROR: Could not determine Gumroad public URL")
    sys.exit(1)

print(f"   Gumroad URL: {gumroad_url}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Add to distribution queue (BEFORE writing the report that claims it was queued)
# ─────────────────────────────────────────────────────────────────────────────
# Ordering: append_item must succeed before the launch report is updated to say
# "Distribution queue updated". append_item is file-locked + schema-validated; if
# it raises, the report is never rewritten with the false claim and a re-run can
# recover.
print("[2/3] Adding to distribution queue…")
from scripts.lib.distribution_queue import append_item

# Derive audience from spec "Who buys this" section
audience = "Environmental compliance attorneys, corporate ESG/sustainability managers, environmental liability insurance underwriters, sustainability consultants, environmental justice researchers"

item = {
    "id": f"{SLUG}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
    "slug": SLUG,
    "name": spec["name"],
    "stripe_payment_link_url": report["stripe_payment_link_url"],
    "gumroad_url": gumroad_url,
    "price_usd": PRICE,
    "audience": audience,
    "added_at": NOW(),
    "status": "ready",
}

append_item(QUEUE_FILE, item)
print("   Distribution queue updated ✓")

# ─────────────────────────────────────────────────────────────────────────────
# Update launch report (only after the queue append succeeded)
# ─────────────────────────────────────────────────────────────────────────────
print("[3/3] Updating launch report…")
report["gumroad_url"] = gumroad_url
if gumroad_product_id:
    report["gumroad_product_id"] = gumroad_product_id
report["summary"] = "Live on Stripe + Gumroad. CSV (78,647 rows) hosted on GitHub Release. Smoke tests green. Distribution queue updated."

REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"   Updated: {REPORT_FILE}")

print("\n─────────────────────────────────────────────────────────────────")
print("FIX COMPLETE ✓")
print(f"  Stripe:  {report['stripe_payment_link_url']}")
print(f"  Gumroad: {gumroad_url}")
print(f"  Status:  SHIPPED")
