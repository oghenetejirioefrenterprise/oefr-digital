---
name: x-posting-browseruse
description: Use when posting to X (Twitter) via browser automation, especially when Playwright headless detection is causing timeout failures on tweetTextarea_0, when X's React-controlled inputs reject keyboard input, or when automating tweet + link-reply strategy for social distribution.
---

# X (Twitter) Posting via browser-use

## Overview

X detects headless Chromium even on residential IPs and redirects to a wall instead of
`/home` — causing raw Playwright to timeout on `[data-testid='tweetTextarea_0']`.
`browser-use` solves this by piloting the browser with an LLM (visual + DOM), which
behaves more like a human and handles bot-check interstitials automatically.

**Distribution strategy:** post the hook tweet first, then reply with the link.
External links in the main tweet suppress algorithmic reach. A reply is ignored by
X's suppression filter.

## Prerequisites

```bash
source ~/.profile   # loads ANTHROPIC_API_KEY, X_USERNAME, X_PASS
pip install browser-use playwright && playwright install chromium
```

Required env vars: `ANTHROPIC_API_KEY`, `X_USERNAME`, `X_PASS`

## Core Pattern

```python
import asyncio, os, re
from pathlib import Path
from browser_use import Agent, BrowserProfile
from browser_use.llm.anthropic.chat import ChatAnthropic

COOKIES = Path("state/browser_cookies/twitter.json")

def _browser_profile() -> BrowserProfile:
    """Headless profile — reuse saved session when available."""
    return BrowserProfile(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        storage_state=str(COOKIES) if COOKIES.exists() else None,
    )

def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-haiku-4-5",   # cost-efficient for browser tasks
        api_key=os.environ["ANTHROPIC_API_KEY"],
        max_tokens=1024,
    )

async def post_tweet(text: str, username: str, password: str) -> str:
    """Post a single tweet. Returns tweet URL (best-effort) or 'https://x.com'."""
    task = f"""
Log in to X (Twitter) at https://x.com/i/flow/login using:
  - Username: {username}
  - Password: <secret>x_pass</secret>

Steps:
1. If already logged in, skip to step 4.
2. On the login page, enter the username, click Next.
3. If a phone/email verification step appears, enter the username again.
4. Enter the password and click Log in.
5. Wait for https://x.com/home to load.
6. Click the "What is happening?!" compose box.
7. Type exactly this text (do not truncate):
{text}
8. Click the Post button.
9. Wait for the tweet to appear in the timeline.
10. Return the URL of the tweet (https://x.com/{username}/status/...).

IMPORTANT: Use the username/password fields only. Do NOT click "Sign in with Google".
"""
    agent = Agent(
        task=task,
        llm=_llm(),
        browser_profile=_browser_profile(),
        sensitive_data={"x_pass": password},
        max_failures=3,
    )
    history = await agent.run(max_steps=30)
    result = str(history.final_result() or "")

    # Persist session for next run
    COOKIES.parent.mkdir(parents=True, exist_ok=True)
    # browser-use exposes session state via the BrowserSession after run
    try:
        session = agent.browser_session
        if session:
            await session.context.storage_state(path=str(COOKIES))
    except Exception:
        pass

    url_match = re.search(r"https://x\.com/\S+/status/\d+", result)
    return url_match.group(0) if url_match else "https://x.com"


async def post_tweet_with_link_reply(
    hook: str, link: str, username: str, password: str
) -> str:
    """Post hook tweet then reply with link. Returns hook tweet URL."""
    task = f"""
Log in to X (Twitter) using username '{username}' and password <secret>x_pass</secret>.
Use https://x.com/i/flow/login. Username/password form only — NOT Google login.

Step 1 — Post the hook tweet:
  Text: {hook}
  Click Post. Wait for the tweet to appear.

Step 2 — Post the link as a reply to the tweet you just posted:
  Navigate to the tweet permalink.
  Click Reply.
  Type: {link}
  Click Reply/Post.

Return the permalink URL of the hook tweet.
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

    url_match = re.search(r"https://x\.com/\S+/status/\d+", result)
    return url_match.group(0) if url_match else "https://x.com"
```

## Session Persistence

**One-time setup** — save a real browser session to skip headless login:
```bash
python3 scripts/save_twitter_session.py   # opens visible browser, save on close
```
`BrowserProfile(storage_state="state/browser_cookies/twitter.json")` reloads it.
If the session expires, browser-use re-logs in automatically via the task instructions.

## Tweet Length Guard

```python
if len(hook) > 280:
    hook = hook[:277] + "..."
```

Apply before calling `post_tweet`. X silently truncates; the agent may misreport success.

## Idempotency

Always check the distribution log before posting:
```python
from scripts.lib.distribution_log import already_posted, append_entry
if already_posted(BASE, item_id, "twitter"):
    return  # already done
```

## Quick Reference

| Concern | Solution |
|---|---|
| Timeout on `tweetTextarea_0` | Switch from Playwright to browser-use |
| React inputs reject `fill()` | browser-use uses vision + DOM, no fiber hack needed |
| Login interstitials / CAPTCHAs | browser-use LLM handles them visually |
| External link reach suppressed | Post link as reply, not in main tweet |
| Session expires | Task includes full login steps as fallback |
| Cost | Use `claude-haiku-4-5` — ~$0.001 per post |

## Common Mistakes

- **Using `headless=False` in production** — works locally but breaks in cron/daemon.
  Use `headless=True` + `storage_state` instead.
- **Putting link in main tweet** — X suppresses algorithmic reach. Always reply.
- **Skipping `sensitive_data`** — password appears in agent logs. Always pass via
  `sensitive_data={"x_pass": password}` and reference as `<secret>x_pass</secret>`.
- **Forgetting `source ~/.profile`** — `ANTHROPIC_API_KEY` missing → agent silently fails.
- **`max_steps` too low** — Login + compose + post = ~15 steps minimum. Set ≥ 30.
