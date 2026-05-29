"""Structured handoff compaction for chat history overflow.

When a chat's rolling history grows past the compaction threshold, the
oldest entries are summarised into one synthetic entry. This module
implements that summarisation as an explicit *handoff* — the produced
summary tells the next-window assistant that resolved threads must NOT
be re-fulfilled, splits the conversation into Resolved / Pending /
Active / User Preferences, and persists a failure cooldown so a flaky
provider can't burn budget on repeated retries.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trinity.config import TrinityConfig
from trinity.providers.base import Message, Provider

log = logging.getLogger(__name__)

_FAILURE_COOLDOWN_S = 600
_FAILURE_ESCALATION_S = 3600
_FAILURE_ESCALATE_AFTER = 3
_TARGET_RATIO = 0.20
_TARGET_CEILING = 12000
_TARGET_FLOOR = 600

_HANDOFF_SYSTEM = """You are summarising a conversation handoff. The continuation will be handled by a different assistant in a fresh context window.

Output four sections, in order, each a short list (Markdown bullets):

RESOLVED — tasks/questions completed in this window. The next assistant must NOT re-fulfil these.
PENDING — open threads, deferred items, things the user expects later.
ACTIVE — what was happening in the last 1–2 turns; the immediate context.
USER PREFERENCES — corrections, style, constraints, or invariants to carry forward.

Be dense and factual. No filler, no preamble, no closing remarks. Target {target_chars} characters total."""


@dataclass
class CompactionResult:
    summary_text: str
    original_count: int
    target_chars: int


def _state_path(config: TrinityConfig) -> Path:
    return config.trinity_dir / "state" / "compactor_state.json"


def _read_state(config: TrinityConfig) -> dict[str, Any]:
    p = _state_path(config)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(config: TrinityConfig, state: dict[str, Any]) -> None:
    from trinity._io import atomic_write_json
    p = _state_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(p, state)


def _in_cooldown(config: TrinityConfig) -> bool:
    state = _read_state(config)
    last_fail = state.get("last_failure_at")
    failures = int(state.get("failure_count", 0))
    if not last_fail:
        return False
    cooldown = _FAILURE_ESCALATION_S if failures >= _FAILURE_ESCALATE_AFTER else _FAILURE_COOLDOWN_S
    return (time.time() - float(last_fail)) < cooldown


def _record_failure(config: TrinityConfig) -> None:
    from trinity._io import file_lock
    with file_lock(_state_path(config)):
        state = _read_state(config)
        state["last_failure_at"] = time.time()
        state["failure_count"] = int(state.get("failure_count", 0)) + 1
        _write_state(config, state)


def _record_success(config: TrinityConfig) -> None:
    from trinity._io import file_lock
    with file_lock(_state_path(config)):
        state = _read_state(config)
        state.pop("last_failure_at", None)
        state["failure_count"] = 0
        state["last_success_at"] = time.time()
        _write_state(config, state)


def _build_transcript(entries: list[dict]) -> str:
    lines: list[str] = []
    for entry in entries:
        u = (entry.get("user") or "").strip()
        a = (entry.get("assistant") or "").strip()
        if u:
            lines.append(f"User: {u[:1500]}")
        if a:
            lines.append(f"Assistant: {a[:1500]}")
    transcript = "\n\n".join(lines)
    if len(transcript) > 16000:
        transcript = transcript[:16000] + "\n\n[truncated]"
    return transcript


def compact_history(
    entries: list[dict],
    config: TrinityConfig,
    provider: Provider | None,
) -> CompactionResult | None:
    """Summarise *entries* into a single handoff. Returns ``None`` on failure."""
    if not entries or provider is None:
        return None
    if _in_cooldown(config):
        log.info("compactor in cooldown — skipping")
        return None

    transcript = _build_transcript(entries)
    raw_size = sum(len(e.get("user") or "") + len(e.get("assistant") or "") for e in entries)
    target = max(_TARGET_FLOOR, min(_TARGET_CEILING, int(raw_size * _TARGET_RATIO)))

    try:
        response = provider.chat(
            model=config.agent.router_model,
            system=_HANDOFF_SYSTEM.format(target_chars=target),
            messages=[Message(
                role="user",
                content=f"Summarise this conversation:\n\n{transcript}",
            )],
            max_tokens=max(256, min(1500, target // 3)),
        )
    except Exception as e:
        log.warning("compactor provider call failed: %s", e)
        _record_failure(config)
        return None

    summary = (response.text or "").strip()
    if not summary:
        log.warning("compactor produced empty summary")
        _record_failure(config)
        return None

    _record_success(config)
    return CompactionResult(
        summary_text=summary, original_count=len(entries), target_chars=target,
    )


def make_synthetic_entry(result: CompactionResult) -> dict[str, Any]:
    """Wrap a CompactionResult into a chat-history entry."""
    return {
        "user": "[compressed handoff]",
        "assistant": result.summary_text,
        "user_name": "system",
        "timestamp": dt.datetime.now().isoformat(),
        "compressed": True,
        "original_count": result.original_count,
        "target_chars": result.target_chars,
    }
