"""Pre-reply memory recall — surfaces relevant memories before the main agent runs."""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from trinity.providers.base import Provider, Message, ToolDef
from trinity.memory.search import search_memories

log = logging.getLogger(__name__)

RECALL_SYSTEM_PROMPT = """You are a memory recall agent. Given the user's message, search for relevant memories and return a compact summary.

Use the memory_search tool to find relevant memories. Then return EITHER:
- "NONE" if nothing relevant was found
- A 1-3 sentence summary of the most relevant memories

Be selective. Only surface memories directly relevant to what the user is asking about."""

_MEMORY_SEARCH_TOOL = ToolDef(
    name="memory_search",
    description="Search the memory system for relevant past memories.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query — keywords related to what you want to recall.",
            },
        },
        "required": ["query"],
    },
)


def recall(
    message: str,
    engine: str,           # "local" | "sdk" | "hybrid"
    trinity_dir: Path,
    provider: Provider | None = None,
    model: str = "",
    mode: str = "recent",  # "message" | "recent" | "full"
    chat_history: list | None = None,
    max_chars: int = 220,
    timeout_ms: int = 5000,
    global_trinity_dir: Path | None = None,
    current_scope: str | None = None,
    memory_agent_model: str = "",
    memory_agent_enabled: bool = True,
) -> str:
    """Run memory recall. Returns "NONE" or a compact summary.

    Primary search is LOCAL to the workspace (ignores global_trinity_dir).
    If the local search returns "NONE" and memory_agent_enabled is True,
    a Haiku memory agent is invoked to broaden the search across the
    global store and other registered workspaces.

    *current_scope* restricts recall to memories scoped to that chat or
    marked global (cross-chat).
    """
    if engine == "local":
        local = _recall_local(message, trinity_dir, max_chars, None, current_scope)
    elif engine == "sdk":
        if not provider:
            local = _recall_local(message, trinity_dir, max_chars, None, current_scope)
        else:
            local = _recall_sdk(message, trinity_dir, provider, model, mode, chat_history, max_chars, timeout_ms, None, current_scope)
    elif engine == "hybrid":
        local = _recall_local(message, trinity_dir, max_chars, None, current_scope)
        if local == "NONE" and provider:
            local = _recall_sdk(message, trinity_dir, provider, model, mode, chat_history, max_chars, timeout_ms, None, current_scope)
    else:
        return "NONE"

    if local != "NONE":
        return local

    if not memory_agent_enabled or not provider:
        return "NONE"

    try:
        from trinity.agents import memory_agent
        agent_model = memory_agent_model or model
        return memory_agent.query(
            precision_query=message,
            provider=provider,
            model=agent_model,
            trinity_dir=trinity_dir,
            max_chars=max_chars,
            timeout_ms=timeout_ms,
            global_trinity_dir=global_trinity_dir,
        )
    except Exception as e:
        log.debug("Memory agent invocation failed: %s", e, exc_info=True)
        return "NONE"


def _recall_local(message: str, trinity_dir: Path, max_chars: int, global_trinity_dir: Path | None = None, current_scope: str | None = None) -> str:
    """Search memories locally using keyword matching."""
    try:
        results = search_memories(trinity_dir, message, limit=3, global_trinity_dir=global_trinity_dir, current_scope=current_scope)
        if not results:
            return "NONE"

        lines = []
        for r in results:
            lines.append(f"- {r['summary']}")

        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars - 3] + "..."
        return text
    except Exception as e:
        log.debug("Local recall failed: %s", e)
        return "NONE"


def _recall_sdk(
    message: str,
    trinity_dir: Path,
    provider: Provider,
    model: str,
    mode: str,
    chat_history: list | None,
    max_chars: int,
    timeout_ms: int,
    global_trinity_dir: Path | None = None,
    current_scope: str | None = None,
) -> str:
    """Use the LLM provider to recall memories via tool use."""
    result_holder: list[str] = ["NONE"]
    error_holder: list[Exception] = []

    def _run():
        try:
            # Build the user message with context
            user_content = f"User message: {message}"
            if mode in ("recent", "full") and chat_history:
                # Include recent history for context
                limit = 4 if mode == "recent" else len(chat_history)
                recent = chat_history[-limit:]
                history_text = "\n".join(
                    f"{'User' if m.role == 'user' else 'Assistant'}: {str(m.content)[:200]}"
                    for m in recent
                )
                user_content = f"Recent conversation:\n{history_text}\n\nCurrent message: {message}"

            messages = [Message(role="user", content=user_content)]

            # First call — the model may call memory_search
            response = provider.chat(
                model=model,
                system=RECALL_SYSTEM_PROMPT,
                messages=messages,
                tools=[_MEMORY_SEARCH_TOOL],
                max_tokens=300,
            )

            # If the model called memory_search, execute it and send results back
            if response.tool_calls:
                # Build assistant message with tool calls
                assistant_content = []
                if response.text:
                    assistant_content.append({"type": "text", "text": response.text})
                for tc in response.tool_calls:
                    assistant_content.append(tc)
                messages.append(Message(role="assistant", content=assistant_content))

                # Execute each tool call
                from trinity.providers.base import ToolResult
                tool_results = []
                for tc in response.tool_calls:
                    query = tc.input.get("query", message)
                    results = search_memories(trinity_dir, query, limit=3, global_trinity_dir=global_trinity_dir, current_scope=current_scope)
                    if results:
                        result_text = "\n".join(
                            f"- [{r['tier']}] {r['summary']} (score: {r['score']})"
                            for r in results
                        )
                    else:
                        result_text = "No memories found."
                    tool_results.append(ToolResult(
                        tool_use_id=tc.id,
                        content=result_text,
                    ))
                messages.append(Message(role="user", content=tool_results))

                # Second call — model summarizes the results
                response = provider.chat(
                    model=model,
                    system=RECALL_SYSTEM_PROMPT,
                    messages=messages,
                    max_tokens=300,
                )

            text = (response.text or "").strip()
            if text and text.upper() != "NONE":
                if len(text) > max_chars:
                    text = text[:max_chars - 3] + "..."
                result_holder[0] = text

        except Exception as e:
            log.debug("SDK recall failed: %s", e)
            error_holder.append(e)

    # Run with timeout
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout_ms / 1000.0)

    if thread.is_alive():
        log.debug("SDK recall timed out after %dms", timeout_ms)
        return "NONE"

    return result_holder[0]
