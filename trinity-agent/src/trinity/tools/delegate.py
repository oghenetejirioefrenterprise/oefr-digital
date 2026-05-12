"""``delegate_task`` — subagent spawn tool.

Lets a builder agent fork off a focused, time-boxed subagent for a
discrete sub-goal. Two roles:

- ``leaf`` (default) — exactly one subagent runs; it is given the
  researcher toolset (read-only filesystem + search + web + memory) and
  cannot itself spawn more subagents. This is the normal case.

- ``orchestrator`` — accepts ``goals`` as a JSON-encoded list of strings
  (max 5). Up to ``max_concurrent`` leaves run in parallel. Returns a
  single concatenated result.

Spawning past depth=2, or from inside a leaf, returns a clean error
string instead of raising — the caller agent can recover.
"""
from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from trinity.config import TrinityConfig
from trinity.providers.base import Provider

log = logging.getLogger(__name__)

MAX_DEPTH = 2
DEFAULT_MAX_CONCURRENT = 3
MAX_GOALS = 5
SUBAGENT_MAX_TURNS = 12
SUBAGENT_MAX_TOKENS = 4096
RESULT_CAP = 50_000

_DEPTH = threading.local()


# ── Module-level state, initialised once at app startup ───────────────

_provider: Provider | None = None
_config: TrinityConfig | None = None


def init_delegate(provider: Provider, config: TrinityConfig) -> None:
    """Wire the live provider + config so the tool can spawn subagents."""
    global _provider, _config
    _provider = provider
    _config = config


# ── Helpers ───────────────────────────────────────────────────────────

def _depth() -> int:
    return getattr(_DEPTH, "value", 0)


def _set_depth(value: int) -> None:
    _DEPTH.value = value


_SUBAGENT_SYSTEM = (
    "You are a focused subagent spawned by the parent agent to complete "
    "ONE specific goal. Be concise and direct. Use tools when needed. "
    "Reply with the result only — no preamble, no closing remarks."
)


def _toolset_for(name: str) -> list[str]:
    from trinity.tools.registry import BUILDER_TOOLS, RESEARCHER_TOOLS
    if name == "builder":
        # Strip delegate_task itself so leaves cannot spawn.
        return [t for t in BUILDER_TOOLS if t != "delegate_task"]
    return list(RESEARCHER_TOOLS)


def _run_subagent(goal: str, toolset_name: str) -> str:
    """Run one subagent and return its final response text."""
    if _provider is None or _config is None:
        return "[delegate_task: not initialised]"
    from trinity.agents.base import run_agent
    from trinity.tools.registry import execute_tool, get_tools

    tool_names = _toolset_for(toolset_name)
    tools = get_tools(tool_names)

    parent_depth = _depth()
    _set_depth(parent_depth + 1)
    try:
        return run_agent(
            provider=_provider,
            model=_config.agent.action_model,
            system=_SUBAGENT_SYSTEM,
            task=goal,
            tools=tools,
            max_turns=SUBAGENT_MAX_TURNS,
            max_tokens=SUBAGENT_MAX_TOKENS,
            workspace_root=_config.workspace_root,
            tool_executor=execute_tool,
        )
    finally:
        _set_depth(parent_depth)


# ── Tool entrypoint ───────────────────────────────────────────────────

DELEGATE_SCHEMA: dict[str, Any] = {
    "name": "delegate_task",
    "description": (
        "Spawn a focused subagent (or several, in orchestrator mode) to "
        "complete a discrete sub-goal in parallel. Use this for "
        "research/lookup tasks that would otherwise block the main agent "
        "with sequential work. role='leaf' (default) runs ONE subagent "
        "with read-only researcher tools; role='orchestrator' runs up to "
        "5 subagents in parallel given a JSON list of goals. Returns the "
        "subagent(s) result text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "The sub-goal to complete (leaf mode).",
            },
            "goals": {
                "type": "string",
                "description": (
                    "JSON-encoded array of sub-goals (orchestrator mode). "
                    "Max 5 items."
                ),
            },
            "role": {
                "type": "string",
                "enum": ["leaf", "orchestrator"],
                "description": "Spawn role. Default 'leaf'.",
            },
            "toolset": {
                "type": "string",
                "enum": ["researcher", "builder"],
                "description": (
                    "Tool surface for the subagent. Default 'researcher' "
                    "(read-only). 'builder' allows write/shell — use "
                    "carefully."
                ),
            },
            "max_concurrent": {
                "type": "integer",
                "description": "Concurrency cap for orchestrator mode. Default 3.",
            },
        },
    },
}


def delegate_task(inp: dict, _ws: Path, **_ctx: Any) -> str:
    """Tool handler — see DELEGATE_SCHEMA for the contract."""
    if _depth() >= MAX_DEPTH:
        return "[delegate_task: delegation depth exceeded — leaves cannot spawn]"

    role = (inp.get("role") or "leaf").lower()
    toolset = (inp.get("toolset") or "researcher").lower()

    if role == "leaf":
        goal = (inp.get("goal") or "").strip()
        if not goal:
            return "[delegate_task: missing 'goal']"
        try:
            return _run_subagent(goal, toolset)[:RESULT_CAP]
        except Exception as e:
            log.exception("subagent (leaf) failed")
            return f"[delegate_task: subagent crashed: {e}]"

    if role == "orchestrator":
        goals_raw = inp.get("goals", "")
        try:
            goals = json.loads(goals_raw) if isinstance(goals_raw, str) else goals_raw
        except json.JSONDecodeError:
            return "[delegate_task: 'goals' must be a JSON array of strings]"
        if not isinstance(goals, list) or not goals:
            return "[delegate_task: 'goals' must be a non-empty list]"
        if len(goals) > MAX_GOALS:
            return f"[delegate_task: too many goals — max {MAX_GOALS}]"
        max_concurrent = max(1, min(int(inp.get("max_concurrent") or DEFAULT_MAX_CONCURRENT), MAX_GOALS))

        results: dict[int, str] = {}
        with ThreadPoolExecutor(max_workers=max_concurrent) as ex:
            futures = {
                ex.submit(_run_subagent, str(g), toolset): i
                for i, g in enumerate(goals)
            }
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    results[idx] = fut.result()
                except Exception as e:
                    log.exception("subagent (orchestrator) failed")
                    results[idx] = f"[crashed: {e}]"

        ordered = [results[i] for i in range(len(goals))]
        body = "\n\n---\n\n".join(
            f"## Result {i + 1}: {goals[i]}\n{ordered[i]}"
            for i in range(len(goals))
        )
        return body[:RESULT_CAP]

    return f"[delegate_task: unknown role '{role}']"
