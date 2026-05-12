"""Parent Router — classifies intent and dispatches to the right sub-agent.

Two-stage classification:
  Stage 1: Local pattern matching (instant, no API call)
  Stage 2: Haiku classification (1-2s, for ambiguous messages)
"""
from __future__ import annotations

import logging
import re

from trinity.providers.base import Message, Provider

log = logging.getLogger(__name__)


# ── Classification results ───────────────────────────────────────

TRACK_CONVERSATION = "conversation"
TRACK_ACTION = "action"
TRACK_MEMORY = "memory"
FAST_PATH_FEEDBACK = "feedback"
FAST_PATH_WIKI = "wiki"
FAST_PATH_STATUS = "status"
FAST_PATH_COMPRESS = "compress"
FAST_PATH_MEMORY_FLAG = "memory_flag"
FAST_PATH_COMMITMENTS = "commitments_list"
FAST_PATH_COMMITMENT_DONE = "commitment_done"
FAST_PATH_COMMITMENT_SNOOZE = "commitment_snooze"


# ── Stage 1: Pattern matching ────────────────────────────────────

# Feedback commands (handled locally, no LLM)
_FEEDBACK_PATTERNS = re.compile(
    r"^(fp|false\s*positive|wontfix|won'?t\s*fix|fixed|ack)$",
    re.IGNORECASE,
)

# Wiki queries
_WIKI_PATTERNS = re.compile(
    r"^(wiki|kb)\s+.+|^briefing$",
    re.IGNORECASE,
)

# Status queries
_STATUS_PATTERNS = re.compile(
    r"^status$|^what are you (doing|working on)",
    re.IGNORECASE,
)

# Action keywords — these strongly suggest the user wants something DONE
_ACTION_STARTS = re.compile(
    r"^(build|deploy|fix|ship|push|audit|create|run|install|update|migrate|"
    r"refactor|delete|remove|add|implement|write|edit|commit|check|test|"
    r"publish|launch|release|setup|configure)\b",
    re.IGNORECASE,
)

# Memory keywords (natural-language remember/forget)
_MEMORY_PATTERNS = re.compile(
    r"^remember\b|^forget\b|^don'?t forget\b",
    re.IGNORECASE,
)

# Context compression keyword: /compress, compress, /compact, compact
_COMPRESS_PATTERNS = re.compile(
    r"^/?(compress|compact)\b.*$",
    re.IGNORECASE,
)

# Memory share toggle: /memory, /memory local, /memory global
_MEMORY_FLAG_PATTERNS = re.compile(
    r"^/memory(?:\s+(local|global))?\s*$",
    re.IGNORECASE,
)

# Commitments
_COMMITMENTS_LIST = re.compile(r"^/commitments\s*$", re.IGNORECASE)
_COMMITMENT_DONE = re.compile(r"^/done\s+(cmt_[a-z0-9]+)\s*$", re.IGNORECASE)
_COMMITMENT_SNOOZE = re.compile(
    r"^/snooze\s+(cmt_[a-z0-9]+)\s+(\d+)\s*([smhd])?\s*$",
    re.IGNORECASE,
)


def classify_local(text: str) -> str | None:
    """Stage 1: Instant local classification. Returns None if ambiguous."""
    text = text.strip()
    if not text:
        return TRACK_CONVERSATION

    if _MEMORY_FLAG_PATTERNS.match(text):
        return FAST_PATH_MEMORY_FLAG
    if _COMPRESS_PATTERNS.match(text):
        return FAST_PATH_COMPRESS
    if _COMMITMENTS_LIST.match(text):
        return FAST_PATH_COMMITMENTS
    if _COMMITMENT_DONE.match(text):
        return FAST_PATH_COMMITMENT_DONE
    if _COMMITMENT_SNOOZE.match(text):
        return FAST_PATH_COMMITMENT_SNOOZE
    if _FEEDBACK_PATTERNS.match(text):
        return FAST_PATH_FEEDBACK
    if _WIKI_PATTERNS.match(text):
        return FAST_PATH_WIKI
    if _STATUS_PATTERNS.match(text):
        return FAST_PATH_STATUS
    if _ACTION_STARTS.match(text):
        return TRACK_ACTION
    if _MEMORY_PATTERNS.match(text):
        return TRACK_MEMORY

    return None  # Ambiguous — needs LLM classification


# ── Stage 2: LLM classification ─────────────────────────────────

_CLASSIFY_PROMPT = """Classify this message from a user in a {context} chat.

Message: "{message}"

Classify as exactly ONE word:
- CONVERSATION — question, discussion, opinion, advice, greeting, chitchat
- ACTION — requires file changes, shell commands, builds, deployments, code edits
- MEMORY — user is telling you something to remember or forget

Respond with ONLY the classification word."""


def classify_llm(
    provider: Provider,
    model: str,
    text: str,
    group_context: str = "general",
) -> str:
    """Stage 2: Use a fast LLM (Haiku) to classify ambiguous messages."""
    try:
        response = provider.chat(
            model=model,
            system="You are a message classifier. Respond with exactly one word.",
            messages=[Message(
                role="user",
                content=_CLASSIFY_PROMPT.format(
                    context=group_context,
                    message=text[:500],
                ),
            )],
            max_tokens=10,
        )
        result = response.text.strip().upper()
        if result == "ACTION":
            return TRACK_ACTION
        if result == "MEMORY":
            return TRACK_MEMORY
        return TRACK_CONVERSATION
    except Exception as e:
        log.warning("LLM classification failed: %s — defaulting to conversation", e)
        return TRACK_CONVERSATION


# ── Combined router ──────────────────────────────────────────────

def classify(
    text: str,
    provider: Provider | None = None,
    router_model: str = "claude-haiku-4-5-20251001",
    group_context: str = "general",
) -> str:
    """Classify a message. Returns one of the TRACK_* or FAST_PATH_* constants."""
    # Stage 1: instant local match
    result = classify_local(text)
    if result is not None:
        return result

    # Stage 2: LLM classification (if provider available)
    if provider:
        return classify_llm(provider, router_model, text, group_context)

    # Fallback: conversation (safe default)
    return TRACK_CONVERSATION
