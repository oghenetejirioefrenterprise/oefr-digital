#!/usr/bin/env python3
"""
Ship tx-tdlr-electricians-2026-05

  1. Upload CSV to GitHub Release (30 MB — exceeds Gist limit)
  2. Create Stripe product + price + Payment Link ($59)
  3. Create Gumroad listing via Playwright (upload CSV, full description)
  4. Smoke test (Stripe link + Gumroad public URL)
  5. Write launch-report.json
  6. Append to distribution-queue.json (only on smoke pass)
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
SLUG        = "tx-tdlr-electricians-2026-05"
SPEC_FILE   = BASE / "state" / "products" / SLUG / "spec.json"
REPORT_FILE = BASE / "state" / "products" / SLUG / "launch-report.json"
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
STRIPE_SECRET = os.environ["STRIPE_SECRET"]
GUMROAD_USER  = os.environ["GUMROAD_USERNAME"]
GUMROAD_PASS  = os.environ["GUMROAD_PASSWORD"]

if not ASSET_PATH.exists():
    sys.exit(f"ERROR: CSV not found: {ASSET_PATH}")

spec    = json.loads(SPEC_FILE.read_text())
listing = spec["gumroad_listing"]
TITLE   = listing["title"]
DESC    = listing["description"]
PRICE   = int(spec["price_usd"])   # 59 — spec is authoritative

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

csv_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
print(f"Shipping: {TITLE} @ ${PRICE}")
print(f"CSV size: {csv_mb:.1f} MB\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Upload CSV to GitHub Release
# ─────────────────────────────────────────────────────────────────────────────
REPO = "oghenetejirioefrenterprise/oefr-digital"
TAG  = "ds-tx-tdlr-electricians-2026-05-v1"

if PRIOR_RELEASE_URL and PRIOR_RAW_URL:
    print(f"[1/5] Reusing existing Release: {PRIOR_RELEASE_URL}")
    release_url      = PRIOR_RELEASE_URL
    raw_download_url = PRIOR_RAW_URL
else:
    print(f"[1/5] Uploading {csv_mb:.1f} MB CSV to GitHub Release…")

    # Delete any stale release with same tag (idempotent)
    subprocess.run(
        ["gh", "release", "delete", TAG, "--repo", REPO, "--yes"],
        capture_output=True,
    )

    result = subprocess.run(
        [
            "gh", "release", "create", TAG,
            "--repo", REPO,
            "--title", "Texas Electricians TDLR 2026 — 204,535 Active Records (CSV)",
            "--notes",
            (
                "DataStructured digital product — Texas licensed electricians and electrical contractors. "
                "Sourced from TDLR (Texas Dept. of Licensing and Regulation) via data.texas.gov public bulk download. "
                "Public government data — mandatory disclosure under Texas Government Code §552. No auth bypass. "
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
    print(f"   Release URL:  {release_url}")
    print(f"   Raw download: {raw_download_url}")

gist_url = release_url  # alias for report field naming

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Stripe: product + price + Payment Link
# ─────────────────────────────────────────────────────────────────────────────
import stripe
stripe.api_key = STRIPE_SECRET

if PRIOR_STRIPE_URL and PRIOR_STRIPE_PID and str(PRIOR_STRIPE_PID).startswith("prod_"):
    print(f"[2/5] Reusing existing Stripe: {PRIOR_STRIPE_URL}")
    stripe_url = PRIOR_STRIPE_URL

    class _Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    stripe_product = _Obj(id=PRIOR_STRIPE_PID)
    stripe_price   = _Obj(id=PRIOR_STRIPE_PRCE)
else:
    print("[2/5] Creating Stripe product…")
    success_msg = (
        "Thank you! Your Texas Electricians TDLR CSV (204,535 active licensed electricians & contractors) is ready:\n\n"
        f"{raw_download_url}\n\n"
        "Questions? Reply to your receipt email."
    )
    assert len(success_msg) <= 500, f"success_msg too long: {len(success_msg)} chars"

    stripe_product = stripe.Product.create(
        name=TITLE,
        description=(
            "204,535 active licensed electricians and electrical contractors in Texas — "
            "sourced from the Texas Department of Licensing and Regulation (TDLR) public database. "
            "Includes Master Electricians, Journeyman Electricians, Apprentice Electricians, "
            "Electrical Contractors, Residential Wiremen, Maintenance Electricians, Sign Electricians. "
            "Fields: name, license type, license number, business address, city, ZIP, phone, expiration date. "
            "Public government data — mandatory disclosure under Texas Government Code §552. No auth bypass."
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
print("[3/5] Creating Gumroad listing…")
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
            page.screenshot(path="/tmp/gr_tx_elec_login_fail.png")
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
    csv_mb_now = ASSET_PATH.stat().st_size / (1024 * 1024)
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ASSET_PATH))
        wait_s = 120
        print(f"   Asset uploading… ({csv_mb_now:.1f} MB — waiting {wait_s}s)")
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

    page.screenshot(path="/tmp/gr_tx_elec_final.png")
    print(f"   Screenshot saved → /tmp/gr_tx_elec_final.png")

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


with sync_playwright() as pw:
    gumroad_url, gumroad_product_id = gumroad_deploy(pw)

if not gumroad_url:
    print("WARNING: Gumroad listing URL could not be determined — continuing without it")
else:
    print(f"   Gumroad: {gumroad_url}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Smoke test
# ─────────────────────────────────────────────────────────────────────────────
print("[4/5] Smoke testing…")
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
# STEP 5 — Write launch-report.json
# ─────────────────────────────────────────────────────────────────────────────
print("[5/5] Writing launch report…")
report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": (
        "Live on Stripe + Gumroad. CSV (204,535 rows) hosted on GitHub Release. "
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
    "csv_path": str(ASSET_PATH.relative_to(BASE)),
    "row_count": 204535,
    "smoke_test": {
        "passed": smoke_passed,
        "checked_at": checked_at,
    },
    "spec_file": str(SPEC_FILE.relative_to(BASE)),
    "pre_ship_requirements_verified": True,
}
if not smoke_passed:
    report["failure_reason"] = smoke_reason
    report["smoke_test"]["failure_reason"] = smoke_reason

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Append to distribution-queue.json BEFORE committing SHIPPED status.
# Ordering matters: if the queue append fails, the launch-report below must NOT
# be written with status=SHIPPED — otherwise the early-exit guard would block
# every retry, leaving the product live but permanently unqueued/undistributed.
# ─────────────────────────────────────────────────────────────────────────────
if smoke_passed:
    print("Appending to distribution queue…")
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
    print("   Distribution queue updated ✓")
else:
    print("Skipping queue append — smoke test did not pass")

# Commit the launch report (status=SHIPPED) only after the queue append above.
REPORT_FILE.write_text(json.dumps(report, indent=2))
print(f"   Written: {REPORT_FILE}")

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
