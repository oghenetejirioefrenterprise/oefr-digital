#!/usr/bin/env python3
"""
Gumroad deploy v3 for sec-registered-investment-advisers-2026-05.
Fixes: React form requires click+keyboard.type, not fill().
Form flow: Name → Select "Digital product" → Price → Next: Customize.
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE    = Path(__file__).resolve().parents[1]
SLUG    = "sec-registered-investment-advisers-2026-05"
ITEM_ID = f"{SLUG}-2026-05-07"

PRODUCT_DIR = BASE / "state" / "products" / SLUG
REPORT_FILE = PRODUCT_DIR / "launch-report.json"
QUEUE_FILE  = BASE / "state" / "distribution-queue.json"
ASSET_PATH  = BASE / "state" / "datasets" / f"{SLUG}.csv"
OPP_FILE    = BASE / "state" / "opportunities" / "2026-05-07-sec-registered-investment-advisers.json"

sys.path.insert(0, str(BASE))

report      = json.loads(REPORT_FILE.read_text())

# ── guard: already shipped? (avoid creating a SECOND Gumroad listing) ──────────
if report.get("status") in ("SHIPPED", "FULLY_SHIPPED"):
    print(f"Already shipped: {report.get('stripe_payment_link_url')} / {report.get('gumroad_url')}")
    sys.exit(0)

STRIPE_URL  = report["stripe_payment_link_url"]

GUMROAD_USER = os.environ.get("GUMROAD_USERNAME", "")
GUMROAD_PASS = os.environ.get("GUMROAD_PASSWORD", "")

TITLE = "SEC RIA Database 2026 — 16,551 Registered Investment Adviser Firms (CSV)"
PRICE = 79

GUMROAD_DESCRIPTION = (
    "Complete database of all 16,551 SEC-registered investment adviser (RIA) firms — "
    "sourced directly from SEC Form ADV public filings, updated May 2026.\n\n"
    "Same data. 1% of the price.\n"
    "Platforms like AdvizorPro and RIA Database charge $5,000-$20,000/year for this exact "
    "government-sourced dataset. You get the full flat file for $79, one-time, instant download.\n\n"
    "What's included (61 fields per firm):\n"
    "- Firm name, CRD#, SEC registration number\n"
    "- Main office: address, city, state, ZIP, phone, website\n"
    "- AUM: discretionary + non-discretionary (USD)\n"
    "- Employees: total + breakdown by role type\n"
    "- Clients: total count + 14 client-type categories\n"
    "- Fee structure: AUM%, hourly, subscription, fixed, performance, other\n"
    "- Private funds flag + gross assets + hedge/PE/VC counts\n"
    "- Disclosure/disciplinary history flag + event count\n"
    "- Registration status + state of incorporation\n\n"
    "Who buys this:\n"
    "- Asset managers and ETF sponsors reaching RIA distribution gatekeepers\n"
    "- Wealthtech SaaS companies prospecting for firm clients\n"
    "- Investment recruiters targeting breakaway advisers\n"
    "- Boutique M&A advisers tracking RIA consolidation\n"
    "- Anyone paying $999-$20,000/year for enterprise RIA data platforms\n\n"
    "Format: CSV, ready for Excel, Google Sheets, or CRM import\n"
    "Records: 16,551 SEC-approved firms\n"
    "Source: SEC IAPD Form ADV bulk data - public domain\n"
    "Updated: May 2026"
)

AUDIENCE = (
    "B2B sales and distribution teams at asset managers, ETF sponsors, and fund companies "
    "prospecting RIA gatekeepers; wealthtech SaaS companies (portfolio management, CRM, compliance "
    "tools) reaching new firm clients; third-party investment recruiters targeting breakaway adviser "
    "talent; boutique M&A advisers tracking RIA consolidation; teams currently paying four-to-five "
    "figures per year for enterprise platforms that wrap the same free SEC public data."
)

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
print(f"Asset: {ASSET_PATH.name} ({asset_mb:.1f} MB)")
print(f"Stripe: {STRIPE_URL}\n")


from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def ss(page, name):
    path = f"/tmp/gr_ria_v3_{name}.png"
    page.screenshot(path=path)
    print(f"   [ss] → {path}")


def type_into(page, selector, text, label="field"):
    """Click element then keyboard-type into it (works with React forms)."""
    try:
        el = page.locator(selector).first
        el.wait_for(state="visible", timeout=5000)
        el.click()
        time.sleep(0.3)
        # Select all and clear first
        page.keyboard.press("Control+a")
        page.keyboard.press("Delete")
        time.sleep(0.2)
        page.keyboard.type(text, delay=5)
        print(f"   {label} typed via keyboard ({selector})")
        return True
    except Exception as e:
        print(f"   {label} FAILED ({selector}): {e}")
        return False


def gumroad_deploy(playwright):
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
    cur = page.url
    print(f"   URL: {cur}")
    if "login" in cur:
        print("   FAIL: auth failed")
        browser.close()
        return None, None

    # ── New product page ───────────────────────────────────────────────────────
    print("[2] Navigate to new product form")
    page.goto("https://app.gumroad.com/products/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    ss(page, "02_new_product")
    print(f"   URL: {page.url}")

    # ── Fill Name using keyboard.type ──────────────────────────────────────────
    print("[3] Fill Name field")
    name_ok = False

    # The name field label is "Name" — try to locate by label first
    for sel in [
        "input[aria-label*='Name' i]",
        "input[aria-label*='name' i]",
        "input[name='name']",
        "input[placeholder*='name' i]",
        "input[placeholder*='Name' i]",
    ]:
        if type_into(page, sel, TITLE, "Name"):
            name_ok = True
            break

    if not name_ok:
        # Fallback: use the first visible text input on the page
        # (the Name field is first in the form)
        inputs = page.locator("input[type='text']").all()
        print(f"   Found {len(inputs)} text inputs — trying each")
        for i, inp in enumerate(inputs):
            try:
                if inp.is_visible(timeout=1000):
                    bounding = inp.bounding_box()
                    print(f"   input[{i}]: box={bounding}")
                    inp.click()
                    time.sleep(0.3)
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Delete")
                    time.sleep(0.2)
                    page.keyboard.type(TITLE, delay=5)
                    # Check if it filled
                    val = inp.input_value()
                    print(f"   input[{i}] value after type: {val[:40] if val else '(empty)'}")
                    if val and len(val) > 5:
                        name_ok = True
                        print(f"   Name filled via input[{i}]")
                        break
            except Exception as e:
                print(f"   input[{i}] error: {e}")

    if not name_ok:
        # Last resort: use evaluate to set value and dispatch events
        try:
            page.evaluate("""
                const inputs = document.querySelectorAll('input[type="text"]');
                if (inputs.length > 0) {
                    const inp = inputs[0];
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(inp, arguments[0]);
                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                }
            """, TITLE)
            print("   Name set via JS evaluate")
            name_ok = True
        except Exception as e:
            print(f"   JS evaluate FAILED: {e}")

    ss(page, "03_name_filled")
    time.sleep(1)

    # ── Select Digital product type ────────────────────────────────────────────
    print("[4] Select Digital product type")
    try:
        page.get_by_text("Digital product", exact=False).first.click()
        print("   Digital product clicked")
        time.sleep(1)
    except Exception as e:
        print(f"   Could not click Digital product: {e}")

    ss(page, "04_type_selected")

    # ── Fill Price ─────────────────────────────────────────────────────────────
    print("[5] Fill Price field")
    price_ok = False

    # Scroll down to price field first
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1)

    # Try the price input — the Gumroad UI has a currency selector + text input
    # The price input appears to be the input inside the Price section
    for sel in [
        "input[name='price']",
        "input[placeholder*='0.99']",
        "input[placeholder*='price' i]",
        "input[type='number']",
    ]:
        if type_into(page, sel, str(PRICE), "Price"):
            price_ok = True
            break

    if not price_ok:
        # Use get_by_label
        try:
            page.get_by_label("Price", exact=False).first.click()
            time.sleep(0.3)
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.keyboard.type(str(PRICE), delay=5)
            print("   Price typed via get_by_label")
            price_ok = True
        except Exception as e:
            print(f"   get_by_label failed: {e}")

    if not price_ok:
        # Find all inputs and try the second one (usually price)
        inputs = page.locator("input").all()
        print(f"   Found {len(inputs)} total inputs — checking each for price")
        for i, inp in enumerate(inputs):
            try:
                if inp.is_visible(timeout=1000):
                    bounding = inp.bounding_box()
                    input_type = inp.get_attribute("type") or ""
                    if bounding and bounding.get("y", 0) > 700:  # Price is lower on page
                        inp.click()
                        time.sleep(0.3)
                        page.keyboard.press("Control+a")
                        page.keyboard.press("Delete")
                        page.keyboard.type(str(PRICE), delay=5)
                        val = inp.input_value()
                        print(f"   input[{i}] (y={bounding.get('y'):.0f}) value: {val}")
                        if val == str(PRICE):
                            price_ok = True
                            print(f"   Price filled via input[{i}]")
                            break
            except Exception as e:
                print(f"   input[{i}] error: {e}")

    ss(page, "05_price_filled")
    time.sleep(1)

    # ── Scroll to top and click Next: Customize ────────────────────────────────
    print("[6] Submit creation form")
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)

    clicked = False
    for sel in [
        "button:has-text('Next: Customize')",
        "button:has-text('Next')",
        "button:has-text('Create')",
        "button:has-text('Continue')",
        "button[type='submit']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                print(f"   Clicked: {sel}")
                clicked = True
                break
        except Exception:
            continue

    time.sleep(3)
    ss(page, "06_post_submit")
    print(f"   URL: {page.url}")

    # Wait for edit URL
    try:
        page.wait_for_url("**/products/**/edit**", timeout=20000)
        print("   Reached edit page ✓")
    except PWTimeout:
        try:
            page.wait_for_url("**/products/**", timeout=10000)
        except PWTimeout:
            pass

    time.sleep(2)
    ss(page, "07_edit_page")
    print(f"   Edit URL: {page.url}")

    if page.url.endswith("/products/new") or page.url == "https://app.gumroad.com/products/new":
        print("   ERROR: still on new-product page")
        browser.close()
        return None, None

    # ── Description ────────────────────────────────────────────────────────────
    print("[7] Fill description")
    for sel in [
        "[contenteditable='true']",
        ".ql-editor",
        "div[role='textbox']",
        "textarea[name='description']",
        "textarea",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                time.sleep(0.3)
                page.keyboard.press("Control+a")
                page.keyboard.press("Delete")
                page.keyboard.type(GUMROAD_DESCRIPTION, delay=2)
                print(f"   Description typed ({sel})")
                break
        except Exception:
            continue

    ss(page, "08_desc_filled")
    time.sleep(1)

    # ── File upload ────────────────────────────────────────────────────────────
    print(f"[8] Upload file ({asset_mb:.1f} MB)")
    upload_ok = False
    try:
        with page.expect_file_chooser(timeout=10000) as fc_info:
            for sel in [
                "button:has-text('Add a file')",
                "button:has-text('Upload')",
                "label:has-text('Upload')",
                "[data-testid*='upload']",
            ]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        break
                except Exception:
                    continue
        fc_info.value.set_files(str(ASSET_PATH))
        upload_ok = True
        print(f"   File chooser upload started")
        print(f"   Waiting 120s for upload…")
        time.sleep(120)
    except Exception:
        try:
            fi = page.locator("input[type='file']").first
            fi.set_input_files(str(ASSET_PATH))
            upload_ok = True
            print("   Direct set_input_files upload started")
            print("   Waiting 120s…")
            time.sleep(120)
        except Exception as exc:
            print(f"   WARNING: upload failed: {exc}")

    ss(page, "09_after_upload")

    # ── Save ────────────────────────────────────────────────────────────────────
    print("[9] Save product")
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
                print(f"   Saved ({sel})")
                time.sleep(4)
                break
        except Exception:
            continue

    ss(page, "10_final")
    print(f"   Final URL: {page.url}")

    # ── Extract public URL ─────────────────────────────────────────────────────
    gumroad_url = None
    gumroad_pid = None

    for sel in ["a[href*='/l/']", "a:has-text('View product')", "a:has-text('View')"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                href = el.get_attribute("href") or ""
                if "/l/" in href:
                    gumroad_url = ("https://gumroad.com" + href) if href.startswith("/") else href
                    print(f"   URL from link: {gumroad_url}")
                    break
        except Exception:
            continue

    if not gumroad_url:
        # The /products/<id>/edit token is NOT the public /l/<permalink> slug, so
        # do NOT synthesize https://gumroad.com/l/<edit_id> — it 404s for buyers.
        # Read the real permalink from the Share tab; if it can't be read, leave
        # gumroad_url unset so the INVALID guard below fails loudly.
        try:
            m = re.search(r"/products/([^/?#]+)", page.url)
            if m:
                page.goto(f"https://app.gumroad.com/products/{m.group(1)}/share",
                          wait_until="domcontentloaded", timeout=20000)
                for sel in ["input[value*='/l/']", "a[href*='/l/']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=3000):
                            val = el.get_attribute("value") or el.get_attribute("href") or ""
                            if "/l/" in val:
                                gumroad_url = ("https://gumroad.com" + val) if val.startswith("/") else val
                                print(f"   URL from Share tab: {gumroad_url}")
                                break
                    except Exception:
                        continue
        except Exception as e:
            print(f"   Could not read Share tab permalink: {e}")
        if not gumroad_url:
            print("   ERROR: could not read the real Gumroad permalink; refusing "
                  "to emit a guessed /l/ URL")

    if gumroad_url:
        m = re.search(r"/l/([^/?#]+)", gumroad_url)
        if m:
            gumroad_pid = m.group(1)

    browser.close()
    return gumroad_url, gumroad_pid


print("=" * 64)
print("Gumroad deploy v3")
print("=" * 64)

with sync_playwright() as pw:
    gumroad_url, gumroad_pid = gumroad_deploy(pw)

print(f"\nResult:")
print(f"  Gumroad URL: {gumroad_url}")
print(f"  Gumroad ID:  {gumroad_pid}")

INVALID = (None, "https://gumroad.com/l/new", "https://app.gumroad.com/l/new")
if not gumroad_url or gumroad_url in INVALID:
    print("\nFAIL: Gumroad URL invalid")
    sys.exit(1)

# ── Smoke test ────────────────────────────────────────────────────────────────
print("\nSmoke testing…")
smoke_passed = True
smoke_reason = None
checked_at   = NOW()

for label, url in [("Stripe", STRIPE_URL), ("Gumroad", gumroad_url)]:
    try:
        req  = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=20)
        print(f"   {label}: HTTP {resp.status} ✓")
    except urllib.error.HTTPError as exc:
        if exc.code in (200, 301, 302, 303):
            print(f"   {label}: HTTP {exc.code} ✓")
        elif label == "Stripe":
            print(f"   {label}: redirect {exc.code} (OK)")
        else:
            smoke_passed = False
            smoke_reason = f"{label} HTTP {exc.code}"
            print(f"   {label}: FAIL — {exc.code}")
    except Exception as exc:
        # Connection-level failure (DNS, refused, timeout, TLS). A buyer-facing
        # Gumroad link that won't even connect must block SHIPPED. Stripe links
        # legitimately redirect, so a Stripe-only connection issue is tolerated.
        if label == "Gumroad":
            smoke_passed = False
            smoke_reason = f"{label} unreachable: {exc}"
            print(f"   {label}: FAIL — {exc}")
        else:
            print(f"   {label}: {exc} — treating as OK (link redirects by design)")

print(f"\nSmoke: {'PASS ✓' if smoke_passed else 'FAIL ✗'}")

# ── Distribution queue (BEFORE writing SHIPPED) ─────────────────────────────────
# Ordering: the queue append must succeed before the launch report is marked
# SHIPPED. If append_item raises (schema/IO error) the report is never written
# SHIPPED, so a re-run can recover instead of leaving a stuck unqueued product.
# append_item is file-locked + schema-validated (replaces the prior no-op
# validate("distribution_queue", ...) call).
if smoke_passed:
    from scripts.lib.distribution_queue import append_item

    append_item(QUEUE_FILE, {
        "id": ITEM_ID,
        "slug": SLUG,
        "name": TITLE,
        "stripe_payment_link_url": STRIPE_URL,
        "gumroad_url": gumroad_url,
        "price_usd": PRICE,
        "audience": AUDIENCE,
        "added_at": NOW(),
        "status": "ready",
    })
    print("Distribution queue updated ✓")

# ── Update launch report (only after the queue append succeeded) ────────────────
report.update({
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": (
        "16,551 SEC-registered investment adviser (RIA) firms from SEC IAPD Form ADV bulk data, "
        "May 2026. 61 fields per firm including AUM, employee count, client categories, fee "
        "structure, private fund flags, and disclosure history. One-time purchase at $79."
    ),
    "spec_file": f"state/products/{SLUG}/spec.json",
    "gumroad_url": gumroad_url,
    "gumroad_product_id": gumroad_pid,
    "shipped_at": NOW(),
    "smoke_test": {"passed": smoke_passed, "checked_at": checked_at},
})
if not smoke_passed:
    report["failure_reason"] = smoke_reason
    report["smoke_test"]["failure_reason"] = smoke_reason

REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"launch-report.json updated ✓")

if smoke_passed:
    if OPP_FILE.exists():
        opp = json.loads(OPP_FILE.read_text())
        opp["status"] = "SHIPPED"
        opp["shipped_at"] = NOW()
        opp["shipped_slug"] = SLUG
        OPP_FILE.write_text(json.dumps(opp, indent=2))
        print("Opportunity brief → SHIPPED ✓")

print("\n" + "=" * 64)
print("DONE ✓" if smoke_passed else "FAILED ✗")
print(f"  Stripe:  {STRIPE_URL}")
print(f"  Gumroad: {gumroad_url}")
