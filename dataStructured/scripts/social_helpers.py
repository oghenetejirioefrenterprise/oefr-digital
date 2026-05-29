#!/usr/bin/env python3
"""Social posting CLI — Reddit, X (Twitter), and LinkedIn via browser-use AI agent.

All platforms use browser-use (AI agent controlling Chromium) with username/password login.
No OAuth API keys required, no IP blocks from datacenter detection.
Credentials loaded from environment (source ~/.profile before running).

Usage:
  python scripts/social_helpers.py post-reddit \\
      --subreddit r/trucking \\
      --title "New FMCSA Carrier Leads — May 2026" \\
      --body "..." \\
      --item-id "new-fmcsa-carrier-leads-2026-05-2026-05-04"

  python scripts/social_helpers.py post-twitter \\
      --text "🚚 15,770 new FMCSA carriers registered in 2026 →..." \\
      --item-id "new-fmcsa-carrier-leads-2026-05-2026-05-04"

  python scripts/social_helpers.py post-linkedin \\
      --text "🚚 15,770 new FMCSA carrier registrations from DOT data..." \\
      --item-id "new-fmcsa-carrier-leads-2026-05-2026-05-04"

  python scripts/social_helpers.py status

Environment:
  Reddit:   REDDIT_USERNAME, REDDIT_PASSWORD
  X:        X_USERNAME, X_PASS
  LinkedIn: LINKEDIN_EMAIL, LINKEDIN_PASS
  Anthropic: ANTHROPIC_API_KEY (used by browser-use agent for Reddit)
"""
import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted, append_entry  # noqa: E402

COOKIES_DIR = BASE / "state" / "browser_cookies"
QUEUE_PATH = BASE / "state" / "distribution-queue.json"

# Tracks whether we've already attempted to source ~/.profile for missing keys,
# so the bash subprocess runs at most once per process instead of per post.
_PROFILE_SOURCED = False


def _ensure_anthropic_key() -> str:
    """Return ANTHROPIC_API_KEY, sourcing ~/.profile at most once if it's missing.

    Only the specific key needed is imported rather than the entire environment,
    avoiding pulling unexpected profile vars into the agent runtime.
    """
    global _PROFILE_SOURCED
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        return api_key
    if not _PROFILE_SOURCED:
        _PROFILE_SOURCED = True
        import subprocess
        result = subprocess.run(
            ["bash", "-c", "source ~/.profile && printf '%s' \"$ANTHROPIC_API_KEY\""],
            capture_output=True, text=True,
        )
        sourced = result.stdout.strip()
        if sourced:
            os.environ["ANTHROPIC_API_KEY"] = sourced
        api_key = sourced
    return api_key


# ── Cookie persistence ────────────────────────────────────────────────────────

def _ctx_path(platform: str) -> Path:
    return COOKIES_DIR / f"{platform}.json"


def _launch_browser(playwright, platform: str):
    """Launch headless Chromium with stored cookies for *platform* if available."""
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx_path = _ctx_path(platform)
    if ctx_path.exists():
        context = browser.new_context(storage_state=str(ctx_path))
    else:
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
    return browser, context


def _save_cookies(context, platform: str) -> None:
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(_ctx_path(platform)))


def _log_entry(
    item_id: str,
    slug: str,
    channel: str,
    status: str,
    url: str = "",
    content: str = "",
    error: str = "",
) -> dict:
    entry = {
        "item_id": item_id,
        "slug": slug,
        "channel": channel,
        "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": status,
        "url": url,
        "content": content,
    }
    if error:
        entry["error"] = error
    return entry


# ── Reddit (browser-use AI agent — username/password, no OAuth API required) ──

async def _reddit_post_browseruse(subreddit: str, title: str, body: str, username: str, password: str) -> str:
    """Submit a text post to Reddit via browser-use AI agent.

    Uses browser-use with Claude to control a real Chromium browser —
    logs in with username/password, navigates to the subreddit, and submits
    a text post. No OAuth credentials required. Works from any IP.
    """
    from browser_use import Agent, BrowserProfile
    from browser_use.llm.anthropic.chat import ChatAnthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — source ~/.profile first")

    sub = (subreddit[2:] if subreddit.startswith("r/") else subreddit).lstrip("/")
    submit_url = f"https://www.reddit.com/r/{sub}/submit?type=self"

    task = (
        f"Log into Reddit using username '{username}' and password <secret>reddit_pass</secret>.\n\n"
        f"Steps:\n"
        f"1. Go to https://www.reddit.com/login\n"
        f"2. Enter the username and password, then click Log In.\n"
        f"3. After login succeeds, navigate to: {submit_url}\n"
        f"4. In the Title field type exactly: {title}\n"
        f"5. In the body/text area type exactly:\n{body}\n\n"
        f"6. Click the Post button to submit.\n"
        f"7. After submission, return the URL of the newly created post (it will look like "
        f"https://www.reddit.com/r/{sub}/comments/...).\n\n"
        f"Important: Do NOT click 'Log in with Google'. Use the username/password form only."
    )

    browser_profile = BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )
    llm = ChatAnthropic(model="claude-haiku-4-5", api_key=api_key, max_tokens=1024)

    agent = Agent(
        task=task,
        llm=llm,
        browser_profile=browser_profile,
        sensitive_data={"reddit_pass": password},
        max_failures=3,
    )

    history = await agent.run(max_steps=25)
    result = history.final_result()

    if not result:
        raise RuntimeError("browser-use agent returned no result — post may have failed")

    # Extract URL from result text
    import re
    url_match = re.search(r"https://www\.reddit\.com/r/[^\s\"']+/comments/[^\s\"']+", str(result))
    if url_match:
        return url_match.group(0).rstrip(")")
    # Fallback: if the agent confirmed success but gave no URL, return the subreddit link
    if any(word in str(result).lower() for word in ["posted", "submitted", "success", "created"]):
        return f"https://www.reddit.com/r/{sub}/"
    raise RuntimeError(f"browser-use agent could not confirm submission. Result: {result}")


def cmd_post_reddit(args) -> None:
    username = os.environ.get("REDDIT_USERNAME", "")
    password = os.environ.get("REDDIT_PASSWORD", "")

    if not username or not password:
        sys.exit("REDDIT_USERNAME / REDDIT_PASSWORD not set — source ~/.profile first")

    channel = f"reddit:{args.subreddit}"
    slug = args.slug or args.item_id

    if already_posted(BASE, args.item_id, channel):
        print(f"SKIP — {args.item_id} already posted to {channel}")
        return

    try:
        post_url = asyncio.run(
            _reddit_post_browseruse(args.subreddit, args.title, args.body, username, password)
        )
        append_entry(BASE, _log_entry(
            item_id=args.item_id,
            slug=slug,
            channel=channel,
            status="posted",
            url=post_url,
            content=f"{args.title}\n\n{args.body}",
        ))
        print(f"POSTED — {post_url}")
    except Exception as exc:
        append_entry(BASE, _log_entry(
            item_id=args.item_id,
            slug=slug,
            channel=channel,
            status="failed",
            error=str(exc),
        ))
        print(f"FAILED — {exc}", file=sys.stderr)
        sys.exit(1)


# ── X (Twitter) — browser-use AI agent ──────────────────────────────────────
# Raw Playwright fails: X detects headless Chrome and redirects to a wall before
# /home loads, causing tweetTextarea_0 timeout. browser-use pilots Chromium with
# an LLM (vision + DOM), handles bot-check interstitials, and manages React inputs
# without needing fiber injection.

def _x_browser_profile() -> "BrowserProfile":
    from browser_use import BrowserProfile
    ctx_path = _ctx_path("twitter")
    return BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        storage_state=str(ctx_path) if ctx_path.exists() else None,
    )


def _browseruse_llm():
    from browser_use.llm.anthropic.chat import ChatAnthropic
    api_key = _ensure_anthropic_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — source ~/.profile first")
    # Use claude-haiku-4-5: fast, ~$0.001/post, covered by $200/mo Anthropic plan
    return ChatAnthropic(model="claude-haiku-4-5", api_key=api_key, max_tokens=1024)


async def _x_post_browseruse(
    hook: str, link: str, username: str, password: str
) -> str:
    """Post hook tweet then reply with link. Returns hook tweet URL.

    Strategy: post the hook first, then reply with the Stripe/Gumroad link.
    External links in the main tweet suppress X algorithmic reach.
    A reply carries the link without the penalty.
    """
    from browser_use import Agent

    # Verification-step handle: env-driven (X_HANDLE), defaulting to the login username.
    handle = os.environ.get("X_HANDLE") or username

    steps = (
        f"Log in to X (Twitter) at https://x.com/i/flow/login\n"
        f"  Email/username: {username}\n"
        f"  Password: <secret>x_pass</secret>\n"
        f"  Use the username/password form ONLY — do NOT click 'Sign in with Google'.\n"
        f"  IMPORTANT: After entering the email, X may show a 'Verify your identity' or\n"
        f"  'Enter your phone or username' step. If it does, enter the handle: {handle}\n"
        f"  Then enter the password and click Log in.\n"
        f"  Wait for https://x.com/home to load fully.\n\n"
        f"Step 1 — Post the hook tweet:\n"
        f"  Click the compose box ('What is happening?!').\n"
        f"  Type exactly (do not truncate):\n{hook}\n"
        f"  Click the Post button. Wait for the tweet to appear.\n\n"
    )
    if link:
        steps += (
            f"Step 2 — Reply with the link:\n"
            f"  Navigate to the hook tweet's permalink.\n"
            f"  Click Reply.\n"
            f"  Type: {link}\n"
            f"  Click Reply/Post.\n\n"
        )
    steps += "Return the permalink URL of the hook tweet (https://x.com/{username}/status/...)."

    agent = Agent(
        task=steps,
        llm=_browseruse_llm(),
        browser_profile=_x_browser_profile(),
        sensitive_data={"x_pass": password},
        max_failures=3,
    )
    history = await agent.run(max_steps=40)
    result = str(history.final_result() or "")

    # Persist session for next run
    try:
        session = getattr(agent, "browser_session", None)
        if session and hasattr(session, "context"):
            COOKIES_DIR.mkdir(parents=True, exist_ok=True)
            await session.context.storage_state(path=str(_ctx_path("twitter")))
    except Exception:
        pass

    url_match = re.search(r"https://x\.com/\S+/status/\d+", result)
    if url_match:
        return url_match.group(0)
    # No tweet permalink captured — agent failed to post (bot-block, login wall, etc.)
    # Raise so the caller logs this as "failed" not "posted".
    raise RuntimeError(
        f"browser-use agent returned no tweet permalink — post likely failed. "
        f"Agent result: {result[:200] or '(empty)'}"
    )


def cmd_post_twitter(args) -> None:
    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")
    if not username or not password:
        sys.exit("X_USERNAME / X_PASS not set — source ~/.profile first")

    channel = "twitter"
    slug = args.slug or args.item_id

    if already_posted(BASE, args.item_id, channel):
        print(f"SKIP — {args.item_id} already posted to {channel}")
        return

    # Separate hook text from link.
    # Links go in a reply (not the main tweet) to preserve algorithmic reach.
    link: str = getattr(args, "link", None) or ""
    main_text: str = args.text

    if not link:
        url_match = re.search(r"(https?://\S+)\s*$", args.text.strip())
        if url_match:
            link = url_match.group(1)
            main_text = args.text[: url_match.start()].rstrip()

    if len(main_text) > 280:
        main_text = main_text[:277] + "..."

    try:
        post_url = asyncio.run(_x_post_browseruse(main_text, link, username, password))
        append_entry(BASE, _log_entry(
            item_id=args.item_id,
            slug=slug,
            channel=channel,
            status="posted",
            url=post_url,
            content=f"{main_text}\n\nREPLY: {link}" if link else main_text,
        ))
        print(f"POSTED — {post_url}")
    except Exception as exc:
        append_entry(BASE, _log_entry(
            item_id=args.item_id,
            slug=slug,
            channel=channel,
            status="failed",
            error=str(exc),
        ))
        print(f"FAILED — {exc}", file=sys.stderr)
        sys.exit(1)


# ── LinkedIn ──────────────────────────────────────────────────────────────────

def _linkedin_is_logged_in(page: Page) -> bool:
    """Check if LinkedIn has an active session."""
    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
    return "/feed" in page.url and "login" not in page.url


def _linkedin_login(page: Page, email: str, password: str) -> None:
    """Log in to LinkedIn via the standard credential flow."""
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("input[name='session_key']", timeout=15000)
    page.fill("input[name='session_key']", email)
    page.fill("input[name='session_password']", password)
    page.click("button[type='submit']")
    page.wait_for_url("**/feed/**", timeout=25000)


def _linkedin_post(page: Page, text: str) -> str:
    """Compose and publish a LinkedIn post. Returns 'https://www.linkedin.com'."""
    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
    page.evaluate("window.scrollTo(0, 0)")
    import time as _time
    _time.sleep(1)

    # Click the "Start a post" trigger — LinkedIn 2025+ uses a <p> element
    trigger = page.locator(
        "p:has-text('Start a post'), "
        "button.share-box-feed-entry__trigger-text, "
        "[data-control-name='share.post'], "
        "[aria-label*='Start a post'], "
        "button:has-text('Start a post')"
    ).first
    trigger.wait_for(timeout=10000)
    trigger.click()

    # Wait for the compose dialog to open
    editor = page.locator("[role='dialog'] [contenteditable='true'], [role='dialog'] [role='textbox']").first
    editor.wait_for(timeout=10000)
    editor.click()
    page.keyboard.type(text, delay=20)

    # Click the Post button inside the dialog
    post_btn = page.locator(
        "[role='dialog'] button:has-text('Post'), "
        "button.share-actions__primary-action, "
        "button[aria-label='Post']"
    ).first
    post_btn.wait_for(timeout=8000)
    post_btn.click()

    # Wait for the modal to close — post has been submitted
    page.wait_for_function(
        "() => !document.querySelector('[role=\"dialog\"]')",
        timeout=20000,
    )
    return "https://www.linkedin.com"


def cmd_post_linkedin(args) -> None:
    email = os.environ.get("LINKEDIN_EMAIL", "")
    password = os.environ.get("LINKEDIN_PASS", "")
    if not email or not password:
        sys.exit("LINKEDIN_EMAIL / LINKEDIN_PASS not set — source ~/.profile first")

    channel = "linkedin"
    slug = args.slug or args.item_id

    if already_posted(BASE, args.item_id, channel):
        print(f"SKIP — {args.item_id} already posted to {channel}")
        return

    if len(args.text) > 3000:
        sys.exit(f"LinkedIn post too long: {len(args.text)} chars (max 3000)")

    with sync_playwright() as pw:
        browser, context = _launch_browser(pw, "linkedin")
        page = context.new_page()
        try:
            if not _linkedin_is_logged_in(page):
                print("LinkedIn: no active session — logging in...")
                _linkedin_login(page, email, password)
                _save_cookies(context, "linkedin")
                print("LinkedIn: login OK, cookies saved")

            post_url = _linkedin_post(page, args.text)
            append_entry(BASE, _log_entry(
                item_id=args.item_id,
                slug=slug,
                channel=channel,
                status="posted",
                url=post_url,
                content=args.text,
            ))
            print(f"POSTED — {post_url}")

        except Exception as exc:
            append_entry(BASE, _log_entry(
                item_id=args.item_id,
                slug=slug,
                channel=channel,
                status="failed",
                error=str(exc),
            ))
            print(f"FAILED — {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            browser.close()


# ── Status ────────────────────────────────────────────────────────────────────

def cmd_status(args) -> None:
    """Print a summary of queue items vs. posted channels."""
    if not QUEUE_PATH.exists():
        print("state/distribution-queue.json not found")
        return

    queue = json.loads(QUEUE_PATH.read_text())
    log_path = BASE / "state" / "distribution-log.json"
    log_entries = []
    if log_path.exists():
        log_entries = json.loads(log_path.read_text()).get("entries", [])

    posted_set = {
        (e["item_id"], e["channel"])
        for e in log_entries
        if e["status"] == "posted"
    }

    seen_ids: set[str] = set()
    rows = []
    for item in queue.get("items", []):
        if item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        channels = ["twitter", "linkedin", "reddit:r/Entrepreneur"]
        for ch in channels:
            status = "✓ posted" if (item["id"], ch) in posted_set else "○ pending"
            rows.append((item["name"][:55], ch, status))

    print(f"\n{'Product':<57} {'Channel':<28} Status")
    print("─" * 95)
    for name, ch, status in rows:
        print(f"{name:<57} {ch:<28} {status}")
    print()

    pending = sum(1 for _, _, s in rows if s == "○ pending")
    posted = sum(1 for _, _, s in rows if s == "✓ posted")
    print(f"  {posted} posted  |  {pending} pending")


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="DataStructured social posting CLI (Reddit browseruse + X + LinkedIn)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")

    r = sub.add_parser("post-reddit", help="Post a text submission to a subreddit (via browser-use AI agent)")
    r.add_argument("--subreddit", required=True, help="e.g. r/trucking or trucking")
    r.add_argument("--title", required=True, help="Post title (max ~300 chars)")
    r.add_argument("--body", required=True, help="Post body (plain text)")
    r.add_argument("--item-id", required=True, dest="item_id", help="Queue item ID for dedup tracking")
    r.add_argument("--slug", default="", help="Slug override (defaults to item-id)")

    t = sub.add_parser("post-twitter", help="Post a tweet to X (link goes in reply for full reach)")
    t.add_argument("--text", required=True, help="Hook tweet text (no link — max 280 chars). Any trailing URL is auto-extracted and posted as a reply.")
    t.add_argument("--link", default="", help="Optional: Stripe/Gumroad URL to post as a reply. Auto-extracted from --text if omitted.")
    t.add_argument("--item-id", required=True, dest="item_id", help="Queue item ID for dedup tracking")
    t.add_argument("--slug", default="", help="Slug override (defaults to item-id)")

    li = sub.add_parser("post-linkedin", help="Post to LinkedIn feed")
    li.add_argument("--text", required=True, help="Post text (max 3000 chars)")
    li.add_argument("--item-id", required=True, dest="item_id", help="Queue item ID for dedup tracking")
    li.add_argument("--slug", default="", help="Slug override (defaults to item-id)")

    sub.add_parser("status", help="Show queue vs. posting status")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.cmd == "post-reddit":
        cmd_post_reddit(args)
    elif args.cmd == "post-twitter":
        cmd_post_twitter(args)
    elif args.cmd == "post-linkedin":
        cmd_post_linkedin(args)
    elif args.cmd == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
