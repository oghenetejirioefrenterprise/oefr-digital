#!/usr/bin/env python3
"""
Finish the Gumroad RIA listing: upload CSV + publish.
Product ibhcj already created. Need to: upload file, publish.
"""

import os
import sys
import time
from pathlib import Path

BASE       = Path(__file__).resolve().parents[1]
SLUG       = "sec-registered-investment-advisers-2026-05"
PRODUCT_ID = "ibhcj"
ASSET_PATH = BASE / "state" / "datasets" / f"{SLUG}.csv"
EDIT_URL   = f"https://gumroad.com/products/{PRODUCT_ID}/edit"
CONTENT_URL= f"https://gumroad.com/products/{PRODUCT_ID}/edit/content"

GUMROAD_USER = os.environ.get("GUMROAD_USERNAME", "")
GUMROAD_PASS = os.environ.get("GUMROAD_PASSWORD", "")

asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
print(f"Asset: {ASSET_PATH.name} ({asset_mb:.1f} MB)")
print(f"Edit URL: {EDIT_URL}")

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def ss(page, name):
    path = f"/tmp/gr_ria_pub_{name}.png"
    page.screenshot(path=path)
    print(f"   [ss] → {path}")


def run(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    ctx  = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # ── Login ──────────────────────────────────────────────────────────────────
    print("[1] Login")
    page.goto("https://gumroad.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    page.fill("input[type='email']", GUMROAD_USER)
    page.fill("input[type='password']", GUMROAD_PASS)
    page.click("button:has-text('Login')")
    time.sleep(4)
    ss(page, "01_post_login")
    if "login" in page.url:
        print("FAIL: auth failed")
        browser.close()
        return False

    # ── Navigate to Content tab ────────────────────────────────────────────────
    print("[2] Navigate to Content tab")
    page.goto(CONTENT_URL, timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    ss(page, "02_content_tab")
    print(f"   URL: {page.url}")

    # ── Upload file ────────────────────────────────────────────────────────────
    print(f"[3] Upload CSV ({asset_mb:.1f} MB)")

    # Try clicking "Upload your files" button first, then use file chooser
    upload_ok = False

    # Method A: file chooser via button click
    try:
        with page.expect_file_chooser(timeout=15000) as fc_info:
            # Try visible upload buttons
            for sel in [
                "button:has-text('Upload your files')",
                "button:has-text('Upload files')",
                "button:has-text('Upload')",
                "[data-testid*='upload']",
                "label:has-text('Upload')",
            ]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        print(f"   Clicked upload btn: {sel}")
                        break
                except Exception:
                    continue
        fc_info.value.set_files(str(ASSET_PATH))
        upload_ok = True
        print(f"   File chooser upload started")
    except Exception as e:
        print(f"   File chooser method failed: {e}")

    if not upload_ok:
        # Method B: direct input[type='file']
        try:
            fi = page.locator("input[type='file']").first
            fi.set_input_files(str(ASSET_PATH))
            upload_ok = True
            print("   Direct file input upload started")
        except Exception as e:
            print(f"   Direct file input failed: {e}")

    if not upload_ok:
        # Method C: look for any file input (including hidden ones)
        try:
            # Use evaluate to find all file inputs
            count = page.evaluate("document.querySelectorAll('input[type=file]').length")
            print(f"   Found {count} file inputs via JS")
            if count > 0:
                page.evaluate("""
                    const fi = document.querySelector('input[type=file]');
                    fi.style.display = 'block';
                    fi.style.opacity = '1';
                    fi.style.position = 'fixed';
                    fi.style.top = '0';
                    fi.style.left = '0';
                    fi.style.zIndex = '9999';
                """)
                fi = page.locator("input[type='file']").first
                fi.set_input_files(str(ASSET_PATH))
                upload_ok = True
                print("   Made hidden file input visible and uploaded")
        except Exception as e:
            print(f"   JS-reveal method failed: {e}")

    if not upload_ok:
        # Upload failure is FATAL: publishing a paid product with no asset attached
        # means buyers pay and receive nothing. Abort instead of publishing.
        print("   FATAL: all upload methods failed — refusing to publish a product "
              "with no downloadable asset")
        ss(page, "03_upload_failed")
        browser.close()
        return False

    # Poll for the uploaded filename chip rather than blindly sleeping, and abort
    # if the file never attaches.
    upload_confirmed = False
    deadline = time.time() + max(120, int(asset_mb * 4))
    chip = page.locator(f"text={ASSET_PATH.name}").first
    print(f"   Uploading {asset_mb:.1f} MB… (polling for completion)")
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
        ss(page, "03_upload_incomplete")
        browser.close()
        return False
    ss(page, "03_after_upload")

    # ── Save content ────────────────────────────────────────────────────────────
    print("[4] Save content")
    for sel in [
        "button:has-text('Save')",
        "button:has-text('Save changes')",
        "button:has-text('Update')",
        "button[type='submit']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=5000):
                el.click()
                print(f"   Saved ({sel})")
                time.sleep(3)
                break
        except Exception:
            continue

    ss(page, "04_after_save")

    # ── Publish via Product tab ────────────────────────────────────────────────
    print("[5] Publish listing")
    page.goto(EDIT_URL, timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    ss(page, "05_product_tab")

    published = False
    for sel in [
        "button:has-text('Publish and continue')",
        "button:has-text('Publish')",
        "button:has-text('Make public')",
        "button:has-text('Go live')",
        "[data-testid*='publish']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                print(f"   Clicked publish: {sel}")
                time.sleep(3)
                published = True
                break
        except Exception:
            continue

    ss(page, "06_after_publish")
    print(f"   URL after publish: {page.url}")

    # ── Navigate to Share tab to get public URL ────────────────────────────────
    print("[6] Get public URL")
    try:
        page.goto(f"https://gumroad.com/products/{PRODUCT_ID}/edit/share", timeout=30000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        ss(page, "07_share_tab")
    except Exception:
        pass

    browser.close()
    return True


with sync_playwright() as pw:
    ok = run(pw)

print("\nDone." if ok else "\nFailed.")
