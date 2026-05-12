"""Haiku-powered memory agent.

Invoked when the primary agent's local recall comes up empty. Given a
precision query, it decides which memory stores to search — global,
another workspace, or both — and returns a consolidated summary with
pointers back to the originating store.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from trinity.memory.search import search_memories
from trinity.providers.base import Message, Provider, ToolDef, ToolResult
from trinity.workspaces import get_workspace_path, list_workspaces, rescan

log = logging.getLogger(__name__)

MEMORY_AGENT_SYSTEM_WITH_GLOBAL = """You are the Memory Agent for a multi-workspace AI system.

The primary agent just searched its LOCAL memory and found nothing relevant for its query. Your job is to search broader memory stores and return what is useful.

Decide which stores to search:
- **global_memory_search** — shared memory at ~/.trinity/ (user prefs, cross-company truths).
- **workspace_memory_search** — another workspace's memory. Use when the query concerns a specific project/company other than the current one. Call **list_workspaces** first if you don't know what's available.

Return EITHER:
- "NONE" — if nothing relevant was found anywhere.
- A compact summary (1-3 sentences) of the most relevant findings, each tagged with a pointer showing where it lives. Example: "[global] mem_20260415_003: user prefers concise replies." or "[workspace: oefr-digital] mem_20260411_012: product launch date is May 1."

Be selective. The primary agent needs only what is directly relevant."""

MEMORY_AGENT_SYSTEM_LOCAL_ONLY = """You are the Memory Agent for an isolated workspace.

The primary agent just searched its LOCAL memory and found nothing relevant. This workspace is configured NOT to share with the global memory store, so only other registered workspaces are available.

Use **workspace_memory_search** when the query concerns a specific project/company other than the current one. Call **list_workspaces** first if you don't know what's available.

Return EITHER:
- "NONE" — if nothing relevant was found.
- A compact summary (1-3 sentences) of the most relevant findings, each tagged with its workspace pointer. Example: "[workspace: oefr-digital] mem_20260411_012: product launch date is May 1."

Be selective. The primary agent needs only what is directly relevant."""


def _build_tools(include_global: bool) -> list[ToolDef]:
    tools: list[ToolDef] = []
    if include_global:
        tools.append(
            ToolDef(
                name="global_memory_search",
                description=(
                    "Search the global shared memory at ~/.trinity/. "
                    "Use for cross-company user preferences or long-term truths."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keywords to search for"},
                    },
                    "required": ["query"],
                },
            )
        )
    tools.extend([
        ToolDef(
            name="workspace_memory_search",
            description=(
                "Search another workspace's memory. Use when the query concerns "
                "a specific project/company other than the current one."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "workspace": {"type": "string", "description": "Workspace name (e.g. 'oefr-digital')"},
                    "query": {"type": "string", "description": "Keywords to search for"},
                },
                "required": ["workspace", "query"],
            },
        ),
        ToolDef(
            name="list_workspaces",
            description="List other Trinity workspaces available on this machine.",
            input_schema={"type": "object", "properties": {}},
        ),
    ])
    return tools


def _exec_tool(
    name: str,
    inp: dict,
    current_workspace: Path | None,
    global_trinity_dir: Path | None,
) -> str:
    if name == "global_memory_search":
        if global_trinity_dir is None:
            return "Global memory is disabled for this workspace."
        query = inp.get("query", "")
        if not global_trinity_dir.exists():
            return "Global memory not initialized."
        results = search_memories(global_trinity_dir, query, limit=3)
        if not results:
            return "No matches in global memory."
        return "\n".join(
            f"[global] {r['id']} ({r['tier']}): {r['summary']}" for r in results
        )

    if name == "workspace_memory_search":
        ws_name = inp.get("workspace", "")
        query = inp.get("query", "")
        ws_path = get_workspace_path(ws_name)
        if not ws_path:
            return f"Workspace '{ws_name}' not found in registry. Use list_workspaces to see available workspaces."
        ws_trinity = ws_path / ".trinity"
        if not ws_trinity.exists():
            return f"Workspace '{ws_name}' has no .trinity directory."
        results = search_memories(ws_trinity, query, limit=3)
        if not results:
            return f"No matches in workspace '{ws_name}'."
        return "\n".join(
            f"[workspace: {ws_name}] {r['id']} ({r['tier']}): {r['summary']}"
            for r in results
        )

    if name == "list_workspaces":
        ws = list_workspaces(current=current_workspace)
        if not ws:
            return "No other workspaces registered."
        return "\n".join(
            f"- {n}: {info.get('company', '(no company)')} — {info.get('description', '')[:80]}"
            for n, info in ws.items()
        )

    return f"Unknown tool: {name}"


def query(
    precision_query: str,
    provider: Provider,
    model: str,
    trinity_dir: Path,
    max_chars: int = 300,
    timeout_ms: int = 8000,
    max_iterations: int = 3,
    auto_rescan: bool = True,
    global_trinity_dir: Path | None = None,
) -> str:
    """Run the memory agent on a precision query.

    Returns "NONE" or a compact summary with pointers.
    """
    current_workspace = trinity_dir.parent if trinity_dir else None

    if auto_rescan:
        try:
            rescan(current=current_workspace)
        except Exception:
            log.debug("Workspace rescan failed", exc_info=True)

    result_holder: list[str] = ["NONE"]

    include_global = global_trinity_dir is not None
    system_prompt = (
        MEMORY_AGENT_SYSTEM_WITH_GLOBAL if include_global else MEMORY_AGENT_SYSTEM_LOCAL_ONLY
    )

    def _run() -> None:
        try:
            tools = _build_tools(include_global=include_global)
            messages: list[Message] = [Message(role="user", content=precision_query)]

            for _iter in range(max_iterations):
                response = provider.chat(
                    model=model,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                    max_tokens=400,
                )

                if not response.tool_calls:
                    text = (response.text or "").strip()
                    if text and text.upper() != "NONE":
                        if len(text) > max_chars:
                            text = text[: max_chars - 3] + "..."
                        result_holder[0] = text
                    return

                assistant_content: list = []
                if response.text:
                    assistant_content.append({"type": "text", "text": response.text})
                for tc in response.tool_calls:
                    assistant_content.append(tc)
                messages.append(Message(role="assistant", content=assistant_content))

                tool_results: list[ToolResult] = []
                for tc in response.tool_calls:
                    out = _exec_tool(tc.name, tc.input, current_workspace, global_trinity_dir)
                    tool_results.append(ToolResult(tool_use_id=tc.id, content=out))
                messages.append(Message(role="user", content=tool_results))

        except Exception as e:
            log.debug("Memory agent failed: %s", e, exc_info=True)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout_ms / 1000.0)

    if t.is_alive():
        log.debug("Memory agent timed out after %dms", timeout_ms)
        return "NONE"

    return result_holder[0]
