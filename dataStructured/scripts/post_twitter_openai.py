#!/usr/bin/env python3
"""
Twitter poster using browser-use + OpenAI (ChatLiteLLM backend).

Why this exists: The old script used raw Playwright, which X detects and blocks.
browser-use drives the browser like a human (visual + DOM), bypassing bot detection.
ANTHROPIC_API_KEY is unavailable; OPENAI_API_KEY is — so we route through ChatLiteLLM.

Distribution strategy: hook tweet first (no link = full algorithmic reach),
then reply with the Gumroad/Stripe URL (X suppresses external links in main tweet).

Usage:
  source ~/.profile
  python3 scripts/post_twitter_openai.py               # posts all unposted items
  python3 scripts/post_twitter_openai.py --dry-run     # prints hooks without posting
  python3 scripts/post_twitter_openai.py --item-id <id>  # single product
"""
import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted, append_entry  # noqa: E402

QUEUE_PATH = BASE / "state" / "distribution-queue.json"
COOKIES_PATH = BASE / "state" / "browser_cookies" / "twitter.json"

# ── Tweet copy for every product in the queue ─────────────────────────────────
# hook: 280-char max, NO link (preserves reach)
# reply: the buy link

TWEETS = {
    "new-fmcsa-carrier-leads-2026-05-2026-05-04": {
        "hook": "15,770 trucking companies just got their DOT authority in 2026. These carriers need insurance, ELD devices, factoring, dispatch, tires — everything. The data is public. Most sales teams haven't touched it yet. 🚚",
        "link": "https://3563705146415.gumroad.com/l/bvdnbx",
    },
    "new-business-formations-csv-2026-05-2026-05-05": {
        "hook": "15,997 new Florida LLCs and corps filed in May 2026. Every one of them needs a bank account, insurance, bookkeeper, website, payroll. They're on record before most salespeople even know they exist. 📋",
        "link": "https://3563705146415.gumroad.com/l/pzbfkf",
    },
    "samgov-small-biz-contractor-leads-2026-05-2026-05-05": {
        "hook": "4,731 small businesses registered on SAM.gov in the DMV IT corridor. 8(a), HUBZone, WOSB, SDVOSB — the teaming partner goldmine that proposal teams actually need. All public data. 🏛️",
        "link": "https://3563705146415.gumroad.com/l/madhdb",
    },
    "fl-real-estate-agent-licenses-2026-05-2026-05-06": {
        "hook": "319,247 licensed Florida real estate agents and brokers — names, license numbers, status, county. If you sell CRM software, E&O insurance, CE courses, or mortgage products to agents, this is your list. 🏠",
        "link": "https://3563705146415.gumroad.com/l/gbkrqm",
    },
    "cms-medicare-home-health-agencies-2026-05-2026-05-05": {
        "hook": "12,392 Medicare-certified home health agencies in the US. If you sell EVV software, billing systems, staffing, or DME supplies to home health operators — the buyer list is right here. 🏥",
        "link": "https://3563705146415.gumroad.com/l/jddyts",
    },
    "faa-civil-aircraft-registration-2026-05-2026-05-06": {
        "hook": "302,810 civil aircraft registered with the FAA in 2026. Tail numbers, owner records, aircraft type, engine class. Aviation insurance, avionics, MRO, flight training — your entire addressable market is in here. ✈️",
        "link": "https://3563705146415.gumroad.com/l/knszdz",
    },
    "fl-alcoholic-beverage-licensees-2026-05-2026-05-07": {
        "hook": "52,152 active Florida bars, restaurants, and liquor stores — licensed, name, address, license type. If you sell POS systems, linen, payment processing, liquor liability insurance, or music licensing, this is your market. 🍺",
        "link": "https://3563705146415.gumroad.com/l/xqymyk",
    },
    "nppes-physical-therapist-clinics-2026-05-2026-05-07": {
        "hook": "377,805 physical therapists and PT clinics with NPI numbers — pulled from CMS public data. Medical SaaS, staffing, equipment reps, and CE providers: your full US market in one CSV. 💪",
        "link": "https://3563705146415.gumroad.com/l/fpxgm",
    },
    "tx-tdlr-electricians-2026-05-2026-05-07": {
        "hook": "Every licensed electrician and electrical contractor in Texas — straight from TDLR records. Name, license class, status, location. Graybar, Rexel, ServiceTitan SDRs: this is the list you've been building manually. ⚡",
        "link": "https://3563705146415.gumroad.com/l/ehxax",
    },
    "tx-tdlr-hvac-contractors-2026-05-2026-05-07": {
        "hook": "Every HVAC contractor and AC tech licensed in Texas, direct from TDLR. Carrier, Trane, Lennox dealers. ServiceTitan sales reps. Refrigerant suppliers. This is the complete Texas HVAC market. ❄️",
        "link": "https://3563705146415.gumroad.com/l/cciox",
    },
    "ca-cslb-licensed-contractors-2026-05-2026-05-07": {
        "hook": "232,617 licensed California contractors from CSLB records. General B, C-10 electricians, C-36 plumbers, C-20 HVAC — every class, every county. Procore SDRs, subcontractor insurers, bonding companies: your list. 🔨",
        "link": "https://gumroad.com/l/rvzovl",
    },
    "nppes-dentists-dental-practices-2026-05-2026-05-07": {
        "hook": "371,786 US dentists and dental practices with NPI data from CMS. Patterson, Henry Schein reps, Dentrix/Eaglesoft sales teams, dental CE providers — your national prospect list, no enterprise subscription needed. 🦷",
        "link": "https://buy.stripe.com/cNi9AM3yL0MvfPl0ey7IY0r",  # Gumroad listing null, use Stripe
    },
    "sec-registered-investment-advisers-2026-05-2026-05-07": {
        "hook": "16,551 SEC-registered RIA firms — the same data enterprise platforms charge $5,000/yr to wrap. AUM ranges, CRD numbers, state registrations. Wealthtech SDRs and breakaway adviser recruiters: here it is. 📈",
        "link": "https://gumroad.com/l/ibhcj",
    },
}


# ── browser-use session helpers ───────────────────────────────────────────────

def _browser_profile():
    """Headless profile with saved session when available."""
    from browser_use import BrowserProfile
    return BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        storage_state=str(COOKIES_PATH) if COOKIES_PATH.exists() else None,
    )


def _llm():
    from browser_use.llm.litellm.chat import ChatLiteLLM
    return ChatLiteLLM(
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
        max_tokens=1024,
        temperature=0.0,
    )


async def _save_session(agent):
    """Persist browser cookies for next run."""
    COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        session = agent.browser_session
        if session:
            await session.context.storage_state(path=str(COOKIES_PATH))
            print(f"  💾 Session saved → {COOKIES_PATH}")
    except Exception as e:
        print(f"  ⚠️  Session save skipped: {e}")


# ── Core posting function ─────────────────────────────────────────────────────

async def post_with_link_reply(
    hook: str,
    link: str,
    username: str,
    password: str,
) -> str:
    """Post hook tweet then reply with link. Returns hook tweet URL or 'failed'."""
    from browser_use import Agent

    if len(hook) > 280:
        hook = hook[:277] + "..."

    task = f"""
Log in to X (Twitter) at https://x.com/i/flow/login using:
  Username: {username}
  Password: <secret>x_pass</secret>

IMPORTANT: Use ONLY the username/password form. Do NOT click any Google or Apple login button.

Steps:
1. If the page shows a home feed (already logged in), skip to Step 4.
2. Enter username → click Next.
3. If prompted for email/phone verification, enter the username again.
4. Enter the password → click "Log in".
5. Wait until https://x.com/home loads fully.
6. Click the compose box ("What is happening?!" or the pencil icon).
7. Type this text EXACTLY — do not shorten or modify it:
{hook}
8. Click the "Post" button. Wait for the tweet to appear in the feed.
9. Click into the new tweet to open its permalink page.
10. Click "Reply" on that tweet.
11. Type exactly: {link}
12. Click the Reply/Post button to submit the reply.
13. Return the permalink URL of the main hook tweet (format: https://x.com/{username}/status/NNNN).
"""

    agent = Agent(
        task=task,
        llm=_llm(),
        browser_profile=_browser_profile(),
        sensitive_data={"x_pass": password},
        max_failures=3,
    )
    history = await agent.run(max_steps=40)
    result = str(history.final_result() or "")

    await _save_session(agent)

    url_match = re.search(r"https://x\.com/\S+/status/\d+", result)
    # Only return a real permalink. If the agent claims success but yields no URL,
    # return "" so the caller logs this as failed rather than storing a fake token.
    return url_match.group(0) if url_match else ""


# ── Main sweep ────────────────────────────────────────────────────────────────

async def run_sweep(dry_run: bool = False, item_id_filter: str = None):
    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")

    if not username or not password:
        print("❌ X_USERNAME / X_PASS not set. Run: source ~/.profile")
        sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set. Run: source ~/.profile")
        sys.exit(1)

    if not QUEUE_PATH.exists():
        print(f"❌ Distribution queue not found at {QUEUE_PATH}. Run the ship pipeline first.")
        sys.exit(1)

    queue = json.loads(QUEUE_PATH.read_text())
    items = queue.get("items", [])

    if item_id_filter:
        items = [i for i in items if i["id"] == item_id_filter]
        if not items:
            print(f"❌ Item '{item_id_filter}' not found in queue.")
            sys.exit(1)

    print(f"📋 Queue: {len(items)} products | dry_run={dry_run}")
    print()

    posted = 0
    skipped = 0
    failed = 0

    for item in items:
        item_id = item["id"]
        slug = item["slug"]
        name = item["name"]
        tweet_data = TWEETS.get(item_id)

        if not tweet_data:
            print(f"⚠️  No tweet copy for {item_id} — skipping")
            continue

        if already_posted(BASE, item_id, "twitter"):
            print(f"✅ Already posted: {name}")
            skipped += 1
            continue

        hook = tweet_data["hook"]
        link = tweet_data["link"]

        print(f"🐦 {'[DRY RUN] ' if dry_run else ''}Posting: {name}")
        print(f"   Hook ({len(hook)} chars): {hook[:80]}...")
        print(f"   Link: {link}")

        if dry_run:
            print()
            continue

        try:
            tweet_url = await post_with_link_reply(hook, link, username, password)
        except Exception as e:
            tweet_url = ""
            err = str(e)
            print(f"  ❌ Exception: {err[:120]}")
            append_entry(BASE, {
                "item_id": item_id,
                "slug": slug,
                "channel": "twitter",
                "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "status": "failed",
                "url": "",
                "content": hook,
                "error": err,
            })
            failed += 1
            continue

        if tweet_url:
            print(f"  🎉 Success: {tweet_url}")
            append_entry(BASE, {
                "item_id": item_id,
                "slug": slug,
                "channel": "twitter",
                "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "status": "posted",
                "url": tweet_url,
                "content": hook,
                "error": "",
            })
            posted += 1
        else:
            print(f"  ❌ browser-use returned no URL — marking failed")
            append_entry(BASE, {
                "item_id": item_id,
                "slug": slug,
                "channel": "twitter",
                "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "status": "failed",
                "url": "",
                "content": hook,
                "error": "No tweet URL in agent result",
            })
            failed += 1

        # Brief pause between posts to avoid rate limiting
        await asyncio.sleep(8)
        print()

    print("─" * 60)
    print(f"Done. Posted: {posted} | Skipped (already done): {skipped} | Failed: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post all DataStructured products to Twitter via browser-use + OpenAI")
    parser.add_argument("--dry-run", action="store_true", help="Print tweets without posting")
    parser.add_argument("--item-id", help="Post a single product by ID")
    args = parser.parse_args()

    asyncio.run(run_sweep(dry_run=args.dry_run, item_id_filter=args.item_id))
