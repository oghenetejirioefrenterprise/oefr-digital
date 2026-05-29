#!/usr/bin/env python3
"""
Ship sec-registered-investment-advisers-2026-05

  1. Create Stripe product + price + Payment Link  ($79)
  2. Create Gumroad listing via Playwright (upload CSV)
  3. Smoke test both URLs
  4. Write launch-report.json
  5. Append to distribution-queue.json (only on smoke pass)
  6. Update opportunity brief → status: SHIPPED
"""

import json
import os
import re
import sys
import tempfile
import time
import urllib.request
import urllib.error
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

# ── guard: already shipped? ───────────────────────────────────────────────────
if REPORT_FILE.exists():
    report = json.loads(REPORT_FILE.read_text())
    if report.get("status") in ("SHIPPED", "FULLY_SHIPPED"):
        print(f"Already shipped:")
        print(f"  Stripe:  {report.get('stripe_payment_link_url')}")
        print(f"  Gumroad: {report.get('gumroad_url')}")
        sys.exit(0)

# ── carry forward partial state ───────────────────────────────────────────────
# Persist Stripe IDs to launch-report.partial.json IMMEDIATELY after creation so a
# crash before the final report (e.g. in the Playwright/Gumroad step) does not cause
# a re-run to create a SECOND live Stripe product/price/payment link.
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

PRIOR_STRIPE_URL  = _prior.get("stripe_payment_link_url")
PRIOR_STRIPE_PID  = _prior.get("stripe_product_id")
PRIOR_STRIPE_PRCE = _prior.get("stripe_price_id")


def _save_partial(**fields) -> None:
    """Persist intermediate Stripe IDs so re-runs skip already-created paid objects."""
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
GUMROAD_USER  = os.environ.get("GUMROAD_USERNAME", "")
GUMROAD_PASS  = os.environ.get("GUMROAD_PASSWORD", "")

if not ASSET_PATH.exists():
    sys.exit(f"ERROR: CSV not found: {ASSET_PATH}")

asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
print(f"Asset: {ASSET_PATH.name} ({asset_mb:.1f} MB)")

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
    "Records: 16,551 SEC-approved firms (all Approved-status only; non-approved filtered out)\n"
    "Source: SEC IAPD Form ADV bulk data — public domain, no authentication required\n"
    "Updated: May 2026"
)

STRIPE_DESCRIPTION = (
    "Complete flat-file export of all 16,551 SEC-approved registered investment adviser (RIA) firms "
    "extracted from the SEC IAPD Form ADV bulk data. Includes firm name, CRD number, AUM "
    "(discretionary + non-discretionary), employee breakdown, total client count by category, "
    "fee structure, website, phone, address, private-fund flags, and disclosure event count. "
    "61 fields per firm. Updated from May 2026 SEC filing data."
)

AUDIENCE = (
    "B2B sales and distribution teams at asset managers, ETF sponsors, and fund companies "
    "prospecting RIA gatekeepers; wealthtech SaaS companies (portfolio management, CRM, compliance "
    "tools) reaching new firm clients; third-party investment recruiters targeting breakaway adviser "
    "talent; boutique M&A advisers tracking RIA consolidation; teams currently paying four-to-five "
    "figures per year for enterprise platforms that wrap the same free SEC public data."
)

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

print(f"\nShipping: {TITLE} @ ${PRICE}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Stripe: product + price + Payment Link
# ─────────────────────────────────────────────────────────────────────────────
import stripe
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
        "Thank you! Your SEC RIA Database 2026 CSV (16,551 firms, 61 fields) is ready. "
        "Download link will be delivered to your receipt email. "
        "Questions? Reply to your Stripe receipt email."
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
        stripe_product = stripe.Product.create(
            name=TITLE,
            description=STRIPE_DESCRIPTION,
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
        # Persist immediately so a crash before the payment link cannot orphan the product.
        _save_partial(stripe_product_id=stripe_product.id, stripe_price_id=stripe_price.id)

    stripe_link = stripe.PaymentLink.create(
        line_items=[{"price": stripe_price.id, "quantity": 1}],
        after_completion={
            "type": "hosted_confirmation",
            "hosted_confirmation": {"custom_message": success_msg},
        },
    )
    stripe_url = stripe_link.url
    _save_partial(
        stripe_product_id=stripe_product.id,
        stripe_price_id=stripe_price.id,
        stripe_payment_link_url=stripe_url,
    )
    print(f"   Payment Link: {stripe_url}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Gumroad listing via Playwright
# ─────────────────────────────────────────────────────────────────────────────
print("[2/5] Creating Gumroad listing…")
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Screenshots can capture an authenticated Gumroad session / filled credential fields.
# Write them to a private (0700) per-run dir instead of world-readable /tmp, and clean
# them up after the run. Never screenshot immediately after filling the password field.
_SHOT_DIR = Path(tempfile.mkdtemp(prefix="gr_ria_"))


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
            # Do NOT screenshot here — the password field is filled and would be captured.
            print("   Login failed (still on login page)")
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
                el.fill(GUMROAD_DESCRIPTION)
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

    _final_shot = _SHOT_DIR / "gr_ria_final.png"
    page.screenshot(path=str(_final_shot))
    print(f"   Screenshot saved → {_final_shot}")

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

# Clean up the private screenshot dir so authenticated-session captures do not linger.
try:
    import shutil
    shutil.rmtree(_SHOT_DIR, ignore_errors=True)
except Exception:
    pass

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

def _smoke_check(label, url):
    """Return (ok: bool, reason_if_failed: str|None).

    Only an explicit 2xx/3xx response (or an expected redirect HTTPError) counts as a
    pass. Connection/DNS/timeout errors are retried a few times for propagation, then
    FAIL — an unreachable buyer-facing link must block SHIPPED rather than silent-pass.
    Use GET, not HEAD: several endpoints (Gumroad/Stripe redirects) reject HEAD.
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
            # urlopen follows redirects, so an HTTPError here is a real error status,
            # except 3xx which some servers surface without following.
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
# STEP 4 — Append to distribution queue, THEN write launch-report.json
#
# Ordering matters: the distribution-queue append must succeed BEFORE the report is
# written with status SHIPPED. The top-of-file guard exits early on SHIPPED/FULLY_SHIPPED,
# so if we wrote SHIPPED first and the queue append then failed, the product would be
# live but permanently un-distributed with no way to retry. By appending first, a
# queue-append failure leaves status un-SHIPPED and the run is safely retryable
# (Stripe objects are reused via launch-report.partial.json).
# ─────────────────────────────────────────────────────────────────────────────
PRODUCT_DIR.mkdir(parents=True, exist_ok=True)

if smoke_passed:
    print("[4/5] Appending to distribution queue…")
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
    append_item(QUEUE_FILE, item)
    print("   Distribution queue updated ✓")
else:
    print("[4/5] Skipping queue append — smoke test did not pass")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Write launch-report.json + update opportunity (queue append already done)
# ─────────────────────────────────────────────────────────────────────────────
print("[5/5] Writing launch-report.json…")

report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": (
        "16,551 SEC-registered investment adviser (RIA) firms from SEC IAPD Form ADV bulk data, "
        "May 2026. 61 fields per firm including AUM, employee count, client categories, fee "
        "structure, private fund flags, and disclosure history. One-time purchase at $79."
    ),
    "spec_file": f"state/products/{SLUG}/spec.json",
    "stripe_product_id": stripe_product.id,
    "stripe_price_id": stripe_price.id,
    "stripe_payment_link_url": stripe_url,
    "gumroad_url": gumroad_url,
    "gumroad_product_id": gumroad_product_id,
    "row_count": 16551,
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

if smoke_passed:
    # Final report now holds the canonical state; drop the partial checkpoint.
    try:
        _PARTIAL_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    # Update opportunity status → SHIPPED
    if OPP_FILE.exists():
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
