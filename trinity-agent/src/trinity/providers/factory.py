"""Provider factory — thin wrapper over the provider registry.

This module exists for backward compatibility with call sites that import
``create_provider`` directly. New code should use
``trinity.providers.registry.PROVIDERS.get(name).factory(...)``.
"""
from __future__ import annotations

from trinity.config import AgentConfig, AuthConfig
from trinity.plugins import NotRegistered

from .base import Provider
from .registry import PROVIDERS


def create_provider(
    config: AuthConfig,
    agent_config: AgentConfig | None = None,
    cwd: str | None = None,
) -> Provider:
    """Create the appropriate Provider based on ``config.provider``.

    Raises:
        ValueError: if the provider name is not registered.
        RuntimeError: if the required API key is not set.
    """
    try:
        spec = PROVIDERS.get(config.provider)
    except NotRegistered:
        raise ValueError(
            f"Unknown provider {config.provider!r}. Registered: {PROVIDERS.names()}"
        ) from None

    return spec.factory(config, agent_config, cwd=cwd)
