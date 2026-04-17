"""Agent registry — named tracks Trinity can route a message through.

All three first-party agents register as builtins at import time.
Third-party agents (domain-specific workflows) can register via the
``trinity.agents`` entry-point group.

The agent signatures differ: conversational agents take chat_history +
new_message; tool-using agents take task + tool_definitions +
tool_executor. Callers inspect ``AgentSpec.kind`` to decide which
keyword arguments to pass.
"""
from __future__ import annotations

from trinity.agents import builder, conversational, researcher
from trinity.plugins import AgentSpec, Registry

AGENTS: Registry[AgentSpec] = Registry("trinity.agents")

AGENTS.register(
    "conversational",
    AgentSpec(
        name="conversational",
        run=conversational.run,
        kind="conversational",
        description=(
            "Single API call, no tools. Fast path for chat-style messages."
        ),
    ),
    source="builtin",
)

AGENTS.register(
    "builder",
    AgentSpec(
        name="builder",
        run=builder.run,
        kind="tool-using",
        tool_subset="builder",
        description=(
            "Full agentic loop with filesystem, shell, git, and knowledge tools."
        ),
    ),
    source="builtin",
)

AGENTS.register(
    "researcher",
    AgentSpec(
        name="researcher",
        run=researcher.run,
        kind="tool-using",
        tool_subset="researcher",
        description=(
            "Read-only filesystem + web tools. For information-gathering cycles."
        ),
    ),
    source="builtin",
)

# Third-party agents register themselves via the entry-point group.
AGENTS.discover()
