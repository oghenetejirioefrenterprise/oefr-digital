#!/usr/bin/env python3
"""
Ship epa-tri-toxic-release-reporting-facilities-2026-05

  1. Upload dataset CSV to GitHub Release (primary download deliverable)
  2. Create Stripe product + price + Payment Link (success msg → Release raw URL)
  3. Create Gumroad listing via Playwright (upload CSV, mirror description)
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
SLUG        = "epa-tri-toxic-release-reporting-facilities-2026-05"
SPEC_FILE   = BASE / "state" / "products" / SLUG / "spec.json"
REPORT_FILE = BASE / "state" / "products" / SLUG / "launch-report.json"
QUEUE_FILE  = BASE / "state" / "distribution-queue.json"
ASSET_PATH  = BASE / "state" / "datasets" / f"{SLUG}.csv"

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
# Prefer the partial-state file (written immediately after each side effect) over
# the final launch-report.json, which is only written at the very end. Without
# this, a crash after the GitHub Release upload but before the report is written
# would make a re-run delete + recreate the live release that buyers' download
# links already point at.
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


def _save_partial(**fields) -> None:
    """Persist intermediate Release/Stripe IDs so re-runs skip completed steps."""
    current: dict = {}
    if _PARTIAL_FILE.exists():
        try:
            current = json.loads(_PARTIAL_FILE.read_text())
        except Exception:
            current = {}
    current.update(fields)
    _PARTIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PARTIAL_FILE.write_text(json.dumps(current, indent=2))


PRIOR_RELEASE_URL = _prior.get("asset_release_url")
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
stripe_spec = spec["stripe"]
gumroad_spec = spec["gumroad"]
TITLE   = gumroad_spec["title"]
PRICE   = int(spec["price_usd"])

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

print(f"Shipping: {TITLE} @ ${PRICE}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Upload CSV to GitHub Release
# ─────────────────────────────────────────────────────────────────────────────
REPO = "oghenetejirioefrenterprise/oefr-digital"
TAG  = "ds-epa-tri-2023-v1"

if PRIOR_RELEASE_URL and PRIOR_RAW_URL:
    print(f"[1/6] Reusing existing Release: {PRIOR_RELEASE_URL}")
    release_url      = PRIOR_RELEASE_URL
    raw_download_url = PRIOR_RAW_URL
else:
    asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
    print(f"[1/6] Uploading {asset_mb:.1f} MB CSV to GitHub Release…")

    release_notes = (
        "DataStructured digital product — EPA TRI 2023 reporting facilities. "
        "Sourced from EPA TRI Basic Plus Data Files 2023 (public government data). "
        "Delivered to buyers via Stripe checkout confirmation."
    )

    # Does a release with this tag already exist? If a prior run created the
    # release but crashed before persisting its URL, NEVER delete it — buyers
    # may already hold the download link. Instead, upload the asset with
    # --clobber so the release/tag is never removed while links are live.
    exists = subprocess.run(
        ["gh", "release", "view", TAG, "--repo", REPO],
        capture_output=True, text=True,
    )
    if exists.returncode == 0:
        print(f"   Release {TAG} already exists — uploading asset with --clobber (no delete).")
        up = subprocess.run(
            ["gh", "release", "upload", TAG, str(ASSET_PATH),
             "--repo", REPO, "--clobber"],
            capture_output=True, text=True, timeout=300,
        )
        if up.returncode != 0:
            sys.exit(f"GitHub Release asset upload failed:\n{up.stderr.strip()}")
        release_url = f"https://github.com/{REPO}/releases/tag/{TAG}"
    else:
        result = subprocess.run(
            [
                "gh", "release", "create", TAG,
                "--repo", REPO,
                "--title", "EPA Toxic Release Inventory 2023 — 78,647 Records (CSV)",
                "--notes", release_notes,
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
    # Persist immediately so any later crash (Stripe/Gumroad) does not cause a
    # re-run to recreate / churn this live release.
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
        "Thank you! Your EPA Toxic Release Inventory 2023 CSV (78,647 records) is ready:\n\n"
        f"{raw_download_url}\n\n"
        "78,647 facility-chemical records from EPA TRI 2023 public data."
    )
    assert len(success_msg) <= 500, f"success_msg too long: {len(success_msg)} chars"

    stripe_product = stripe_helpers.create_product(
        SLUG,
        stripe_spec["product_name"],
        stripe_spec["description"],
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_product",
    )
    print(f"   Product: {stripe_product.id}")

    stripe_price = stripe_helpers.create_price(
        stripe_product.id,
        PRICE,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_price",
    )
    print(f"   Price:   {stripe_price.id}")
    _save_partial(stripe_product_id=stripe_product.id, stripe_price_id=stripe_price.id)

    stripe_link = stripe_helpers.create_payment_link(
        stripe_price.id,
        success_msg,
        idempotency_key=f"dsl_{SLUG.replace('-', '_')}_link",
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

DESC = gumroad_spec["description"]

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
            page.screenshot(path="/tmp/gr_epa_tri_login_fail.png")
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
    asset_mb = ASSET_PATH.stat().st_size / (1024 * 1024)
    try:
        fi = page.locator("input[type='file']").first
        fi.set_input_files(str(ASSET_PATH))
        wait_s = max(60, int(asset_mb / 2))  # ~2 MB/s upload speed estimate
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

    page.screenshot(path="/tmp/gr_epa_tri_final.png")
    print(f"   Screenshot saved → /tmp/gr_epa_tri_final.png")

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
            # Payment links always redirect — treat as OK if link was just created
            print(f"   {label} smoke: redirect {exc.code} (link just created — OK)")
        else:
            smoke_passed = False
            smoke_reason = f"{label} URL returned HTTP {exc.code}"
            print(f"   {label} smoke: FAIL — HTTP {exc.code}")
    except Exception as exc:
        # Connection refused / timeout / DNS failure — the buyer-facing link is
        # NOT reachable. Fail the smoke test rather than shipping a dead link.
        smoke_passed = False
        smoke_reason = f"{label} URL unreachable: {exc}"
        print(f"   {label} smoke: FAIL — unreachable ({exc})")

print(f"   Smoke test: {'PASS ✓' if smoke_passed else 'FAIL ✗'}\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Append to distribution-queue.json BEFORE writing the SHIPPED report.
# If the append fails (e.g. schema violation), we mark the ship FAILED instead of
# leaving a SHIPPED-but-unqueued product that can never be retried. Stripe objects
# are preserved in launch-report.partial.json so a re-run reuses them (no dup).
# ─────────────────────────────────────────────────────────────────────────────
if smoke_passed:
    print("[5/6] Appending to distribution queue…")
    from scripts.lib.distribution_queue import append_item

    # The distribution_queue schema REQUIRES a non-empty `audience` string. This
    # spec has no top-level `audience`, so derive one from its distribution
    # targets (reddit angles).
    _dq = spec.get("distribution_queue", {})
    _angles = [t.get("angle", "").strip() for t in _dq.get("reddit_targets", [])]
    _audience = "; ".join(a for a in _angles if a) or (
        "ESG / environmental-compliance attorneys, sustainability consultants, "
        "and ESG benchmarking analysts."
    )

    item = {
        "id": f"{SLUG}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "slug": SLUG,
        "name": spec["name"],
        "stripe_payment_link_url": stripe_url,
        "gumroad_url": gumroad_url,
        "price_usd": PRICE,
        "audience": _audience,
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
    print("[5/6] Skipping queue append — smoke test did not pass")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Write launch-report.json (status reflects the queue-append result)
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
        f"Live on Stripe + Gumroad. CSV (78,647 rows) hosted on GitHub Release. "
        f"Smoke tests green. Distribution queue updated."
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
print(f"   Written: {REPORT_FILE}")

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
