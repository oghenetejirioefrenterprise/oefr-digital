"""Auto-extract memories from conversations using local heuristics.

No LLM call — pure regex pattern matching.  Fast and free.
"""
from __future__ import annotations

import re


# ── Pattern definitions ────────────────────────────────────────────

_CORRECTION_PATTERNS = [
    re.compile(r"\bdon'?t\b", re.IGNORECASE),
    re.compile(r"\bstop\b", re.IGNORECASE),
    re.compile(r"\bnever\b", re.IGNORECASE),
    re.compile(r"\binstead\b", re.IGNORECASE),
    re.compile(r"\bnot that\b", re.IGNORECASE),
    re.compile(r"\bwrong\b", re.IGNORECASE),
    re.compile(r"\bactually\b", re.IGNORECASE),
    re.compile(r"\bno,?\s", re.IGNORECASE),
]

_PREFERENCE_PATTERNS = [
    re.compile(r"\bI prefer\b", re.IGNORECASE),
    re.compile(r"\bI like\b", re.IGNORECASE),
    re.compile(r"\balways\b", re.IGNORECASE),
    re.compile(r"\buse \w+ for\b", re.IGNORECASE),
    re.compile(r"\bI want\b", re.IGNORECASE),
    re.compile(r"\bmake sure\b", re.IGNORECASE),
]

_FACT_PATTERNS = [
    re.compile(r"\bI am\b", re.IGNORECASE),
    re.compile(r"\bwe use\b", re.IGNORECASE),
    re.compile(r"\bour \w+ is\b", re.IGNORECASE),
    re.compile(r"\bmy \w+ is\b", re.IGNORECASE),
    re.compile(r"\bwe have\b", re.IGNORECASE),
    re.compile(r"\bthe \w+ runs on\b", re.IGNORECASE),
]


def _match_count(text: str, patterns: list[re.Pattern]) -> int:
    """Count how many patterns match in the text."""
    return sum(1 for p in patterns if p.search(text))


def _extract_relevant_sentences(text: str, patterns: list[re.Pattern]) -> list[str]:
    """Return sentences from text that match any pattern."""
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    relevant = []
    for sentence in sentences:
        if any(p.search(sentence) for p in patterns):
            cleaned = sentence.strip()
            if len(cleaned) > 10:  # skip trivially short matches
                relevant.append(cleaned)
    return relevant


def extract_memories(
    user_message: str,
    agent_response: str,
    chat_name: str,
) -> list[dict]:
    """Analyze a user/agent exchange and return memory candidates.

    Returns list of dicts:
        {"content": str, "segment": str, "importance": float, "source": chat_name}

    This is a LOCAL heuristic extraction -- no LLM call.
    """
    candidates: list[dict] = []

    # Only analyze the user message for extractable memories
    text = user_message

    # Check for corrections
    correction_hits = _match_count(text, _CORRECTION_PATTERNS)
    if correction_hits >= 1:
        sentences = _extract_relevant_sentences(text, _CORRECTION_PATTERNS)
        if sentences:
            content = "\n".join(sentences)
            importance = min(0.95, 0.7 + (correction_hits * 0.05))
            candidates.append({
                "content": content,
                "segment": "corrections",
                "importance": importance,
                "source": chat_name,
            })

    # Check for preferences
    preference_hits = _match_count(text, _PREFERENCE_PATTERNS)
    if preference_hits >= 1:
        sentences = _extract_relevant_sentences(text, _PREFERENCE_PATTERNS)
        if sentences:
            content = "\n".join(sentences)
            importance = min(0.85, 0.6 + (preference_hits * 0.05))
            candidates.append({
                "content": content,
                "segment": "preferences",
                "importance": importance,
                "source": chat_name,
            })

    # Check for facts
    fact_hits = _match_count(text, _FACT_PATTERNS)
    if fact_hits >= 1:
        sentences = _extract_relevant_sentences(text, _FACT_PATTERNS)
        if sentences:
            content = "\n".join(sentences)
            importance = min(0.7, 0.5 + (fact_hits * 0.05))
            candidates.append({
                "content": content,
                "segment": "facts",
                "importance": importance,
                "source": chat_name,
            })

    return candidates
