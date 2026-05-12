"""Track 2 — Researcher agent (web tools only)."""
from __future__ import annotations

import logging
from typing import Callable

from trinity.agents.base import run_agent
from trinity.config import TrinityConfig
from trinity.providers.base import Provider

log = logging.getLogger(__name__)

# Researcher only gets web + read + memory tools
RESEARCHER_TOOL_NAMES = [
    "web_search", "web_fetch", "read_file", "search_content",
    "search_files", "list_directory", "memory_store", "memory_search",
    "send_telegram",
]


def run(
    provider: Provider,
    config: TrinityConfig,
    system: str,
    task: str,
    tool_definitions: list[dict],
    tool_executor: Callable,
    model: str | None = None,
    on_text: Callable[[str], None] | None = None,
    on_tool: Callable[[str, str], None] | None = None,
) -> str:
    """Run a researcher agent with web + read-only tools."""
    model = model or config.agent.default_model

    # Filter tools to researcher subset
    filtered = [t for t in tool_definitions if t["name"] in RESEARCHER_TOOL_NAMES]

    return run_agent(
        provider=provider,
        model=model,
        system=system,
        task=task,
        tools=filtered,
        max_turns=config.agent.max_turns,
        max_tokens=config.agent.max_tokens,
        workspace_root=config.workspace_root,
        tool_executor=tool_executor,
        on_text=on_text,
        on_tool=on_tool,
    )
