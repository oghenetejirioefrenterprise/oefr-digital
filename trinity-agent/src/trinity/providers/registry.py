"""Provider registry — holds ProviderSpec entries keyed by name.

All four first-party providers register here at import time. Third-party
providers join via the ``trinity.providers`` entry-point group.
"""
from __future__ import annotations

from trinity.plugins import ProviderSpec, Registry

PROVIDERS: Registry[ProviderSpec] = Registry("trinity.providers")


# ── Builtin factories ─────────────────────────────────────────────────
# Each factory receives ``(auth, agent_config, cwd)`` and must return a
# Provider instance. API-key checks happen inside each factory.

def _claude_sdk_factory(auth, agent_config, cwd=None):
    from .claude_sdk_provider import ClaudeSDKProvider
    max_turns = agent_config.max_turns if agent_config else 30
    return ClaudeSDKProvider(max_turns=max_turns, cwd=cwd)


def _anthropic_factory(auth, agent_config, cwd=None):
    from .anthropic_provider import AnthropicProvider
    api_key = auth.get_api_key()
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {auth.api_key_env} environment variable."
        )
    return AnthropicProvider(api_key=api_key)


def _openai_factory(auth, agent_config, cwd=None):
    from .openai_provider import OpenAIProvider
    api_key = auth.get_api_key()
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {auth.api_key_env} environment variable."
        )
    return OpenAIProvider(api_key=api_key)


def _openrouter_factory(auth, agent_config, cwd=None):
    from .openrouter_provider import OpenRouterProvider
    api_key = auth.get_api_key()
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {auth.api_key_env} environment variable."
        )
    base_url = auth.base_url or "https://openrouter.ai/api/v1"
    return OpenRouterProvider(api_key=api_key, base_url=base_url)


# ── Register builtins ─────────────────────────────────────────────────

PROVIDERS.register(
    "claude_sdk",
    ProviderSpec(
        name="claude_sdk",
        factory=_claude_sdk_factory,
        description="Claude Agent SDK — runs its own tool loop, has built-in tools.",
        requires_api_key=False,
    ),
    source="builtin",
)

PROVIDERS.register(
    "anthropic_api",
    ProviderSpec(
        name="anthropic_api",
        factory=_anthropic_factory,
        description="Anthropic Messages API (direct).",
        requires_api_key=True,
    ),
    source="builtin",
)

# Alias accepted in older configs.
PROVIDERS.register(
    "anthropic_login",
    ProviderSpec(
        name="anthropic_login",
        factory=_anthropic_factory,
        description="Alias for anthropic_api.",
        requires_api_key=True,
    ),
    source="builtin",
)

PROVIDERS.register(
    "openai",
    ProviderSpec(
        name="openai",
        factory=_openai_factory,
        description="OpenAI Chat Completions API.",
        requires_api_key=True,
    ),
    source="builtin",
)

PROVIDERS.register(
    "openrouter",
    ProviderSpec(
        name="openrouter",
        factory=_openrouter_factory,
        description="OpenRouter (OpenAI-compatible multi-model gateway).",
        requires_api_key=True,
    ),
    source="builtin",
)

# Third-party providers register themselves via the entry-point group.
PROVIDERS.discover()
