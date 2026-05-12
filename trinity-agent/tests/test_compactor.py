"""Tests for the structured-handoff compactor."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from trinity.config import TrinityConfig, MemoryConfig, AgentConfig
from trinity.memory.compactor import (
    compact_history,
    make_synthetic_entry,
    _in_cooldown,
    _record_failure,
    _record_success,
    _read_state,
    CompactionResult,
)


class _FakeResp:
    def __init__(self, text):
        self.text = text


class _OkProvider:
    def chat(self, **kw):
        return _FakeResp(
            "RESOLVED\n- thing 1 done\n\nPENDING\n- followup\n\nACTIVE\n- "
            "discussing Y\n\nUSER PREFERENCES\n- terse",
        )


class _FailProvider:
    def chat(self, **kw):
        raise RuntimeError("simulated outage")


class _EmptyProvider:
    def chat(self, **kw):
        return _FakeResp("")


def _cfg(tmp_path: Path) -> TrinityConfig:
    cfg = TrinityConfig(
        memory=MemoryConfig(),
        agent=AgentConfig(),
        workspace_root=tmp_path,
        trinity_dir=tmp_path / ".trinity",
    )
    (cfg.trinity_dir / "state").mkdir(parents=True)
    return cfg


def test_compact_returns_structured_summary(tmp_path):
    cfg = _cfg(tmp_path)
    entries = [
        {"user": "do X", "assistant": "done X"},
        {"user": "now Y", "assistant": "starting Y"},
    ]
    result = compact_history(entries, cfg, _OkProvider())
    assert isinstance(result, CompactionResult)
    assert "RESOLVED" in result.summary_text
    assert "PENDING" in result.summary_text
    assert result.original_count == 2


def test_compact_empty_entries_returns_none(tmp_path):
    cfg = _cfg(tmp_path)
    assert compact_history([], cfg, _OkProvider()) is None


def test_compact_no_provider_returns_none(tmp_path):
    cfg = _cfg(tmp_path)
    entries = [{"user": "x", "assistant": "y"}]
    assert compact_history(entries, cfg, None) is None


def test_provider_failure_records_cooldown(tmp_path):
    cfg = _cfg(tmp_path)
    entries = [{"user": "x", "assistant": "y"}]
    assert compact_history(entries, cfg, _FailProvider()) is None
    assert _in_cooldown(cfg)


def test_empty_response_is_failure(tmp_path):
    cfg = _cfg(tmp_path)
    entries = [{"user": "x", "assistant": "y"}]
    assert compact_history(entries, cfg, _EmptyProvider()) is None
    assert _in_cooldown(cfg)


def test_success_clears_failure_state(tmp_path):
    cfg = _cfg(tmp_path)
    _record_failure(cfg)
    assert _in_cooldown(cfg)
    _record_success(cfg)
    assert not _in_cooldown(cfg)
    state = _read_state(cfg)
    assert state.get("failure_count", 0) == 0


def test_synthetic_entry_shape(tmp_path):
    result = CompactionResult(
        summary_text="RESOLVED\n- a", original_count=5, target_chars=200,
    )
    entry = make_synthetic_entry(result)
    assert entry["user"] == "[compressed handoff]"
    assert entry["assistant"] == "RESOLVED\n- a"
    assert entry["compressed"] is True
    assert entry["original_count"] == 5
