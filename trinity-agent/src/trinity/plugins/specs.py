"""Typed descriptors for each kind of plugin Trinity accepts.

Providers, tools, and agents each carry different metadata. Giving each
its own dataclass keeps the ``Registry`` payloads strongly typed and
makes ``trinity plugins show`` output richer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProviderSpec:
    """Describes an LLM provider backend.

    ``factory`` is called with ``(auth_config, agent_config, cwd)`` and
    must return a :class:`trinity.providers.base.Provider` instance.
    """

    name: str
    factory: Callable[..., Any]
    description: str = ""
    requires_api_key: bool = True


@dataclass(frozen=True)
class ToolSpec:
    """Describes a tool the agent can call.

    ``handler`` receives ``(input: dict, workspace_root: Path, **context)``
    and returns a string result.
    """

    name: str
    definition: dict[str, Any]
    handler: Callable[..., str]
    subsets: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


@dataclass(frozen=True)
class AgentSpec:
    """Describes an agent persona / track.

    ``kind`` is either ``"conversational"`` (no tools) or
    ``"tool-using"``. ``run`` is the entry function; its signature depends
    on ``kind`` — conversational agents take chat history, tool-using
    agents take task + tool_definitions + tool_executor. Callers inspect
    ``kind`` to decide which keyword arguments to pass.
    """

    name: str
    run: Callable[..., str]
    kind: str  # "conversational" | "tool-using"
    tool_subset: str | None = None
    description: str = ""
