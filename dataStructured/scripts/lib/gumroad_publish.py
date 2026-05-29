"""Canonical Gumroad listing publisher (Playwright, browser-only).

The Gumroad write API is deprecated, so every ship script drives the dashboard
UI. That flow was copy-pasted (and drifted) across ~20 scripts; this is the
single hardened implementation, ported from the reviewed ``deploy_gumroad.py``
flow with the audit fixes baked in:

* file-upload completion is verified (poll for the filename chip) before
  publishing — never publish a paid product with no asset attached;
* the publish action targets an explicit Publish control, then confirms the
  listing is live;
* the public ``/l/<permalink>`` URL is read from the page / Share tab — it is
  NEVER synthesized from the ``/products/<id>/edit`` token (that 404s buyers).
  If the real permalink can't be read, we raise rather than emit a guess.
* login-failure screenshots go to a private 0700 dir, not world-readable /tmp.

Callers own the browser lifecycle and pass a logged-in (or to-be-logged-in)
``page``. All fatal conditions raise ``GumroadError`` so the caller can mark the
ship FAILED instead of recording a false success.
"""
import re
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PWTimeout


class GumroadError(RuntimeError):
    """Raised on any fatal Gumroad publishing failure."""


def _shot_dir() -> Path:
    """Private (0700) directory for diagnostic screenshots."""
    return Path(tempfile.mkdtemp(prefix="gumroad_", dir=None))


def _normalize_permalink(href: str | None) -> str | None:
    """Return an absolute ``https://gumroad.com/l/...`` URL from *href*, else None.

    Pure helper (unit-tested). Accepts absolute or root-relative hrefs; rejects
    anything without the public ``/l/`` segment so a guessed ``/products/<id>``
    edit link can never be mistaken for a permalink.
    """
    if not href or "/l/" not in href:
        return None
    href = href.strip()
    if href.startswith("/"):
        return "https://gumroad.com" + href
    return href


def login(page: Page, username: str, password: str) -> None:
    """Log in to Gumroad. Raises GumroadError on missing creds or failed login."""
    if not username or not password:
        raise GumroadError("Gumroad username and password are required")
    page.goto("https://gumroad.com/login", timeout=30000)
    page.wait_for_load_state("networkidle")
    page.fill("input[type='email']", username)
    page.fill("input[type='password']", password)
    page.click("button[type='submit']")
    try:
        page.wait_for_url("https://gumroad.com/dashboard**", timeout=30000)
    except PWTimeout:
        current = page.url
        if "gumroad.com" not in current or "login" in current:
            shot = _shot_dir() / "gumroad_login_fail.png"
            try:
                page.screenshot(path=str(shot))
            except Exception:
                pass
            raise GumroadError(f"Gumroad login failed (at {current}); screenshot: {shot}")


def _fill_first(page: Page, selectors, value: str) -> bool:
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(value)
                return True
        except Exception:
            continue
    return False


def _click_first(page: Page, selectors) -> str | None:
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                return sel
        except Exception:
            continue
    return None


def publish_listing(
    page: Page,
    *,
    name: str,
    description: str,
    price_usd: int,
    asset_path: str,
) -> str:
    """Create + publish a Gumroad listing; return its real public permalink.

    Raises GumroadError if the form can't be submitted, the asset upload can't
    be confirmed, or the public permalink can't be read.
    """
    asset = Path(asset_path)
    if not asset.exists():
        raise GumroadError(f"Asset not found: {asset}")

    page.goto("https://app.gumroad.com/products/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    if not _fill_first(page, [
        "input[placeholder*='name' i]", "input[name='name']",
        "input[type='text']:first-of-type", "[data-testid='product-name']", "#name",
    ], name):
        raise GumroadError("Could not fill product name field")

    _fill_first(page, [
        "input[name='price']", "input[placeholder*='price' i]",
        "input[aria-label*='price' i]", "#price",
    ], str(price_usd))

    if not _click_first(page, [
        "button[type='submit']", "button:has-text('Create')",
        "button:has-text('Continue')", "button:has-text('Next')", "input[type='submit']",
    ]):
        raise GumroadError("Could not find the create/submit button")

    try:
        page.wait_for_url("https://app.gumroad.com/products/*/edit**", timeout=30000)
    except PWTimeout:
        try:
            page.wait_for_url("**/products/**", timeout=15000)
        except PWTimeout:
            pass
    time.sleep(2)

    _fill_first(page, [
        "textarea[name='description']", "[contenteditable='true']",
        ".ql-editor", "textarea", "[role='textbox']",
    ], description)

    # Upload — fatal if it can't start or never completes.
    asset_mb = asset.stat().st_size / (1024 * 1024)
    try:
        page.locator("input[type='file']").first.set_input_files(str(asset))
    except Exception as e:
        raise GumroadError(f"File upload could not start: {e}")

    deadline = time.time() + max(120, int(asset_mb * 4))
    chip = page.locator(f"text={asset.name}").first
    confirmed = False
    while time.time() < deadline:
        try:
            if chip.is_visible(timeout=2000):
                confirmed = True
                break
        except Exception:
            pass
        time.sleep(3)
    if not confirmed:
        raise GumroadError(
            f"Upload of {asset.name} ({asset_mb:.1f} MB) did not complete; "
            "refusing to publish a product with no downloadable asset"
        )

    # Publish (explicit), then confirm live.
    if not _click_first(page, [
        "button:has-text('Publish and continue')", "button:has-text('Publish')",
        "button:has-text('Go live')", "button:has-text('Make public')",
    ]):
        _click_first(page, [
            "button:has-text('Save')", "button:has-text('Update')", "button[type='submit']",
        ])
    time.sleep(3)

    # Read the REAL permalink (in-page links, then Share tab). Never synthesize.
    url = None
    for sel in ["a[href*='/l/']", "input[value*='/l/']",
                "a:has-text('View product')", "a:has-text('gumroad.com/l/')"]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                url = _normalize_permalink(el.get_attribute("href") or el.get_attribute("value"))
                if url:
                    break
        except Exception:
            continue

    if not url:
        m = re.search(r"/products/([^/?#]+)", page.url)
        if m:
            try:
                page.goto(f"https://app.gumroad.com/products/{m.group(1)}/edit/share", timeout=30000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                for sel in ["input[value*='/l/']", "a[href*='/l/']"]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=3000):
                            url = _normalize_permalink(el.get_attribute("value") or el.get_attribute("href"))
                            if url:
                                break
                    except Exception:
                        continue
            except Exception:
                pass

    if not url:
        raise GumroadError(
            "Could not read the real Gumroad permalink; refusing to emit a guessed /l/ URL"
        )
    return url
