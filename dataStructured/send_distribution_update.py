#!/usr/bin/env python3
"""Send distribution update to founder."""
import os
import sys
import requests

# Founder chat ID is read from the env (sourced from .profile/trinity.toml) with
# a shared default so it lives in one place across the notify scripts.
founder_chat_id = os.environ.get("FOUNDER_CHAT_ID", "1366707521")

# Default message body. Kept as a function default so the status can be passed in
# at call time rather than re-sending this stale snapshot on every run.
# HTML markup (<b>) is used because parse_mode is "HTML" — Telegram's HTML parser
# does not interpret Markdown ** ** and would otherwise show literal asterisks.
DEFAULT_MESSAGE = """🔔 Distribution Update — 2026-05-23 19:40 ET

✅ <b>LinkedIn: 16/16 products posted</b>
• All queued items successfully distributed

❌ <b>X/Twitter: 0/16 blocked</b>
❌ <b>Reddit: 0/16 blocked</b>
• Cause: Anthropic API $0 balance (browser-use scripts frozen)
• Known issue since 2026-05-19

<b>Immediate Options:</b>
1. Add Anthropic API credits ($100+ recommended)
2. Manual posting to X/Reddit (I can generate copy)
3. Defer X/Reddit until credits restored

LinkedIn distribution is fully operational. X/Reddit require API credits for browser automation.

Need decision on which option to pursue for the 16 queued products."""


def send_update(message: str = DEFAULT_MESSAGE) -> bool:
    """Send a distribution update to the founder. Returns True on success."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": founder_chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=(5, 15))
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed: network error: {e}")
        sys.exit(1)

    if response.status_code == 200:
        print("✅ Distribution update sent")
        return True
    print(f"❌ Failed: {response.status_code}")
    sys.exit(1)


if __name__ == '__main__':
    send_update()
