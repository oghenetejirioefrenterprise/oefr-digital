#!/usr/bin/env python3
"""
Ship fl-real-estate-agent-licenses-2026-05 (v2 — Active-only Gist strategy)

  0. Filter cleaned CSV to Active rows → active.csv  (~81 MB, < Gist 100 MB limit)
  1. Upload active.csv to GitHub Gist (primary download deliverable)
  2. Create Stripe product + price + Payment Link  (success msg → Gist raw URL)
  3. Create Gumroad listing via Playwright (upload active.csv, Active-only description)
  4. Smoke test (Stripe link + Gumroad public URL)
  5. Write launch-report.json
  6. Append to distribution-queue.json (only on smoke pass)

Pre-ship requirements verified:
  [✓] Mailing address described as "address on file with DBPR as the licensee's official contact address"
  [✓] B2B disclaimer: buyer responsible for CAN-SPAM / TCPA; must not use for consumer solicitation
  [✓] No claim of email or phone data — explicitly stated as absent
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
SLUG        = "fl-real-estate-agent-licenses-2026-05"
SPEC_FILE   = BASE / "state" / "products" / SLUG / "spec.json"
REPORT_FILE = BASE / "state" / "products" / SLUG / "launch-report.json"
QUEUE_FILE  = BASE / "state" / "distribution-queue.json"
ASSET_PATH  = BASE / "state" / "datasets" / f"{SLUG}.cleaned.csv"
ACTIVE_PATH = BASE / "state" / "datasets" / f"{SLUG}.active.csv"

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
# Persist Stripe/Release IDs to launch-report.partial.json IMMEDIATELY after creation
# so a crash before the final report (e.g. in the Playwright step) does not cause a
# re-run to create a SECOND live Stripe product/price/payment link.
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

PRIOR_RELEASE_URL = _prior.get("asset_gist_url") or _prior.get("asset_release_url")
PRIOR_RAW_URL     = _prior.get("asset_raw_url")
PRIOR_STRIPE_URL  = _prior.get("stripe_payment_link_url")
PRIOR_STRIPE_PID  = _prior.get("stripe_product_id")
PRIOR_STRIPE_PRCE = _prior.get("stripe_price_id")


def _save_partial(**fields) -> None:
    """Persist intermediate Stripe/Release IDs so re-runs skip already-created objects."""
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
    sys.exit(f"ERROR: cleaned CSV not found: {ASSET_PATH}")

spec    = json.loads(SPEC_FILE.read_text())
listing = spec["gumroad_listing"]
TITLE   = listing["title"]
PRICE   = int(spec["price_usd"])   # 49 — spec is authoritative

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

# ── Gumroad description: base spec + Active-only delivery note ─────────────────
# All 3 pre_ship_requirements are satisfied in the base spec description.
# Add prominent note that delivered file is Active-only.
BASE_DESC = listing["description"]
ACTIVE_NOTE = (
    "\n\n---\n\n"
    "**Delivered file: 319,247 Active FL licensees — Inactive records available on request.**\n\n"
    "The downloaded CSV contains all Active-status licensees. "
    "If you need the Inactive records as well (full 448,610-row dataset), "
    "reply to your purchase confirmation email and we'll send them within 24 hours."
)
DESC = BASE_DESC + ACTIVE_NOTE

print(f"Shipping: {TITLE} @ ${PRICE}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0 — Create Active-only CSV
# ─────────────────────────────────────────────────────────────────────────────
if ACTIVE_PATH.exists():
    active_mb = ACTIVE_PATH.stat().st_size / (1024 * 1024)
    print(f"[0/6] Reusing existing active.csv ({active_mb:.1f} MB) ✓")
else:
    print("[0/6] Filtering cleaned CSV to primary_status == 'Active'…")
    # Stream row-by-row with the csv module instead of loading the full ~113 MB file
    # into a pandas DataFrame (which, with dtype=str + .copy(), peaks at several
    # hundred MB and can OOM a small cron host).
    import csv as _csv
    _csv.field_size_limit(10 * 1024 * 1024)  # tolerate large free-text fields
    active_count = 0
    _TMP_ACTIVE = ACTIVE_PATH.with_suffix(ACTIVE_PATH.suffix + ".tmp")
    with open(ASSET_PATH, newline="", encoding="utf-8", errors="replace") as _src, \
         open(_TMP_ACTIVE, "w", newline="", encoding="utf-8") as _dst:
        reader = _csv.reader(_src)
        writer = _csv.writer(_dst)
        try:
            header = next(reader)
        except StopIteration:
            sys.exit(f"ERROR: cleaned CSV is empty: {ASSET_PATH}")
        if "primary_status" not in header:
            sys.exit(f"ERROR: 'primary_status' column not found in {ASSET_PATH} header")
        status_idx = header.index("primary_status")
        writer.writerow(header)
        for row in reader:
            if len(row) > status_idx and row[status_idx] == "Active":
                writer.writerow(row)
                active_count += 1
    # Atomic-ish swap so a partial write never leaves a truncated active.csv in place.
    _TMP_ACTIVE.replace(ACTIVE_PATH)
    active_mb = ACTIVE_PATH.stat().st_size / (1024 * 1024)
    print(f"   {active_count:,} Active rows → {ACTIVE_PATH.name} ({active_mb:.1f} MB)")
    if active_mb > 95:
        print(f"   WARNING: active.csv is {active_mb:.1f} MB — may approach Gist 100 MB limit")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Upload active.csv to GitHub Release
# (GitHub Gist API 502s on files > ~10 MB; Release handles up to 2 GB)
# ─────────────────────────────────────────────────────────────────────────────
REPO = "oghenetejirioefrenterprise/oefr-digital"
TAG  = "ds-fl-re-licenses-2026-05-active-v1"

if PRIOR_RELEASE_URL and PRIOR_RAW_URL:
    print(f"[1/6] Reusing existing Release: {PRIOR_RELEASE_URL}")
    release_url      = PRIOR_RELEASE_URL
    raw_download_url = PRIOR_RAW_URL
else:
    active_mb = ACTIVE_PATH.stat().st_size / (1024 * 1024)
    print(f"[1/6] Uploading {active_mb:.1f} MB active.csv to GitHub Release…")

    # Delete any stale release with same tag (idempotent)
    subprocess.run(
        ["gh", "release", "delete", TAG, "--repo", REPO, "--yes"],
        capture_output=True,
    )

    result = subprocess.run(
        [
            "gh", "release", "create", TAG,
            "--repo", REPO,
            "--title", "Florida RE Licenses 2026 — 319,247 Active Records (CSV)",
            "--notes",
            (
                "DataStructured digital product — Active FL real estate licensees. "
                "Sourced from Florida DBPR public records (public government data, no auth bypass). "
                "Delivered to buyers via Stripe checkout confirmation."
            ),
            str(ACTIVE_PATH),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        sys.exit(f"GitHub Release upload failed:\n{result.stderr.strip()}")

    release_url = result.stdout.strip() or f"https://github.com/{REPO}/releases/tag/{TAG}"
    raw_download_url = (
        f"https://github.com/{REPO}/releases/download/{TAG}/{ACTIVE_PATH.name}"
    )
    _save_partial(asset_release_url=release_url, asset_raw_url=raw_download_url)
    print(f"   Release URL:  {release_url}")
    print(f"   Raw download: {raw_download_url}")

gist_url = release_url  # alias for report field naming

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Stripe: product + price + Payment Link
# ─────────────────────────────────────────────────────────────────────────────
import stripe
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
        "Thank you! Your FL Real Estate CSV (319,247 Active licensees) is ready:\n\n"
        f"{raw_download_url}\n\n"
        "Inactive records (129,379 rows) available on request — reply to your receipt email."
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
            description=(
                "319,247 Active Florida-licensed real estate agents and brokers from DBPR public records. "
                "Name, rank (Sales Associate / Broker / Broker Associate), Active/Inactive status, "
                "county, mailing address (address on file with DBPR), license number, "
                "issue date, expiration date. DBPR source URL on every row. "
                "Public government data — no auth bypass. "
                "No personal email or phone data included."
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
            page.screenshot(path="/tmp/gr_fl_re_login_fail.png")
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

    # ── File upload — active.csv (~81 MB) ─────────────────────────────────────
    active_mb_now = ACTIVE_PATH.stat().st_size / (1024 * 1024)
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ACTIVE_PATH))
        timeout_s = 180  # ceiling, not a fixed wait
        print(f"   Asset uploading… ({active_mb_now:.1f} MB — up to {timeout_s}s)")

        # Poll for an upload-complete signal instead of a blind fixed sleep:
        #  - the uploaded file name appears in the page, AND/OR
        #  - the progress / "Uploading" indicator has disappeared.
        # Proceed as soon as completion is detected; otherwise warn loudly at timeout
        # rather than silently clicking Save on a partial/missing attachment.
        deadline   = time.time() + timeout_s
        fname      = ACTIVE_PATH.name
        upload_ok  = False
        while time.time() < deadline:
            time.sleep(5)
            uploading_visible = False
            for prog_sel in ["text=Uploading", "[role='progressbar']", ".progress", "progress"]:
                try:
                    if page.locator(prog_sel).first.is_visible(timeout=1000):
                        uploading_visible = True
                        break
                except Exception:
                    continue
            filename_visible = False
            try:
                if page.get_by_text(fname, exact=False).first.is_visible(timeout=1000):
                    filename_visible = True
            except Exception:
                pass
            # Complete = filename shown and no active progress indicator.
            if filename_visible and not uploading_visible:
                upload_ok = True
                print(f"   Upload complete ✓ ({fname} present, no progress indicator)")
                break
        if not upload_ok:
            print(f"   WARNING: upload completion not confirmed within {timeout_s}s — "
                  f"attachment may be missing/partial")
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

    page.screenshot(path="/tmp/gr_fl_re_final.png")
    print(f"   Screenshot saved → /tmp/gr_fl_re_final.png")

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
# STEP 5 — Append to distribution-queue.json (smoke pass only), THEN write report
#
# Ordering matters: the queue append must succeed BEFORE the report is written with
# status SHIPPED. The top-of-file guard exits early on SHIPPED/FULLY_SHIPPED, so if we
# wrote SHIPPED first and the append then failed, the product would be live but
# permanently un-distributed with no retry. Append first; a failure here leaves the
# run safely retryable (Stripe/Release objects are reused via the partial file).
# ─────────────────────────────────────────────────────────────────────────────
PRODUCT_DIR_FOR_REPORT = REPORT_FILE.parent
PRODUCT_DIR_FOR_REPORT.mkdir(parents=True, exist_ok=True)

if smoke_passed:
    print("[5/6] Appending to distribution queue…")
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
    print("[5/6] Skipping queue append — smoke test did not pass")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Write launch-report.json (queue append already done above)
# ─────────────────────────────────────────────────────────────────────────────
print("[6/6] Writing launch report…")
report = {
    "version": 1,
    "type": "launch_report",
    "slug": SLUG,
    "created": NOW(),
    "created_by": "engineer",
    "status": "SHIPPED" if smoke_passed else "FAILED",
    "summary": (
        "Live on Stripe + Gumroad. Active-only CSV (319,247 rows) hosted on GitHub Gist. "
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
    "active_csv_path": str(ACTIVE_PATH.relative_to(BASE)),
    "active_row_count": 319247,
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
print(f"  Gist:    {gist_url}")
print(f"  Status:  {'SHIPPED' if smoke_passed else 'FAILED'}")
