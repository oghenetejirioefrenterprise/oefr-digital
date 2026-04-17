"""Tests for the provider registry and factory shim."""
from __future__ import annotations

import pytest

from trinity.config import AuthConfig, AgentConfig
from trinity.plugins import ProviderSpec
from trinity.providers.registry import PROVIDERS


def test_builtins_registered():
    # All four first-party providers must be registered as builtins.
    assert "claude_sdk" in PROVIDERS
    assert "anthropic_api" in PROVIDERS
    assert "openai" in PROVIDERS
    assert "openrouter" in PROVIDERS
    for name in ("claude_sdk", "anthropic_api", "openai", "openrouter"):
        assert PROVIDERS.source_of(name) == "builtin"


def test_builtins_are_provider_specs():
    for name in PROVIDERS.names():
        spec = PROVIDERS.get(name)
        assert isinstance(spec, ProviderSpec)
        assert callable(spec.factory)
        assert spec.name == name


def test_create_provider_unknown_raises_value_error():
    from trinity.providers.factory import create_provider

    auth = AuthConfig(provider="bogus")
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider(auth, AgentConfig())


def test_create_provider_missing_key_raises_runtime_error(monkeypatch):
    from trinity.providers.factory import create_provider

    # openai requires an API key; clear the env var.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    auth = AuthConfig(provider="openai", api_key_env="OPENAI_API_KEY")
    with pytest.raises(RuntimeError, match="API key not found"):
        create_provider(auth, AgentConfig())


def test_register_custom_provider_via_registry():
    """A third party can register a custom provider without editing source."""
    calls = {}

    def custom_factory(auth, agent_cfg, cwd=None):
        calls["made"] = True
        return object()

    PROVIDERS.register(
        "custom-test",
        ProviderSpec(
            name="custom-test",
            factory=custom_factory,
            description="Test provider",
            requires_api_key=False,
        ),
        source="manual",
        override=True,
    )
    try:
        from trinity.providers.factory import create_provider
        auth = AuthConfig(provider="custom-test")
        create_provider(auth, AgentConfig())
        assert calls["made"] is True
    finally:
        # Guard protects the singleton from test-order contamination if
        # register() raised before the entry was added.
        if "custom-test" in PROVIDERS:
            PROVIDERS.unregister("custom-test")
