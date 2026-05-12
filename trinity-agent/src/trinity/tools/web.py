"""Web operations — search and fetch."""
from __future__ import annotations

import requests

MAX_FETCH_BYTES = 50 * 1024  # 50 KB
FETCH_TIMEOUT = 30


def web_search(query: str) -> str:
    """Placeholder — web search is not yet implemented.

    Returns guidance to use run_command with curl instead.
    """
    return (
        "Web search not yet implemented — use run_command with curl "
        "or a search API to perform web searches."
    )


def web_fetch(url: str) -> str:
    """Fetch a URL and return the text content, capped at 50 KB.

    Uses a 30-second timeout.  Returns the response body as text.
    """
    try:
        resp = requests.get(
            url,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": "TrinityAgent/0.1"},
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return f"Fetch failed: {e}"

    text = resp.text
    if len(text.encode("utf-8")) > MAX_FETCH_BYTES:
        # Truncate to roughly MAX_FETCH_BYTES
        text = text[: MAX_FETCH_BYTES]
        return text + f"\n\n[truncated — response exceeds {MAX_FETCH_BYTES // 1024} KB]"
    return text
