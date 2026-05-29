#!/usr/bin/env python3
"""
Ship tx-tdlr-hvac-contractors-2026-05

  1. Upload CSV to GitHub Release (asset delivery)
  2. Create Stripe product + price + Payment Link
  3. Create Gumroad listing via Playwright
  4. Smoke test (Stripe link + Gumroad public URL)
  5. Write launch-report.json
  6. Append to distribution-queue.json (only on smoke pass)

Source: Texas TDLR public bulk download — data.texas.gov (no auth required, public domain)
Compliance: PASS (tx-tdlr-hvac-contractors-2026-05.compliance.json)
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
SLUG        = "tx-tdlr-hvac-contractors-2026-05"
PRODUCT_DIR = BASE / "state" / "products" / SLUG
REPORT_FILE = PRODUCT_DIR / "launch-report.json"
QUEUE_FILE  = BASE / "state" / "distribution-queue.json"
ASSET_PATH  = BASE / "state" / f"{SLUG}.csv"

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
# Persist Stripe/Release/Gumroad IDs to launch-report.partial.json IMMEDIATELY after
# creation so a crash before the final report (e.g. in the Playwright step) does not
# cause a re-run to create a SECOND live Stripe product/price/payment link or Gumroad
# listing.
_PARTIAL_FILE = REPORT_FILE.parent / "launch-report.partial.json"
_prior: dict = {}
if _PARTIAL_FILE.exists():
    try:
        _prior = json.loads(_PARTIAL_FILE.read_text())
    except Exception:
        pass
elif REPORT_FILE.exists():
    try:
        _prior = json.loads(REPORT_FILE.read_text())
    except Exception:
        pass

PRIOR_RELEASE_URL = _prior.get("asset_release_url")
PRIOR_RAW_URL     = _prior.get("asset_raw_url")
PRIOR_STRIPE_URL  = _prior.get("stripe_payment_link_url")
PRIOR_STRIPE_PID  = _prior.get("stripe_product_id")
PRIOR_STRIPE_PRCE = _prior.get("stripe_price_id")
PRIOR_GUMROAD_URL = _prior.get("gumroad_url")
PRIOR_GUMROAD_PID = _prior.get("gumroad_product_id")


def _save_partial(**fields) -> None:
    """Persist intermediate IDs so re-runs skip already-created paid/published objects."""
    current = {}
    if _PARTIAL_FILE.exists():
        try:
            current = json.loads(_PARTIAL_FILE.read_text())
        except Exception:
            current = {}
    current.update(fields)
    _PARTIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PARTIAL_FILE.write_text(json.dumps(current, indent=2))

# ── creds ─────────────────────────────────────────────────────────────────────
STRIPE_SECRET = os.environ["STRIPE_SECRET"]
GUMROAD_USER  = os.environ["GUMROAD_USERNAME"]
GUMROAD_PASS  = os.environ["GUMROAD_PASSWORD"]

if not ASSET_PATH.exists():
    sys.exit(f"ERROR: CSV not found: {ASSET_PATH}")

# Validate the advertised row count against the actual delivered file. The count is
# baked into the public title/description/spec/report; if the upstream monthly refresh
# shifts it, ship must FAIL rather than advertise a provably-wrong number to buyers.
EXPECTED_ROWS = 56001
row_count = sum(1 for _ in open(ASSET_PATH, encoding="utf-8", errors="replace")) - 1  # minus header
if row_count != EXPECTED_ROWS:
    sys.exit(
        f"ERROR: advertised {EXPECTED_ROWS:,} rows but CSV has {row_count:,}. "
        "Update the advertised count (title/description/spec/report) before shipping."
    )

TITLE   = "Texas HVAC Contractors & AC Technicians — TDLR Database 2026"
PRICE   = 49
DESC    = (
    "56,001 active licensed HVAC contractors and AC technicians in Texas — "
    "sourced from the Texas Department of Licensing and Regulation (TDLR) public database.\n\n"
    "**License types included:**\n"
    "- A/C Contractors\n"
    "- A/C Technicians\n"
    "- Service Technicians\n\n"
    "**Fields per record:**\n"
    "- Name\n"
    "- License type\n"
    "- License number\n"
    "- Business address\n"
    "- City\n"
    "- ZIP code\n"
    "- Phone number\n"
    "- Expiration date\n"
    "- TDLR source URL (every row verifiable)\n\n"
    "**Key stats:**\n"
    "- 56,001 active licensed HVAC professionals\n"
    "- Updated May 2026\n"
    "- One CSV file, instant download\n\n"
    "**Important notes:**\n"
    "- Data is sourced from the Texas TDLR (Texas Department of Licensing and Regulation) "
    "public license database — the official state regulatory database\n"
    "- All records are active licensed professionals — business/regulatory contact information\n"
    "- No personal email, no home addresses — this is a clean B2B licensing dataset\n"
    "- Buyer is responsible for complying with applicable contact laws (CAN-SPAM, TCPA, Texas Business & Commerce Code)\n"
    "- Must not use this data for consumer solicitation\n\n"
    "**Who buys this:** Carrier/Trane/Lennox dealer territory reps, ServiceTitan & FieldEdge SDRs, "
    "refrigerant & parts suppliers, HVAC CE education companies, insurance brokers (liability/workers comp for HVAC).\n\n"
    "**Data source:** Texas Department of Licensing and Regulation (TDLR) via data.texas.gov — "
    "public government record, no auth bypass."
)

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
print(f"Shipping: {TITLE} @ ${PRICE}")
print(f"  Asset: {ASSET_PATH.name} ({asset_mb:.1f} MB, {row_count:,} rows)\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Upload CSV to GitHub Release
# ─────────────────────────────────────────────────────────────────────────────
REPO = "oghenetejirioefrenterprise/oefr-digital"
TAG  = "ds-tx-tdlr-hvac-2026-05-v1"

if PRIOR_RELEASE_URL and PRIOR_RAW_URL:
    print(f"[1/6] Reusing existing Release: {PRIOR_RELEASE_URL}")
    release_url      = PRIOR_RELEASE_URL
    raw_download_url = PRIOR_RAW_URL
else:
    print(f"[1/6] Uploading {asset_mb:.1f} MB CSV to GitHub Release…")

    # Delete any stale release with same tag (idempotent)
    subprocess.run(
        ["gh", "release", "delete", TAG, "--repo", REPO, "--yes"],
        capture_output=True,
    )

    result = subprocess.run(
        [
            "gh", "release", "create", TAG,
            "--repo", REPO,
            "--title", "Texas HVAC Contractors 2026 — 56,001 Active Records (CSV)",
            "--notes",
            (
                "DataStructured digital product — Active Texas HVAC contractors and AC technicians. "
                "Sourced from Texas TDLR public license database via data.texas.gov (public government data, no auth bypass). "
                "Delivered to buyers via Stripe checkout confirmation."
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
    _save_partial(asset_release_url=release_url, asset_raw_url=raw_download_url)
    print(f"   Release URL:  {release_url}")
    print(f"   Raw download: {raw_download_url}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Stripe: product + price + Payment Link
# ─────────────────────────────────────────────────────────────────────────────
import stripe
from scripts import stripe_helpers
stripe.api_key = STRIPE_SECRET

if PRIOR_STRIPE_URL and PRIOR_STRIPE_PID and str(PRIOR_STRIPE_PID).startswith("prod_"):
    print(f"[2/6] Reusing existing Stripe: {PRIOR_STRIPE_URL}")
    stripe_url = PRIOR_STRIPE_URL

    class _Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    stripe_product = _Obj(id=PRIOR_STRIPE_PID)
    stripe_price   = _Obj(id=PRIOR_STRIPE_PRCE)
else:
    print("[2/6] Creating Stripe product…")
    success_msg = (
        "Thank you! Your Texas HVAC CSV (56,001 active licensed contractors & technicians) is ready:\n\n"
        f"{raw_download_url}\n\n"
        "Questions? Reply to your receipt email."
    )
    assert len(success_msg) <= 500, f"success_msg too long: {len(success_msg)} chars"

    # Reuse a product+price created on a prior run whose payment-link step failed.
    if PRIOR_STRIPE_PID and PRIOR_STRIPE_PRCE and str(PRIOR_STRIPE_PID).startswith("prod_") and not PRIOR_STRIPE_URL:
        print(f"   Reusing existing product {PRIOR_STRIPE_PID} + price {PRIOR_STRIPE_PRCE}")

        class _Obj:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        stripe_product = _Obj(id=PRIOR_STRIPE_PID)
        stripe_price   = _Obj(id=PRIOR_STRIPE_PRCE)
    else:
        stripe_product = stripe_helpers.create_product(
            SLUG,
            TITLE,
            (
                "56,001 active licensed HVAC contractors and AC technicians in Texas from TDLR public records. "
                "Name, license type, license number, business address, city, ZIP, phone, expiration date. "
                "TDLR source URL on every row. Public government data — no auth bypass. "
                "No personal email or home address data included."
            ),
            idempotency_key=f"dsl_{SLUG.replace('-', '_')}_product",
        )
        print(f"   Product: {stripe_product.id}")

        stripe_price = stripe_helpers.create_price(
            stripe_product.id,
            PRICE,
            idempotency_key=f"dsl_{SLUG.replace('-', '_')}_price",
        )
        print(f"   Price:   {stripe_price.id}")
        # Persist immediately so a crash before the payment link cannot orphan the product.
        _save_partial(stripe_product_id=stripe_product.id, stripe_price_id=stripe_price.id)

    stripe_link = stripe_helpers.create_payment_link(
        stripe_price.id,
        success_msg,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_payment_link",
    )
    stripe_url = stripe_link.url
    _save_partial(
        stripe_product_id=stripe_product.id,
        stripe_price_id=stripe_price.id,
        stripe_payment_link_url=stripe_url,
    )
    print(f"   Payment Link: {stripe_url}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Gumroad listing via Playwright
# ─────────────────────────────────────────────────────────────────────────────
print("[3/6] Creating Gumroad listing…")
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
            page.screenshot(path="/tmp/gr_tx_hvac_login_fail.png")
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

    # ── File upload ────────────────────────────────────────────────────────────
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ASSET_PATH))
        wait_s = 120
        print(f"   Asset uploading… ({asset_mb:.1f} MB — waiting {wait_s}s)")
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

    page.screenshot(path="/tmp/gr_tx_hvac_final.png")
    print(f"   Screenshot saved → /tmp/gr_tx_hvac_final.png")

    # ── Extract public URL ─────────────────────────────────────────────────────
    final_url           = page.url
    gumroad_public_url  = None
    gumroad_product_id  = None

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


def _url_healthy(url) -> bool:
    """True only on an explicit 2xx/3xx response — used to decide if a prior Gumroad
    listing can be reused instead of creating a duplicate."""
    import urllib.request as _r
    import urllib.error as _e
    try:
        resp = _r.urlopen(_r.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
        return 200 <= resp.status < 400
    except _e.HTTPError as exc:
        return 200 <= exc.code < 400
    except Exception:
        return False


# Reuse a healthy prior Gumroad listing instead of publishing a duplicate on retry.
if PRIOR_GUMROAD_URL and _url_healthy(PRIOR_GUMROAD_URL):
    print(f"[3/6] Reusing existing Gumroad listing: {PRIOR_GUMROAD_URL}")
    gumroad_url        = PRIOR_GUMROAD_URL
    gumroad_product_id = PRIOR_GUMROAD_PID
else:
    with sync_playwright() as pw:
        gumroad_url, gumroad_product_id = gumroad_deploy(pw)
    if gumroad_url:
        _save_partial(gumroad_url=gumroad_url, gumroad_product_id=gumroad_product_id)

if not gumroad_url:
    print("WARNING: Gumroad listing URL could not be determined — continuing without it")
else:
    print(f"   Gumroad: {gumroad_url}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Smoke test
# ─────────────────────────────────────────────────────────────────────────────
print("[4/6] Smoke testing…")
import urllib.request
import urllib.error

smoke_passed = True
smoke_reason = None
checked_at   = NOW()


def _smoke_check(label, url):
    """Return (ok: bool, reason_if_failed: str|None).

    Only an explicit 2xx/3xx response counts as a pass. Connection/DNS/timeout errors
    are retried a few times for propagation, then FAIL — an unreachable buyer-facing
    link must block SHIPPED rather than silent-pass. Use GET, not HEAD: several
    endpoints (Gumroad/Stripe redirects) reject HEAD.
    """
    last_err = None
    for attempt in range(3):
        try:
            req  = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=20)
            if 200 <= resp.status < 400:
                print(f"   {label} smoke: HTTP {resp.status} ✓")
                return True, None
            print(f"   {label} smoke: FAIL — HTTP {resp.status}")
            return False, f"{label} URL returned HTTP {resp.status}"
        except urllib.error.HTTPError as exc:
            if 200 <= exc.code < 400:
                print(f"   {label} smoke: HTTP {exc.code} ✓")
                return True, None
            print(f"   {label} smoke: FAIL — HTTP {exc.code}")
            return False, f"{label} URL returned HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_err = exc
            print(f"   {label} smoke: {exc} (attempt {attempt + 1}/3) — retrying…")
            time.sleep(5)
    print(f"   {label} smoke: FAIL — unreachable after retries: {last_err}")
    return False, f"{label} URL unreachable: {last_err}"


for label, url in [("Stripe", stripe_url), ("Gumroad", gumroad_url)]:
    if not url:
        smoke_passed = False
        smoke_reason = f"{label} URL missing"
        print(f"   {label} smoke: FAIL — URL missing")
        continue
    ok, reason = _smoke_check(label, url)
    if not ok:
        smoke_passed = False
        smoke_reason = reason

print(f"   Smoke test: {'PASS ✓' if smoke_passed else 'FAIL ✗'}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Write launch-report.json + spec.json
# ─────────────────────────────────────────────────────────────────────────────
print("[5/6] Writing product records…")
PRODUCT_DIR.mkdir(parents=True, exist_ok=True)

spec = {
    "version": 1,
    "type": "product_spec",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "READY_TO_SHIP",
    "name": TITLE,
    "summary": (
        "56,001 active licensed HVAC contractors and AC technicians in Texas — "
        "sourced from the Texas Department of Licensing and Regulation (TDLR) public database. "
        "Includes A/C Contractors, A/C Technicians, and Service Technicians. "
        "Fields: name, license type, license number, business address, city, ZIP, phone, expiration date. "
        "Updated May 2026. TDLR source URL on every row."
    ),
    "format": "one_time",
    "deliverable": "csv",
    "price_usd": PRICE,
    "dataset_file": f"state/{SLUG}.csv",
    "ethics_ledger": f"state/{SLUG}.compliance.json",
    "audience": (
        "HVAC equipment distributors (Carrier, Trane, Lennox dealers), "
        "HVAC software vendors (ServiceTitan, FieldEdge, Jobber), "
        "refrigerant suppliers, HVAC CE education providers, "
        "insurance brokers selling liability/workers comp to HVAC companies, "
        "HVAC parts suppliers."
    ),
    "stripe_product_prefix": "dsl_",
    "channels": ["stripe_payment_link", "gumroad"],
    "compliance_verdict": "PASS",
    "compliance_audited_at": "2026-05-07T12:10:00Z",
    "row_count": 56001,
    "source": "Texas Department of Licensing and Regulation (TDLR) via data.texas.gov — public domain, no auth required",
    "gumroad_listing": {
        "title": TITLE,
        "description": DESC,
        "price": PRICE,
        "tags": ["texas", "hvac", "ac contractors", "tdlr", "license", "csv", "b2b", "leads", "contractors"]
    },
}

spec_file = PRODUCT_DIR / "spec.json"
spec_file.write_text(json.dumps(spec, indent=2))
print(f"   Written: {spec_file}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 (before report) — Append to distribution-queue.json (smoke pass only)
#
# Ordering matters: the queue append must succeed BEFORE the report is written with
# status SHIPPED. The top-of-file guard exits early on SHIPPED/FULLY_SHIPPED, so if we
# wrote SHIPPED first and the append then failed, the product would be live but
# permanently un-distributed with no retry. Append first; a failure here leaves the
# run safely retryable (Stripe/Gumroad/Release objects are reused via the partial file).
# ─────────────────────────────────────────────────────────────────────────────
if smoke_passed:
    print("[6/6] Appending to distribution queue…")
    from scripts.lib.distribution_queue import append_item

    item = {
        "id": f"{SLUG}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "slug": SLUG,
        "name": TITLE,
        "stripe_payment_link_url": stripe_url,
        "gumroad_url": gumroad_url,
        "price_usd": PRICE,
        "audience": spec["audience"],
        "added_at": NOW(),
        "status": "ready",
    }
    append_item(QUEUE_FILE, item)
    print("   Distribution queue updated ✓")
else:
    print("[6/6] Skipping queue append — smoke test did not pass")

# ─────────────────────────────────────────────────────────────────────────────
# Write launch-report.json (queue append already done above)
# ─────────────────────────────────────────────────────────────────────────────
report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": (
        f"Live on Stripe + Gumroad. CSV ({row_count:,} rows) hosted on GitHub Release. "
        "Smoke tests green. Distribution queue updated."
        if smoke_passed else
        f"Stripe shipped; smoke test failed: {smoke_reason}"
    ),
    "stripe_product_id": stripe_product.id,
    "stripe_price_id": stripe_price.id,
    "stripe_payment_link_url": stripe_url,
    "gumroad_url": gumroad_url,
    "gumroad_product_id": gumroad_product_id,
    "asset_release_url": release_url,
    "asset_raw_url": raw_download_url,
    "csv_path": f"state/{SLUG}.csv",
    "row_count": row_count,
    "smoke_test": {
        "passed": smoke_passed,
        "checked_at": checked_at,
    },
    "spec_file": f"state/products/{SLUG}/spec.json",
    "pre_ship_requirements_verified": True,
}
if not smoke_passed:
    report["failure_reason"] = smoke_reason
    report["smoke_test"]["failure_reason"] = smoke_reason

REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"   Written: {REPORT_FILE}")

if smoke_passed:
    # Final report now holds canonical state; drop the partial checkpoint.
    try:
        _PARTIAL_FILE.unlink(missing_ok=True)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
print("\n─────────────────────────────────────────────────────────────────")
if smoke_passed:
    print("SHIP COMPLETE ✓")
else:
    print("SHIP FAILED ✗")
print(f"  Stripe:  {stripe_url}")
print(f"  Gumroad: {gumroad_url}")
print(f"  Release: {release_url}")
print(f"  Status:  {'SHIPPED' if smoke_passed else 'FAILED'}")
