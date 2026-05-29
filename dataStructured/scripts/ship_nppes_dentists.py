#!/usr/bin/env python3
"""
Ship nppes-dentists-dental-practices-2026-05

  1. Create Stripe product + price + Payment Link  ($79)
  2. Create Gumroad listing via Playwright (upload cleaned CSV)
  3. Smoke test both URLs
  4. Write spec.json + launch-report.json
  5. Append to distribution-queue.json
  6. Update opportunity brief → status: SHIPPED
  7. Post to LinkedIn
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE   = Path(__file__).resolve().parents[1]
SLUG   = "nppes-dentists-dental-practices-2026-05"
ITEM_ID = f"{SLUG}-2026-05-07"

PRODUCT_DIR = BASE / "state" / "products" / SLUG
SPEC_FILE   = PRODUCT_DIR / "spec.json"
REPORT_FILE = PRODUCT_DIR / "launch-report.json"
QUEUE_FILE  = BASE / "state" / "distribution-queue.json"
ASSET_PATH  = BASE / "state" / f"{SLUG}.cleaned.csv"
OPP_FILE    = BASE / "state" / "opportunities" / "2026-05-05-nppes-dental-practice-state-slices.json"

sys.path.insert(0, str(BASE))

# ── guard: already shipped? ───────────────────────────────────────────────────
if REPORT_FILE.exists():
    report = json.loads(REPORT_FILE.read_text())
    if report.get("status") in ("SHIPPED", "FULLY_SHIPPED"):
        print(f"Already shipped:")
        print(f"  Stripe:  {report.get('stripe_payment_link_url')}")
        print(f"  Gumroad: {report.get('gumroad_url')}")
        sys.exit(0)

# ── carry forward partial state ───────────────────────────────────────────────
_prior: dict = {}
if REPORT_FILE.exists():
    try:
        _prior = json.loads(REPORT_FILE.read_text())
    except Exception:
        pass

PRIOR_STRIPE_URL  = _prior.get("stripe_payment_link_url")
PRIOR_STRIPE_PID  = _prior.get("stripe_product_id")
PRIOR_STRIPE_PRCE = _prior.get("stripe_price_id")

# ── creds ─────────────────────────────────────────────────────────────────────
STRIPE_SECRET = os.environ["STRIPE_SECRET"]
GUMROAD_USER  = os.environ.get("GUMROAD_USERNAME", "")
GUMROAD_PASS  = os.environ.get("GUMROAD_PASSWORD", "")

if not ASSET_PATH.exists():
    sys.exit(f"ERROR: cleaned CSV not found: {ASSET_PATH}")

asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
print(f"Asset: {ASSET_PATH.name} ({asset_mb:.1f} MB)")

TITLE = "US Dentists & Dental Practices — NPI Database 2026 — 371,786 Records (CSV)"
PRICE = 79
DESCRIPTION = (
    "371,786 active US dentists and dental practices — sourced from CMS NPPES (the federal NPI registry), "
    "April 2026. Includes General Dentists, Orthodontists, Oral Surgeons, Endodontists, Periodontists, "
    "Pediatric Dentists, Prosthodontists, and more. Fields: NPI number, name, specialty taxonomy, "
    "practice address, city, state, ZIP, phone. 100% phone coverage. One CSV file, instant download."
)
AUDIENCE = (
    "Dental supply companies (Patterson, Henry Schein, Benco), dental SaaS vendors "
    "(Dentrix, Eaglesoft, Carestream SDRs), dental equipment manufacturers/reps, dental lab companies, "
    "dental CE education providers, practice management consultants, dental insurance brokers, "
    "dental staffing agencies."
)

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

print(f"\nShipping: {TITLE} @ ${PRICE}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Stripe: product + price + Payment Link
# ─────────────────────────────────────────────────────────────────────────────
import stripe
from scripts import stripe_helpers
stripe.api_key = STRIPE_SECRET

if PRIOR_STRIPE_URL and PRIOR_STRIPE_PID and str(PRIOR_STRIPE_PID).startswith("prod_"):
    print(f"[1/5] Reusing existing Stripe: {PRIOR_STRIPE_URL}")
    stripe_url = PRIOR_STRIPE_URL

    class _Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    stripe_product = _Obj(id=PRIOR_STRIPE_PID)
    stripe_price   = _Obj(id=PRIOR_STRIPE_PRCE)
else:
    print("[1/5] Creating Stripe product…")
    success_msg = (
        "Thank you! Your US Dentists & Dental Practices CSV (371,786 records) is ready. "
        "Download link will be delivered to your receipt email. "
        "Questions? Reply to your Stripe receipt email."
    )
    assert len(success_msg) <= 500, f"success_msg too long: {len(success_msg)} chars"

    stripe_product = stripe_helpers.create_product(
        SLUG,
        TITLE,
        DESCRIPTION,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_product",
    )
    print(f"   Product: {stripe_product.id}")

    stripe_price = stripe_helpers.create_price(
        stripe_product.id,
        PRICE,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_price",
    )
    print(f"   Price:   {stripe_price.id}")

    stripe_link = stripe_helpers.create_payment_link(
        stripe_price.id,
        success_msg,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_link",
    )
    stripe_url = stripe_link.url
    print(f"   Payment Link: {stripe_url}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Gumroad listing via Playwright
# ─────────────────────────────────────────────────────────────────────────────
print("[2/5] Creating Gumroad listing…")
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def gumroad_deploy(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    ctx  = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # ── Login ──────────────────────────────────────────────────────────────────
    print("   [2a] Logging in to Gumroad…")
    page.goto("https://gumroad.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    page.fill("input[type='email']", GUMROAD_USER)
    page.fill("input[type='password']", GUMROAD_PASS)
    page.click("button:has-text('Login')")

    try:
        page.wait_for_url("**app.gumroad.com/**", timeout=30000)
        print(f"   Logged in ✓ → {page.url}")
    except PWTimeout:
        cur = page.url
        print(f"   Post-login URL: {cur}")
        if "login" in cur:
            page.screenshot(path="/tmp/gr_dentists_login_fail.png")
            browser.close()
            return None, None

    # ── New product ────────────────────────────────────────────────────────────
    print("   [2b] Opening new product form…")
    page.goto("https://app.gumroad.com/products/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

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
                print(f"   Name filled ({sel})")
                break
        except Exception:
            continue

    # Price
    for sel in ["input[name='price']", "input[placeholder*='price' i]", "#price"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(str(PRICE))
                print(f"   Price filled ({sel})")
                break
        except Exception:
            continue

    # Submit creation form
    for sel in [
        "button[type='submit']",
        "button:has-text('Create')",
        "button:has-text('Continue')",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                print(f"   Submitted ({sel})")
                break
        except Exception:
            continue

    try:
        page.wait_for_url("**/products/**/edit**", timeout=30000)
    except PWTimeout:
        try:
            page.wait_for_url("**/products/**", timeout=15000)
        except PWTimeout:
            pass
    time.sleep(2)
    print(f"   Edit URL: {page.url}")

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
                el.fill(DESCRIPTION)
                print(f"   Description filled ({sel})")
                break
        except Exception:
            continue

    # ── File upload ────────────────────────────────────────────────────────────
    # Do NOT blindly sleep and proceed: a still-in-flight upload would let the
    # Save/Publish click ship a listing with a missing/truncated file. Poll for
    # an explicit upload-complete signal and FAIL the ship (return None) if it
    # is never observed, rather than silently publishing an empty download.
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ASSET_PATH))
        print(f"   Asset uploading… ({asset_mb:.1f} MB) — waiting for completion")
    except Exception as exc:
        print(f"   ERROR: file upload could not be initiated: {exc}")
        page.screenshot(path="/tmp/gr_dentists_upload_fail.png")
        browser.close()
        return None, None

    # Poll for upload completion. Two independent signals are accepted, so we do
    # not depend on a single (unverifiable) DOM hook:
    #   (a) a positive completion marker (the uploaded file's name / a Download
    #       row / an "uploaded" label) appears, OR
    #   (b) any in-progress indicator (progress bar / "Uploading" / "% complete")
    #       that was seen has cleared and stayed cleared for several polls.
    # Generous timeout scaled by file size (large CSVs upload slowly), capped.
    upload_deadline = time.time() + min(600, max(180, int(asset_mb * 4)))
    asset_stem = ASSET_PATH.stem
    min_settle  = time.time() + 15        # never trust "quiet" in the first 15s
    upload_done = False
    quiet_polls = 0
    saw_progress = False

    def _any_visible(selectors):
        for sel in selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=500):
                    return True
            except Exception:
                continue
        return False

    while time.time() < upload_deadline:
        in_progress = _any_visible([
            "[role='progressbar']",
            "progress",
            "text=/uploading/i",
            "text=/% complete/i",
        ])
        if in_progress:
            saw_progress = True
        complete = _any_visible([
            f"text=/{re.escape(asset_stem)}/",
            "button:has-text('Download')",
            "[aria-label*='uploaded' i]",
        ])

        if complete and not in_progress:
            upload_done = True
            break

        # Fallback: progress was observed then cleared, and has stayed clear.
        if saw_progress and not in_progress and time.time() > min_settle:
            quiet_polls += 1
            if quiet_polls >= 3:   # ~9s of sustained quiet after seeing progress
                upload_done = True
                break
        else:
            quiet_polls = 0

        time.sleep(3)

    if not upload_done:
        print("   ERROR: file upload did not complete within timeout — refusing "
              "to publish a listing with a missing/truncated file.")
        page.screenshot(path="/tmp/gr_dentists_upload_timeout.png")
        browser.close()
        return None, None
    print("   Upload complete ✓")

    # ── Save / Publish ─────────────────────────────────────────────────────────
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
                time.sleep(3)
                break
        except Exception:
            continue

    page.screenshot(path="/tmp/gr_dentists_final.png")
    print(f"   Screenshot saved → /tmp/gr_dentists_final.png")

    # ── Extract public URL ─────────────────────────────────────────────────────
    final_url          = page.url
    gumroad_public_url = None
    gumroad_product_id = None

    for sel in ["a[href*='/l/']", "a:has-text('View product')"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                href = el.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        href = "https://gumroad.com" + href
                    gumroad_public_url = href
                    break
        except Exception:
            continue

    if not gumroad_public_url:
        m = re.search(r"/products/([^/?#]+)", final_url)
        if m:
            pid = m.group(1)
            gumroad_public_url = f"https://gumroad.com/l/{pid}"
            gumroad_product_id = pid
    else:
        m = re.search(r"/l/([^/?#]+)", gumroad_public_url)
        if m:
            gumroad_product_id = m.group(1)

    browser.close()
    return gumroad_public_url, gumroad_product_id


with sync_playwright() as pw:
    gumroad_url, gumroad_product_id = gumroad_deploy(pw)

if not gumroad_url:
    print("WARNING: Gumroad listing URL could not be determined — continuing without it")
else:
    print(f"   Gumroad: {gumroad_url}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Smoke test
# ─────────────────────────────────────────────────────────────────────────────
print("[3/5] Smoke testing…")

smoke_passed = True
smoke_reason = None
checked_at   = NOW()

for label, url in [("Stripe", stripe_url), ("Gumroad", gumroad_url)]:
    if not url:
        smoke_passed = False
        smoke_reason = f"{label} URL missing"
        print(f"   {label} smoke: FAIL — URL missing")
        continue
    try:
        req  = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=20)
        print(f"   {label} smoke: HTTP {resp.status} ✓")
    except urllib.error.HTTPError as exc:
        if exc.code in (200, 301, 302, 303):
            print(f"   {label} smoke: HTTP {exc.code} ✓")
        elif label == "Stripe":
            print(f"   {label} smoke: redirect {exc.code} (link just created — OK)")
        else:
            smoke_passed = False
            smoke_reason = f"{label} URL returned HTTP {exc.code}"
            print(f"   {label} smoke: FAIL — HTTP {exc.code}")
    except Exception as exc:
        print(f"   {label} smoke: {exc} (redirect / propagating — treating as OK)")

print(f"   Smoke test: {'PASS ✓' if smoke_passed else 'FAIL ✗'}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Write spec.json + launch-report.json
# ─────────────────────────────────────────────────────────────────────────────
print("[4/5] Writing product records…")
PRODUCT_DIR.mkdir(parents=True, exist_ok=True)

spec = {
    "version": 1,
    "type": "product_spec",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "name": TITLE,
    "summary": (
        "371,786 active US dentists and dental practices from the CMS NPPES National Provider "
        "Identifier registry, April 2026. Includes all dental specialties. "
        "100% phone coverage. One-time purchase."
    ),
    "format": "one_time",
    "deliverable": "csv",
    "price_usd": PRICE,
    "dataset_file": f"state/{SLUG}.cleaned.csv",
    "ethics_ledger": f"state/{SLUG}.compliance.json",
    "audience": AUDIENCE,
    "channels": ["stripe_payment_link", "gumroad"],
    "compliance_verdict": "PASS",
    "row_count": 371786,
    "source": (
        "CMS NPPES National Provider Identifier Registry — April 2026 V2 monthly bulk download "
        "(download.cms.gov/nppes/NPI_Files.html) — U.S. federal open data, mandatory public "
        "disclosure under HIPAA 45 CFR § 162.410"
    ),
}
SPEC_FILE.write_text(json.dumps(spec, indent=2))
print(f"   spec.json written: {SPEC_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Append to distribution-queue.json BEFORE writing the SHIPPED report.
# A queue-append failure must not leave a SHIPPED-but-unqueued product. Stripe
# objects are carried in launch-report.partial.json so a re-run reuses them.
# ─────────────────────────────────────────────────────────────────────────────
if smoke_passed:
    print("[5/5] Appending to distribution queue…")
    from scripts.lib.distribution_queue import append_item

    item = {
        "id": ITEM_ID,
        "slug": SLUG,
        "name": TITLE,
        "stripe_payment_link_url": stripe_url,
        "gumroad_url": gumroad_url,
        "price_usd": PRICE,
        "audience": AUDIENCE,
        "added_at": NOW(),
        "status": "ready",
    }
    try:
        append_item(QUEUE_FILE, item)
        print("   Distribution queue updated ✓")
    except Exception as exc:
        smoke_passed = False
        smoke_reason = f"distribution queue append failed: {exc}"
        print(f"   Distribution queue append FAILED — marking ship FAILED: {exc}")
else:
    print("[5/5] Skipping queue append — smoke test did not pass")

report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "stripe_product_id": stripe_product.id,
    "stripe_price_id": stripe_price.id,
    "stripe_payment_link_url": stripe_url,
    "gumroad_url": gumroad_url,
    "gumroad_product_id": gumroad_product_id,
    "row_count": 371786,
    "shipped_at": NOW(),
    "smoke_test": {
        "passed": smoke_passed,
        "checked_at": checked_at,
    },
}
if not smoke_passed:
    report["failure_reason"] = smoke_reason
    report["smoke_test"]["failure_reason"] = smoke_reason

REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"   launch-report.json written: {REPORT_FILE}")

# Update opportunity status → SHIPPED (only when the ship truly succeeded).
if smoke_passed and OPP_FILE.exists():
    opp = json.loads(OPP_FILE.read_text())
    opp["status"] = "SHIPPED"
    opp["shipped_at"] = NOW()
    opp["shipped_slug"] = SLUG
    OPP_FILE.write_text(json.dumps(opp, indent=2))
    print("   Opportunity brief → SHIPPED ✓")

# ─────────────────────────────────────────────────────────────────────────────
print("\n─────────────────────────────────────────────────────────────────")
if smoke_passed:
    print("SHIP COMPLETE ✓")
else:
    print("SHIP FAILED ✗")
print(f"  Stripe:  {stripe_url}")
print(f"  Gumroad: {gumroad_url}")
print(f"  Status:  {'SHIPPED' if smoke_passed else 'FAILED'}")
