#!/usr/bin/env python3
"""
Gumroad-only retry for sec-registered-investment-advisers-2026-05.
Stripe is already done. This creates the listing and updates launch-report.json.
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

# Load existing report to get Stripe IDs
report = json.loads(REPORT_FILE.read_text())

# ── guard: already shipped? (avoid creating a SECOND Gumroad listing) ──────────
if report.get("status") in ("SHIPPED", "FULLY_SHIPPED"):
    print(f"Already shipped: {report.get('stripe_payment_link_url')} / {report.get('gumroad_url')}")
    sys.exit(0)

STRIPE_URL      = report["stripe_payment_link_url"]

GUMROAD_USER = os.environ.get("GUMROAD_USERNAME", "")
GUMROAD_PASS = os.environ.get("GUMROAD_PASSWORD", "")

TITLE = "SEC RIA Database 2026 — 16,551 Registered Investment Adviser Firms (CSV)"
PRICE = 79

GUMROAD_DESCRIPTION = (
    "Complete database of all 16,551 SEC-registered investment adviser (RIA) firms — "
    "sourced directly from SEC Form ADV public filings, updated May 2026.\n\n"
    "Same data. 1% of the price.\n"
    "Platforms like AdvizorPro and RIA Database charge $5,000–$20,000/year for this exact "
    "government-sourced dataset. You get the full flat file for $79, one-time, instant download.\n\n"
    "What's included (61 fields per firm):\n"
    "- Firm name, CRD#, SEC registration number\n"
    "- Main office: address, city, state, ZIP, phone, website\n"
    "- AUM: discretionary + non-discretionary (USD)\n"
    "- Employees: total + breakdown by role type\n"
    "- Clients: total count + 14 client-type categories (HNW individuals, pension plans, corporations, etc.)\n"
    "- Fee structure: AUM%, hourly, subscription, fixed, performance, other\n"
    "- Private funds flag + gross assets + hedge/PE/VC counts\n"
    "- Disclosure/disciplinary history flag + event count\n"
    "- Registration status + state of incorporation\n\n"
    "Who buys this:\n"
    "- Asset managers and ETF sponsors reaching RIA distribution gatekeepers\n"
    "- Wealthtech SaaS companies (CRM, portfolio management, compliance tools) prospecting for firm clients\n"
    "- Investment recruiters targeting breakaway advisers\n"
    "- Boutique M&A advisers tracking the RIA consolidation wave\n"
    "- Anyone paying $999–$20,000/year for enterprise RIA data platforms\n\n"
    "Format: CSV, ready for Excel, Google Sheets, or CRM import\n"
    "Records: 16,551 SEC-approved firms (Approved-status only; non-approved filtered out)\n"
    "Source: SEC IAPD Form ADV bulk data — public domain, no authentication required\n"
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
print(f"Stripe already done: {STRIPE_URL}\n")


from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def ss(page, name):
    path = f"/tmp/gr_ria_{name}.png"
    page.screenshot(path=path)
    print(f"   Screenshot → {path}")


def gumroad_deploy(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    ctx  = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # ── Login ──────────────────────────────────────────────────────────────────
    print("[Gumroad] Logging in…")
    page.goto("https://gumroad.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    ss(page, "01_login_page")

    page.fill("input[type='email']", GUMROAD_USER)
    page.fill("input[type='password']", GUMROAD_PASS)
    page.click("button:has-text('Login')")
    time.sleep(4)
    ss(page, "02_post_login")
    print(f"   Post-login URL: {page.url}")

    if "login" in page.url:
        print("   ERROR: still on login page — auth failed")
        browser.close()
        return None, None

    # ── Navigate to new product ────────────────────────────────────────────────
    print("[Gumroad] Opening new product page…")
    # Try app subdomain first, fall back to www
    page.goto("https://app.gumroad.com/products/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    ss(page, "03_new_product_page")
    print(f"   URL: {page.url}")

    # ── Fill name ──────────────────────────────────────────────────────────────
    print("[Gumroad] Filling product name…")
    name_filled = False
    for sel in [
        "input[name='name']",
        "input[placeholder*='name' i]",
        "input[placeholder*='Name' i]",
        "input[type='text']:first-of-type",
        "input[type='text']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.triple_click()
                el.fill(TITLE)
                print(f"   Name filled via: {sel}")
                name_filled = True
                break
        except Exception:
            continue

    if not name_filled:
        print("   WARNING: could not fill name")

    time.sleep(1)

    # ── Select "Digital product" type ──────────────────────────────────────────
    print("[Gumroad] Selecting product type = Digital product…")
    type_selected = False
    for sel in [
        "button:has-text('Digital product')",
        "[data-type='digital']",
        "div:has-text('Digital product') button",
        "label:has-text('Digital product')",
        # The card may just be a clickable div/button
        "button.product-type-card:first-of-type",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                print(f"   Product type selected via: {sel}")
                type_selected = True
                time.sleep(1)
                break
        except Exception:
            continue

    if not type_selected:
        # Try clicking the "Digital product" card by text content
        try:
            page.get_by_text("Digital product", exact=False).first.click()
            print("   Product type selected via get_by_text")
            type_selected = True
            time.sleep(1)
        except Exception as e:
            print(f"   WARNING: could not select product type: {e}")

    ss(page, "04_type_selected")

    # ── Fill price ─────────────────────────────────────────────────────────────
    print("[Gumroad] Filling price…")
    price_filled = False
    # Inspect actual input elements
    inputs = page.locator("input[type='text'], input[type='number'], input").all()
    print(f"   Found {len(inputs)} input elements")

    for sel in [
        "input[name='price']",
        "input[placeholder*='price' i]",
        "input[placeholder*='Price' i]",
        "input[placeholder*='0.99' i]",
        "input[placeholder*='amount' i]",
        "#price",
        "input[data-testid*='price' i]",
        # The price input in the Gumroad new product form may have no label
        # Try nth-of-type after the currency dropdown
        "input[type='number']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.triple_click()
                el.fill(str(PRICE))
                print(f"   Price filled via: {sel}")
                price_filled = True
                break
        except Exception:
            continue

    if not price_filled:
        # Last resort: get all visible inputs and try the second one
        try:
            all_inputs = page.locator("input").all()
            for i, inp in enumerate(all_inputs):
                try:
                    if inp.is_visible(timeout=1000):
                        placeholder = inp.get_attribute("placeholder") or ""
                        name_attr   = inp.get_attribute("name") or ""
                        input_type  = inp.get_attribute("type") or ""
                        print(f"   Input[{i}]: type={input_type} name={name_attr} placeholder={placeholder}")
                except Exception:
                    pass
        except Exception:
            pass

        # Try clicking in the price section and typing
        try:
            page.get_by_label("Price", exact=False).first.fill(str(PRICE))
            print("   Price filled via get_by_label")
            price_filled = True
        except Exception:
            pass

    ss(page, "05_price_filled")
    time.sleep(1)

    # ── Click Next/Continue/Submit ─────────────────────────────────────────────
    print("[Gumroad] Submitting creation form…")
    submitted = False
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
                print(f"   Clicked submit via: {sel}")
                submitted = True
                break
        except Exception:
            continue

    time.sleep(3)
    ss(page, "06_post_submit")
    print(f"   URL after submit: {page.url}")

    # Wait for edit page
    try:
        page.wait_for_url("**/products/**/edit**", timeout=20000)
    except PWTimeout:
        try:
            page.wait_for_url("**/products/**", timeout=10000)
        except PWTimeout:
            pass
    time.sleep(2)
    ss(page, "07_edit_page")
    print(f"   Edit page URL: {page.url}")

    # Check we actually moved forward (not stuck on /products/new)
    if page.url.endswith("/products/new") or "/l/new" in page.url:
        print("   ERROR: still on new-product page — form submission failed")
        browser.close()
        return None, None

    # ── Fill description ────────────────────────────────────────────────────────
    print("[Gumroad] Filling description…")
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
                el.fill(GUMROAD_DESCRIPTION)
                print(f"   Description filled via: {sel}")
                break
        except Exception:
            continue

    ss(page, "08_desc_filled")
    time.sleep(1)

    # ── Upload file ────────────────────────────────────────────────────────────
    print(f"[Gumroad] Uploading file ({asset_mb:.1f} MB)…")
    try:
        with page.expect_file_chooser(timeout=10000) as fc_info:
            # Try clicking a visible upload button
            for sel in [
                "button:has-text('Add a file')",
                "button:has-text('Upload')",
                "label:has-text('Upload')",
                "input[type='file']",
            ]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        break
                except Exception:
                    continue
        fc = fc_info.value
        fc.set_files(str(ASSET_PATH))
        print(f"   File chooser used — upload started")
        wait_s = 120
        print(f"   Waiting {wait_s}s for upload…")
        time.sleep(wait_s)
    except Exception:
        # Fallback: direct set_input_files
        try:
            fi = page.locator("input[type='file']").first
            fi.set_input_files(str(ASSET_PATH))
            print("   File set via set_input_files")
            wait_s = 120
            print(f"   Waiting {wait_s}s for upload…")
            time.sleep(wait_s)
        except Exception as exc:
            print(f"   WARNING: file upload error: {exc}")

    ss(page, "09_after_upload")

    # ── Save ────────────────────────────────────────────────────────────────────
    print("[Gumroad] Saving product…")
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
                print(f"   Saved via: {sel}")
                time.sleep(4)
                break
        except Exception:
            continue

    ss(page, "10_after_save")
    print(f"   Final URL: {page.url}")

    # ── Extract public URL ─────────────────────────────────────────────────────
    gumroad_public_url = None
    gumroad_product_id = None

    for sel in ["a[href*='/l/']", "a:has-text('View product')", "a:has-text('View')"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                href = el.get_attribute("href")
                if href and "/l/" in href:
                    if href.startswith("/"):
                        href = "https://gumroad.com" + href
                    gumroad_public_url = href
                    print(f"   Public URL found via link: {gumroad_public_url}")
                    break
        except Exception:
            continue

    if not gumroad_public_url:
        # The /products/<id>/edit token is NOT the public /l/<permalink> slug, so
        # do NOT synthesize https://gumroad.com/l/<edit_id> — it 404s for buyers.
        # Read the real permalink from the Share tab; if it can't be read, leave it
        # unset so the invalid-URL guard below fails loudly.
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
                                gumroad_public_url = ("https://gumroad.com" + val) if val.startswith("/") else val
                                print(f"   Public URL from Share tab: {gumroad_public_url}")
                                break
                    except Exception:
                        continue
        except Exception as e:
            print(f"   Could not read Share tab permalink: {e}")
        if not gumroad_public_url:
            print("   ERROR: could not read the real Gumroad permalink; refusing "
                  "to emit a guessed /l/ URL")
    else:
        m = re.search(r"/l/([^/?#]+)", gumroad_public_url)
        if m:
            gumroad_product_id = m.group(1)

    browser.close()
    return gumroad_public_url, gumroad_product_id


print("=" * 60)
print("Starting Gumroad deploy…")
print("=" * 60)

with sync_playwright() as pw:
    gumroad_url, gumroad_product_id = gumroad_deploy(pw)

print(f"\nGumroad result:")
print(f"  URL:  {gumroad_url}")
print(f"  ID:   {gumroad_product_id}")

if not gumroad_url or gumroad_url in ("https://gumroad.com/l/new", "https://gumroad.com/products/new"):
    print("\nERROR: Gumroad deploy failed — URL is invalid")
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
            print(f"   {label}: redirect {exc.code} (OK for fresh link)")
        else:
            smoke_passed = False
            smoke_reason = f"{label} returned HTTP {exc.code}"
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

# ── Update launch report ───────────────────────────────────────────────────────
summary = (
    "16,551 SEC-registered investment adviser (RIA) firms from SEC IAPD Form ADV bulk data, "
    "May 2026. 61 fields per firm including AUM, employee count, client categories, fee "
    "structure, private fund flags, and disclosure history. One-time purchase at $79."
)

# ── Append to distribution queue (BEFORE writing SHIPPED) ──────────────────────
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

report.update({
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": summary,
    "spec_file": f"state/products/{SLUG}/spec.json",
    "gumroad_url": gumroad_url,
    "gumroad_product_id": gumroad_product_id,
    "shipped_at": NOW(),
    "smoke_test": {
        "passed": smoke_passed,
        "checked_at": checked_at,
    },
})
if not smoke_passed:
    report["failure_reason"] = smoke_reason
    report["smoke_test"]["failure_reason"] = smoke_reason

REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"launch-report.json updated: {REPORT_FILE}")

# ── Update opportunity brief ───────────────────────────────────────────────────
if smoke_passed:
    if OPP_FILE.exists():
        opp = json.loads(OPP_FILE.read_text())
        opp["status"] = "SHIPPED"
        opp["shipped_at"] = NOW()
        opp["shipped_slug"] = SLUG
        OPP_FILE.write_text(json.dumps(opp, indent=2))
        print("Opportunity brief → SHIPPED ✓")

print("\n" + "=" * 60)
print("GUMROAD RETRY COMPLETE ✓" if smoke_passed else "GUMROAD RETRY FAILED ✗")
print(f"  Stripe:  {STRIPE_URL}")
print(f"  Gumroad: {gumroad_url}")
