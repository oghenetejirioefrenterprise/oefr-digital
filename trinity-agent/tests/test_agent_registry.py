"""Tests for the agent registry."""
from __future__ import annotations

import pytest

from trinity.agents.registry import AGENTS
from trinity.plugins import AgentSpec


def test_three_builtins_registered():
    assert "conversational" in AGENTS
    assert "builder" in AGENTS
    assert "researcher" in AGENTS
    for name in ("conversational", "builder", "researcher"):
        assert AGENTS.source_of(name) == "builtin"


def test_specs_typed():
    for name in AGENTS.names():
        spec = AGENTS.get(name)
        assert isinstance(spec, AgentSpec)
        assert callable(spec.run)
        assert spec.kind in {"conversational", "tool-using"}


def test_conversational_kind():
    assert AGENTS.get("conversational").kind == "conversational"
    assert AGENTS.get("conversational").tool_subset is None


def test_builder_and_researcher_are_tool_using():
    assert AGENTS.get("builder").kind == "tool-using"
    assert AGENTS.get("builder").tool_subset == "builder"
    assert AGENTS.get("researcher").kind == "tool-using"
    assert AGENTS.get("researcher").tool_subset == "researcher"


def test_register_custom_agent():
    def custom(*args, **kwargs):
        return "custom-ran"

    AGENTS.register(
        "test-custom-agent",
        AgentSpec(
            name="test-custom-agent",
            run=custom,
            kind="conversational",
            description="Test-only agent",
        ),
        source="manual",
    )
    try:
        spec = AGENTS.get("test-custom-agent")
        assert spec.run() == "custom-ran"
    finally:
        if "test-custom-agent" in AGENTS:
            AGENTS.unregister("test-custom-agent")
