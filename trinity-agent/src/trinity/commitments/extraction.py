"""LLM-driven extraction of time-bound commitments from a chat exchange.

Run once after every Telegram exchange (in the same background thread as
memory extraction). Uses the cheap router model, looks at just the
latest user+assistant pair plus a tight system prompt, and returns 0..N
candidate ``CommitmentRecord``s.

Output shape from the model is JSON. We parse defensively: if anything
goes sideways (no JSON, wrong types) we drop the candidate rather than
let bad data land in the store.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re

from trinity.commitments.types import (
    CommitmentRecord,
    KIND_DEADLINE_CHECK,
    KIND_EVENT_CHECK_IN,
    KIND_OPEN_LOOP,
    make_dedupe_key,
    make_id,
)
from trinity.config import TrinityConfig
from trinity.providers.base import Message, Provider

log = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.6

_SYSTEM_PROMPT = """You extract time-bound commitments and follow-ups from a single chat exchange.

A commitment is anything the assistant or user expects to revisit later: "I'll check tomorrow", "remind me Friday", "let me know when you hear back", a hard deadline ("the launch is on the 12th"), an open thread ("we still need to decide X").

Output a JSON array. Each item:
{{
  "kind": "event_check_in" | "deadline_check" | "open_loop",
  "text": "<short paraphrase of the promise>",
  "due_at": "<ISO 8601 datetime in UTC>",
  "nudge_text": "<the message to send the user when this fires>",
  "confidence": 0.0-1.0
}}

Rules:
- If nothing committal happened, return []. Do NOT invent.
- "Tomorrow" / "next week" / "Friday": resolve relative to NOW = {now_iso}.
- If a time-of-day isn't stated, default to 09:00 in the user's local timezone (assume UTC).
- Confidence < 0.6 means uncertain; keep it but the runtime may filter.
- Return ONLY the JSON array. No prose, no fences."""


def _extract_json_array(text: str) -> list[dict]:
    """Pull the first JSON array out of *text*, tolerating fences/preamble."""
    # Strip code fences if present
    text = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.MULTILINE)
    # Find the first [ ... ] span
    start = text.find("[")
    if start < 0:
        return []
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                blob = text[start:i + 1]
                try:
                    parsed = json.loads(blob)
                    return parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    return []
    return []


def _normalise_kind(value: str) -> str:
    v = (value or "").strip().lower()
    if v in (KIND_DEADLINE_CHECK, KIND_EVENT_CHECK_IN, KIND_OPEN_LOOP):
        return v
    return KIND_OPEN_LOOP


def _validate_due_at(value: str) -> str | None:
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except (ValueError, AttributeError):
        return None


def extract_commitments(
    user_msg: str,
    assistant_msg: str,
    chat_id: str,
    config: TrinityConfig,
    provider: Provider,
) -> list[CommitmentRecord]:
    """Return zero-or-more commitment records extracted from one exchange."""
    if not user_msg or not assistant_msg or provider is None:
        return []

    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    system = _SYSTEM_PROMPT.format(now_iso=now_iso)
    user_content = (
        f"User: {user_msg[:2000]}\n\nAssistant: {assistant_msg[:2000]}"
    )

    try:
        resp = provider.chat(
            model=config.agent.router_model,
            system=system,
            messages=[Message(role="user", content=user_content)],
            max_tokens=600,
        )
    except Exception as e:
        log.debug("commitment extraction LLM call failed: %s", e)
        return []

    raw_items = _extract_json_array(resp.text or "")
    out: list[CommitmentRecord] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        due = _validate_due_at(item.get("due_at") or "")
        if not text or not due:
            continue
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < CONFIDENCE_FLOOR:
            continue
        kind = _normalise_kind(item.get("kind") or "")
        out.append(CommitmentRecord(
            id=make_id(),
            kind=kind,
            text=text,
            chat_id=str(chat_id),
            due_at=due,
            dedupe_key=make_dedupe_key(str(chat_id), kind, text),
            confidence=round(confidence, 3),
            nudge_text=(item.get("nudge_text") or text).strip()[:600],
        ))
    return out
