"""Grok CLI headless wrapper — search, draft, and analyze via subprocess."""
from __future__ import annotations

import logging
import shutil
import subprocess

log = logging.getLogger(__name__)

_GROK_BIN = shutil.which("grok") or "grok"
# search_x runs take ~45-70s; 60s was too tight and produced spurious timeouts.
_TIMEOUT = 120


def _run(prompt: str) -> str:
    """Run grok -p <prompt> headlessly and return stdout.

    ``--no-alt-screen`` + a /dev/null stdin are REQUIRED: grok does not
    auto-detect a non-interactive context and will otherwise start its TUI
    alt-screen/pager and hang forever (until the timeout) when run from a
    daemon/subprocess with no TTY.
    """
    try:
        result = subprocess.run(
            [_GROK_BIN, "-p", prompt, "--output-format", "plain", "--no-alt-screen"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0 and result.stderr:
            log.warning("grok stderr: %s", result.stderr[:500])
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return f"Error: grok CLI timed out after {_TIMEOUT}s"
    except FileNotFoundError:
        return "Error: grok CLI not found in PATH"


def search(query: str, limit: int = 10) -> str:
    """Search X for posts matching query via Grok's built-in search_x tool."""
    prompt = (
        f"Search X (Twitter) for: {query}\n\n"
        f"Return up to {limit} recent, relevant posts. "
        f"For each post include: author handle, text, date, and URL if available. "
        f"Use your search_x tool."
    )
    return _run(prompt)


def draft(topic: str, context: str = "", tone: str = "professional") -> str:
    """Generate a tweet draft via Grok CLI."""
    prompt = (
        f"Draft a tweet (max 280 characters) about: {topic}\n"
        f"Tone: {tone}. "
        f"Make it specific with real numbers or facts — no vague claims. "
        f"No hashtags unless they add real value. "
        f"Do not include any links in the tweet text."
    )
    if context:
        prompt += f"\nAdditional context: {context}"
    return _run(prompt)


def analyze(query: str) -> str:
    """Analyze X sentiment and engagement patterns via Grok CLI."""
    prompt = (
        f"Analyze X (Twitter) activity around: {query}\n\n"
        f"Cover: overall sentiment (positive/negative/neutral), "
        f"engagement level, key themes, notable accounts discussing it, "
        f"and any trending angles. Use your search_x tool to gather data first."
    )
    return _run(prompt)
