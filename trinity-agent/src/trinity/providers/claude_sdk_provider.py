"""Claude Agent SDK provider — uses the official Claude Agent SDK.

The SDK handles the entire agent loop including tool execution.
Built-in tools (Read, Write, Edit, Bash, Glob, Grep, etc.) are
executed by the SDK — no manual tool loop needed.

Authentication: Set ANTHROPIC_API_KEY environment variable.
Works with Anthropic API keys from console.anthropic.com.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any, Callable, Generator

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    tool,
    create_sdk_mcp_server,
)

from .base import (
    Message,
    Provider,
    Response,
    ToolCall,
    ToolDef,
    Usage,
)

log = logging.getLogger(__name__)

# All built-in tools from the Agent SDK
BUILTIN_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    "WebSearch", "WebFetch",
]

# Trinity tools NOT exposed as MCP tools to the SDK:
#  - filesystem/shell/web: already covered by SDK built-ins (Read/Write/Edit/
#    Bash/Glob/Grep/Web*), so don't duplicate them.
#  - send_telegram: a cycle's result is already delivered to its report_to
#    channel by run_cycle, so exposing it would risk double-reporting.
# Everything else (x_*, memory_*, knowledge, kanban, git, delegate) IS exposed
# so claude_sdk employees can call it directly instead of improvising via Bash.
_SDK_TOOL_EXCLUDE = {
    "read_file", "write_file", "edit_file", "run_command",
    "search_files", "list_files", "web_fetch", "web_search",
    "send_telegram",
}


class ClaudeSDKProvider(Provider):
    """Provider using the Claude Agent SDK.

    The SDK handles the entire agent loop including tool execution.
    When chat() is called, the SDK runs the full agentic loop
    autonomously — reading files, running commands, editing code —
    and returns the final result. No manual tool loop needed.

    Optional callbacks can be set to receive live tool-use events
    as the SDK processes them internally.
    """

    def __init__(
        self,
        allowed_tools: list[str] | None = None,
        permission_mode: str = "bypassPermissions",
        cwd: str | None = None,
        max_turns: int = 30,
        timeout_seconds: float = 600.0,
    ) -> None:
        self._allowed_tools = allowed_tools or BUILTIN_TOOLS
        self._permission_mode = permission_mode
        self._cwd = cwd
        self._max_turns = max_turns
        self._timeout_seconds = timeout_seconds

        # Live callbacks — set by the caller before chat()/stream()
        self.on_tool: Callable[[str, str], None] | None = None
        self.on_text: Callable[[str], None] | None = None

    @staticmethod
    def _find_system_cli() -> str | None:
        """Return the system-installed claude binary, preferring it over the SDK bundle.

        The bundled claude that ships with claude_agent_sdk may lag behind the
        system install by several patch versions and can produce "exit code 1"
        fatal errors when the two versions diverge. Always prefer the system
        binary so the SDK and CLI stay in sync.
        """
        candidates = [
            Path.home() / ".local/bin/claude",
            Path("/usr/local/bin/claude"),
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                return str(p)
        found = shutil.which("claude")
        return found if found else None

    def _build_trinity_mcp(
        self, tools: list[ToolDef] | None
    ) -> tuple[dict[str, Any] | None, list[str]]:
        """Expose Trinity's non-built-in tools to the SDK as in-process MCP tools.

        Without this the SDK only has Read/Write/Bash/etc., so an employee told
        to use x_search/x_post (which have no built-in equivalent) improvises
        raw shell calls and hangs. Returns (mcp_servers, extra_allowed_names).
        Sync Trinity handlers run in a worker thread so handlers that call
        ``asyncio.run`` themselves (e.g. browser-based x_post) don't collide
        with the SDK's running event loop.
        """
        if not tools:
            return None, []
        ws = Path(self._cwd) if self._cwd else Path.cwd()
        sdk_tools = []
        names: list[str] = []
        for td in tools:
            if td.name in _SDK_TOOL_EXCLUDE:
                continue
            handler = _make_sdk_tool_handler(td.name, ws)
            sdk_tools.append(tool(td.name, td.description, td.input_schema)(handler))
            names.append(f"mcp__trinity__{td.name}")

        if not sdk_tools:
            return None, []
        server = create_sdk_mcp_server(name="trinity", version="1.0.0", tools=sdk_tools)
        return {"trinity": server}, names

    def _build_options(
        self,
        model: str,
        system: str,
        max_tokens: int,
        tools: list[ToolDef] | None = None,
    ) -> ClaudeAgentOptions:
        """Build ClaudeAgentOptions for a query."""
        mcp_servers, mcp_names = self._build_trinity_mcp(tools)
        allowed = list(self._allowed_tools) + mcp_names
        kwargs: dict[str, Any] = {
            "allowed_tools": allowed,
            "permission_mode": self._permission_mode,
            "max_turns": self._max_turns,
        }
        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers
        if model:
            kwargs["model"] = model
        if system:
            kwargs["system_prompt"] = system
        if self._cwd:
            kwargs["cwd"] = self._cwd
        # Prefer the system claude over the SDK-bundled binary to avoid
        # version-mismatch "exit code 1" failures.
        cli = self._find_system_cli()
        if cli:
            kwargs["cli_path"] = cli
        return ClaudeAgentOptions(**kwargs)

    def chat(
        self,
        model: str,
        system: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 16384,
    ) -> Response:
        """Run a full agent query and return the final result.

        The SDK handles all tool execution internally. Returns a
        Response with the final text and stop_reason="end_turn".
        The caller's agent loop completes in one iteration.
        """
        last_msg = messages[-1] if messages else None
        if not last_msg:
            return Response(text="(no message)", stop_reason="end_turn")

        prompt = (
            last_msg.content
            if isinstance(last_msg.content, str)
            else str(last_msg.content)
        )
        options = self._build_options(model, system, max_tokens, tools)

        async def _timed() -> tuple:
            return await asyncio.wait_for(
                self._run_query(prompt, options),
                timeout=self._timeout_seconds,
            )

        try:
            result_text, usage_data = asyncio.run(_timed())
        except asyncio.TimeoutError:
            log.error("SDK query timed out after %.0fs", self._timeout_seconds)
            return Response(
                text=f"(SDK query timed out after {int(self._timeout_seconds)}s)",
                tool_calls=[],
                stop_reason="end_turn",
            )

        usage = Usage()
        if usage_data:
            usage = Usage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            )

        return Response(
            text=result_text,
            tool_calls=[],
            stop_reason="end_turn",
            usage=usage,
        )

    def stream(
        self,
        model: str,
        system: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 16384,
    ) -> Generator[str | ToolCall | Response, None, None]:
        """Stream agent output.

        Collects text from AssistantMessage blocks and yields them,
        then yields the final Response.
        """
        last_msg = messages[-1] if messages else None
        if not last_msg:
            yield Response(text="(no message)", stop_reason="end_turn")
            return

        prompt = (
            last_msg.content
            if isinstance(last_msg.content, str)
            else str(last_msg.content)
        )
        options = self._build_options(model, system, max_tokens, tools)

        async def _timed_stream() -> tuple:
            return await asyncio.wait_for(
                self._run_query_with_chunks(prompt, options),
                timeout=self._timeout_seconds,
            )

        try:
            text_parts, usage_data = asyncio.run(_timed_stream())
        except asyncio.TimeoutError:
            log.error("SDK stream timed out after %.0fs", self._timeout_seconds)
            yield Response(
                text=f"(SDK stream timed out after {int(self._timeout_seconds)}s)",
                tool_calls=[],
                stop_reason="end_turn",
            )
            return

        # Yield all collected text chunks
        for chunk in text_parts:
            yield chunk

        usage = Usage()
        if usage_data:
            usage = Usage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            )

        yield Response(
            text="".join(text_parts),
            tool_calls=[],
            stop_reason="end_turn",
            usage=usage,
        )

    def _fire_tool(self, block: ToolUseBlock) -> None:
        """Notify the on_tool callback if set."""
        if not self.on_tool:
            return
        name = block.name
        summary = _summarize_sdk_tool(name, block.input)
        try:
            self.on_tool(name, summary)
        except Exception:
            pass

    def _fire_text(self, text: str) -> None:
        """Notify the on_text callback if set."""
        if not self.on_text:
            return
        try:
            self.on_text(text)
        except Exception:
            pass

    async def _run_query(
        self, prompt: str, options: ClaudeAgentOptions
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute a query and return (result_text, usage_dict)."""
        result_text = ""
        usage_data = None

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        self._fire_tool(block)
                    elif isinstance(block, TextBlock):
                        self._fire_text(block.text)
            elif isinstance(message, ResultMessage):
                result_text = message.result or ""
                usage_data = message.usage

        return result_text or "(no response)", usage_data

    async def _run_query_with_chunks(
        self, prompt: str, options: ClaudeAgentOptions
    ) -> tuple[list[str], dict[str, Any] | None]:
        """Execute a query and return (text_chunks, usage_dict)."""
        text_parts: list[str] = []
        usage_data = None

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        self._fire_tool(block)
                    elif isinstance(block, TextBlock):
                        text_parts.append(block.text)
                        self._fire_text(block.text)
            elif isinstance(message, ResultMessage):
                usage_data = message.usage
                # Use result text if we didn't capture chunks
                if not text_parts and message.result:
                    text_parts.append(message.result)

        if not text_parts:
            text_parts.append("(no response)")

        return text_parts, usage_data


def _make_sdk_tool_handler(tool_name: str, workspace_root: Path):
    """Build an async SDK MCP handler that dispatches to Trinity's tool registry.

    ``execute_tool`` is synchronous and some handlers (e.g. browser-based
    x_post) call ``asyncio.run`` internally, so it runs in a worker thread to
    avoid nesting event loops. ``registry`` is imported lazily and by-module so
    the dispatch target stays patchable and free of import cycles.
    """
    async def _handler(args: dict) -> dict:
        import asyncio
        import trinity.tools.registry as _registry
        try:
            result = await asyncio.to_thread(
                _registry.execute_tool, tool_name, dict(args or {}), workspace_root
            )
        except Exception as e:  # pragma: no cover - defensive
            result = f"Error in {tool_name}: {type(e).__name__}: {e}"
        return {"content": [{"type": "text", "text": str(result)}]}
    return _handler


def _summarize_sdk_tool(name: str, tool_input: dict) -> str:
    """Create a short summary of an SDK tool call for display."""
    if name == "Read":
        return tool_input.get("file_path", "")[:80]
    if name == "Write":
        return tool_input.get("file_path", "")[:80]
    if name == "Edit":
        return tool_input.get("file_path", "")[:80]
    if name == "Bash":
        return tool_input.get("command", "")[:80]
    if name == "Glob":
        return tool_input.get("pattern", "")[:60]
    if name == "Grep":
        return tool_input.get("pattern", "")[:60]
    if name == "WebSearch":
        return tool_input.get("query", "")[:60]
    if name == "WebFetch":
        return tool_input.get("url", "")[:60]
    # Generic
    for v in tool_input.values():
        return str(v)[:60]
    return ""
