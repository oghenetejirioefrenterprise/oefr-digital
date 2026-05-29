"""claude_sdk provider exposes Trinity's non-built-in tools as SDK MCP tools."""
from __future__ import annotations

import asyncio

from trinity.providers.base import ToolDef
from trinity.providers.claude_sdk_provider import ClaudeSDKProvider, _SDK_TOOL_EXCLUDE


def _defs():
    return [
        ToolDef(name="x_search", description="search X",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
        ToolDef(name="x_post", description="post to X",
                input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}),
        ToolDef(name="read_file", description="read",
                input_schema={"type": "object", "properties": {"path": {"type": "string"}}}),
        ToolDef(name="send_telegram", description="tg",
                input_schema={"type": "object", "properties": {"message": {"type": "string"}}}),
    ]


def test_exposes_x_tools_excludes_builtins_and_telegram():
    p = ClaudeSDKProvider(cwd="/tmp")
    servers, names = p._build_trinity_mcp(_defs())
    assert "mcp__trinity__x_search" in names
    assert "mcp__trinity__x_post" in names
    assert "mcp__trinity__read_file" not in names      # built-in covered
    assert "mcp__trinity__send_telegram" not in names  # run_cycle reports
    assert servers and "trinity" in servers


def test_options_merge_builtins_and_mcp():
    p = ClaudeSDKProvider(cwd="/tmp")
    opts = p._build_options("", "sys", 4096, _defs())
    assert "Bash" in opts.allowed_tools                 # built-ins retained
    assert "mcp__trinity__x_search" in opts.allowed_tools
    assert getattr(opts, "mcp_servers", None)           # in-process server wired


def test_no_tools_no_mcp():
    p = ClaudeSDKProvider(cwd="/tmp")
    servers, names = p._build_trinity_mcp(None)
    assert servers is None and names == []
    opts = p._build_options("", "sys", 4096, None)
    assert "Bash" in opts.allowed_tools
    assert not any(n.startswith("mcp__trinity__") for n in opts.allowed_tools)


def test_handler_dispatches_to_execute_tool(monkeypatch):
    """The SDK tool handler routes to execute_tool and returns SDK content shape."""
    import trinity.tools.registry as reg
    from pathlib import Path
    from trinity.providers.claude_sdk_provider import _make_sdk_tool_handler

    seen = {}

    def fake_exec(name, inp, ws, **ctx):
        seen["name"] = name
        seen["inp"] = inp
        seen["ws"] = ws
        return f"executed {name}"

    monkeypatch.setattr(reg, "execute_tool", fake_exec)

    handler = _make_sdk_tool_handler("x_search", Path("/tmp"))
    out = asyncio.run(handler({"query": "hi"}))

    assert seen["name"] == "x_search"
    assert seen["inp"] == {"query": "hi"}
    assert seen["ws"] == Path("/tmp")
    assert out["content"][0]["text"] == "executed x_search"
