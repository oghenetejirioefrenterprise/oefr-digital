#!/usr/bin/env python3
"""
One-shot Gumroad deployment for samgov-small-biz-contractor-leads-2026-05.
Browser-first (Gumroad write API is deprecated).
Updates launch-report.json with gumroad_url on success.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
SLUG = "samgov-small-biz-contractor-leads-2026-05"
SPEC_FILE = BASE / f"state/products/{SLUG}/spec.json"
LAUNCH_REPORT = BASE / f"state/products/{SLUG}/launch-report.json"
ASSET_PATH = BASE / f"state/datasets/{SLUG}.csv"

# ── creds ─────────────────────────────────────────────────────────────────────
GUMROAD_USER = os.environ.get("GUMROAD_USERNAME", "")
GUMROAD_PASS = os.environ.get("GUMROAD_PASSWORD", "")

if not GUMROAD_USER or not GUMROAD_PASS:
    print("ERROR: GUMROAD_USERNAME and GUMROAD_PASSWORD must be set in environment")
    sys.exit(1)

if not ASSET_PATH.exists():
    print(f"ERROR: Asset not found: {ASSET_PATH}")
    sys.exit(1)

# ── load spec ─────────────────────────────────────────────────────────────────
spec = json.loads(SPEC_FILE.read_text())
listing = spec["gumroad_listing"]

TITLE = listing["title"]
DESCRIPTION = listing["description"]
PRICE = listing["price"]  # 49

print(f"Deploying to Gumroad: {TITLE} @ ${PRICE}")
print(f"Asset: {ASSET_PATH} ({ASSET_PATH.stat().st_size / 1024:.0f} KB)")

# ── browser automation ─────────────────────────────────────────────────────────
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def run(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    # ── 1. Login ──────────────────────────────────────────────────────────────
    print("[1/6] Logging in to Gumroad...")
    page.goto("https://gumroad.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")

    page.fill("input[type='email']", GUMROAD_USER)
    page.fill("input[type='password']", GUMROAD_PASS)
    page.click("button[type='submit']")

    try:
        page.wait_for_url("https://gumroad.com/dashboard**", timeout=30000)
        print("   Logged in ✓")
    except PWTimeout:
        current = page.url
        print(f"   Login redirect: {current}")
        if "gumroad.com" not in current or "login" in current:
            page.screenshot(path="/tmp/gumroad_samgov_login_fail.png")
            print("   ERROR: Login failed — screenshot at /tmp/gumroad_samgov_login_fail.png")
            browser.close()
            sys.exit(1)

    # ── 2. Navigate to new product page ──────────────────────────────────────
    print("[2/6] Opening new product form...")
    page.goto("https://app.gumroad.com/products/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    page.screenshot(path="/tmp/gumroad_samgov_new_product.png")
    print(f"   Current URL: {page.url}")

    # ── 3. Fill product name ──────────────────────────────────────────────────
    print("[3/6] Filling product details...")

    name_selectors = [
        "input[placeholder*='name' i]",
        "input[name='name']",
        "input[type='text']:first-of-type",
        "[data-testid='product-name']",
        "#name",
    ]
    name_filled = False
    for sel in name_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(TITLE)
                name_filled = True
                print(f"   Name filled via: {sel}")
                break
        except Exception:
            continue

    if not name_filled:
        print("   WARNING: Could not fill name field directly, trying JS")
        page.evaluate(f"""
            const inputs = document.querySelectorAll('input[type="text"], input:not([type])');
            for (const inp of inputs) {{
                if (inp.offsetParent !== null) {{
                    inp.value = {json.dumps(TITLE)};
                    inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                    inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                    break;
                }}
            }}
        """)

    # ── 4. Set price ──────────────────────────────────────────────────────────
    price_selectors = [
        "input[name='price']",
        "input[placeholder*='price' i]",
        "input[aria-label*='price' i]",
        "#price",
    ]
    price_filled = False
    for sel in price_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(str(PRICE))
                price_filled = True
                print(f"   Price filled via: {sel}")
                break
        except Exception:
            continue

    if not price_filled:
        print("   WARNING: Price field not found via standard selectors")

    # ── 5. Click "Create product" / Continue ──────────────────────────────────
    print("[4/6] Submitting product creation form...")
    submit_selectors = [
        "button[type='submit']",
        "button:has-text('Create')",
        "button:has-text('Continue')",
        "button:has-text('Next')",
        "input[type='submit']",
    ]
    submitted = False
    for sel in submit_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                submitted = True
                print(f"   Clicked submit via: {sel}")
                break
        except Exception:
            continue

    if not submitted:
        print("   ERROR: Could not find submit button")
        page.screenshot(path="/tmp/gumroad_samgov_submit_fail.png")
        browser.close()
        sys.exit(1)

    # Wait for navigation to product edit page
    try:
        page.wait_for_url("https://app.gumroad.com/products/*/edit**", timeout=30000)
    except PWTimeout:
        try:
            page.wait_for_url("**/products/**", timeout=15000)
        except PWTimeout:
            pass

    time.sleep(2)
    current_url = page.url
    print(f"   Post-submit URL: {current_url}")
    page.screenshot(path="/tmp/gumroad_samgov_after_create.png")

    # ── 6. Fill description & upload file ─────────────────────────────────────
    print("[5/6] Adding description and uploading asset...")

    desc_selectors = [
        "textarea[name='description']",
        "[contenteditable='true']",
        ".ql-editor",
        "textarea",
        "[role='textbox']",
    ]
    for sel in desc_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(DESCRIPTION)
                print(f"   Description filled via: {sel}")
                break
        except Exception:
            continue

    # Upload file
    # Upload failure is FATAL: publishing a paid product with no asset attached
    # means buyers pay and receive nothing. Poll for the filename chip rather than
    # a fixed sleep, and abort the deploy if the file never attaches.
    asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
    try:
        file_input = page.locator("input[type='file']").first
        file_input.set_input_files(str(ASSET_PATH))
    except Exception as e:
        print(f"   FATAL: file upload could not start: {e}")
        page.screenshot(path="/tmp/gumroad_samgov_upload_fail.png")
        browser.close()
        sys.exit(1)

    upload_confirmed = False
    deadline = time.time() + max(120, int(asset_mb * 4))
    chip = page.locator(f"text={ASSET_PATH.name}").first
    print(f"   Uploading {ASSET_PATH.name} ({asset_mb:.1f} MB)… (polling for completion)")
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
        page.screenshot(path="/tmp/gumroad_samgov_upload_incomplete.png")
        browser.close()
        sys.exit(1)
    print(f"   Asset uploaded: {ASSET_PATH.name} ✓")

    # Publish — explicitly target Publish (not the first save-like button, which
    # may be a draft "Save"), then confirm the listing actually went live.
    published = False
    for sel in [
        "button:has-text('Publish and continue')",
        "button:has-text('Publish')",
        "button:has-text('Go live')",
        "button:has-text('Make public')",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=5000):
                el.click()
                print(f"   Clicked publish via: {sel}")
                time.sleep(3)
                published = True
                break
        except Exception:
            continue

    if not published:
        for sel in ["button:has-text('Save')", "button:has-text('Update')", "button[type='submit']"]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.click()
                    print(f"   Saved via: {sel} (no explicit Publish button found)")
                    time.sleep(3)
                    break
            except Exception:
                continue

    page.screenshot(path="/tmp/gumroad_samgov_final.png")

    live_confirmed = False
    for sel in ["button:has-text('Unpublish')", "text=/is now live/i", "text=/Published/i"]:
        try:
            if page.locator(sel).first.is_visible(timeout=3000):
                live_confirmed = True
                break
        except Exception:
            continue
    if not live_confirmed:
        print("   WARNING: could not confirm the listing is published (no Unpublish/Published indicator)")

    # ── 7. Get the public listing URL ─────────────────────────────────────────
    print("[6/6] Extracting public listing URL...")
    final_url = page.url
    print(f"   Final URL: {final_url}")

    # Read the REAL public permalink. The /products/<id>/edit token is NOT the
    # public /l/<permalink> slug, so we must not synthesize one.
    gumroad_public_url = None

    link_selectors = [
        "a[href*='/l/']",
        "input[value*='/l/']",
        "a:has-text('View product')",
        "a:has-text('gumroad.com/l/')",
    ]
    for sel in link_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                href = el.get_attribute("href") or el.get_attribute("value")
                if href and "/l/" in href:
                    if href.startswith("/"):
                        href = "https://gumroad.com" + href
                    gumroad_public_url = href
                    print(f"   Public URL found: {gumroad_public_url}")
                    break
        except Exception:
            continue

    if not gumroad_public_url:
        # Navigate to the product's Share tab and read the real permalink.
        m = re.search(r"/products/([^/?#]+)", final_url)
        if m:
            pid = m.group(1)
            try:
                page.goto(f"https://app.gumroad.com/products/{pid}/edit/share", timeout=30000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                for sel in ["input[value*='/l/']", "a[href*='/l/']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=3000):
                            val = el.get_attribute("value") or el.get_attribute("href")
                            if val and "/l/" in val:
                                if val.startswith("/"):
                                    val = "https://gumroad.com" + val
                                gumroad_public_url = val
                                print(f"   Public URL from Share tab: {gumroad_public_url}")
                                break
                    except Exception:
                        continue
            except Exception as e:
                print(f"   Could not read Share tab permalink: {e}")

    if not gumroad_public_url:
        # Do NOT synthesize https://gumroad.com/l/<edit_id> — that internal id is
        # not the public permalink and produces a 404 link for buyers. Fail loudly.
        print("   ERROR: could not read the real Gumroad permalink; refusing to "
              "emit a guessed /l/ URL")

    browser.close()
    return gumroad_public_url


with sync_playwright() as playwright:
    gumroad_url = run(playwright)

if not gumroad_url:
    print("ERROR: Could not determine Gumroad listing URL")
    sys.exit(1)

# ── update launch report ───────────────────────────────────────────────────────
print(f"\nGumroad URL: {gumroad_url}")
report = json.loads(LAUNCH_REPORT.read_text())
report["gumroad_listing_url"] = gumroad_url

# Extract product_id from URL (last path segment)
gumroad_product_id = gumroad_url.rstrip("/").split("/")[-1]
report["gumroad_product_id"] = gumroad_product_id
report["status"] = "FULLY_SHIPPED"
report["gumroad_deployed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
LAUNCH_REPORT.write_text(json.dumps(report, indent=2))
print(f"Launch report updated: {LAUNCH_REPORT}")
print("\nDEPLOY COMPLETE ✓")
print(f"  Stripe:  {report['stripe_payment_link_url']}")
print(f"  Gumroad: {gumroad_url}")
