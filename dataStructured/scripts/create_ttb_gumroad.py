#!/usr/bin/env python3
"""
Create Gumroad listing for TTB Brewery/Winery/Distillery Directory.
"""

import json
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── paths ─────────────────────────────────────────────────────────────────────
BASE = Path("/home/oghenetejiri/apps/dataStructured")
SLUG = "ttb-brewery-winery-distillery-directory"
SPEC_FILE = BASE / "state" / "products" / SLUG / "spec.json"
ASSET_PATH = BASE / "state" / "ttb-brewery-winery-distillery-directory-2026-05.cleaned.csv"

# ── creds ─────────────────────────────────────────────────────────────────────
GUMROAD_USER = os.environ["GUMROAD_USERNAME"]
GUMROAD_PASS = os.environ["GUMROAD_PASSWORD"]

spec = json.loads(SPEC_FILE.read_text())
gumroad_spec = spec["gumroad"]
TITLE = gumroad_spec["title"]
PRICE = int(spec["price_usd"])
DESC = gumroad_spec["description"]

print(f"🎯 Creating Gumroad listing: {TITLE}")
print(f"   Price: ${PRICE}")
print(f"   Asset: {ASSET_PATH.name} ({ASSET_PATH.stat().st_size / 1024 / 1024:.1f} MB)")


def create_gumroad_listing():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── Login ──────────────────────────────────────────────────────────────────
        print("\n[1/6] Logging in to Gumroad…")
        page.goto("https://gumroad.com/login", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        page.fill("input[type='email']", GUMROAD_USER)
        page.fill("input[type='password']", GUMROAD_PASS)
        page.click("button:has-text('Login')")

        try:
            page.wait_for_url("**app.gumroad.com/**", timeout=30000)
            print("   ✅ Logged in")
        except PWTimeout:
            print("   ❌ Login failed")
            page.screenshot(path="/tmp/gumroad_ttb_login_fail.png")
            browser.close()
            return None

        # ── New product ────────────────────────────────────────────────────────────
        print("\n[2/6] Creating new product…")
        page.goto("https://app.gumroad.com/products/new", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Select "Digital product" type
        try:
            digital_product = page.locator("text=Digital product").first
            if digital_product.is_visible(timeout=3000):
                digital_product.click()
                print("   ✅ Selected Digital product type")
                time.sleep(2)
        except Exception as e:
            print(f"   ⚠️  Could not select Digital product: {e}")

        # Fill name
        print("\n[3/6] Filling product details…")
        for sel in [
            "input[placeholder*='name' i]",
            "input[name='name']",
            "input[type='text']:first-of-type",
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.fill(TITLE)
                    print(f"   ✅ Name filled")
                    break
            except Exception:
                continue

        # Fill price
        for sel in ["input[name='price']", "input[placeholder*='price' i]", "#price"]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.fill(str(PRICE))
                    print(f"   ✅ Price filled: ${PRICE}")
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
                    print(f"   ✅ Submitted creation form")
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
        print(f"   📝 Edit page: {page.url}")

        # ── Description ────────────────────────────────────────────────────────────
        print("\n[4/6] Adding description…")
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
                    # Clear existing content
                    el.click()
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    time.sleep(0.5)

                    # Fill description
                    el.fill(DESC)
                    print(f"   ✅ Description filled ({len(DESC)} chars)")
                    time.sleep(2)
                    break
            except Exception as e:
                print(f"   ⚠️  Description selector {sel} failed: {e}")
                continue

        # ── Upload file ────────────────────────────────────────────────────────────
        # Upload failure is FATAL: publishing a paid product with no asset attached
        # means buyers pay and receive nothing. Poll for the filename chip rather
        # than a fixed sleep, and abort if the file never attaches.
        print("\n[5/6] Uploading CSV file…")
        asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
        try:
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(str(ASSET_PATH))
        except Exception as e:
            print(f"   ❌ FATAL: file upload could not start: {e}")
            page.screenshot(path="/tmp/gumroad_ttb_upload_fail.png")
            browser.close()
            return None

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
            print("   ❌ FATAL: upload did not complete (filename chip never appeared); "
                  "refusing to publish a product with no downloadable asset")
            page.screenshot(path="/tmp/gumroad_ttb_upload_incomplete.png")
            browser.close()
            return None
        print(f"   ✅ File uploaded: {ASSET_PATH.name}")

        # ── Publish ────────────────────────────────────────────────────────────────
        # Explicitly target Publish (not the first save-like button, which may be a
        # draft "Save"), then confirm the listing actually went live.
        print("\n[6/6] Publishing…")
        published = False
        for sel in [
            "button:has-text('Publish and continue')",
            "button:has-text('Publish')",
            "button:has-text('Go live')",
            "button:has-text('Make public')",
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.click()
                    print(f"   ✅ Clicked publish button: {sel}")
                    time.sleep(3)
                    published = True
                    break
            except Exception:
                continue

        if not published:
            for sel in ["button:has-text('Save')", "button[type='submit']"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        print(f"   Saved via: {sel} (no explicit Publish button found)")
                        time.sleep(3)
                        break
                except Exception:
                    continue

        live_confirmed = False
        for sel in ["button:has-text('Unpublish')", "text=/is now live/i", "text=/Published/i"]:
            try:
                if page.locator(sel).first.is_visible(timeout=3000):
                    live_confirmed = True
                    break
            except Exception:
                continue
        if not live_confirmed:
            print("   ⚠️  Could not confirm the listing is published (no Unpublish/Published indicator)")

        # ── Get public URL ─────────────────────────────────────────────────────────
        print("\n🔍 Finding public URL…")

        # Try to find the product permalink/public link
        public_url = None
        try:
            # Look for share link or permalink
            for sel in [
                "input[readonly*='gumroad.com/l/']",
                "a[href*='gumroad.com/l/']",
                "input[value*='gumroad.com/l/']",
            ]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        url = el.get_attribute("value") or el.get_attribute("href")
                        if url and "gumroad.com/l/" in url:
                            public_url = url
                            print(f"   ✅ Found public URL: {public_url}")
                            break
                except Exception:
                    continue
        except Exception as e:
            print(f"   ⚠️  Could not find public URL: {e}")

        # If we still don't have the URL, open the product's Share tab and read the
        # REAL permalink. The /products/<id>/edit token is NOT the public
        # /l/<permalink> slug, so we must never synthesize a /l/<edit_id> link
        # (it 404s for buyers).
        if not public_url:
            print("   🔄 Checking products list for the real permalink…")
            page.goto("https://app.gumroad.com/products", timeout=30000)
            time.sleep(3)
            page.screenshot(path="/tmp/gumroad_ttb_products_page.png")

            try:
                product_link = page.locator(f"a:has-text('{TITLE[:30]}')").first
                if product_link.is_visible(timeout=5000):
                    href = product_link.get_attribute("href")
                    if href and "/products/" in href:
                        product_id = href.split("/products/")[1].split("/")[0]
                        page.goto(
                            f"https://app.gumroad.com/products/{product_id}/edit/share",
                            timeout=30000,
                        )
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
                                        public_url = val
                                        print(f"   ✅ Public URL from Share tab: {public_url}")
                                        break
                            except Exception:
                                continue
            except Exception as e:
                print(f"   ⚠️  Could not read the real permalink: {e}")

        if not public_url:
            print("   ❌ Could not read the real Gumroad permalink; refusing to "
                  "emit a guessed /l/ URL")

        page.screenshot(path="/tmp/gumroad_ttb_final.png")
        browser.close()

        return public_url


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    listing_url = create_gumroad_listing()

    if listing_url:
        print("\n" + "="*60)
        print("✅ GUMROAD LISTING CREATED")
        print("="*60)
        print(f"Public URL: {listing_url}")
        print("\n📝 Updating spec.json…")

        # Update spec with Gumroad URL
        spec["gumroad"]["listing_url"] = listing_url
        SPEC_FILE.write_text(json.dumps(spec, indent=2))
        print(f"   ✅ Updated {SPEC_FILE}")
    else:
        print("\n❌ FAILED TO CREATE GUMROAD LISTING")
        print("Check screenshots in /tmp/ for debugging")
        exit(1)
