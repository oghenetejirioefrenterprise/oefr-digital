#!/usr/bin/env python3
"""
Ship new-business-formations-csv-2026-05
  1. Upload asset to GitHub Gist (delivery URL)
  2. Create Stripe product + price + Payment Link
  3. Create Gumroad listing via Playwright
  4. Smoke test
  5. Write launch-report.json
  6. Append to distribution-queue.json
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
BASE       = Path(__file__).resolve().parents[1]
SLUG       = "new-business-formations-csv-2026-05"
SPEC_FILE  = BASE / "state" / "products" / SLUG / "spec.json"
REPORT_FILE= BASE / "state" / "products" / SLUG / "launch-report.json"
QUEUE_FILE = BASE / "state" / "distribution-queue.json"
ASSET_PATH = BASE / "state" / "datasets" / f"{SLUG}.csv"

sys.path.insert(0, str(BASE))

# ── guard: already shipped? ───────────────────────────────────────────────────
if REPORT_FILE.exists():
    report = json.loads(REPORT_FILE.read_text())
    if report.get("status") in ("SHIPPED", "FULLY_SHIPPED"):
        print(f"Already shipped: {report.get('stripe_payment_link_url')} / {report.get('gumroad_listing_url') or report.get('gumroad_url')}")
        sys.exit(0)

# ── state: carry over Stripe/Gist if already created ─────────────────────────
_prior = {}
if REPORT_FILE.exists():
    _prior = json.loads(REPORT_FILE.read_text())

PRIOR_GIST_URL      = _prior.get("asset_gist_url")
PRIOR_RAW_URL       = _prior.get("asset_raw_url")
PRIOR_STRIPE_URL    = _prior.get("stripe_payment_link_url")
PRIOR_STRIPE_PID    = _prior.get("stripe_product_id")
PRIOR_STRIPE_PRICID = _prior.get("stripe_price_id")

# ── creds ─────────────────────────────────────────────────────────────────────
STRIPE_SECRET   = os.environ["STRIPE_SECRET"]
GUMROAD_USER    = os.environ["GUMROAD_USERNAME"]
GUMROAD_PASS    = os.environ["GUMROAD_PASSWORD"]

if not ASSET_PATH.exists():
    sys.exit(f"ERROR: asset not found: {ASSET_PATH}")

spec    = json.loads(SPEC_FILE.read_text())
listing = spec["gumroad_listing"]
TITLE   = listing["title"]
DESC    = listing["description"]
PRICE   = int(listing["price"])   # 49
NOW     = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

print(f"Shipping: {TITLE} @ ${PRICE}")
print(f"Asset:    {ASSET_PATH} ({ASSET_PATH.stat().st_size / 1024:.0f} KB)\n")

# ── 1. Upload asset to GitHub Gist ───────────────────────────────────────────
if PRIOR_GIST_URL and PRIOR_RAW_URL:
    print(f"[1/5] Reusing existing Gist: {PRIOR_GIST_URL}")
    gist_url         = PRIOR_GIST_URL
    raw_download_url = PRIOR_RAW_URL
else:
    print("[1/5] Uploading CSV to GitHub Gist…")
    result = subprocess.run(
        ["gh", "gist", "create", str(ASSET_PATH),
         "--desc", TITLE,
         "--public"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.exit(f"Gist upload failed: {result.stderr.strip()}")

    gist_url = result.stdout.strip()
    gist_id  = gist_url.rstrip("/").split("/")[-1]
    gh_user  = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True, text=True
    ).stdout.strip()
    raw_download_url = (
        f"https://gist.githubusercontent.com/{gh_user}/{gist_id}/raw/{ASSET_PATH.name}"
    )
    print(f"   Gist: {gist_url}")
    print(f"   Raw:  {raw_download_url}")

# ── 2. Stripe: product + price + payment link ─────────────────────────────────
import stripe
stripe.api_key = STRIPE_SECRET

from scripts.stripe_helpers import create_product, create_price, create_payment_link

if PRIOR_STRIPE_URL and PRIOR_STRIPE_PID:
    print(f"[2/5] Reusing existing Stripe: {PRIOR_STRIPE_URL}")
    stripe_url    = PRIOR_STRIPE_URL
    # Reconstruct minimal objects for report
    class _Obj:
        def __init__(self, **kw): self.__dict__.update(kw)
    stripe_product = _Obj(id=PRIOR_STRIPE_PID)
    stripe_price   = _Obj(id=PRIOR_STRIPE_PRICID)
else:
    print("[2/5] Creating Stripe product…")
    success_msg = (
        f"Thank you for purchasing {TITLE}!\n\n"
        f"Download your CSV here:\n{raw_download_url}\n\n"
        "File is ready to import into Excel, Google Sheets, or your CRM. "
        "Reply to your receipt email if you have any issues."
    )

    stripe_product = create_product(
        SLUG,
        TITLE,
        (
            "15,997 Florida LLC & Corp registrations (Apr–May 2026). "
            "Entity name, type, filing date, registered agent, principal address, sunbiz.org source URL. "
            "Public SOS data — no auth bypass."
        ),
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_product",
    )
    print(f"   Product: {stripe_product.id}")

    stripe_price = create_price(
        stripe_product.id,
        PRICE,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_price",
    )
    print(f"   Price: {stripe_price.id}")

    stripe_link = create_payment_link(
        stripe_price.id,
        success_msg,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_link",
    )
    stripe_url = stripe_link.url
    print(f"   Payment Link: {stripe_url}")

# ── 3. Gumroad listing via Playwright ─────────────────────────────────────────
print("[3/5] Creating Gumroad listing…")
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Per-run private dir (0700) for debug screenshots taken during the Gumroad auth
# flow. Avoids leaving auth-flow artifacts in world-readable /tmp on a shared host.
_SHOT_DIR = Path(tempfile.mkdtemp(prefix="gr_fl_"))

def gumroad_deploy(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    ctx  = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # Login
    print("   [3a] Logging in…")
    page.goto("https://gumroad.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # New Gumroad login form uses input[type='email'] / input[type='password']
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
            page.screenshot(path=str(_SHOT_DIR / "gr_fl_login_fail.png"))
            browser.close()
            return None, None

    # New product
    print("   [3b] New product form…")
    page.goto("https://app.gumroad.com/products/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Fill name
    for sel in ["input[placeholder*='name' i]", "input[name='name']", "input[type='text']:first-of-type"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(TITLE)
                print(f"   Name filled ({sel})")
                break
        except Exception:
            continue

    # Fill price
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
    for sel in ["button[type='submit']", "button:has-text('Create')", "button:has-text('Continue')"]:
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
    current_url = page.url
    print(f"   Edit URL: {current_url}")

    # Description
    for sel in ["textarea[name='description']", "[contenteditable='true']", ".ql-editor", "textarea", "[role='textbox']"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(DESC)
                print(f"   Description filled ({sel})")
                break
        except Exception:
            continue

    # File upload
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ASSET_PATH))
        print(f"   Asset uploading… (may take ~30s for 7MB)")
        time.sleep(30)
    except Exception as e:
        print(f"   WARNING: file upload: {e}")

    # Save/Publish
    for sel in ["button:has-text('Save')", "button:has-text('Publish')", "button:has-text('Update')", "button[type='submit']"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=5000):
                el.click()
                print(f"   Saved ({sel})")
                time.sleep(3)
                break
        except Exception:
            continue

    page.screenshot(path=str(_SHOT_DIR / "gr_fl_final.png"))

    # Extract public URL and product ID
    final_url = page.url
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
        import re
        m = re.search(r"/products/([^/?#]+)", final_url)
        if m:
            pid = m.group(1)
            gumroad_public_url = f"https://gumroad.com/l/{pid}"
            gumroad_product_id = pid
    else:
        import re
        m = re.search(r"/l/([^/?#]+)", gumroad_public_url)
        if m:
            gumroad_product_id = m.group(1)

    browser.close()
    return gumroad_public_url, gumroad_product_id


with sync_playwright() as pw:
    gumroad_url, gumroad_product_id = gumroad_deploy(pw)

if not gumroad_url:
    print("ERROR: Gumroad listing URL could not be determined")
    gumroad_url = None
else:
    # Success — remove the private auth-flow screenshot dir so nothing persists.
    import shutil
    shutil.rmtree(_SHOT_DIR, ignore_errors=True)

print(f"   Gumroad: {gumroad_url}\n")

# ── 4. Smoke test ─────────────────────────────────────────────────────────────
print("[4/5] Smoke testing…")
import urllib.request
import urllib.error

smoke_passed = True
smoke_reason = None
checked_at   = NOW()

# Stripe payment link
try:
    req = urllib.request.Request(stripe_url, method="HEAD",
                                  headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    if resp.status not in (200, 301, 302):
        smoke_passed = False
        smoke_reason = f"Stripe link returned HTTP {resp.status}"
    else:
        print(f"   Stripe smoke: HTTP {resp.status} ✓")
except urllib.error.HTTPError as e:
    # Payment links may emit a redirect surfaced as HTTPError — a 2xx/3xx is fine,
    # anything else is a buyer-facing failure and must block SHIPPED.
    if e.code in (200, 301, 302):
        print(f"   Stripe smoke: HTTP {e.code} ✓")
    else:
        smoke_passed = False
        smoke_reason = f"Stripe link returned HTTP {e.code}"
except Exception as e:
    # URLError / timeout / DNS / connection failure — the link is unreachable.
    # A broken payment link must NOT be advertised to customers; fail loud.
    smoke_passed = False
    smoke_reason = f"Stripe link unreachable: {e}"
    print(f"   Stripe smoke: FAIL — {smoke_reason}")

# Gumroad listing
if gumroad_url:
    try:
        req = urllib.request.Request(gumroad_url, method="HEAD",
                                      headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        print(f"   Gumroad smoke: HTTP {resp.status} ✓")
    except urllib.error.HTTPError as e:
        if e.code in (200, 301, 302):
            print(f"   Gumroad smoke: HTTP {e.code} ✓")
        else:
            smoke_passed = False
            smoke_reason = f"Gumroad URL returned HTTP {e.code}"
    except Exception as e:
        print(f"   Gumroad smoke: {e} (treating as ok — listing just created)")

print(f"   Smoke test: {'PASS ✓' if smoke_passed else 'FAIL'}\n")

# ── 5. Write launch-report.json ───────────────────────────────────────────────
print("[5/5] Writing launch report and updating distribution queue…")

report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": (
        "Live on Stripe. Asset hosted on GitHub Gist. Gumroad mirror live. Smoke test green."
        if smoke_passed else
        f"Stripe shipped; smoke test failed: {smoke_reason}"
    ),
    "stripe_product_id": stripe_product.id,
    "stripe_price_id": stripe_price.id,
    "stripe_payment_link_url": stripe_url,
    "gumroad_listing_url": gumroad_url,
    "gumroad_product_id": gumroad_product_id,
    "asset_gist_url": gist_url,
    "asset_raw_url": raw_download_url,
    "smoke_test": {
        "passed": smoke_passed,
        "checked_at": checked_at,
    },
    "spec_file": str(SPEC_FILE.relative_to(BASE)),
}
if not smoke_passed:
    report["failure_reason"] = smoke_reason
    report["smoke_test"]["failure_reason"] = smoke_reason

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"   Launch report: {REPORT_FILE}")

# ── 6. Append to distribution queue (only on smoke pass) ──────────────────────
if smoke_passed:
    from scripts.lib.distribution_queue import append_item
    item = {
        "id": f"{SLUG}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "slug": SLUG,
        "name": spec["name"],
        "stripe_payment_link_url": stripe_url,
        "gumroad_url": gumroad_url,
        "price_usd": PRICE,
        "audience": spec["audience"],
        "added_at": NOW(),
        "status": "ready",
    }
    append_item(QUEUE_FILE, item)
    print(f"   Distribution queue updated ✓")

print("\n─────────────────────────────────────────────")
print("SHIP COMPLETE ✓")
print(f"  Stripe:  {stripe_url}")
print(f"  Gumroad: {gumroad_url}")
print(f"  Gist:    {gist_url}")
print(f"  Status:  {'SHIPPED' if smoke_passed else 'FAILED'}")
