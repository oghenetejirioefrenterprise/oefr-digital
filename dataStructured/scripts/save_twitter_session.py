#!/usr/bin/env python3
"""
One-time helper: opens a REAL visible browser window for you to log into X.
Once you log in and close the window, your session is saved and posting is automated forever.

Usage:
  source ~/.profile
  python3 scripts/save_twitter_session.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
COOKIES_PATH = BASE / "state" / "browser_cookies" / "twitter.json"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright not installed — run: pip install playwright && playwright install chromium")

print("=" * 60)
print("X/Twitter Session Setup")
print("=" * 60)
print()
print("A browser window is about to open.")
print("1. Log into X with your credentials")
print("2. Once you see your home feed, CLOSE the browser window")
print("3. Your session will be saved automatically")
print()
print("Press Enter to open the browser...")
input()

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=False,  # REAL visible window
        args=["--no-sandbox"],
    )
    ctx = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.6367.155 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()
    page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")

    print("\nBrowser is open. Log in to X, then CLOSE the window.")
    print("Waiting for you to close the browser...")

    try:
        browser.wait_for_event("disconnected", timeout=300_000)  # 5 min timeout
    except Exception:
        pass

    # Save the session before closing
    COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        ctx.storage_state(path=str(COOKIES_PATH))
        print(f"\n✅ Session saved to {COOKIES_PATH}")
        print("X posting is now enabled — run the distribution agent to catch up.")
    except Exception as e:
        print(f"\n❌ Could not save session: {e}")
    
    browser.close()
