#!/usr/bin/env python3
"""Send the CEO daily DM for 2026-05-28 using the format_daily_dm template."""
import os
import sys
from pathlib import Path

import requests

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE))
from scripts.ceo_orchestrator import format_daily_dm  # noqa: E402

DATE = "2026-05-28"

advanced = [
    "independent-retail-pharmacy-directory (brief score 8/10): pipeline INITIATED — "
    "data-engineer → data-steward → compliance-officer → (PASS) → engineer/ship. "
    "Target: ~19,400 independent community/compounding/specialty/LTC pharmacy FACILITIES "
    "(NPPES Type 2 333600000X + DEA registrant + state boards). "
    "Wedge: chain-exclusion filter (CVS/Walgreens/Rite Aid/Walmart/Kroger removed) — "
    "no $1.5K–$6K/yr vendor offers it. First SKU: TX independents-only CSV $49. "
    "Currently in Phase 1 (harvest); est. completion 6–8h.",
    "Cross-checked the other 3 PROPOSED briefs (score 7): animal-hospital-veterinary-clinic, "
    "licensed-land-surveyors-pls, towing-recovery-operator — all queued, none rejected, none duplicates.",
]

shipped: list[dict] = []  # none — pharmacy pipeline still running

blocked = [
    {
        "slug": "distribution (X / Reddit / LinkedIn)",
        "reason": "Channels frozen — 48 of last 50 browser posts failing bot-detection; "
                  "distribution-queue.json absent (0 unposted items). Root-cause re-diagnosis "
                  "still open (issues 2026-05-19 / 2026-05-25). Pharmacy go-to-market is LinkedIn-DM / "
                  "direct-vendor-partner, which bypasses the frozen channels — build keeps flowing.",
    },
    {
        "slug": "revenue",
        "reason": "MRR $0, 7+ days $0 across 27 live products (CFO digest). CFO proposes high-priority "
                  "distribution-channel audit + launch-week pricing test. Needs your call on direction.",
    },
]

running_tomorrow = (
    "13:00 ET opportunity-researcher demand scan · 14:00 ET product-manager spec drafting · "
    "19:00 ET CEO pipeline orchestration + distribution sweep · "
    "monitor independent-retail-pharmacy-directory (harvest→validate→compliance→ship) to completion"
)

message = format_daily_dm(
    date=DATE,
    advanced=advanced,
    shipped=shipped,
    blocked=blocked,
    running_tomorrow=running_tomorrow,
    cycle_cost_tokens=95000,
)

bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not bot_token:
    print("ERROR: TELEGRAM_BOT_TOKEN not set")
    print("---- DM PREVIEW ----")
    print(message)
    sys.exit(1)

founder_chat_id = os.environ.get("FOUNDER_CHAT_ID", "1366707521")
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": founder_chat_id,
    "text": message,
    "disable_web_page_preview": True,
}
try:
    resp = requests.post(url, json=payload, timeout=(5, 15))
except requests.exceptions.RequestException as e:
    print(f"FAILED to send DM: {e}")
    print(message)
    sys.exit(1)

if resp.status_code == 200:
    print("Daily DM sent to founder")
    print(message)
else:
    print(f"FAILED to send DM: {resp.status_code} {resp.text}")
    print(message)
    sys.exit(1)
