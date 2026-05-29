#!/usr/bin/env python3
"""Post to X (Twitter) using browser-use AI agent — handles bot detection."""
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from browser_use import Agent, BrowserProfile

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted, append_entry
from scripts.lib.nvidia_nim_llm import create_nvidia_nim_llm

COOKIES = BASE / "state" / "browser_cookies" / "twitter.json"


def _browser_profile() -> BrowserProfile:
    """Headless profile — reuse saved session when available."""
    return BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        storage_state=str(COOKIES) if COOKIES.exists() else None,
    )


def _llm():
    """
    Nvidia NIM LLM for browser automation.

    Uses nemotron-3-nano-omni-30b-a3b-reasoning — optimized for:
    - Multimodal reasoning (page screenshots + DOM)
    - Cost efficiency (nano tier)
    - Low latency browser actions
    """
    return create_nvidia_nim_llm(
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        max_completion_tokens=2048,
        temperature=0.2,  # deterministic for consistent posting
    )


async def post_tweet_with_link_reply(
    hook: str, link: str, username: str, password: str
) -> str:
    """Post hook tweet then reply with link. Returns hook tweet URL."""
    task = f"""Log in to X (Twitter) at https://x.com/i/flow/login
  Email/username: {username}
  Password: <secret>x_pass</secret>

Use the username/password form ONLY — do NOT click 'Sign in with Google'.

IMPORTANT: After entering the email, X may show a 'Verify your identity' or
'Enter your phone or username' step. If it does, enter the handle: eustaceorukpe
Then enter the password and click Log in.

Wait for https://x.com/home to load fully.

Step 1 — Post the hook tweet:
  Click the compose box ('What is happening?!').
  Type exactly (do not truncate):
{hook}
  Click the Post button. Wait for the tweet to appear.

Step 2 — Reply with the link:
  Navigate to the hook tweet's permalink.
  Click Reply.
  Type: {link}
  Click Reply/Post.

Return the permalink URL of the hook tweet (https://x.com/{username}/status/...)."""

    agent = Agent(
        task=task,
        llm=_llm(),
        browser_profile=_browser_profile(),
        sensitive_data={"x_pass": password},
        max_failures=3,
    )
    history = await agent.run(max_steps=40)
    result = str(history.final_result() or "")

    # Persist session for next run
    COOKIES.parent.mkdir(parents=True, exist_ok=True)
    try:
        session = getattr(agent, "browser_session", None)
        if session and hasattr(session, "context"):
            await session.context.storage_state(path=str(COOKIES))
    except Exception:
        pass

    url_match = re.search(r"https://x\.com/\S+/status/\d+", result)
    if url_match:
        return url_match.group(0)
    raise RuntimeError(
        f"browser-use agent returned no tweet permalink — post likely failed. "
        f"Agent result: {result[:200] or '(empty)'}"
    )


def generate_tweet_content(product: dict) -> tuple[str, str]:
    """Generate hook tweet (no link) and link for reply."""
    name = product["name"]
    price = product["price_usd"]
    link = product["stripe_payment_link_url"]

    # Hook tweet templates based on product type
    if "FMCSA" in name or "Carrier" in name:
        hook = (
            f"🚚 15,770 trucking companies just got their DOT authority in 2026. "
            f"These carriers need insurance, ELD devices, factoring, dispatch, tires — everything. "
            f"The data is public. Most sales teams haven't touched it yet."
        )
    elif "Florida" in name and ("LLC" in name or "Corp" in name):
        hook = (
            f"📋 15,997 new Florida LLCs and corps filed in May 2026. "
            f"Every one of them needs a bank account, insurance, bookkeeper, website, payroll. "
            f"They're on record before most salespeople even know they exist."
        )
    elif "Real Estate" in name:
        hook = (
            f"🏡 319,247 FL licensed real estate agents & brokers from state records. "
            f"For proptech SDRs, mortgage lenders, E&O insurance brokers, CE providers. "
            f"99% of your competitors don't have this list."
        )
    elif "SAM.gov" in name:
        hook = (
            f"🏛️ 4,731 small-biz IT contractors registered on SAM.gov in the DMV corridor. "
            f"For teaming partners, IT staffing, SaaS vendors targeting federal contractors. "
            f"Public data, curated for immediate outreach."
        )
    elif "Home Health" in name:
        hook = (
            f"🏥 12,392 Medicare-certified home health agencies across 55 US states. "
            f"For medical SaaS (EVV, scheduling, billing), DME supply reps, staffing agencies. "
            f"Direct from CMS public records."
        )
    elif "Aircraft" in name:
        hook = (
            f"✈️ 302,810 active US-registered civil aircraft from FAA records. "
            f"For aviation insurance brokers, avionics shops, MRO facilities, parts vendors. "
            f"Includes N-number, make, model, registrant details."
        )
    elif "Alcohol" in name or "Beverage" in name:
        hook = (
            f"🍺 52,152 active Florida alcohol licensees — bars, restaurants, package stores. "
            f"For liquor distributors, POS vendors (Toast/Square), payment processors, "
            f"insurance brokers selling liquor liability."
        )
    elif "Physical Therapist" in name or "PT" in name:
        hook = (
            f"🏥 377,805 US Physical Therapists and PT clinics from CMS NPPES. "
            f"For medical SaaS vendors, medical equipment reps, staffing agencies, "
            f"liability insurance brokers. 99.98% have practice phone numbers."
        )
    elif "Electrician" in name:
        hook = (
            f"⚡ 204,535 licensed electricians in Texas — sourced from TDLR. "
            f"For electrical supply distributors (Graybar, Rexel), "
            f"SaaS vendors (ServiceTitan, Jobber), safety training providers."
        )
    elif "HVAC" in name:
        hook = (
            f"❄️ 56,001 active HVAC contractors & AC technicians in Texas. "
            f"For Carrier/Trane/Lennox dealers, ServiceTitan/FieldEdge SDRs, "
            f"refrigerant suppliers, CE providers, insurance brokers."
        )
    elif "Contractor" in name and "California" in name:
        hook = (
            f"🏗️ 232,617 active licensed contractors in California — CSLB database. "
            f"For Procore/Buildertrend SDRs, construction insurance/bonding brokers, "
            f"building material distributors, safety training providers."
        )
    elif "Dentist" in name or "Dental" in name:
        hook = (
            f"🦷 371,786 US dentists & dental practices from CMS NPPES. "
            f"For Patterson/Henry Schein reps, Dentrix/Eaglesoft SDRs, "
            f"dental labs, CE providers, insurance brokers. All specialties included."
        )
    elif "RIA" in name or "Investment Adviser" in name:
        hook = (
            f"💼 16,551 SEC-registered investment adviser firms from IAPD. "
            f"For wealthtech SaaS, asset manager BD teams, recruiters, M&A advisers. "
            f"Teams pay $5K-20K/yr for platforms wrapping this same free SEC data."
        )
    else:
        # Generic fallback
        hook = (
            f"📊 {name[:100]}... "
            f"Public data, niche-packaged for immediate prospecting. ${price} one-time."
        )

    # Truncate hook if too long
    if len(hook) > 280:
        hook = hook[:277] + "..."

    return hook, link


def main():
    if len(sys.argv) < 2:
        print("Usage: python post_twitter_browseruse.py <item_id>")
        sys.exit(1)

    item_id = sys.argv[1]

    # Load product from queue
    queue_path = BASE / "state" / "distribution-queue.json"
    queue = json.loads(queue_path.read_text())
    product = next((p for p in queue["items"] if p["id"] == item_id), None)

    if not product:
        print(f"ERROR: Product {item_id} not found in queue")
        sys.exit(1)

    # Check if already posted
    channel = "twitter"
    if already_posted(BASE, item_id, channel):
        print(f"SKIP — {item_id} already posted to {channel}")
        return

    # Get credentials
    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")
    if not username or not password:
        print("ERROR: X_USERNAME / X_PASS not set — source ~/.profile first")
        sys.exit(1)

    # Generate content
    hook, link = generate_tweet_content(product)
    slug = product["slug"]

    print(f"\n📤 Posting to Twitter: {product['name'][:60]}...")
    print(f"Hook: {hook[:100]}...")
    print(f"Link: {link}")

    try:
        post_url = asyncio.run(
            post_tweet_with_link_reply(hook, link, username, password)
        )

        entry = {
            "item_id": item_id,
            "slug": slug,
            "channel": channel,
            "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "status": "posted",
            "url": post_url,
            "content": f"{hook}\n\nREPLY: {link}",
        }
        append_entry(BASE, entry)
        print(f"✓ POSTED — {post_url}\n")

    except Exception as exc:
        entry = {
            "item_id": item_id,
            "slug": slug,
            "channel": channel,
            "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "status": "failed",
            "url": "",
            "content": hook,
            "error": str(exc),
        }
        append_entry(BASE, entry)
        print(f"✗ FAILED — {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
