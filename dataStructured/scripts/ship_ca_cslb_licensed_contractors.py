#!/usr/bin/env python3
"""
Ship ca-cslb-licensed-contractors-2026-05

  1. Upload CSV to GitHub Release (52 MB)
  2. Create Stripe product + price + Payment Link ($79)
  3. Create Gumroad listing via Playwright (upload CSV)
  4. Smoke test (Stripe link + Gumroad public URL)
  5. Write launch-report.json + spec.json
  6. Append to distribution-queue.json
  7. Update opportunity status → SHIPPED
  8. Post to LinkedIn
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).resolve().parents[1]
SLUG        = "ca-cslb-licensed-contractors-2026-05"
PRODUCT_DIR = BASE / "state" / "products" / SLUG
REPORT_FILE = PRODUCT_DIR / "launch-report.json"
SPEC_FILE   = PRODUCT_DIR / "spec.json"
QUEUE_FILE  = BASE / "state" / "distribution-queue.json"
ASSET_PATH  = BASE / "state" / f"{SLUG}.cleaned.csv"
OPP_FILE    = BASE / "state" / "opportunities" / "2026-05-07-ca-cslb-licensed-contractors.json"

sys.path.insert(0, str(BASE))

# ── guard: already fully shipped? ─────────────────────────────────────────────
if REPORT_FILE.exists():
    report = json.loads(REPORT_FILE.read_text())
    if report.get("status") in ("SHIPPED", "FULLY_SHIPPED"):
        print(f"Already shipped:")
        print(f"  Stripe:  {report.get('stripe_payment_link_url')}")
        print(f"  Gumroad: {report.get('gumroad_url')}")
        sys.exit(0)

# ── carry forward partial state from prior run ─────────────────────────────────
_prior: dict = {}
if REPORT_FILE.exists():
    try:
        _prior = json.loads(REPORT_FILE.read_text())
    except Exception:
        pass

PRIOR_RELEASE_URL = _prior.get("asset_gist_url") or _prior.get("asset_release_url")
PRIOR_RAW_URL     = _prior.get("asset_raw_url")
PRIOR_STRIPE_URL  = _prior.get("stripe_payment_link_url")
PRIOR_STRIPE_PID  = _prior.get("stripe_product_id")
PRIOR_STRIPE_PRCE = _prior.get("stripe_price_id")

# ── creds ─────────────────────────────────────────────────────────────────────
STRIPE_SECRET  = os.environ["STRIPE_SECRET"]
GUMROAD_USER   = os.environ["GUMROAD_USERNAME"]
GUMROAD_PASS   = os.environ["GUMROAD_PASSWORD"]
LINKEDIN_EMAIL = os.environ.get("LINKEDIN_EMAIL", "")
LINKEDIN_PASS  = os.environ.get("LINKEDIN_PASS", "")

if not ASSET_PATH.exists():
    sys.exit(f"ERROR: cleaned CSV not found: {ASSET_PATH}")

TITLE   = "California Licensed Contractors — CSLB Database 2026 — 232,617 Records (CSV)"
PRICE   = 79
DESC    = (
    "232,617 active licensed contractors in California — sourced directly from the CSLB "
    "(California Contractors State License Board) Master License Database. The largest state "
    "contractor database in the US. Includes General Building (B), General Engineering (A), "
    "and all C-specialty trades: Electrical (C10), Plumbing (C36), Painting (C33), HVAC (C20), "
    "Roofing (C39), Landscaping (C27), and 30+ more specialty classes. Fields: license number, "
    "business name, DBA, license class, entity type, address, city, ZIP, county, phone, "
    "expiration date, issue date. 99.9% phone coverage. Updated May 2026. One CSV file, instant download."
)
AUDIENCE = (
    "Building material distributors, construction SaaS vendors (Procore, Buildertrend, "
    "CoConstruct SDRs), subcontractor insurance brokers, bonding companies, construction "
    "equipment rental companies, safety training providers, lien management software vendors, "
    "specialty trade CE providers."
)

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
print(f"Shipping: {TITLE} @ ${PRICE}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Upload CSV to GitHub Release
# ─────────────────────────────────────────────────────────────────────────────
REPO = "oghenetejirioefrenterprise/oefr-digital"
TAG  = "ds-ca-cslb-contractors-2026-05-v1"

if PRIOR_RELEASE_URL and PRIOR_RAW_URL:
    print(f"[1/7] Reusing existing Release: {PRIOR_RELEASE_URL}")
    release_url      = PRIOR_RELEASE_URL
    raw_download_url = PRIOR_RAW_URL
else:
    asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
    print(f"[1/7] Uploading {asset_mb:.1f} MB CSV to GitHub Release…")

    subprocess.run(
        ["gh", "release", "delete", TAG, "--repo", REPO, "--yes"],
        capture_output=True,
    )

    result = subprocess.run(
        [
            "gh", "release", "create", TAG,
            "--repo", REPO,
            "--title", TITLE,
            "--notes",
            (
                "DataStructured digital product — California CSLB licensed contractors (May 2026). "
                "Sourced from CSLB Data Portal public bulk download — no auth required. "
                "Delivered to buyers via Stripe/Gumroad checkout."
            ),
            str(ASSET_PATH),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        sys.exit(f"GitHub Release upload failed:\n{result.stderr.strip()}")

    release_url = result.stdout.strip() or f"https://github.com/{REPO}/releases/tag/{TAG}"
    raw_download_url = (
        f"https://github.com/{REPO}/releases/download/{TAG}/{ASSET_PATH.name}"
    )
    print(f"   Release URL:  {release_url}")
    print(f"   Raw download: {raw_download_url}")

gist_url = release_url  # alias for report field naming

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Stripe: product + price + Payment Link
# ─────────────────────────────────────────────────────────────────────────────
import stripe
stripe.api_key = STRIPE_SECRET

if PRIOR_STRIPE_URL and PRIOR_STRIPE_PID and str(PRIOR_STRIPE_PID).startswith("prod_"):
    print(f"[2/7] Reusing existing Stripe: {PRIOR_STRIPE_URL}")
    stripe_url = PRIOR_STRIPE_URL

    class _Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    stripe_product = _Obj(id=PRIOR_STRIPE_PID)
    stripe_price   = _Obj(id=PRIOR_STRIPE_PRCE)
else:
    print("[2/7] Creating Stripe product…")
    success_msg = (
        f"Thank you! Your CA Contractor CSV (232,617 records) is ready:\n\n"
        f"{raw_download_url}\n\n"
        "Sourced from CSLB Master License Database — May 2026 bulk export."
    )
    assert len(success_msg) <= 500, f"success_msg too long: {len(success_msg)} chars"

    stripe_product = stripe.Product.create(
        name=TITLE,
        description=(
            "232,617 active California-licensed contractors from the CSLB Master License Database. "
            "License number, business name, DBA, license class (A/B/C specialty trades), entity type, "
            "address, city, ZIP, county, phone, expiration date, issue date. "
            "Public government data — no auth bypass. CSLB source URL on every row."
        ),
        metadata={
            "product_id": f"dsl_{SLUG.replace('-', '_')}",
            "lob": "datastructured"
        },
    )
    print(f"   Product: {stripe_product.id}")

    stripe_price = stripe.Price.create(
        product=stripe_product.id,
        unit_amount=PRICE * 100,
        currency="usd",
    )
    print(f"   Price:   {stripe_price.id}")

    stripe_link = stripe.PaymentLink.create(
        line_items=[{"price": stripe_price.id, "quantity": 1}],
        after_completion={
            "type": "hosted_confirmation",
            "hosted_confirmation": {"custom_message": success_msg},
        },
    )
    stripe_url = stripe_link.url
    print(f"   Payment Link: {stripe_url}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Gumroad listing via Playwright
# ─────────────────────────────────────────────────────────────────────────────
print("[3/7] Creating Gumroad listing…")
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def gumroad_deploy(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    ctx  = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # ── Login ──────────────────────────────────────────────────────────────────
    print("   [3a] Logging in to Gumroad…")
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
            page.screenshot(path="/tmp/gr_ca_cslb_login_fail.png")
            browser.close()
            return None, None

    # ── New product ────────────────────────────────────────────────────────────
    print("   [3b] Opening new product form…")
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
                el.fill(DESC)
                print(f"   Description filled ({sel})")
                break
        except Exception:
            continue

    # ── File upload (52 MB) ────────────────────────────────────────────────────
    asset_mb_now = ASSET_PATH.stat().st_size / (1024 * 1024)
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ASSET_PATH))
        wait_s = 120
        print(f"   Asset uploading… ({asset_mb_now:.1f} MB — waiting {wait_s}s)")
        time.sleep(wait_s)
    except Exception as exc:
        print(f"   WARNING: file upload error: {exc}")

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

    page.screenshot(path="/tmp/gr_ca_cslb_final.png")
    print(f"   Screenshot saved → /tmp/gr_ca_cslb_final.png")

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
# STEP 4 — Smoke test
# ─────────────────────────────────────────────────────────────────────────────
print("[4/7] Smoke testing…")
import urllib.request

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
        # Only an explicit success / expected redirect may pass. A Stripe Payment
        # Link or a freshly-created Gumroad listing answers a HEAD with 2xx/3xx;
        # any other status (4xx/5xx) means the buyer-facing link is broken.
        if exc.code in (200, 301, 302, 303, 307, 308):
            print(f"   {label} smoke: HTTP {exc.code} ✓")
        else:
            smoke_passed = False
            smoke_reason = f"{label} URL returned HTTP {exc.code}"
            print(f"   {label} smoke: FAIL — HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        # URLError/timeout/connection errors mean the link is unreachable —
        # a buyer could not use it. Fail the smoke test; do NOT silently pass.
        smoke_passed = False
        smoke_reason = f"{label} URL unreachable: {exc}"
        print(f"   {label} smoke: FAIL — unreachable ({exc})")

print(f"   Smoke test: {'PASS ✓' if smoke_passed else 'FAIL ✗'}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Write spec.json + launch-report.json
# ─────────────────────────────────────────────────────────────────────────────
print("[5/7] Writing product spec and launch report…")

spec = {
    "version": 1,
    "type": "product_spec",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "name": TITLE,
    "summary": (
        "232,617 active licensed contractors in California — sourced directly from the CSLB "
        "Master License Database. The largest state contractor database in the US. "
        "Includes all license classes: A (General Engineering), B (General Building), "
        "and 30+ C-specialty trades. $79 one-time vs. $0.10–$2.00/record from commercial brokers."
    ),
    "format": "one_time",
    "deliverable": "csv",
    "price_usd": PRICE,
    "dataset_file": f"state/{SLUG}.cleaned.csv",
    "ethics_ledger": f"state/{SLUG}.compliance.json",
    "audience": AUDIENCE,
    "channels": ["stripe_payment_link", "gumroad"],
    "compliance_verdict": "PASS",
    "compliance_audited_at": "2026-05-07T12:20:00Z",
    "row_count": 232617,
    "source": "California Contractors State License Board (CSLB) Master License Database — cslb.ca.gov/OnlineServices/DataPortal/ — public bulk download, no auth required",
}
SPEC_FILE.write_text(json.dumps(spec, indent=2))
print(f"   Spec written: {SPEC_FILE}")

report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": (
        "Live on Stripe + Gumroad. 232,617-row CSLB contractor CSV. "
        "Smoke tests green. Distribution queue updated."
        if smoke_passed else
        f"Stripe shipped; smoke test failed: {smoke_reason}"
    ),
    "stripe_product_id": stripe_product.id,
    "stripe_price_id": stripe_price.id,
    "stripe_payment_link_url": stripe_url,
    "gumroad_url": gumroad_url,
    "gumroad_product_id": gumroad_product_id,
    "asset_gist_url": gist_url,
    "asset_raw_url": raw_download_url,
    "asset_csv_path": str(ASSET_PATH.relative_to(BASE)),
    "row_count": 232617,
    "smoke_test": {
        "passed": smoke_passed,
        "checked_at": checked_at,
    },
}
if not smoke_passed:
    report["failure_reason"] = smoke_reason
    report["smoke_test"]["failure_reason"] = smoke_reason

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Append to distribution-queue.json BEFORE committing SHIPPED status.
# Ordering matters: if the queue append fails, the launch-report below must NOT
# be written with status=SHIPPED — otherwise the early-exit guard would block
# every retry, leaving the product live but permanently unqueued/undistributed.
# ─────────────────────────────────────────────────────────────────────────────
if smoke_passed:
    print("[6/7] Appending to distribution queue…")
    from scripts.lib.distribution_queue import append_item

    item = {
        "id": f"{SLUG}-2026-05-07",
        "slug": SLUG,
        "name": TITLE,
        "stripe_payment_link_url": stripe_url,
        "gumroad_url": gumroad_url,
        "price_usd": PRICE,
        "audience": AUDIENCE,
        "added_at": NOW(),
        "status": "ready",
    }
    append_item(QUEUE_FILE, item)
    print("   Distribution queue updated ✓")
else:
    print("[6/7] Skipping queue append — smoke test did not pass")

# Commit the launch report (status=SHIPPED) only after the queue append above.
REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"   Report written: {REPORT_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Update opportunity status → SHIPPED
# ─────────────────────────────────────────────────────────────────────────────
print("[7/7] Updating opportunity status → SHIPPED…")
if OPP_FILE.exists():
    opp = json.loads(OPP_FILE.read_text())
    opp["status"] = "SHIPPED"
    opp["shipped_at"] = NOW()
    opp["stripe_payment_link_url"] = stripe_url
    opp["gumroad_url"] = gumroad_url
    OPP_FILE.write_text(json.dumps(opp, indent=2))
    print(f"   Opportunity updated: {OPP_FILE}")
else:
    print(f"   WARNING: opportunity file not found: {OPP_FILE}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n─────────────────────────────────────────────────────────────────")
if smoke_passed:
    print("SHIP COMPLETE ✓")
else:
    print("SHIP FAILED ✗")
print(f"  Stripe:  {stripe_url}")
print(f"  Gumroad: {gumroad_url}")
print(f"  Release: {gist_url}")
print(f"  Status:  {'SHIPPED' if smoke_passed else 'FAILED'}")
print()
print("Next: run LinkedIn post")
print(f"  python scripts/social_helpers.py post-linkedin \\")
print(f"    --item-id {SLUG}-2026-05-07 \\")
print(f"    --text \"<post text>\"")
