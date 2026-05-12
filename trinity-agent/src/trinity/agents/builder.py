"""Track 2 — Builder agent (full tool-use agentic loop)."""
from __future__ import annotations

import logging
from typing import Callable

from trinity.agents.base import run_agent
from trinity.config import TrinityConfig
from trinity.providers.base import Provider

log = logging.getLogger(__name__)


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
    """Run a builder agent with full tool access.

    This is Track 2 — the heavy path for tasks that need file system,
    shell, git, or web access.
    """
    model = model or config.agent.action_model

    return run_agent(
        provider=provider,
        model=model,
        system=system,
        task=task,
        tools=tool_definitions,
        max_turns=config.agent.max_turns,
        max_tokens=config.agent.max_tokens,
        workspace_root=config.workspace_root,
        tool_executor=tool_executor,
        on_text=on_text,
        on_tool=on_tool,
    )
