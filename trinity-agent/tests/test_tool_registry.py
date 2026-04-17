"""Tests for the tool registry migration."""
from __future__ import annotations

from pathlib import Path

import pytest

from trinity.plugins import ToolSpec
from trinity.tools.registry import (
    BUILDER_TOOLS,
    MEMORY_TOOLS,
    RESEARCHER_TOOLS,
    TOOL_DEFINITIONS,
    TOOLS,
    execute_tool,
    get_tools,
)


def test_tool_definitions_still_shaped_as_before():
    # Back-compat contract: list of dicts with name/description/input_schema.
    assert isinstance(TOOL_DEFINITIONS, list)
    for t in TOOL_DEFINITIONS:
        assert set(t.keys()) >= {"name", "description", "input_schema"}


def test_builtin_tools_registered():
    for name in ("read_file", "write_file", "edit_file", "run_command",
                 "git_status", "memory_store", "log_issue", "send_telegram"):
        assert name in TOOLS
        assert isinstance(TOOLS.get(name), ToolSpec)
        assert TOOLS.source_of(name) == "builtin"


def test_subsets_preserved():
    # Core subsets exist and contain the expected anchor tools.
    assert "read_file" in BUILDER_TOOLS
    assert "web_fetch" in RESEARCHER_TOOLS
    assert "memory_search" in MEMORY_TOOLS


def test_get_tools_filters_by_name():
    subset = get_tools(["read_file", "write_file"])
    names = [t["name"] for t in subset]
    assert set(names) == {"read_file", "write_file"}


def test_get_tools_none_returns_all():
    all_tools = get_tools()
    assert len(all_tools) == len(TOOL_DEFINITIONS)


def test_get_tools_unknown_name_skipped():
    # Contract: unknown names are silently skipped, not raised.
    subset = get_tools(["read_file", "does-not-exist"])
    assert [t["name"] for t in subset] == ["read_file"]


def test_execute_tool_unknown_name_raises():
    with pytest.raises(KeyError, match="Unknown tool"):
        execute_tool("nope", {}, Path("/tmp"))


def test_execute_tool_dispatches(tmp_workspace):
    (tmp_workspace / "sample.txt").write_text("hello\nworld")
    result = execute_tool("read_file", {"path": "sample.txt"}, tmp_workspace)
    assert "hello" in result
    assert "world" in result


def test_execute_tool_wraps_exceptions_as_strings(tmp_workspace):
    # Reading a file that does not exist should surface the error as a string,
    # matching the pre-migration contract (agents parse the string).
    result = execute_tool("read_file", {"path": "missing.txt"}, tmp_workspace)
    assert result.lower().startswith("error in read_file")


def test_register_custom_tool(tmp_workspace):
    """A third party can register a tool; it shows up in execute_tool."""

    def handler(inp, ws, **_):
        return f"got {inp['value']}"

    TOOLS.register(
        "test_custom_tool",
        ToolSpec(
            name="test_custom_tool",
            definition={
                "name": "test_custom_tool",
                "description": "Test-only tool",
                "input_schema": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
            },
            handler=handler,
        ),
        source="manual",
    )
    try:
        # The TOOL_DEFINITIONS list is computed from TOOLS — make sure a
        # freshly computed view picks up the new entry.
        from trinity.tools.registry import build_tool_definitions
        assert "test_custom_tool" in [t["name"] for t in build_tool_definitions()]

        result = execute_tool(
            "test_custom_tool", {"value": "xyz"}, tmp_workspace
        )
        assert result == "got xyz"
    finally:
        TOOLS.unregister("test_custom_tool")
