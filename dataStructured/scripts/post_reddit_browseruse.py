#!/usr/bin/env python3
"""Post to Reddit using browser-use AI agent — handles bot detection."""
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


def _browser_profile() -> BrowserProfile:
    return BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
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


async def post_to_reddit(
    subreddit: str,
    title: str,
    body: str,
    username: str,
    password: str,
) -> str:
    """Submit a text post to a subreddit. Returns the post URL."""
    sub = subreddit.lstrip("r/").lstrip("/")
    submit_url = f"https://www.reddit.com/r/{sub}/submit?type=self"

    task = (
        f"Log into Reddit using username '{username}' "
        f"and password <secret>reddit_pass</secret>.\n\n"
        f"Steps:\n"
        f"1. Go to https://www.reddit.com/login\n"
        f"2. Enter the username and password, then click Log In.\n"
        f"3. After login succeeds, navigate to: {submit_url}\n"
        f"4. In the Title field type exactly: {title}\n"
        f"5. In the body/text area type exactly:\n{body}\n\n"
        f"6. Click the Post button to submit.\n"
        f"7. After submission, return the URL of the newly created post "
        f"(looks like https://www.reddit.com/r/{sub}/comments/...).\n\n"
        f"IMPORTANT: Do NOT click 'Log in with Google'. "
        f"Use the username/password form only."
    )

    agent = Agent(
        task=task,
        llm=_llm(),
        browser_profile=_browser_profile(),
        sensitive_data={"reddit_pass": password},
        max_failures=3,
    )
    history = await agent.run(max_steps=30)
    result = str(history.final_result() or "")

    # Extract post URL
    url_match = re.search(
        r"https://www\.reddit\.com/r/[^\s\"']+/comments/[^\s\"']+",
        result,
    )
    if url_match:
        return url_match.group(0).rstrip(")")

    # Fallback: agent confirmed success but gave no URL
    if any(w in result.lower() for w in ["posted", "submitted", "success", "created"]):
        return f"https://www.reddit.com/r/{sub}/"

    raise RuntimeError(f"Agent could not confirm submission. Result: {result}")


def generate_reddit_content(product: dict, subreddit: str) -> tuple[str, str]:
    """Generate title and body for Reddit post based on product and subreddit."""
    name = product["name"]
    price = product["price_usd"]
    link = product["stripe_payment_link_url"]
    audience = product.get("audience", "")

    # Subreddit-specific formatting
    sub = subreddit.lower()

    if "truckers" in sub or "freight" in sub:
        title = "New FMCSA Carrier Database — May 2026 — 15,770 Records"
        body = (
            "For anyone in trucking insurance, ELD sales, factoring, or dispatch:\n\n"
            "15,770 new FMCSA carriers registered in May 2026, pulled from DOT public records. "
            "Each record includes DOT #, MC #, carrier name, address, phone, and operating authority dates.\n\n"
            "These companies just got their authority — they need everything: insurance, ELD devices, "
            "factoring, tires, dispatch services. Most sales teams haven't touched this list yet.\n\n"
            f"CSV download, ${price} one-time.\n\n"
            f"{link}"
        )
    elif "realestate" in sub:
        title = "Florida Licensed Real Estate Agent Database — 2026 — 319,247 Records"
        body = (
            "For PropTech SDRs, mortgage lenders, E&O insurance brokers, and CE providers:\n\n"
            "319,247 active Florida licensed real estate agents and brokers from DBPR public records. "
            "Includes license number, name, license class, address, county, phone, and license dates.\n\n"
            "Targeting agents directly? This is the complete state roster, updated 2026. "
            "99.9% have phone numbers on file.\n\n"
            f"CSV download, ${price} one-time.\n\n"
            f"{link}"
        )
    elif "smallbusiness" in sub or "entrepreneur" in sub:
        if "Florida" in name and ("LLC" in name or "Corp" in name):
            title = "New Florida LLCs & Corps — May 2026 — 15,997 Records"
            body = (
                "For anyone prospecting new businesses (insurance, bookkeeping, web design, banking, payroll):\n\n"
                "15,997 new Florida LLCs and corporations filed in May 2026, sourced from state records. "
                "Each record includes entity name, filing date, principal address, registered agent, and entity type.\n\n"
                "These businesses are on the public record before most salespeople know they exist. "
                "They need everything: bank accounts, insurance, bookkeepers, websites, payroll processors.\n\n"
                f"CSV download, ${price} one-time.\n\n"
                f"{link}"
            )
        else:
            # Generic small business angle
            title = f"{name[:250]}"
            body = (
                f"Public data, curated for prospecting.\n\n"
                f"Target: {audience}\n\n"
                f"CSV download, ${price} one-time.\n\n"
                f"{link}"
            )
    else:
        # Generic fallback
        title = name[:300]
        body = (
            f"Public data, curated and packaged for immediate prospecting.\n\n"
            f"Who uses this: {audience}\n\n"
            f"CSV download, ${price} one-time.\n\n"
            f"{link}"
        )

    # Reddit title limit is 300 chars
    if len(title) > 300:
        title = title[:297] + "..."

    return title, body


def main():
    if len(sys.argv) < 3:
        print("Usage: python post_reddit_browseruse.py <item_id> <subreddit>")
        print("Example: python post_reddit_browseruse.py new-fmcsa-carrier-leads-2026-05-2026-05-04 r/Truckers")
        sys.exit(1)

    item_id = sys.argv[1]
    subreddit = sys.argv[2]

    # Load product from queue
    queue_path = BASE / "state" / "distribution-queue.json"
    queue = json.loads(queue_path.read_text())
    product = next((p for p in queue["items"] if p["id"] == item_id), None)

    if not product:
        print(f"ERROR: Product {item_id} not found in queue")
        sys.exit(1)

    # Check if already posted
    channel = f"reddit:{subreddit}"
    if already_posted(BASE, item_id, channel):
        print(f"SKIP — {item_id} already posted to {channel}")
        return

    # Get credentials
    username = os.environ.get("REDDIT_USERNAME", "")
    password = os.environ.get("REDDIT_PASSWORD", "")
    if not username or not password:
        # Try auto-sourcing ~/.profile
        import subprocess
        result = subprocess.run(
            ["bash", "-c", "source ~/.profile && env"],
            capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if "=" in line:
                k, _, v = line.partition("=")
                if "REDDIT" in k:
                    os.environ.setdefault(k, v)
        username = os.environ.get("REDDIT_USERNAME", "")
        password = os.environ.get("REDDIT_PASSWORD", "")

    if not username or not password:
        print("ERROR: REDDIT_USERNAME / REDDIT_PASSWORD not set — source ~/.profile first")
        sys.exit(1)

    # Generate content
    title, body = generate_reddit_content(product, subreddit)
    slug = product["slug"]

    print(f"\n📤 Posting to Reddit {subreddit}: {product['name'][:60]}...")
    print(f"Title: {title[:100]}...")
    print(f"Body: {body[:150]}...\n")

    try:
        post_url = asyncio.run(
            post_to_reddit(subreddit, title, body, username, password)
        )

        entry = {
            "item_id": item_id,
            "slug": slug,
            "channel": channel,
            "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "status": "posted",
            "url": post_url,
            "content": f"{title}\n\n{body}",
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
            "content": title,
            "error": str(exc),
        }
        append_entry(BASE, entry)
        print(f"✗ FAILED — {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
