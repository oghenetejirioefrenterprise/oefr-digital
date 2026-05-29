#!/usr/bin/env python3
"""Send urgent pipeline blocker notification."""
import os
import sys
import requests

# Founder chat ID is read from the env (sourced from .profile/trinity.toml) with
# a shared default so it lives in one place across the notify scripts.
founder_chat_id = os.environ.get("FOUNDER_CHAT_ID", "1366707521")

# Default message body. Kept as a function default so the blocker details can be
# passed in at call time rather than re-sending this stale snapshot on every run.
# HTML markup (<b>) is used because parse_mode is "HTML" — Telegram's HTML parser
# does not interpret Markdown ** ** and would otherwise show literal asterisks.
DEFAULT_MESSAGE = """🚨 URGENT: nonprofit-board-directors-executives BLOCKED

<b>Pipeline Status:</b> ❌ FAILED at data-engineer phase

<b>Critical Issue:</b>
IRS Form 990 XML files DEPRECATED - AWS S3 bucket completely empty. Cannot extract individual officer/director names from Part VII as originally planned.

<b>What Failed:</b>
• IRS 990 XML bulk downloads (404 - source removed)
• ProPublica bulk downloads (404)
• IRS SOI extracts (no Part VII officer names)

<b>What We Have:</b>
✅ 392,072 nonprofits from IRS EO BMF ($50K+ revenue)
✅ State charity registries (CA, NY, etc.) with contact emails/phones

<b>Recommended Pivot:</b>
Build "Contact-Enriched Nonprofit Directory" instead:
• Organization-level contacts (not individual board members)
• 200K-300K contactable nonprofits
• State registry emails + phones + NTEE codes + revenue tiers
• Price: $99-$149 (lower than original $149 due to reduced scope)

<b>Decision Required:</b>
1. ✅ PIVOT to contact-enriched approach (simpler, available data)
2. ❌ SEARCH for alternative 990 XML sources (may not exist)
3. ❌ ABANDON opportunity (lose work invested)

<b>Impact on Original Spec:</b>
• Original: 550K individual executives/board members
• Pivot: 200-300K organizational contacts
• Buyer segments same: fundraising software, grant consultants, board SaaS, CPA firms
• Value prop shifts from "board director list" to "nonprofit contact database"

Need your call on pivot vs. abandon. Data-engineer cannot proceed without decision.

Reply with option 1, 2, or 3."""


def send_blocker(message: str = DEFAULT_MESSAGE) -> bool:
    """Send an urgent pipeline-blocker notification. Returns True on success."""
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
        print("✅ Urgent blocker notification sent")
        return True
    print(f"❌ Failed: {response.status_code}")
    sys.exit(1)


if __name__ == '__main__':
    send_blocker()
