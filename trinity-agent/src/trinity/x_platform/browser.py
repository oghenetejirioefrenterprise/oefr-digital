"""browser-use X automation — post, reply, thread via headless Chromium + NIM Omni."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from browser_use import Agent, BrowserProfile

from trinity.x_platform.nim_llm import create_nim_llm

log = logging.getLogger(__name__)

_MAX_FAILURES = 3
_MAX_STEPS = 40
_BROWSER_ARGS = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
_X_HANDLE = "eustaceorukpe"


def _cookies_path(trinity_dir: Path) -> Path:
    return trinity_dir / "state" / "browser_cookies" / "twitter.json"


def _browser_profile(trinity_dir: Path) -> BrowserProfile:
    cp = _cookies_path(trinity_dir)
    return BrowserProfile(
        headless=True,
        args=_BROWSER_ARGS,
        storage_state=str(cp) if cp.exists() else None,
    )


def _creds() -> tuple[str, str]:
    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")
    if not username or not password:
        raise RuntimeError("X_USERNAME / X_PASS not set — source ~/.profile first")
    return username, password


def _login_preamble(username: str) -> str:
    return (
        f"Log in to X (Twitter) at https://x.com/i/flow/login\n"
        f"  Email/username: {username}\n"
        f"  Password: <secret>x_pass</secret>\n"
        f"  Use the username/password form ONLY — do NOT click 'Sign in with Google'.\n"
        f"  IMPORTANT: After entering the email, X may show a 'Verify your identity' or\n"
        f"  'Enter your phone or username' step. If it does, enter the handle: {_X_HANDLE}\n"
        f"  Then enter the password and click Log in.\n"
        f"  Wait for https://x.com/home to load fully.\n\n"
    )


async def _save_cookies(agent: Agent, trinity_dir: Path) -> None:
    try:
        session = getattr(agent, "browser_session", None)
        if session and hasattr(session, "context"):
            cp = _cookies_path(trinity_dir)
            cp.parent.mkdir(parents=True, exist_ok=True)
            await session.context.storage_state(path=str(cp))
    except Exception:
        log.debug("cookie save failed", exc_info=True)


def _extract_permalink(result: str) -> str:
    match = re.search(r"https://x\.com/\S+/status/\d+", result)
    if match:
        return match.group(0)
    raise RuntimeError(
        f"browser-use agent returned no tweet permalink — post likely failed. "
        f"Agent result: {result[:200] or '(empty)'}"
    )


async def post_tweet(
    trinity_dir: Path,
    text: str,
    reply_link: str = "",
    username: str = "",
    password: str = "",
) -> str:
    """Post a tweet, optionally reply with a link. Returns tweet permalink URL."""
    if not username or not password:
        username, password = _creds()

    if len(text) > 280:
        text = text[:277] + "..."

    task = _login_preamble(username)
    task += (
        f"Step 1 — Post the tweet:\n"
        f"  Click the compose box ('What is happening?!').\n"
        f"  Type exactly (do not truncate):\n{text}\n"
        f"  Click the Post button. Wait for the tweet to appear.\n\n"
    )
    if reply_link:
        task += (
            f"Step 2 — Reply with the link:\n"
            f"  Navigate to the tweet's permalink.\n"
            f"  Click Reply.\n"
            f"  Type: {reply_link}\n"
            f"  Click Reply/Post.\n\n"
        )
    task += f"Return the permalink URL of the tweet (https://x.com/{username}/status/...)."

    agent = Agent(
        task=task,
        llm=create_nim_llm(),
        browser_profile=_browser_profile(trinity_dir),
        sensitive_data={"x_pass": password},
        max_failures=_MAX_FAILURES,
    )
    history = await agent.run(max_steps=_MAX_STEPS)
    await _save_cookies(agent, trinity_dir)

    result = str(history.final_result() or "")
    return _extract_permalink(result)


async def reply_to_tweet(
    trinity_dir: Path,
    tweet_url: str,
    text: str,
    username: str = "",
    password: str = "",
) -> str:
    """Reply to an existing tweet. Returns the reply permalink URL."""
    if not username or not password:
        username, password = _creds()

    task = _login_preamble(username)
    task += (
        f"Navigate to: {tweet_url}\n"
        f"Click Reply.\n"
        f"Type exactly:\n{text}\n"
        f"Click Reply/Post.\n\n"
        f"Return the permalink URL of the reply."
    )

    agent = Agent(
        task=task,
        llm=create_nim_llm(),
        browser_profile=_browser_profile(trinity_dir),
        sensitive_data={"x_pass": password},
        max_failures=_MAX_FAILURES,
    )
    history = await agent.run(max_steps=_MAX_STEPS)
    await _save_cookies(agent, trinity_dir)

    result = str(history.final_result() or "")
    return _extract_permalink(result)


async def post_thread(
    trinity_dir: Path,
    tweets: list[str],
    username: str = "",
    password: str = "",
) -> str:
    """Post a multi-tweet thread. Returns the first tweet's permalink URL."""
    if not tweets:
        raise ValueError("tweets list is empty")
    if not username or not password:
        username, password = _creds()

    truncated = [t[:277] + "..." if len(t) > 280 else t for t in tweets]

    steps = _login_preamble(username)
    steps += (
        f"Step 1 — Post the first tweet:\n"
        f"  Click the compose box ('What is happening?!').\n"
        f"  Type exactly:\n{truncated[0]}\n"
        f"  Click the Post button. Wait for the tweet to appear.\n\n"
    )
    for i, tweet in enumerate(truncated[1:], start=2):
        steps += (
            f"Step {i} — Reply to continue the thread:\n"
            f"  Navigate to the previous tweet's permalink.\n"
            f"  Click Reply.\n"
            f"  Type exactly:\n{tweet}\n"
            f"  Click Reply/Post.\n\n"
        )
    steps += "Return the permalink URL of the FIRST tweet."

    agent = Agent(
        task=steps,
        llm=create_nim_llm(),
        browser_profile=_browser_profile(trinity_dir),
        sensitive_data={"x_pass": password},
        max_failures=_MAX_FAILURES,
    )
    history = await agent.run(max_steps=_MAX_STEPS * len(truncated))
    await _save_cookies(agent, trinity_dir)

    result = str(history.final_result() or "")
    return _extract_permalink(result)
