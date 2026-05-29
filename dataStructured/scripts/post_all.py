#!/usr/bin/env python3
"""Post all pending items to X and Reddit.

Requires: source ~/.profile first to load credentials
Usage: source ~/.profile && python3 scripts/post_all.py [--dry-run] [--twitter-only | --reddit-only]
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted, append_entry  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

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


def _generate_tweet_content(item: dict) -> tuple[str, str]:
    """Generate (hook_text, link_url) for Twitter."""
    name = item["name"]
    url = item["stripe_payment_link_url"]

    # Product-specific hooks
    hooks = {
        "fmcsa": "🚚 15,770 new FMCSA carriers May 2026. Fresh leads for trucking insurance, ELD vendors, freight factoring.",
        "florida-llc": "📋 15,997 new FL LLCs & Corps May 2026. Target new businesses before competitors.",
        "samgov": "🏛️ 4,731 SAM.gov small-biz IT contractors (DMV). For teaming partners, staffing, fed contractor SaaS.",
        "real-estate": "🏡 319,247 FL real estate agents/brokers from DBPR. For proptech, lenders, E&O insurance, CE.",
        "home-health": "🏥 12,392 Medicare home health agencies. For medical SaaS (EVV, billing), DME, staffing.",
        "aircraft": "✈️ 302,810 US civil aircraft from FAA. For aviation insurance, avionics, MRO, parts vendors.",
        "alcohol": "🍺 52,152 FL alcohol licensees (bars/restaurants). For distributors, POS vendors, insurance.",
        "physical-therapy": "🏥 377,805 US PTs & clinics from NPPES. 99.98% phone coverage. For SaaS, equipment, staffing.",
        "electricians": "⚡ 204,535 TX electricians from TDLR. For supply distributors, SaaS, CE providers.",
        "hvac": "❄️ 56,001 TX HVAC contractors from TDLR. For equipment distributors, SaaS, parts suppliers.",
        "ca-contractors": "🏗️ 232,617 CA contractors from CSLB. Largest state DB. For Procore/Buildertrend, insurance.",
        "dentists": "🦷 371,786 US dentists from NPPES. 100% phone. For dental supply, SaaS, equipment, CE.",
        "ria": "💼 16,551 SEC RIAs from IAPD. For wealthtech SaaS, asset managers, recruiters, M&A.",
    }

    # Match product to hook
    hook = name[:200]  # fallback
    for key, text in hooks.items():
        if key.replace("-", "").lower() in name.lower().replace(" ", "").replace("-", ""):
            hook = text
            break

    return (hook[:280], url)


def _generate_reddit_content(item: dict, subreddit: str) -> tuple[str, str]:
    """Generate (title, body) for Reddit."""
    name = item["name"]
    price = item["price_usd"]
    url = item["stripe_payment_link_url"]
    audience = item.get("audience", "")

    # Simple title from name
    title = name[:295]

    # Body
    body = (
        f"Public data product from {name.split('—')[0].strip()}.\n\n"
        f"**Use cases:** {audience}\n\n"
        f"CSV format. One-time purchase, instant download. ${price}\n\n"
        f"Link: {url}"
    )

    return (title, body)


def _log_entry(item_id, slug, channel, status, url="", content="", error=""):
    return {
        "item_id": item_id,
        "slug": slug,
        "channel": channel,
        "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": status,
        "url": url,
        "content": content,
        **({"error": error} if error else {}),
    }


async def post_to_twitter(item: dict, dry_run: bool) -> bool:
    """Post to Twitter. Returns True on success."""
    missing = [k for k in ("id", "slug", "name", "stripe_payment_link_url") if not item.get(k)]
    if missing:
        print(f"[X] SKIP — malformed queue item missing {missing}: {item.get('id') or item.get('slug') or '?'}")
        return False

    item_id = item["id"]
    slug = item["slug"]

    if already_posted(BASE, item_id, "twitter"):
        print(f"[X] SKIP — already posted: {slug}")
        return True

    hook, link = _generate_tweet_content(item)

    if dry_run:
        print(f"[X] DRY-RUN — {slug}")
        print(f"    Hook: {hook}")
        print(f"    Link: {link}")
        return True

    # Import here to avoid loading browser-use unless needed
    try:
        from browser_use import Agent, BrowserProfile
        from browser_use.llm.anthropic.chat import ChatAnthropic
    except ImportError:
        print("[X] ERROR — browser-use not installed. Run: pip install browser-use")
        return False

    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not all([username, password, api_key]):
        print("[X] ERROR — X_USERNAME, X_PASS, or ANTHROPIC_API_KEY not set")
        return False

    try:
        print(f"[X] POSTING — {slug}...")
        print(f"    Hook: {hook[:70]}...")

        # Create task for browser-use agent
        task = (
            f"Log in to X at https://x.com/i/flow/login using:\n"
            f"  Username: <secret>x_user</secret>\n"
            f"  Password: <secret>x_pass</secret>\n\n"
            f"Step 1: Post hook tweet:\n{hook}\n\n"
            f"Step 2: Reply with link:\n{link}\n\n"
            f"Return the hook tweet URL."
        )

        profile = BrowserProfile(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        llm = ChatAnthropic(model="claude-haiku-4-5", api_key=api_key, max_tokens=1024)

        agent = Agent(
            task=task,
            llm=llm,
            browser_profile=profile,
            sensitive_data={"x_user": username, "x_pass": password},
            max_failures=3,
        )

        history = await agent.run(max_steps=40)
        result = str(history.final_result() or "")

        # Extract URL
        url_match = re.search(r"https://x\.com/\S+/status/\d+", result)
        if not url_match:
            raise RuntimeError(f"No tweet URL in agent result: {result[:100]}")

        post_url = url_match.group(0)

        append_entry(BASE, _log_entry(
            item_id, slug, "twitter", "posted",
            url=post_url, content=f"{hook}\nREPLY: {link}"
        ))
        print(f"[X] SUCCESS — {post_url}")
        return True

    except Exception as e:
        append_entry(BASE, _log_entry(item_id, slug, "twitter", "failed", error=str(e)))
        print(f"[X] FAILED — {slug}: {e}")
        return False


async def post_to_reddit(item: dict, dry_run: bool) -> bool:
    """Post to all mapped subreddits. Returns True if all succeed."""
    missing = [k for k in ("id", "slug", "name", "stripe_payment_link_url", "price_usd") if item.get(k) in (None, "")]
    if missing:
        print(f"[Reddit] SKIP — malformed queue item missing {missing}: {item.get('id') or item.get('slug') or '?'}")
        return False

    item_id = item["id"]
    slug = item["slug"]

    subs = SUBREDDITS.get(slug, [])
    if not subs:
        return True  # No subreddits mapped

    all_success = True

    for subreddit in subs:
        channel = f"reddit:{subreddit}"

        if already_posted(BASE, item_id, channel):
            print(f"[Reddit] SKIP — already posted: {slug} → {subreddit}")
            continue

        title, body = _generate_reddit_content(item, subreddit)

        if dry_run:
            print(f"[Reddit] DRY-RUN — {slug} → {subreddit}")
            print(f"    Title: {title[:70]}...")
            print(f"    Body: {body[:100]}...")
            continue

        # Import here
        try:
            from browser_use import Agent, BrowserProfile
            from browser_use.llm.anthropic.chat import ChatAnthropic
        except ImportError:
            print("[Reddit] ERROR — browser-use not installed")
            return False

        username = os.environ.get("REDDIT_USERNAME", "")
        password = os.environ.get("REDDIT_PASSWORD", "")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if not all([username, password, api_key]):
            print("[Reddit] ERROR — REDDIT_USERNAME, REDDIT_PASSWORD, or ANTHROPIC_API_KEY not set")
            return False

        try:
            print(f"[Reddit] POSTING — {slug} → {subreddit}...")

            sub_clean = subreddit[2:] if subreddit.startswith("r/") else subreddit.lstrip("/")
            task = (
                f"Log into Reddit at https://www.reddit.com/login\n"
                f"  Username: <secret>reddit_user</secret>\n"
                f"  Password: <secret>reddit_pass</secret>\n\n"
                f"Then navigate to https://www.reddit.com/r/{sub_clean}/submit?type=self\n"
                f"Title: {title}\n"
                f"Body:\n{body}\n\n"
                f"Click Post. Return the post URL."
            )

            profile = BrowserProfile(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            llm = ChatAnthropic(model="claude-haiku-4-5", api_key=api_key, max_tokens=1024)

            agent = Agent(
                task=task,
                llm=llm,
                browser_profile=profile,
                sensitive_data={"reddit_user": username, "reddit_pass": password},
                max_failures=3,
            )

            history = await agent.run(max_steps=25)
            result = str(history.final_result() or "")

            # Extract URL
            url_match = re.search(r"https://www\.reddit\.com/r/[^\s]+/comments/[^\s]+", result)
            post_url = url_match.group(0) if url_match else f"https://www.reddit.com/r/{sub_clean}/"

            append_entry(BASE, _log_entry(
                item_id, slug, channel, "posted",
                url=post_url, content=f"{title}\n\n{body}"
            ))
            print(f"[Reddit] SUCCESS — {post_url}")

        except Exception as e:
            append_entry(BASE, _log_entry(item_id, slug, channel, "failed", error=str(e)))
            print(f"[Reddit] FAILED — {slug} → {subreddit}: {e}")
            all_success = False

    return all_success


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--twitter-only", action="store_true")
    parser.add_argument("--reddit-only", action="store_true")
    args = parser.parse_args()

    if not QUEUE_PATH.exists():
        print(f"ERROR: distribution queue not found at {QUEUE_PATH}", file=sys.stderr)
        sys.exit(1)

    queue = json.loads(QUEUE_PATH.read_text())
    items = queue.get("items", [])

    print(f"\n{'='*80}")
    print(f"Distribution Sweep — {len(items)} products")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"{'='*80}\n")

    for item in items:
        print(f"\n--- {item.get('name', item.get('slug', '?'))[:65]} ---")

        if not args.reddit_only:
            await post_to_twitter(item, args.dry_run)

        if not args.twitter_only:
            await post_to_reddit(item, args.dry_run)

    print(f"\n{'='*80}\nSweep complete.\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
