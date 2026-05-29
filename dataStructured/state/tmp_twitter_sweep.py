#!/usr/bin/env python3
"""Temporary Twitter distribution sweep — 2026-05-09"""
import asyncio
import os
import sys
from pathlib import Path

BASE = Path("/home/oghenetejiri/apps/dataStructured")
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted, append_entry
from scripts.social_helpers import _x_post_browseruse, _log_entry, COOKIES_DIR

ITEMS = [
    {
        "item_id": "new-fmcsa-carrier-leads-2026-05-2026-05-04",
        "slug": "new-fmcsa-carrier-leads-2026-05",
        "hook": "15,770 new FMCSA carrier registrations from DOT public data — name, MC#, DOT#, address, phone. Every new trucking operator that registered this month. If you sell to new carriers, this is your list.",
        "link": "https://buy.stripe.com/cNi14g4CP7aT8mT1iC7IY0c",
    },
    {
        "item_id": "new-business-formations-csv-2026-05-2026-05-05",
        "slug": "new-business-formations-csv-2026-05",
        "hook": "15,997 new Florida LLCs and corps from state public records filed this month. If you target new businesses — insurance, bookkeeping, web design, payroll — hit them before anyone else.",
        "link": "https://buy.stripe.com/aFaaEQc5h66Pbz5f9s7IY0f",
    },
    {
        "item_id": "samgov-small-biz-contractor-leads-2026-05-2026-05-05",
        "slug": "samgov-small-biz-contractor-leads-2026-05",
        "hook": "4,731 small-business IT contractors in the DC/MD/VA corridor from SAM.gov — 8(a), HUBZone, WOSB, SDVOSB. If you need teaming partners or federal IT clients, this is the list.",
        "link": "https://buy.stripe.com/dRm5kwb1dfHp7iPe5o7IY0g",
    },
    {
        "item_id": "fl-real-estate-agent-licenses-2026-05-2026-05-06",
        "slug": "fl-real-estate-agent-licenses-2026-05",
        "hook": "319,247 licensed Florida real estate agents and brokers from DBPR public records. Name, license #, address, brokerage. Full FL market in one CSV — proptech SDRs, mortgage lenders, E&O brokers.",
        "link": "https://buy.stripe.com/cNi8wIb1dfHpeLhe5o7IY0k",
    },
    {
        "item_id": "cms-medicare-home-health-agencies-2026-05-2026-05-05",
        "slug": "cms-medicare-home-health-agencies-2026-05",
        "hook": "12,392 Medicare-certified home health agencies across the US from CMS public data. Name, address, phone, certification date. If you sell EVV, billing, or staffing to HHAs, this is your list.",
        "link": "https://buy.stripe.com/5kQcMYfhtgLtdHdgdw7IY0h",
    },
    {
        "item_id": "faa-civil-aircraft-registration-2026-05-2026-05-06",
        "slug": "faa-civil-aircraft-registration-2026-05",
        "hook": "302,810 US-registered civil aircraft from the FAA database. N-number, make, model, year, registrant name and address. Full US civil aviation market in one CSV — insurers, avionics, MRO, parts.",
        "link": "https://buy.stripe.com/5kQdR20mz0Mvbz5f9s7IY0l",
    },
    {
        "item_id": "fl-alcoholic-beverage-licensees-2026-05-2026-05-07",
        "slug": "fl-alcoholic-beverage-licensees-2026-05",
        "hook": "52,152 active Florida alcohol licensees — bars, restaurants, nightclubs, package stores — from DBPR. Name, license type, address, county. Full FL hospitality market in one CSV.",
        "link": "https://buy.stripe.com/cNi5kwglx9j10Ur0ey7IY0m",
    },
    {
        "item_id": "nppes-physical-therapist-clinics-2026-05-2026-05-07",
        "slug": "nppes-physical-therapist-clinics-2026-05",
        "hook": "377,805 active US physical therapists and PT clinics from CMS NPPES. NPI, specialty, address, phone — 99.98% phone coverage. Every licensed PT in the country, all 50 states.",
        "link": "https://buy.stripe.com/6oU3co9X9br9dHd2mG7IY0n",
    },
    {
        "item_id": "tx-tdlr-electricians-2026-05-2026-05-07",
        "slug": "tx-tdlr-electricians-2026-05",
        "hook": "204,535 licensed Texas electricians from TDLR — master, journeyman, contractors, apprentices. Name, license class, address, phone. Complete TX electrical market in one CSV.",
        "link": "https://buy.stripe.com/00w28k3yLbr946D5yS7IY0o",
    },
    {
        "item_id": "tx-tdlr-hvac-contractors-2026-05-2026-05-07",
        "slug": "tx-tdlr-hvac-contractors-2026-05",
        "hook": "56,001 active Texas HVAC contractors and AC technicians from TDLR. Name, license type, address, phone. If you sell equipment, software, or services to TX HVAC shops — full market in one CSV.",
        "link": "https://buy.stripe.com/8x27sEglx3YHdHd8L47IY0p",
    },
    {
        "item_id": "ca-cslb-licensed-contractors-2026-05-2026-05-07",
        "slug": "ca-cslb-licensed-contractors-2026-05",
        "hook": "232,617 active California licensed contractors from CSLB. 30+ trade classes — general building, electrical, plumbing, roofing, HVAC and more. Largest US state contractor database. One CSV.",
        "link": "https://buy.stripe.com/4gMaEQb1deDlcD91iC7IY0q",
    },
    {
        "item_id": "nppes-dentists-dental-practices-2026-05-2026-05-07",
        "slug": "nppes-dentists-dental-practices-2026-05",
        "hook": "371,786 active US dentists and dental practices from CMS NPPES. NPI, specialty, address, phone — 100% phone coverage, all 50 states. If you sell to dental practices, this is the full US market.",
        "link": "https://buy.stripe.com/cNi9AM3yL0MvfPl0ey7IY0r",
    },
    {
        "item_id": "sec-registered-investment-advisers-2026-05-2026-05-07",
        "slug": "sec-registered-investment-advisers-2026-05",
        "hook": "16,551 SEC-registered RIA firms from IAPD public data. Same data wealthtech platforms charge $5K-20K/yr to access. CRD#, SEC#, reg date, address. One CSV, one payment, yours forever.",
        "link": "https://buy.stripe.com/bJe00c1qD7aT8mT0ey7IY0s",
    },
]


def main():
    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")
    if not username or not password:
        print("ERROR: X_USERNAME / X_PASS not set — run: source ~/.profile", file=sys.stderr)
        sys.exit(1)

    results = []
    for item in ITEMS:
        item_id = item["item_id"]
        slug = item["slug"]
        hook = item["hook"]
        link = item["link"]
        channel = "twitter"

        if already_posted(BASE, item_id, channel):
            print(f"SKIP — {item_id} already posted to twitter")
            results.append({"item_id": item_id, "status": "skipped"})
            continue

        # Enforce 280-char limit on hook
        if len(hook) > 280:
            hook = hook[:277] + "..."

        print(f"\nPosting: {item_id}")
        print(f"  Hook ({len(hook)} chars): {hook[:60]}...")
        print(f"  Link: {link}")

        try:
            post_url = asyncio.run(_x_post_browseruse(hook, link, username, password))
            append_entry(BASE, _log_entry(
                item_id=item_id,
                slug=slug,
                channel=channel,
                status="posted",
                url=post_url,
                content=f"{hook}\n\nREPLY: {link}",
            ))
            print(f"  POSTED — {post_url}")
            results.append({"item_id": item_id, "status": "posted", "url": post_url})
        except Exception as exc:
            err = str(exc)
            append_entry(BASE, _log_entry(
                item_id=item_id,
                slug=slug,
                channel=channel,
                status="failed",
                error=err,
            ))
            print(f"  FAILED — {err[:120]}", file=sys.stderr)
            results.append({"item_id": item_id, "status": "failed", "error": err[:120]})

    print("\n=== TWITTER SWEEP SUMMARY ===")
    posted = [r for r in results if r["status"] == "posted"]
    failed = [r for r in results if r["status"] == "failed"]
    skipped = [r for r in results if r["status"] == "skipped"]
    print(f"Posted:  {len(posted)}")
    print(f"Failed:  {len(failed)}")
    print(f"Skipped: {len(skipped)}")
    for r in posted:
        print(f"  + {r['item_id']} — {r.get('url', '')}")
    for r in failed:
        print(f"  x {r['item_id']} — {r.get('error', '')}")


if __name__ == "__main__":
    main()
