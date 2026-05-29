---
name: reddit-posting-browseruse
description: Use when submitting text posts to Reddit via browser automation without OAuth API keys, when Reddit's bot detection blocks datacenter Playwright, or when distributing product links to niche subreddits using username/password login.
---

# Reddit Posting via browser-use

## Overview

Reddit's API OAuth flow is deprecated/rate-limited for posting; their anti-bot measures
block datacenter-originating Playwright. `browser-use` (AI agent piloting Chromium) logs
in with username/password via the web UI and submits text posts — no API keys, no OAuth,
works from any IP.

## Prerequisites

```bash
source ~/.profile   # loads ANTHROPIC_API_KEY, REDDIT_USERNAME, REDDIT_PASSWORD
pip install browser-use playwright && playwright install chromium
```

Required env vars: `ANTHROPIC_API_KEY`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`

## Core Pattern

```python
import asyncio, os, re
from browser_use import Agent, BrowserProfile
from browser_use.llm.anthropic.chat import ChatAnthropic


def _browser_profile() -> BrowserProfile:
    return BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )

def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-haiku-4-5",
        api_key=os.environ["ANTHROPIC_API_KEY"],
        max_tokens=1024,
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
    history = await agent.run(max_steps=25)
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
```

## Calling It

```python
import asyncio
from scripts.lib.distribution_log import already_posted, append_entry

def cmd_post_reddit(item_id: str, subreddit: str, title: str, body: str) -> None:
    username = os.environ["REDDIT_USERNAME"]
    password = os.environ["REDDIT_PASSWORD"]
    channel = f"reddit:{subreddit}"

    if already_posted(BASE, item_id, channel):
        print(f"SKIP — {item_id} already posted to {channel}")
        return

    post_url = asyncio.run(
        post_to_reddit(subreddit, title, body, username, password)
    )
    append_entry(BASE, {
        "item_id": item_id,
        "channel": channel,
        "status": "posted",
        "url": post_url,
        "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
    })
    print(f"POSTED — {post_url}")
```

## Task Formulation Rules

| Rule | Why |
|---|---|
| Always include `?type=self` in submit URL | Forces the text-post form; link-post form is different |
| Put body text after a newline in the task | Prevents LLM from confusing body with task instructions |
| Always say "Do NOT click Log in with Google" | Agent defaults to Google SSO if not told otherwise |
| Use `<secret>reddit_pass</secret>` reference | Keeps password out of agent logs |
| Keep title under 300 chars | Reddit hard limit |

## Quick Reference

| Concern | Solution |
|---|---|
| No OAuth API keys | browser-use uses username/password web login |
| Datacenter IP blocked | browser-use visual agent bypasses most bot checks |
| Google SSO prompt | Task explicitly says username/password only |
| Post URL not returned | Regex + keyword fallback (`"submitted"`, `"success"`) |
| Cost | `claude-haiku-4-5` ≈ $0.001–0.002 per post |
| CAPTCHA on login | Increase `max_steps` to 30; agent handles most CAPTCHAs |

## Common Mistakes

- **`subreddit` includes `r/` prefix** — strip it: `sub = subreddit.lstrip("r/").lstrip("/")`.
  The submit URL uses the bare name: `reddit.com/r/trucking/submit`.
- **Body contains curly braces** — Python f-strings break. Use `str.replace()` or pass
  body as a separate variable outside the f-string if it has `{...}` characters.
- **Forgetting idempotency check** — distribution agent runs on a schedule; without
  `already_posted()` the same item gets reposted every cycle.
- **`max_steps=25` not enough for CAPTCHAs** — If Reddit shows a CAPTCHA, bump to 35.
- **Async in sync context** — call with `asyncio.run(post_to_reddit(...))` from sync code,
  or `await post_to_reddit(...)` from an async function. Never mix both.
- **Missing `source ~/.profile`** — `ANTHROPIC_API_KEY` not set → `Agent` raises
  `RuntimeError` immediately.

## Subreddit Targeting (DataStructured)

Match the product niche to a high-signal subreddit. Examples:

| Product slug | Subreddit |
|---|---|
| fmcsa-carrier-leads | r/trucking |
| cms-hospital-directory | r/healthIT |
| dol-h1b-employer-database | r/immigration |
| nppes-dental-directory | r/Dentistry |
| irs-990-nonprofit | r/nonprofit |

Always check subreddit rules before posting. Self-promotion rules vary.
