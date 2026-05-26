"""X platform Trinity tool specs + handlers — registered with the tool registry."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from trinity.x_platform import grok

log = logging.getLogger(__name__)

_trinity_dir: Path | None = None


def set_trinity_dir(path: Path) -> None:
    global _trinity_dir
    _trinity_dir = path


def _ensure_dir() -> Path:
    if _trinity_dir is None:
        raise RuntimeError("x_platform tools used before set_trinity_dir() was called")
    return _trinity_dir


# ── Read tools (Grok CLI) ───────────────────────────────────────────


X_SEARCH_SCHEMA: dict[str, Any] = {
    "name": "x_search",
    "description": (
        "Search X (Twitter) for posts, hashtags, users, or trends. "
        "Returns recent relevant posts with author, text, date, and URL."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "limit": {
                "type": "integer",
                "description": "Max results to return. Default 10.",
            },
        },
        "required": ["query"],
    },
}


def x_search_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    return grok.search(inp["query"], limit=int(inp.get("limit") or 10))


X_DRAFT_SCHEMA: dict[str, Any] = {
    "name": "x_draft",
    "description": (
        "Generate a tweet or thread draft using AI. Returns text ready to post. "
        "Does not post — use x_post or x_thread to publish."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "What the tweet is about."},
            "context": {
                "type": "string",
                "description": "Additional context (product details, audience, etc.).",
            },
            "tone": {
                "type": "string",
                "description": "Tone: professional, casual, urgent. Default professional.",
            },
        },
        "required": ["topic"],
    },
}


def x_draft_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    return grok.draft(
        inp["topic"],
        context=inp.get("context", ""),
        tone=inp.get("tone", "professional"),
    )


X_ANALYZE_SCHEMA: dict[str, Any] = {
    "name": "x_analyze",
    "description": (
        "Analyze X (Twitter) sentiment and engagement patterns around a topic. "
        "Returns sentiment, themes, notable accounts, trending angles."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Topic or keyword to analyze."},
        },
        "required": ["query"],
    },
}


def x_analyze_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    return grok.analyze(inp["query"])


# ── Write tools (browser-use) ───────────────────────────────────────


X_POST_SCHEMA: dict[str, Any] = {
    "name": "x_post",
    "description": (
        "Post a tweet to X (Twitter) via browser automation. "
        "Optionally include a reply_link which will be posted as a reply "
        "(links in replies preserve algorithmic reach)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Tweet text (max 280 chars, auto-truncated).",
            },
            "reply_link": {
                "type": "string",
                "description": "Optional URL to post as a reply to the main tweet.",
            },
        },
        "required": ["text"],
    },
}


def x_post_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    from trinity.x_platform.browser import post_tweet
    try:
        url = asyncio.run(post_tweet(
            _ensure_dir(),
            text=inp["text"],
            reply_link=inp.get("reply_link", ""),
        ))
        return f"Posted: {url}"
    except Exception as e:
        return f"Error posting tweet: {e}"


X_REPLY_SCHEMA: dict[str, Any] = {
    "name": "x_reply",
    "description": "Reply to an existing tweet on X (Twitter) via browser automation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tweet_url": {
                "type": "string",
                "description": "URL of the tweet to reply to.",
            },
            "text": {
                "type": "string",
                "description": "Reply text (max 280 chars).",
            },
        },
        "required": ["tweet_url", "text"],
    },
}


def x_reply_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    from trinity.x_platform.browser import reply_to_tweet
    try:
        url = asyncio.run(reply_to_tweet(
            _ensure_dir(),
            tweet_url=inp["tweet_url"],
            text=inp["text"],
        ))
        return f"Replied: {url}"
    except Exception as e:
        return f"Error replying: {e}"


X_THREAD_SCHEMA: dict[str, Any] = {
    "name": "x_thread",
    "description": (
        "Post a multi-tweet thread on X (Twitter) via browser automation. "
        "Each item in tweets becomes one tweet in the thread."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tweets": {
                "type": "string",
                "description": "JSON-encoded array of tweet texts.",
            },
        },
        "required": ["tweets"],
    },
}


def x_thread_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    from trinity.x_platform.browser import post_thread
    try:
        tweets_raw = inp["tweets"]
        tweets = json.loads(tweets_raw) if isinstance(tweets_raw, str) else tweets_raw
        if not isinstance(tweets, list) or not tweets:
            return "Error: 'tweets' must be a non-empty JSON array of strings."
        url = asyncio.run(post_thread(_ensure_dir(), tweets=tweets))
        return f"Thread posted: {url}"
    except json.JSONDecodeError:
        return "Error: 'tweets' must be valid JSON array."
    except Exception as e:
        return f"Error posting thread: {e}"


ALL_SPECS = [
    (X_SEARCH_SCHEMA, x_search_handler),
    (X_DRAFT_SCHEMA, x_draft_handler),
    (X_ANALYZE_SCHEMA, x_analyze_handler),
    (X_POST_SCHEMA, x_post_handler),
    (X_REPLY_SCHEMA, x_reply_handler),
    (X_THREAD_SCHEMA, x_thread_handler),
]
