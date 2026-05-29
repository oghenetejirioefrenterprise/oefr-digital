#!/usr/bin/env python3
"""Simple distribution sweep - shows what needs to be posted."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted

QUEUE_PATH = BASE / "state" / "distribution-queue.json"

# Subreddit mapping
SUBREDDITS = {
    "new-fmcsa-carrier-leads-2026-05": ["r/Truckers", "r/FreightBrokers"],
    "new-business-formations-csv-2026-05": ["r/smallbusiness"],
    "samgov-small-biz-contractor-leads-2026-05": ["r/govcontracting"],
    "fl-real-estate-agent-licenses-2026-05": ["r/RealEstate"],
    "cms-medicare-home-health-agencies-2026-05": ["r/homehealth"],
    "faa-civil-aircraft-registration-2026-05": ["r/aviation"],
    "fl-alcoholic-beverage-licensees-2026-05": ["r/bartenders"],
    "nppes-physical-therapist-clinics-2026-05": ["r/physicaltherapy"],
    "tx-tdlr-electricians-2026-05": ["r/electricians"],
    "tx-tdlr-hvac-contractors-2026-05": ["r/HVAC"],
    "ca-cslb-licensed-contractors-2026-05": ["r/Construction"],
    "nppes-dentists-dental-practices-2026-05": ["r/Dentistry"],
    "sec-registered-investment-advisers-2026-05": ["r/FinancialPlanning"],
}


def main():
    if not QUEUE_PATH.exists():
        print(f"ERROR: {QUEUE_PATH} not found")
        return

    queue = json.loads(QUEUE_PATH.read_text())
    items = queue.get("items", [])

    print(f"\n{'='*90}")
    print(f"DISTRIBUTION STATUS — {len(items)} products")
    print(f"{'='*90}\n")

    twitter_pending = []
    reddit_pending = []

    for item in items:
        item_id = item["id"]
        slug = item["slug"]
        name = item["name"][:60]

        # Check Twitter
        if not already_posted(BASE, item_id, "twitter"):
            twitter_pending.append((slug, name))

        # Check Reddit
        subs = SUBREDDITS.get(slug, [])
        for sub in subs:
            if not already_posted(BASE, item_id, f"reddit:{sub}"):
                reddit_pending.append((slug, name, sub))

    print(f"🐦 X/TWITTER — {len(twitter_pending)} pending posts")
    print("─" * 90)
    for slug, name in twitter_pending:
        print(f"  ○ {name}")
    print()

    print(f"🔴 REDDIT — {len(reddit_pending)} pending posts")
    print("─" * 90)
    for slug, name, sub in reddit_pending:
        print(f"  ○ {name[:50]:<52} → {sub}")
    print()

    print(f"{'='*90}")
    print(f"TOTAL PENDING: {len(twitter_pending)} Twitter + {len(reddit_pending)} Reddit")
    print(f"{'='*90}\n")

    if twitter_pending or reddit_pending:
        print("To execute: source ~/.profile && python3 scripts/distribution_sweep.py")
    else:
        print("✓ All items already posted!")


if __name__ == "__main__":
    main()
