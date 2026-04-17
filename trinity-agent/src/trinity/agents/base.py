"""Core agentic loop — used by all sub-agents.

The loop is simple:
  1. Send messages to the provider
  2. If the model returns tool_use, execute tools and continue
  3. If the model returns end_turn, return the text
  4. Repeat until max_turns
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
import time
from pathlib import Path
from typing import Callable

from trinity._io import atomic_write_json
from trinity.providers.base import (
    Message, Provider, Response, ToolCall, ToolDef, ToolResult,
)

log = logging.getLogger(__name__)

# Module-level usage tracking path — set by init in app.py via set_usage_path()
_usage_path: Path | None = None
_usage_lock = threading.Lock()


def set_usage_path(trinity_dir: Path) -> None:
    """Set the path for usage.json persistence. Called once at init."""
    global _usage_path
    _usage_path = trinity_dir / "state" / "usage.json"


def _persist_usage(input_tokens: int, output_tokens: int) -> None:
    """Append token counts to today's usage totals."""
    if not _usage_path:
        return
    with _usage_lock:
        try:
            today = dt.date.today().isoformat()
            data: dict = {}
            if _usage_path.exists():
                try:
                    data = json.loads(_usage_path.read_text())
                except (json.JSONDecodeError, OSError):
                    data = {}

            if data.get("date") != today:
                # New day — reset counters
                data = {"date": today, "input_tokens": 0, "output_tokens": 0, "calls": 0}

            data["input_tokens"] = data.get("input_tokens", 0) + input_tokens
            data["output_tokens"] = data.get("output_tokens", 0) + output_tokens
            data["calls"] = data.get("calls", 0) + 1

            atomic_write_json(_usage_path, data)
        except Exception:
            log.debug("Failed to persist usage", exc_info=True)


def run_agent(
    provider: Provider,
    model: str,
    system: str,
    task: str,
    tools: list[dict] | None = None,
    max_turns: int = 30,
    max_tokens: int = 16384,
    workspace_root: Path | None = None,
    tool_executor: Callable | None = None,
    on_text: Callable[[str], None] | None = None,
    on_tool: Callable[[str, str], None] | None = None,
) -> str:
    """Run a full agentic loop and return the final text response.

    Args:
        provider: LLM provider instance
        model: Model ID to use
        system: System prompt
        task: User task / message
        tools: Tool definitions (Anthropic format dicts)
        max_turns: Max tool-use loop iterations
        max_tokens: Max tokens per response
        workspace_root: Root path for tool execution
        tool_executor: fn(name, input, workspace_root) -> str
        on_text: Callback for streaming text chunks
        on_tool: Callback when a tool is called: fn(tool_name, input_summary)

    Returns:
        Final text response from the model.
    """
    tool_defs = None
    if tools:
        tool_defs = [
            ToolDef(
                name=t["name"],
                description=t["description"],
                input_schema=t["input_schema"],
            )
            for t in tools
        ]

    messages: list[Message] = [Message(role="user", content=task)]
    total_input_tokens = 0
    total_output_tokens = 0

    for turn in range(max_turns):
        log.debug("Turn %d/%d", turn + 1, max_turns)

        # Stream if we have a text callback, otherwise use regular chat
        if on_text and not tool_defs:
            # Track 1: streaming without tools (conversational)
            final_text = ""
            for item in provider.stream(
                model=model,
                system=system,
                messages=messages,
                tools=tool_defs,
                max_tokens=max_tokens,
            ):
                if isinstance(item, str):
                    on_text(item)
                    final_text += item
                elif isinstance(item, Response):
                    total_input_tokens += item.usage.input_tokens
                    total_output_tokens += item.usage.output_tokens
                    if item.text:
                        final_text = item.text
            log.info(
                "Completed in %d turns. Tokens: %d in, %d out",
                turn + 1, total_input_tokens, total_output_tokens,
            )
            _persist_usage(total_input_tokens, total_output_tokens)
            return final_text

        # Regular chat (with or without tools)
        response = provider.chat(
            model=model,
            system=system,
            messages=messages,
            tools=tool_defs,
            max_tokens=max_tokens,
        )
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Model is done — return text
        if response.stop_reason == "end_turn" or not response.tool_calls:
            if on_text and response.text:
                on_text(response.text)
            log.info(
                "Completed in %d turns. Tokens: %d in, %d out",
                turn + 1, total_input_tokens, total_output_tokens,
            )
            _persist_usage(total_input_tokens, total_output_tokens)
            return response.text or "(no response)"

        # Model wants to use tools
        if response.stop_reason == "tool_use" and tool_executor:
            # Append assistant message preserving text + tool_calls as structured content
            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for tc in response.tool_calls:
                assistant_content.append(tc)
            messages.append(Message(role="assistant", content=assistant_content))

            tool_results: list[ToolResult] = []
            for tc in response.tool_calls:
                input_summary = _summarize_input(tc.name, tc.input)
                log.info("Tool call: %s(%s)", tc.name, input_summary)
                if on_tool:
                    on_tool(tc.name, input_summary)

                try:
                    result = tool_executor(tc.name, tc.input, workspace_root)
                    # Cap tool results to prevent context explosion
                    result_str = str(result)[:50_000]
                    tool_results.append(ToolResult(
                        tool_use_id=tc.id,
                        content=result_str,
                    ))
                except Exception as e:
                    log.error("Tool %s failed: %s", tc.name, e)
                    tool_results.append(ToolResult(
                        tool_use_id=tc.id,
                        content=f"Error: {e}",
                        is_error=True,
                    ))

            # Send tool results back
            messages.append(Message(role="user", content=tool_results))
        else:
            # No tool executor or unknown stop reason — return what we have
            _persist_usage(total_input_tokens, total_output_tokens)
            return response.text or "(no response)"

    log.warning("Max turns (%d) reached", max_turns)
    _persist_usage(total_input_tokens, total_output_tokens)
    return "(max turns reached — task may be incomplete)"


def run_conversational(
    provider: Provider,
    model: str,
    system: str,
    messages: list[Message],
    max_tokens: int = 4096,
    on_text: Callable[[str], None] | None = None,
) -> str:
    """Run a single-shot conversational response (no tools, no loop).

    This is Track 1 — fast, cheap, streaming.
    """
    if on_text:
        final_text = ""
        for item in provider.stream(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        ):
            if isinstance(item, str):
                on_text(item)
                final_text += item
            elif isinstance(item, Response):
                if item.text:
                    final_text = item.text
        return final_text or "(no response)"

    response = provider.chat(
        model=model,
        system=system,
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.text or "(no response)"


def _summarize_input(tool_name: str, tool_input: dict) -> str:
    """Create a short summary of tool input for logging."""
    if tool_name in ("read_file", "write_file", "edit_file"):
        return tool_input.get("path", "")[:80]
    if tool_name == "run_command":
        return tool_input.get("command", "")[:80]
    if tool_name in ("search_files", "search_content"):
        return tool_input.get("pattern", "")[:60]
    if tool_name == "send_telegram":
        return tool_input.get("group", "")
    if tool_name in ("git_status", "git_diff"):
        return tool_input.get("args", "")[:40]
    # Generic: show first key's value
    for v in tool_input.values():
        return str(v)[:60]
    return ""
