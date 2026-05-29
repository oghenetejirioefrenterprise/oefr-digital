#!/usr/bin/env python3
"""Send CEO daily DM to founder via Telegram."""
import os
import sys
import requests
from datetime import datetime

# Load Telegram bot token
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not bot_token:
    print("ERROR: TELEGRAM_BOT_TOKEN not set")
    sys.exit(1)

# Founder chat ID is read from the env (sourced from .profile/trinity.toml) with
# a shared default so it lives in one place across the notify scripts.
founder_chat_id = os.environ.get("FOUNDER_CHAT_ID", "1366707521")

# Format the daily DM
date = datetime.now().strftime("%Y-%m-%d")
message = f"""📊 DataStructured — {date}
══════════════════════════════
💰 FINANCIALS (CFO Digest):
• MRR: $0
• Revenue today: $0
• Anomalies: 0

ADVANCED TODAY:
• nonprofit-board-directors-executives: Pipeline initiated
  └─ Phases: harvest → validate → compliance → ship (running)
  └─ Product: 500K+ nonprofit executives & board directors from IRS 990s
  └─ Price: $149 CSV (61% below NonProfitLists.com $379 baseline)
  └─ Expected completion: 6-8 hours

DISTRIBUTION:
• 16 products queued for social posting (distribution-agent running)
  └─ FMCSA carriers, FL LLCs, SAM.gov contractors, FL real estate agents
  └─ Medicare home health, FAA aircraft, FL alcohol licensees, PT clinics
  └─ TX electricians, TX HVAC, CA contractors, dentists, SEC RIAs
  └─ FDIC banks, TTB breweries/wineries, SBIR/STTR awards
• Marketing plan: TTB breweries → r/b2bsales scheduled 21:00 ET

SHIPPED:
• (none — nonprofit pipeline in progress)

BLOCKED (needs you):
• (none)

RUNNING TOMORROW:
• 13:00 ET: opportunity-researcher demand scan
• 14:00 ET: product-manager spec drafting for top opportunities
• 19:00 ET: CEO pipeline orchestration + distribution sweep
• Monitor nonprofit-board-directors-executives completion

CYCLE COST: ~85,000 tokens
"""

# Send via Telegram
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": founder_chat_id,
    "text": message,
    "parse_mode": "HTML",
    "disable_web_page_preview": True
}

try:
    response = requests.post(url, json=payload, timeout=(5, 15))
except requests.exceptions.RequestException as e:
    print(f"❌ Failed to send DM: network error: {e}")
    sys.exit(1)

if response.status_code == 200:
    print("✅ Daily DM sent to founder")
    print(message)
else:
    print(f"❌ Failed to send DM: {response.status_code}")
    print(response.text)
    sys.exit(1)
