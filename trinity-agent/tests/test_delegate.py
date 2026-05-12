"""Tests for ``delegate_task``."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from trinity.config import TrinityConfig, AgentConfig, MemoryConfig
from trinity.tools import delegate


class _StubResp:
    def __init__(self, text):
        self.text = text
        self.tool_calls = []
        self.stop_reason = "end_turn"

        class _U:
            input_tokens = 0
            output_tokens = 0
        self.usage = _U()


class _StubProvider:
    """Minimal provider that returns a canned text and never uses tools."""

    def __init__(self, response_text="ok"):
        self.response_text = response_text
        self.calls = 0

    def chat(self, **kw):
        self.calls += 1
        # Echo the task back so we can verify which goal was passed.
        msgs = kw.get("messages", [])
        last = msgs[-1].content if msgs else ""
        return _StubResp(f"[{self.response_text}] {last}")

    def stream(self, **kw):
        yield self.chat(**kw)


def _bootstrap(tmp_path: Path, response_text="ok"):
    cfg = TrinityConfig(
        memory=MemoryConfig(),
        agent=AgentConfig(),
        workspace_root=tmp_path,
        trinity_dir=tmp_path / ".trinity",
    )
    (cfg.trinity_dir / "state").mkdir(parents=True)
    provider = _StubProvider(response_text)
    delegate.init_delegate(provider, cfg)
    return cfg, provider


def test_leaf_runs_one_subagent(tmp_path):
    _bootstrap(tmp_path, "leafdone")
    out = delegate.delegate_task({"goal": "look up X"}, tmp_path)
    assert "leafdone" in out


def test_orchestrator_runs_multiple(tmp_path):
    _bootstrap(tmp_path, "orch")
    goals = ["one", "two", "three"]
    out = delegate.delegate_task(
        {"goals": json.dumps(goals), "role": "orchestrator"}, tmp_path,
    )
    for g in goals:
        assert g in out
    assert out.count("orch") == 3


def test_missing_goal_in_leaf_returns_error(tmp_path):
    _bootstrap(tmp_path)
    out = delegate.delegate_task({}, tmp_path)
    assert "missing 'goal'" in out


def test_orchestrator_too_many_goals(tmp_path):
    _bootstrap(tmp_path)
    too_many = json.dumps([f"g{i}" for i in range(10)])
    out = delegate.delegate_task(
        {"goals": too_many, "role": "orchestrator"}, tmp_path,
    )
    assert "too many" in out


def test_invalid_goals_json(tmp_path):
    _bootstrap(tmp_path)
    out = delegate.delegate_task(
        {"goals": "not-json", "role": "orchestrator"}, tmp_path,
    )
    assert "JSON array" in out


def test_depth_cap(tmp_path):
    """Manually pump depth to MAX_DEPTH and confirm the tool refuses."""
    _bootstrap(tmp_path)
    delegate._set_depth(delegate.MAX_DEPTH)
    try:
        out = delegate.delegate_task({"goal": "anything"}, tmp_path)
        assert "delegation depth exceeded" in out
    finally:
        delegate._set_depth(0)


def test_unknown_role(tmp_path):
    _bootstrap(tmp_path)
    out = delegate.delegate_task({"role": "spooky", "goal": "x"}, tmp_path)
    assert "unknown role" in out
