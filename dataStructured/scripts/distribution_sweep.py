#!/usr/bin/env python3
"""Distribution sweep — post all unposted queue items to X and Reddit.

Reads distribution-queue.json, generates platform-specific content,
and posts to X (Twitter) and Reddit for all items not already posted.

Usage:
  source ~/.profile && python scripts/distribution_sweep.py
  source ~/.profile && python scripts/distribution_sweep.py --dry-run
  source ~/.profile && python scripts/distribution_sweep.py --platform twitter
  source ~/.profile && python scripts/distribution_sweep.py --platform reddit
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted  # noqa: E402
from scripts.social_helpers import _x_post_browseruse, _reddit_post_browseruse, _log_entry, append_entry  # noqa: E402
from scripts.social_helpers import _browseruse_llm, _x_browser_profile  # noqa: E402

QUEUE_PATH = BASE / "state" / "distribution-queue.json"

# Subreddit mapping for each product type
SUBREDDIT_MAP = {
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
    "fdic-bank-branch-directory-2026-05": ["r/fintech"],
    "ttb-brewery-winery-distillery-directory-2026-05": ["r/TheBrewery", "r/winemaking"],
    "sbir-sttr-award-recipients": ["r/govcontracting", "r/startups"],
}


def _generate_tweet(item: dict) -> tuple[str, str]:
    """Generate hook tweet + link for X. Returns (hook_text, link_url)."""
    name = item["name"]
    price = item["price_usd"]
    url = item["stripe_payment_link_url"]

    # Extract key stats from name
    if "15,770" in name and "FMCSA" in name:
        hook = "🚚 15,770 new FMCSA carriers registered May 2026. Fresh leads for trucking insurance agents, ELD vendors, freight factoring reps."
    elif "15,997" in name and "Florida LLC" in name:
        hook = "📋 15,997 new Florida LLCs & Corps from May 2026 state filings. Target new businesses before competitors find them."
    elif "4,731" in name and "SAM.gov" in name:
        hook = "🏛️ 4,731 SAM.gov small-biz IT contractors (DC/MD/VA corridor). For teaming partners, IT staffing, SaaS vendors targeting fed contractors."
    elif "319,247" in name and "Real Estate" in name:
        hook = "🏡 319,247 FL licensed real estate agents & brokers from DBPR. For proptech SDRs, mortgage lenders, E&O insurance, CE providers."
    elif "12,392" in name and "Home Health" in name:
        hook = "🏥 12,392 Medicare-certified home health agencies nationwide. For medical SaaS (EVV, billing), DME reps, healthcare staffing."
    elif "302,810" in name and "Aircraft" in name:
        hook = "✈️ 302,810 US civil aircraft from FAA registry. For aviation insurance, avionics shops, MRO facilities, parts vendors."
    elif "52,152" in name and "Alcohol" in name:
        hook = "🍺 52,152 active FL alcohol licensees (bars, restaurants, package stores). For liquor distributors, POS vendors, insurance."
    elif "377,805" in name and "Physical Therap" in name:
        hook = "🏥 377,805 US Physical Therapists & PT clinics from CMS NPPES. 99.98% phone coverage. For medical SaaS, equipment reps, staffing."
    elif "Electrician" in name and ("TDLR" in name or "Texas" in name):
        hook = "⚡ 204,535 Texas licensed electricians & electrical contractors from TDLR. For supply distributors, SaaS vendors, CE providers."
    elif "HVAC" in name and ("TDLR" in name or "Texas" in name):
        hook = "❄️ 56,001 Texas HVAC contractors & AC technicians from TDLR. For equipment distributors, SaaS vendors, parts suppliers."
    elif "California" in name and "Contractor" in name and "CSLB" in name:
        hook = "🏗️ 232,617 California licensed contractors from CSLB. Largest state contractor database. For Procore/Buildertrend SDRs, insurance, distributors."
    elif "Dentist" in name and "NPPES" in name:
        hook = "🦷 371,786 US dentists & dental practices from CMS NPPES. 100% phone coverage. For dental supply, SaaS, equipment reps, CE providers."
    elif "Investment Adviser" in name or "RIA" in name:
        hook = "💼 16,551 SEC-registered investment adviser firms from IAPD. For wealthtech SaaS, asset managers, recruiters, M&A advisers."
    elif "Bank Branch" in name or "FDIC" in name:
        hook = "🏦 77,542 US bank branches from FDIC. For fintech BD teams, CRE brokers, insurance companies, ATM operators, site-selection consultants."
    elif "Brewery" in name or "Winery" in name or "Distillery" in name:
        hook = "🍷 82,500+ US licensed wineries, breweries & distilleries from TTB federal data. For equipment suppliers, POS platforms, ingredient vendors."
    elif "SBIR" in name or "STTR" in name:
        hook = "🚀 17,664 SBIR/STTR federal R&D awards (FY2023-2025), $13.71B funding tracked. For defense primes, deep-tech VCs, SBIR consultants."
    else:
        # Fallback: first 200 chars of name
        hook = name[:200]

    # Add price if hook is short enough
    if len(hook) < 240:
        hook += f" CSV. ${price}."

    # Truncate if needed
    if len(hook) > 280:
        hook = hook[:277] + "..."

    return (hook, url)


def _generate_reddit_post(item: dict, subreddit: str) -> tuple[str, str]:
    """Generate title + body for Reddit. Returns (title, body)."""
    name = item["name"]
    price = item["price_usd"]
    url = item["stripe_payment_link_url"]
    audience = item.get("audience", "B2B sales teams, vendors")

    # Create a subreddit-specific title
    if "FMCSA" in name and "r/Truckers" in subreddit:
        title = "15,770 New FMCSA Carrier Registrations (May 2026) — Fresh DOT Data"
    elif "FMCSA" in name and "r/FreightBrokers" in subreddit:
        title = "Fresh FMCSA Carrier Leads — May 2026 (15,770 Records)"
    elif "Florida LLC" in name:
        title = "15,997 New Florida Business Formations — May 2026 (CSV)"
    elif "SAM.gov" in name:
        title = "SAM.gov Small Biz Contractor Database — DMV IT Corridor (4,731 Records)"
    elif "Real Estate" in name:
        title = "Florida Licensed Real Estate Agents Database — 2026 (319,247 Records)"
    elif "Home Health" in name:
        title = "Medicare-Certified Home Health Agencies — US Database 2026"
    elif "Aircraft" in name:
        title = "US Civil Aircraft Registration Database — FAA 2026 (302,810 Records)"
    elif "Alcohol" in name:
        title = "Florida Active Alcohol Licensees — Bars, Restaurants, Package Stores (52,152)"
    elif "Physical Therap" in name:
        title = "US Physical Therapists & PT Clinics — NPI Database 2026 (377,805)"
    elif "Electrician" in name:
        title = "Texas Licensed Electricians Database — TDLR 2026 (204,535 Records)"
    elif "HVAC" in name:
        title = "Texas HVAC Contractors & AC Technicians — TDLR 2026 (56,001)"
    elif "California" in name and "Contractor" in name:
        title = "California Licensed Contractors — CSLB Database 2026 (232,617 Records)"
    elif "Dentist" in name:
        title = "US Dentists & Dental Practices — NPI Database 2026 (371,786 Records)"
    elif "Investment Adviser" in name:
        title = "SEC Registered Investment Advisers — 2026 RIA Database (16,551 Firms)"
    elif "Bank Branch" in name or "FDIC" in name:
        title = "US Bank Branch Directory 2026 — 77,542 FDIC-Insured Branches (CSV)"
    elif "Brewery" in name or "Winery" in name or "Distillery" in name:
        title = "US Winery & Distillery Directory 2026 — 82,500+ Licensed Producers (TTB)"
    elif "SBIR" in name or "STTR" in name:
        title = "SBIR/STTR Federal R&D Award Database FY2023-2025 — 17,664 Awards ($13.71B)"
    else:
        title = name[:295] + "..." if len(name) > 295 else name

    # Body: problem statement + use case + link
    body = (
        f"Public data product built from {name.split('—')[0].strip()} records.\n\n"
        f"**Who uses this:**\n{audience}\n\n"
        f"CSV format. One-time purchase, instant download.\n\n"
        f"${price} → {url}"
    )

    return (title, body)


async def post_to_twitter(item: dict, dry_run: bool = False) -> None:
    """Post item to X (Twitter) if not already posted."""
    item_id = item["id"]
    slug = item["slug"]
    channel = "twitter"

    if already_posted(BASE, item_id, channel):
        print(f"[X] SKIP — {slug} already posted to {channel}")
        return

    if dry_run:
        hook, link = _generate_tweet(item)
        print(f"[X] DRY-RUN — {slug}")
        print(f"    Hook: {hook}")
        print(f"    Link: {link}")
        return

    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")

    if not username or not password:
        print("[X] ERROR — X_USERNAME / X_PASS not set", file=sys.stderr)
        return

    try:
        hook, link = _generate_tweet(item)
        print(f"[X] POSTING — {slug}")
        print(f"    Hook: {hook[:80]}...")

        post_url = await _x_post_browseruse(hook, link, username, password)

        append_entry(BASE, _log_entry(
            item_id=item_id,
            slug=slug,
            channel=channel,
            status="posted",
            url=post_url,
            content=f"{hook}\n\nREPLY: {link}",
        ))
        print(f"[X] SUCCESS — {post_url}")

    except Exception as exc:
        append_entry(BASE, _log_entry(
            item_id=item_id,
            slug=slug,
            channel=channel,
            status="failed",
            error=str(exc),
        ))
        print(f"[X] FAILED — {slug}: {exc}", file=sys.stderr)


async def post_to_reddit(item: dict, dry_run: bool = False) -> None:
    """Post item to all mapped subreddits if not already posted."""
    item_id = item["id"]
    slug = item["slug"]

    subreddits = SUBREDDIT_MAP.get(slug, [])
    if not subreddits:
        print(f"[Reddit] SKIP — {slug} (no subreddit mapping)")
        return

    username = os.environ.get("REDDIT_USERNAME", "")
    password = os.environ.get("REDDIT_PASSWORD", "")

    if not username or not password:
        print("[Reddit] ERROR — REDDIT_USERNAME / REDDIT_PASSWORD not set", file=sys.stderr)
        return

    for subreddit in subreddits:
        channel = f"reddit:{subreddit}"

        if already_posted(BASE, item_id, channel):
            print(f"[Reddit] SKIP — {slug} already posted to {channel}")
            continue

        if dry_run:
            title, body = _generate_reddit_post(item, subreddit)
            print(f"[Reddit] DRY-RUN — {slug} → {subreddit}")
            print(f"    Title: {title}")
            print(f"    Body: {body[:100]}...")
            continue

        try:
            title, body = _generate_reddit_post(item, subreddit)
            print(f"[Reddit] POSTING — {slug} → {subreddit}")
            print(f"    Title: {title[:80]}...")

            post_url = await _reddit_post_browseruse(subreddit, title, body, username, password)

            append_entry(BASE, _log_entry(
                item_id=item_id,
                slug=slug,
                channel=channel,
                status="posted",
                url=post_url,
                content=f"{title}\n\n{body}",
            ))
            print(f"[Reddit] SUCCESS — {post_url}")

        except Exception as exc:
            append_entry(BASE, _log_entry(
                item_id=item_id,
                slug=slug,
                channel=channel,
                status="failed",
                error=str(exc),
            ))
            print(f"[Reddit] FAILED — {slug} → {subreddit}: {exc}", file=sys.stderr)


async def main():
    parser = argparse.ArgumentParser(description="Distribution sweep for all unposted products")
    parser.add_argument("--dry-run", action="store_true", help="Preview content without posting")
    parser.add_argument("--platform", choices=["twitter", "reddit", "both"], default="both",
                        help="Which platform(s) to post to")
    args = parser.parse_args()

    # Check env vars early — auto-source ~/.profile if needed
    if not os.environ.get("ANTHROPIC_API_KEY"):
        import subprocess
        result = subprocess.run(
            ["bash", "-c", "source ~/.profile && env"],
            capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k, v)

    # social_helpers uses ChatAnthropic (ANTHROPIC_API_KEY) — not OpenAI
    if args.platform in ["twitter", "both"]:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ERROR: ANTHROPIC_API_KEY not set — run: source ~/.profile")
        if not os.environ.get("X_USERNAME") or not os.environ.get("X_PASS"):
            sys.exit("ERROR: X_USERNAME / X_PASS not set — run: source ~/.profile")

    if args.platform in ["reddit", "both"]:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ERROR: ANTHROPIC_API_KEY not set — run: source ~/.profile")
        if not os.environ.get("REDDIT_USERNAME") or not os.environ.get("REDDIT_PASSWORD"):
            sys.exit("ERROR: REDDIT_USERNAME / REDDIT_PASSWORD not set — run: source ~/.profile")

    if not QUEUE_PATH.exists():
        sys.exit(f"ERROR: {QUEUE_PATH} not found")

    queue = json.loads(QUEUE_PATH.read_text())
    items = queue.get("items", [])

    if not items:
        print("No items in queue.")
        return

    print(f"\n{'='*80}")
    print(f"Distribution Sweep — {len(items)} products in queue")
    print(f"Platform: {args.platform.upper()}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"{'='*80}\n")

    for item in items:
        print(f"\n--- {item['name'][:70]} ---")

        if args.platform in ["twitter", "both"]:
            await post_to_twitter(item, dry_run=args.dry_run)

        if args.platform in ["reddit", "both"]:
            await post_to_reddit(item, dry_run=args.dry_run)

    print(f"\n{'='*80}")
    print("Sweep complete.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
