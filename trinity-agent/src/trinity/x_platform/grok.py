"""Grok via the xAI API — live X (Twitter) search/analysis + drafting.

The grok *CLI* (the local `grok` binary, model `grok-build`) is a coding agent
and has NO X-search tool — so the old subprocess approach returned empty. The
official live-X-search path is the xAI **Agent Tools API**: POST
``/v1/responses`` with ``tools:[{type:"x_search"}]``. We authenticate with the
OAuth token grok stores at ``~/.grok/auth.json`` (the same login the CLI uses) —
no separate API key needed. ``search``/``analyze`` use ``x_search``; ``draft``
is plain generation. Public function signatures are unchanged.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

_API_URL = "https://api.x.ai/v1/responses"
_MODEL = "grok-4-fast"
_TIMEOUT = 90
_AUTH_PATH = Path.home() / ".grok" / "auth.json"


def _oauth_token() -> str | None:
    """Read the current xAI OAuth access token from grok's auth store.

    Read fresh each call so a token grok has refreshed is picked up.
    """
    try:
        data = json.loads(_AUTH_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for v in data.values():
        if isinstance(v, dict) and v.get("key"):
            return v["key"]
    return None


def _extract_text(data: dict) -> str:
    """Pull the assistant's output_text out of a /v1/responses payload."""
    texts: list[str] = []

    def walk(o: object) -> None:
        if isinstance(o, dict):
            if o.get("type") == "output_text" and isinstance(o.get("text"), str):
                texts.append(o["text"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data.get("output", data))
    return "\n".join(t for t in texts if t).strip()


def _call(prompt: str, x_search: bool = True) -> str:
    """Call the xAI Responses API and return the assistant text (or an Error: string)."""
    token = _oauth_token()
    if not token:
        return "Error: no grok OAuth token found (run `grok login`)"

    body: dict = {"model": _MODEL, "input": prompt}
    if x_search:
        body["tools"] = [{"type": "x_search"}]

    req = urllib.request.Request(
        _API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        log.warning("xAI API HTTP %s: %s", e.code, detail)
        return f"Error: xAI API returned HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return f"Error: xAI API call failed: {e}"
    except Exception as e:  # pragma: no cover - defensive
        return f"Error: xAI API unexpected failure: {type(e).__name__}: {e}"

    return _extract_text(data) or "(no result)"


def search(query: str, limit: int = 10) -> str:
    """Search X for posts matching *query* via the xAI x_search tool."""
    prompt = (
        f"Search X (Twitter) for: {query}\n\n"
        f"Return up to {limit} recent, relevant posts. For each post include the "
        f"author @handle, the text, the date, and the post URL."
    )
    return _call(prompt, x_search=True)


def draft(topic: str, context: str = "", tone: str = "professional") -> str:
    """Generate a tweet draft (no X search needed)."""
    prompt = (
        f"Draft a tweet (max 280 characters) about: {topic}\n"
        f"Tone: {tone}. Make it specific with real numbers or facts — no vague "
        f"claims. No hashtags unless they add real value. Do not include links "
        f"in the tweet text."
    )
    if context:
        prompt += f"\nAdditional context: {context}"
    return _call(prompt, x_search=False)


def analyze(query: str) -> str:
    """Analyze X sentiment and engagement patterns via the xAI x_search tool."""
    prompt = (
        f"Search X (Twitter) for activity around: {query}\n\n"
        f"Cover: overall sentiment (positive/negative/neutral), engagement level, "
        f"key themes, notable accounts discussing it, and any trending angles. "
        f"Cite specific posts with @handles and URLs."
    )
    return _call(prompt, x_search=True)
