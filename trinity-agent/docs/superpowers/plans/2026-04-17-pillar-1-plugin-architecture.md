# Pillar 1 — Plugin Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Trinity's three existing extension points — providers, tools, agents — from hardcoded string matches and static module-level dicts into typed registries with Python entry-point discovery, so third-party packages can extend Trinity without editing source.

**Architecture:** Introduce a generic `Registry[T]` at `trinity/plugins/registry.py` backed by a dict and augmented with an `importlib.metadata` entry-point scanner. Add three typed spec dataclasses (`ProviderSpec`, `ToolSpec`, `AgentSpec`) to carry the metadata each extension point needs. Migrate existing first-party implementations to register themselves as builtins on import. The existing public symbols (`create_provider`, `TOOL_DEFINITIONS`, `execute_tool`, `BUILDER_TOOLS`, etc.) remain as thin shims so all current call sites keep working.

**Tech Stack:** Python 3.11+, `importlib.metadata.entry_points()` for discovery (stdlib), `pytest` for tests (new dev dep), existing Trinity dependencies only. No new runtime dependencies.

**Scope exclusions:**
- Transport registry — deferred to Pillar 3 (Telegram/Discord/Slack/HTTP). The Transport ABC and chat-worker-pool extraction belong in that plan.
- Memory-backend registry — deferred to Pillar 5 (memory overhaul). The `MemoryBackend` ABC + sqlite/vector backends belong in that plan.
- MCP server integration — deferred to Pillar 2. MCP tools will plug into the `ToolRegistry` created here, so Pillar 1 is the prerequisite.
- Dynamic plugin install/uninstall CLI — `trinity plugins install <pkg>` calls out to pip which is out of scope here. This plan adds only `list` and `show`.

**Blast radius:** Five source files modified, seven new files created, eight new test files. All existing callers continue to work unchanged. The CLI gains one new subcommand tree (`plugins`). No runtime behavior changes for the shipped Telegram bot path.

---

## File structure

### New files
- `src/trinity/plugins/__init__.py` — public imports
- `src/trinity/plugins/registry.py` — `Registry[T]` generic
- `src/trinity/plugins/specs.py` — `ProviderSpec`, `ToolSpec`, `AgentSpec`
- `src/trinity/plugins/discovery.py` — entry-point scanner
- `src/trinity/providers/registry.py` — `PROVIDERS: Registry[ProviderSpec]` with builtins
- `src/trinity/agents/registry.py` — `AGENTS: Registry[AgentSpec]` with builtins
- `tests/__init__.py` — empty
- `tests/conftest.py` — shared pytest fixtures
- `tests/test_plugin_registry.py`
- `tests/test_plugin_discovery.py`
- `tests/test_provider_registry.py`
- `tests/test_tool_registry.py`
- `tests/test_agent_registry.py`
- `tests/test_cli_plugins.py`

### Modified files
- `pyproject.toml` — add `[project.optional-dependencies] dev = ["pytest>=7.0"]`
- `src/trinity/providers/factory.py` — `create_provider` becomes a shim over `PROVIDERS.get(...)`
- `src/trinity/providers/__init__.py` — export `PROVIDERS`
- `src/trinity/tools/registry.py` — rebuild `TOOL_DEFINITIONS`, `execute_tool`, subsets from a `ToolRegistry`
- `src/trinity/cli.py` — add `plugins list` / `plugins show` subcommands
- `CLAUDE.md` — document the plugin system and how to author plugins

---

## Tasks

### Task 1: Bootstrap pytest infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pytest to dev dependencies**

Modify `pyproject.toml` by adding after the existing `[project]` block:

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0"]
```

- [ ] **Step 2: Install dev dependencies**

Run: `source ~/venvs/oefr/bin/activate && pip install -e ".[dev]"`
Expected: `pytest` appears in `pip list` output.

- [ ] **Step 3: Create empty tests package**

Create `tests/__init__.py` with content: (empty file)

- [ ] **Step 4: Create shared conftest**

Create `tests/conftest.py`:

```python
"""Shared pytest fixtures for Trinity tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """A temporary workspace directory with a .trinity subdirectory."""
    trinity = tmp_path / ".trinity"
    trinity.mkdir()
    for sub in ("memory/short-term", "memory/long-term", "memory/permanent",
                "state", "logs", "employees", "knowledge", "sessions",
                "chat-history"):
        (trinity / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path
```

- [ ] **Step 5: Write a smoke test**

Create `tests/test_smoke.py`:

```python
"""Sanity check: the trinity package imports and the test runner works."""
from __future__ import annotations


def test_trinity_imports():
    import trinity
    assert trinity is not None


def test_tmp_workspace_fixture(tmp_workspace):
    assert (tmp_workspace / ".trinity" / "memory").is_dir()
```

- [ ] **Step 6: Run the smoke test**

Run: `cd /home/oghenetejiri/apps/trinity-agent && pytest tests/test_smoke.py -v`
Expected:
```
tests/test_smoke.py::test_trinity_imports PASSED
tests/test_smoke.py::test_tmp_workspace_fixture PASSED
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/__init__.py tests/conftest.py tests/test_smoke.py
git commit -m "test: bootstrap pytest infrastructure"
```

---

### Task 2: Generic Registry[T]

**Files:**
- Create: `src/trinity/plugins/__init__.py`
- Create: `src/trinity/plugins/registry.py`
- Create: `tests/test_plugin_registry.py`

- [ ] **Step 1: Write failing tests for basic register/get**

Create `tests/test_plugin_registry.py`:

```python
"""Tests for the generic plugin registry."""
from __future__ import annotations

import pytest

from trinity.plugins.registry import Registry, AlreadyRegistered, NotRegistered


def test_register_and_get():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "value-a")
    assert reg.get("alpha") == "value-a"


def test_get_unknown_raises():
    reg: Registry[str] = Registry("test.group")
    with pytest.raises(NotRegistered):
        reg.get("missing")


def test_double_register_without_override_raises():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "first")
    with pytest.raises(AlreadyRegistered):
        reg.register("alpha", "second")


def test_double_register_with_override_succeeds():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "first")
    reg.register("alpha", "second", override=True)
    assert reg.get("alpha") == "second"


def test_names_returns_sorted():
    reg: Registry[str] = Registry("test.group")
    reg.register("charlie", "c")
    reg.register("alpha", "a")
    reg.register("bravo", "b")
    assert reg.names() == ["alpha", "bravo", "charlie"]


def test_unregister_removes_entry():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a")
    reg.unregister("alpha")
    assert reg.names() == []
    with pytest.raises(NotRegistered):
        reg.get("alpha")


def test_unregister_unknown_raises():
    reg: Registry[str] = Registry("test.group")
    with pytest.raises(NotRegistered):
        reg.unregister("missing")


def test_source_tracking():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a", source="builtin")
    reg.register("bravo", "b", source="entry_points")
    assert reg.source_of("alpha") == "builtin"
    assert reg.source_of("bravo") == "entry_points"


def test_contains():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a")
    assert "alpha" in reg
    assert "missing" not in reg


def test_items_returns_copy():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a")
    snapshot = reg.items()
    snapshot["beta"] = "b"  # mutate the returned dict
    assert "beta" not in reg  # internal state unaffected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_plugin_registry.py -v`
Expected: All tests fail with `ModuleNotFoundError: No module named 'trinity.plugins'` or similar.

- [ ] **Step 3: Create the plugins package**

Create `src/trinity/plugins/__init__.py`:

```python
"""Plugin infrastructure: generic registry + spec dataclasses + discovery."""
from __future__ import annotations

from .registry import AlreadyRegistered, NotRegistered, Registry

__all__ = ["Registry", "AlreadyRegistered", "NotRegistered"]
```

- [ ] **Step 4: Implement the Registry class**

Create `src/trinity/plugins/registry.py`:

```python
"""Generic named registry with source tracking.

The registry holds name→item mappings and records how each entry arrived
(``"builtin"``, ``"entry_points"``, ``"manual"``). This powers the
``trinity plugins list`` CLI and lets us distinguish first-party defaults
from third-party additions when debugging.
"""
from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class AlreadyRegistered(Exception):
    """Raised when registering a name that already exists without ``override=True``."""


class NotRegistered(KeyError):
    """Raised when looking up a name that is not registered."""


class Registry(Generic[T]):
    """Name→item registry with source tracking.

    ``group`` is the entry-point group name (e.g. ``"trinity.providers"``)
    used by :meth:`discover`.
    """

    def __init__(self, group: str) -> None:
        self.group = group
        self._items: dict[str, T] = {}
        self._sources: dict[str, str] = {}

    def register(
        self,
        name: str,
        item: T,
        *,
        source: str = "manual",
        override: bool = False,
    ) -> None:
        if name in self._items and not override:
            raise AlreadyRegistered(
                f"{self.group}: '{name}' is already registered "
                f"(source={self._sources[name]!r}). "
                f"Pass override=True to replace."
            )
        self._items[name] = item
        self._sources[name] = source

    def unregister(self, name: str) -> None:
        if name not in self._items:
            raise NotRegistered(f"{self.group}: '{name}' is not registered")
        del self._items[name]
        del self._sources[name]

    def get(self, name: str) -> T:
        if name not in self._items:
            raise NotRegistered(
                f"{self.group}: '{name}' is not registered. "
                f"Known: {self.names()}"
            )
        return self._items[name]

    def names(self) -> list[str]:
        return sorted(self._items)

    def items(self) -> dict[str, T]:
        return dict(self._items)

    def source_of(self, name: str) -> str:
        if name not in self._sources:
            raise NotRegistered(f"{self.group}: '{name}' is not registered")
        return self._sources[name]

    def __contains__(self, name: object) -> bool:
        return name in self._items
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_plugin_registry.py -v`
Expected: All ten tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/trinity/plugins/__init__.py src/trinity/plugins/registry.py tests/test_plugin_registry.py
git commit -m "feat(plugins): add generic Registry[T] with source tracking"
```

---

### Task 3: Entry-point discovery

**Files:**
- Create: `src/trinity/plugins/discovery.py`
- Modify: `src/trinity/plugins/registry.py` (add `discover` method)
- Modify: `src/trinity/plugins/__init__.py` (export `DiscoveryError`)
- Create: `tests/test_plugin_discovery.py`

- [ ] **Step 1: Write failing tests for discovery**

Create `tests/test_plugin_discovery.py`:

```python
"""Tests for entry-point discovery on the Registry."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from trinity.plugins.registry import Registry


def _fake_entry_point(name: str, load_returns):
    """Build a stand-in for importlib.metadata.EntryPoint."""
    ep = MagicMock()
    ep.name = name
    ep.load.return_value = load_returns
    return ep


def test_discover_loads_entry_points(monkeypatch):
    reg: Registry[str] = Registry("trinity.fake")
    ep_alpha = _fake_entry_point("alpha", "value-a")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [ep_alpha]
        errors = reg.discover()

    assert errors == []
    assert "alpha" in reg
    assert reg.get("alpha") == "value-a"
    assert reg.source_of("alpha") == "entry_points"


def test_discover_handles_load_failure(monkeypatch):
    reg: Registry[str] = Registry("trinity.fake")
    bad_ep = MagicMock()
    bad_ep.name = "broken"
    bad_ep.load.side_effect = ImportError("boom")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [bad_ep]
        errors = reg.discover()

    assert len(errors) == 1
    assert errors[0][0] == "broken"
    assert "boom" in errors[0][1]
    assert "broken" not in reg


def test_discover_does_not_clobber_existing(monkeypatch):
    reg: Registry[str] = Registry("trinity.fake")
    reg.register("alpha", "builtin-value", source="builtin")
    ep_alpha = _fake_entry_point("alpha", "entry-value")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [ep_alpha]
        errors = reg.discover()

    assert len(errors) == 1
    assert errors[0][0] == "alpha"
    assert "already registered" in errors[0][1].lower()
    # The builtin wins.
    assert reg.get("alpha") == "builtin-value"
    assert reg.source_of("alpha") == "builtin"


def test_discover_with_override_replaces(monkeypatch):
    reg: Registry[str] = Registry("trinity.fake")
    reg.register("alpha", "builtin-value", source="builtin")
    ep_alpha = _fake_entry_point("alpha", "entry-value")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [ep_alpha]
        errors = reg.discover(override=True)

    assert errors == []
    assert reg.get("alpha") == "entry-value"
    assert reg.source_of("alpha") == "entry_points"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_plugin_discovery.py -v`
Expected: All fail with `AttributeError: 'Registry' object has no attribute 'discover'`.

- [ ] **Step 3: Implement the discovery module**

Create `src/trinity/plugins/discovery.py`:

```python
"""Entry-point discovery helpers.

Isolated in its own module so tests can patch :func:`entry_points` cleanly.
"""
from __future__ import annotations

from importlib.metadata import entry_points


def scan(group: str) -> list:
    """Return the entry points registered under ``group``.

    Wraps the stdlib call so tests can monkeypatch a single symbol.
    """
    return list(entry_points(group=group))
```

- [ ] **Step 4: Add `discover` to the Registry**

Modify `src/trinity/plugins/registry.py`. Add the following method to the `Registry` class (at the end, before the closing of the class):

```python
    def discover(self, *, override: bool = False) -> list[tuple[str, str]]:
        """Load entry points registered under ``self.group``.

        Returns a list of ``(name, error_message)`` tuples — one per entry
        point that failed to load or conflicted with an existing builtin
        when ``override`` is False. An empty list means everything
        registered cleanly.
        """
        from .discovery import scan
        from .registry import AlreadyRegistered  # self-reference via package

        errors: list[tuple[str, str]] = []
        for ep in scan(self.group):
            try:
                item = ep.load()
            except Exception as e:
                errors.append((ep.name, f"load failed: {type(e).__name__}: {e}"))
                continue
            try:
                self.register(ep.name, item, source="entry_points", override=override)
            except AlreadyRegistered as e:
                errors.append((ep.name, str(e)))
        return errors
```

Note: the `from .registry import AlreadyRegistered` line is inside the method because Python's AST lets a class refer to its own module via relative import. The exception type is already defined at module level above.

A cleaner version — remove the inner import and just reference the exception directly:

```python
    def discover(self, *, override: bool = False) -> list[tuple[str, str]]:
        """Load entry points registered under ``self.group``.

        Returns ``[(name, error_message), ...]`` — one per entry point that
        failed to load or conflicted with an existing builtin when
        ``override`` is False. An empty list means everything registered.
        """
        from .discovery import scan

        errors: list[tuple[str, str]] = []
        for ep in scan(self.group):
            try:
                item = ep.load()
            except Exception as e:
                errors.append((ep.name, f"load failed: {type(e).__name__}: {e}"))
                continue
            try:
                self.register(ep.name, item, source="entry_points", override=override)
            except AlreadyRegistered as e:
                errors.append((ep.name, str(e)))
        return errors
```

Use the second version. `AlreadyRegistered` is already in scope at module level.

- [ ] **Step 5: Wire the new export**

Modify `src/trinity/plugins/__init__.py` to also export `scan`:

```python
"""Plugin infrastructure: generic registry + spec dataclasses + discovery."""
from __future__ import annotations

from .discovery import scan
from .registry import AlreadyRegistered, NotRegistered, Registry

__all__ = ["Registry", "AlreadyRegistered", "NotRegistered", "scan"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_plugin_discovery.py tests/test_plugin_registry.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/trinity/plugins/discovery.py src/trinity/plugins/registry.py src/trinity/plugins/__init__.py tests/test_plugin_discovery.py
git commit -m "feat(plugins): add entry-point discovery via importlib.metadata"
```

---

### Task 4: Spec dataclasses

**Files:**
- Create: `src/trinity/plugins/specs.py`
- Modify: `src/trinity/plugins/__init__.py` (re-export specs)

- [ ] **Step 1: Create the specs module**

Create `src/trinity/plugins/specs.py`:

```python
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
    agents take tool definitions + executor. Callers inspect ``kind`` to
    decide which keyword arguments to pass.
    """

    name: str
    run: Callable[..., str]
    kind: str  # "conversational" | "tool-using"
    tool_subset: str | None = None
    description: str = ""
```

- [ ] **Step 2: Export specs from package init**

Modify `src/trinity/plugins/__init__.py`:

```python
"""Plugin infrastructure: generic registry + spec dataclasses + discovery."""
from __future__ import annotations

from .discovery import scan
from .registry import AlreadyRegistered, NotRegistered, Registry
from .specs import AgentSpec, ProviderSpec, ToolSpec

__all__ = [
    "Registry",
    "AlreadyRegistered",
    "NotRegistered",
    "scan",
    "AgentSpec",
    "ProviderSpec",
    "ToolSpec",
]
```

- [ ] **Step 3: Verify the package still imports**

Run: `python -c "from trinity.plugins import Registry, ProviderSpec, ToolSpec, AgentSpec; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add src/trinity/plugins/specs.py src/trinity/plugins/__init__.py
git commit -m "feat(plugins): add ProviderSpec, ToolSpec, AgentSpec dataclasses"
```

---

### Task 5: Provider registry

**Files:**
- Create: `src/trinity/providers/registry.py`
- Modify: `src/trinity/providers/factory.py`
- Modify: `src/trinity/providers/__init__.py`
- Create: `tests/test_provider_registry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_provider_registry.py`:

```python
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
        PROVIDERS.unregister("custom-test")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_provider_registry.py -v`
Expected: Import failures (`trinity.providers.registry` does not exist).

- [ ] **Step 3: Create the provider registry**

Create `src/trinity/providers/registry.py`:

```python
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
```

- [ ] **Step 4: Rewrite the factory as a shim**

Replace the entire contents of `src/trinity/providers/factory.py` with:

```python
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
```

- [ ] **Step 5: Export PROVIDERS from the providers package**

Modify `src/trinity/providers/__init__.py` to add the registry:

```python
"""Provider abstraction: Provider ABC, message types, registry, factory."""
from .base import Message, Provider, Response, ToolCall, ToolDef, ToolResult
from .factory import create_provider
from .registry import PROVIDERS

__all__ = [
    "Provider",
    "Message",
    "ToolDef",
    "ToolResult",
    "Response",
    "create_provider",
    "PROVIDERS",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_provider_registry.py -v`
Expected: All five tests PASS.

- [ ] **Step 7: Verify existing call sites still work**

Run: `python -c "from trinity.app import init; from trinity.providers import create_provider, PROVIDERS; print(PROVIDERS.names())"`
Expected: `['anthropic_api', 'anthropic_login', 'claude_sdk', 'openai', 'openrouter']`

- [ ] **Step 8: Commit**

```bash
git add src/trinity/providers/registry.py src/trinity/providers/factory.py src/trinity/providers/__init__.py tests/test_provider_registry.py
git commit -m "feat(providers): route through plugin registry, preserve create_provider shim"
```

---

### Task 6: Tool registry

**Files:**
- Modify: `src/trinity/tools/registry.py` (substantial rewrite, same public surface)
- Create: `tests/test_tool_registry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_tool_registry.py`:

```python
"""Tests for the tool registry migration."""
from __future__ import annotations

from pathlib import Path

import pytest

from trinity.plugins import ToolSpec
from trinity.tools.registry import (
    BUILDER_TOOLS,
    MEMORY_TOOLS,
    RESEARCHER_TOOLS,
    TOOL_DEFINITIONS,
    TOOLS,
    execute_tool,
    get_tools,
)


def test_tool_definitions_still_shaped_as_before():
    # Back-compat contract: list of dicts with name/description/input_schema.
    assert isinstance(TOOL_DEFINITIONS, list)
    for t in TOOL_DEFINITIONS:
        assert set(t.keys()) >= {"name", "description", "input_schema"}


def test_builtin_tools_registered():
    for name in ("read_file", "write_file", "edit_file", "run_command",
                 "git_status", "memory_store", "log_issue", "send_telegram"):
        assert name in TOOLS
        assert isinstance(TOOLS.get(name), ToolSpec)
        assert TOOLS.source_of(name) == "builtin"


def test_subsets_preserved():
    # Core subsets exist and contain the expected anchor tools.
    assert "read_file" in BUILDER_TOOLS
    assert "web_fetch" in RESEARCHER_TOOLS
    assert "memory_search" in MEMORY_TOOLS


def test_get_tools_filters_by_name():
    subset = get_tools(["read_file", "write_file"])
    names = [t["name"] for t in subset]
    assert set(names) == {"read_file", "write_file"}


def test_get_tools_none_returns_all():
    all_tools = get_tools()
    assert len(all_tools) == len(TOOL_DEFINITIONS)


def test_get_tools_unknown_name_skipped():
    # Contract: unknown names are silently skipped, not raised.
    subset = get_tools(["read_file", "does-not-exist"])
    assert [t["name"] for t in subset] == ["read_file"]


def test_execute_tool_unknown_name_raises():
    with pytest.raises(KeyError, match="Unknown tool"):
        execute_tool("nope", {}, Path("/tmp"))


def test_execute_tool_dispatches(tmp_workspace):
    (tmp_workspace / "sample.txt").write_text("hello\nworld")
    result = execute_tool("read_file", {"path": "sample.txt"}, tmp_workspace)
    assert "hello" in result
    assert "world" in result


def test_execute_tool_wraps_exceptions_as_strings(tmp_workspace):
    # Reading a file that does not exist should surface the error as a string,
    # matching the pre-migration contract (agents parse the string).
    result = execute_tool("read_file", {"path": "missing.txt"}, tmp_workspace)
    assert result.lower().startswith("error in read_file")


def test_register_custom_tool(tmp_workspace):
    """A third party can register a tool; it shows up in execute_tool."""

    def handler(inp, ws, **_):
        return f"got {inp['value']}"

    TOOLS.register(
        "test_custom_tool",
        ToolSpec(
            name="test_custom_tool",
            definition={
                "name": "test_custom_tool",
                "description": "Test-only tool",
                "input_schema": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
            },
            handler=handler,
        ),
        source="manual",
    )
    try:
        # The TOOL_DEFINITIONS list is computed from TOOLS — make sure a
        # freshly computed view picks up the new entry.
        from trinity.tools.registry import build_tool_definitions
        assert "test_custom_tool" in [t["name"] for t in build_tool_definitions()]

        result = execute_tool(
            "test_custom_tool", {"value": "xyz"}, tmp_workspace
        )
        assert result == "got xyz"
    finally:
        TOOLS.unregister("test_custom_tool")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tool_registry.py -v`
Expected: Import errors (`TOOLS` and `build_tool_definitions` do not exist).

- [ ] **Step 3: Rewrite the tool registry**

Replace the entire contents of `src/trinity/tools/registry.py` with:

```python
"""Central tool registry.

Tools register as :class:`trinity.plugins.ToolSpec` entries in the module-level
``TOOLS`` registry at import time. Third-party packages can add more via the
``trinity.tools`` entry-point group.

Back-compat exports — every symbol that pre-migration callers use:
  * ``TOOL_DEFINITIONS`` — list of Anthropic-format schema dicts
  * ``BUILDER_TOOLS`` / ``RESEARCHER_TOOLS`` / ``MEMORY_TOOLS`` — name lists
  * ``get_tools(names)`` — filtered definition list
  * ``execute_tool(name, input, workspace_root, **context)`` — dispatcher
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trinity.plugins import Registry, ToolSpec
from trinity.tools import (
    filesystem,
    git,
    knowledge_tools,
    memory_tools,
    search,
    shell,
    telegram_tools,
    web,
)


TOOLS: Registry[ToolSpec] = Registry("trinity.tools")


# ── Builtin tool specs ────────────────────────────────────────────────

_BUILTIN_SPECS: list[ToolSpec] = [
    # Filesystem
    ToolSpec(
        name="read_file",
        definition={
            "name": "read_file",
            "description": (
                "Read a file's contents with line numbers. Returns up to 50 KB. "
                "Path is relative to the workspace root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root.",
                    },
                },
                "required": ["path"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.read_file(inp["path"], ws),
        subsets=("builder", "researcher"),
    ),
    ToolSpec(
        name="write_file",
        definition={
            "name": "write_file",
            "description": (
                "Create or overwrite a file. Creates parent directories "
                "automatically. Path is relative to the workspace root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full file content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.write_file(
            inp["path"], inp["content"], ws
        ),
        subsets=("builder",),
    ),
    ToolSpec(
        name="edit_file",
        definition={
            "name": "edit_file",
            "description": (
                "Find and replace text in an existing file. old_text must appear "
                "exactly once."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find (must appear exactly once).",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.edit_file(
            inp["path"], inp["old_text"], inp["new_text"], ws
        ),
        subsets=("builder",),
    ),
    ToolSpec(
        name="list_directory",
        definition={
            "name": "list_directory",
            "description": (
                "List the contents of a directory, showing types, names, sizes. "
                "Path is relative to workspace root. Use '.' for root."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path relative to workspace root.",
                    },
                },
                "required": ["path"],
            },
        },
        handler=lambda inp, ws, **_: filesystem.list_directory(inp["path"], ws),
        subsets=("builder", "researcher"),
    ),

    # Search
    ToolSpec(
        name="search_files",
        definition={
            "name": "search_files",
            "description": (
                "Find files by glob pattern (e.g. '*.py', '**/*.tsx'). "
                "Returns matching paths. Skips node_modules, .git, __pycache__, .next, dist, build."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search, relative to workspace. Defaults to '.'.",
                    },
                },
                "required": ["pattern"],
            },
        },
        handler=lambda inp, ws, **_: search.search_files(
            inp["pattern"], inp.get("path", "."), ws
        ),
        subsets=("builder", "researcher"),
    ),
    ToolSpec(
        name="search_content",
        definition={
            "name": "search_content",
            "description": (
                "Search file contents using a regex. Returns filename:line:match. "
                "Skips binary files and excluded directories."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search. Defaults to '.'.",
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File extension without the dot (e.g. 'py').",
                    },
                },
                "required": ["pattern"],
            },
        },
        handler=lambda inp, ws, **_: search.search_content(
            inp["pattern"],
            inp.get("path", "."),
            ws,
            file_type=inp.get("file_type", ""),
        ),
        subsets=("builder", "researcher"),
    ),

    # Shell
    ToolSpec(
        name="run_command",
        definition={
            "name": "run_command",
            "description": (
                "Run a shell command via bash and return stdout + stderr. "
                "Default timeout 120s, max 600s."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (workspace-relative or absolute).",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds.",
                    },
                },
                "required": ["command"],
            },
        },
        handler=lambda inp, ws, **_: shell.run_command(
            inp["command"],
            ws,
            cwd=inp.get("cwd", ""),
            timeout=min(inp.get("timeout", 120), 600),
        ),
        subsets=("builder", "researcher"),
    ),

    # Git
    ToolSpec(
        name="git_status",
        definition={
            "name": "git_status",
            "description": "Show the working tree status of the workspace git repo.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        handler=lambda inp, ws, **_: git.git_status(ws),
        subsets=("builder",),
    ),
    ToolSpec(
        name="git_diff",
        definition={
            "name": "git_diff",
            "description": "Show git diff output. Supports --stat, --staged, HEAD~N, paths.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "string",
                        "description": "Arguments passed through to git diff.",
                    },
                },
                "required": [],
            },
        },
        handler=lambda inp, ws, **_: git.git_diff(ws, args=inp.get("args", "")),
        subsets=("builder",),
    ),
    ToolSpec(
        name="git_commit",
        definition={
            "name": "git_commit",
            "description": "Stage the given files and create a commit. Returns the hash.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message."},
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths to stage and commit.",
                    },
                },
                "required": ["message", "files"],
            },
        },
        handler=lambda inp, ws, **_: git.git_commit(
            inp["message"], inp["files"], ws
        ),
        subsets=("builder",),
    ),

    # Web
    ToolSpec(
        name="web_search",
        definition={
            "name": "web_search",
            "description": (
                "Search the web for information. (Not yet implemented — use "
                "run_command with curl as a workaround.)"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                },
                "required": ["query"],
            },
        },
        handler=lambda inp, ws, **_: web.web_search(inp["query"]),
        subsets=("researcher",),
    ),
    ToolSpec(
        name="web_fetch",
        definition={
            "name": "web_fetch",
            "description": (
                "Fetch a URL and return the content as text. Capped at 50 KB, "
                "30-second timeout."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch."},
                },
                "required": ["url"],
            },
        },
        handler=lambda inp, ws, **_: web.web_fetch(inp["url"]),
        subsets=("researcher",),
    ),

    # Telegram
    ToolSpec(
        name="send_telegram",
        definition={
            "name": "send_telegram",
            "description": (
                "Send a message to a configured Telegram group. Group names "
                "come from trinity.toml."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message text (Markdown supported).",
                    },
                    "group": {
                        "type": "string",
                        "description": "Logical group name (from trinity.toml).",
                    },
                },
                "required": ["message", "group"],
            },
        },
        handler=lambda inp, ws, **ctx: telegram_tools.send_telegram(
            inp["message"],
            inp["group"],
            ctx.get("bot_token", ""),
            ctx.get("groups", {}),
        ),
        subsets=("builder", "researcher"),
    ),

    # Memory
    ToolSpec(
        name="memory_store",
        definition=memory_tools.MEMORY_STORE_SCHEMA,
        handler=memory_tools.memory_store,
        subsets=("builder", "researcher", "memory"),
    ),
    ToolSpec(
        name="memory_search",
        definition=memory_tools.MEMORY_SEARCH_SCHEMA,
        handler=memory_tools.memory_search,
        subsets=("builder", "researcher", "memory"),
    ),
    ToolSpec(
        name="memory_forget",
        definition=memory_tools.MEMORY_FORGET_SCHEMA,
        handler=memory_tools.memory_forget,
        subsets=("memory",),
    ),
    ToolSpec(
        name="memory_recall",
        definition=memory_tools.MEMORY_RECALL_SCHEMA,
        handler=memory_tools.memory_recall,
        subsets=("memory",),
    ),
    ToolSpec(
        name="memory_update",
        definition=memory_tools.MEMORY_UPDATE_SCHEMA,
        handler=memory_tools.memory_update,
        subsets=("memory",),
    ),
    ToolSpec(
        name="memory_promote",
        definition=memory_tools.MEMORY_PROMOTE_SCHEMA,
        handler=memory_tools.memory_promote,
        subsets=("memory",),
    ),

    # Knowledge
    ToolSpec(
        name="log_issue",
        definition=knowledge_tools.LOG_ISSUE_SCHEMA,
        handler=knowledge_tools.log_issue,
        subsets=("builder",),
    ),
    ToolSpec(
        name="log_decision",
        definition=knowledge_tools.LOG_DECISION_SCHEMA,
        handler=knowledge_tools.log_decision,
        subsets=("builder",),
    ),
    ToolSpec(
        name="log_audit",
        definition=knowledge_tools.LOG_AUDIT_SCHEMA,
        handler=knowledge_tools.log_audit,
        subsets=("builder",),
    ),
    ToolSpec(
        name="log_lesson",
        definition=knowledge_tools.LOG_LESSON_SCHEMA,
        handler=knowledge_tools.log_lesson,
        subsets=("builder",),
    ),
]

for _spec in _BUILTIN_SPECS:
    TOOLS.register(_spec.name, _spec, source="builtin")

# Third-party tools register themselves via the entry-point group.
TOOLS.discover()


# ── Back-compat API ───────────────────────────────────────────────────

def build_tool_definitions() -> list[dict[str, Any]]:
    """Return the current list of Anthropic-format tool definitions."""
    return [TOOLS.get(name).definition for name in TOOLS.names()]


def _subset(tag: str) -> list[str]:
    return sorted(
        name for name in TOOLS.names()
        if tag in TOOLS.get(name).subsets
    )


# Computed once at import time — third parties that register after import
# should call build_tool_definitions() directly to see fresh state.
TOOL_DEFINITIONS: list[dict[str, Any]] = build_tool_definitions()
BUILDER_TOOLS: list[str] = _subset("builder")
RESEARCHER_TOOLS: list[str] = _subset("researcher")
MEMORY_TOOLS: list[str] = _subset("memory")


def get_tools(names: list[str] | None = None) -> list[dict[str, Any]]:
    """Return Anthropic-format tool definitions for the given names.

    If ``names`` is None, returns all registered definitions. Unknown names
    are silently skipped (back-compat contract).
    """
    if names is None:
        return build_tool_definitions()
    result = []
    for n in names:
        if n in TOOLS:
            result.append(TOOLS.get(n).definition)
    return result


def execute_tool(
    name: str,
    input: dict[str, Any],
    workspace_root: Path,
    **context: Any,
) -> str:
    """Execute a tool by name and return the string result.

    Raises KeyError if the tool is not registered.
    """
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: '{name}'")
    spec = TOOLS.get(name)
    try:
        return spec.handler(input, workspace_root, **context)
    except Exception as e:
        return f"Error in {name}: {type(e).__name__}: {e}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tool_registry.py -v`
Expected: All ten tests PASS.

- [ ] **Step 5: Verify existing call sites still work**

Run: `python -c "from trinity.tools.registry import TOOL_DEFINITIONS, BUILDER_TOOLS, execute_tool; print(len(TOOL_DEFINITIONS), 'tools;', len(BUILDER_TOOLS), 'builder tools')"`
Expected: `23 tools; 14 builder tools`

- [ ] **Step 6: Commit**

```bash
git add src/trinity/tools/registry.py tests/test_tool_registry.py
git commit -m "feat(tools): route tool registry through plugin system, preserve public API"
```

---

### Task 7: Agent registry

**Files:**
- Create: `src/trinity/agents/registry.py`
- Create: `tests/test_agent_registry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agent_registry.py`:

```python
"""Tests for the agent registry."""
from __future__ import annotations

import pytest

from trinity.agents.registry import AGENTS
from trinity.plugins import AgentSpec


def test_three_builtins_registered():
    assert "conversational" in AGENTS
    assert "builder" in AGENTS
    assert "researcher" in AGENTS
    for name in ("conversational", "builder", "researcher"):
        assert AGENTS.source_of(name) == "builtin"


def test_specs_typed():
    for name in AGENTS.names():
        spec = AGENTS.get(name)
        assert isinstance(spec, AgentSpec)
        assert callable(spec.run)
        assert spec.kind in {"conversational", "tool-using"}


def test_conversational_kind():
    assert AGENTS.get("conversational").kind == "conversational"
    assert AGENTS.get("conversational").tool_subset is None


def test_builder_and_researcher_are_tool_using():
    assert AGENTS.get("builder").kind == "tool-using"
    assert AGENTS.get("builder").tool_subset == "builder"
    assert AGENTS.get("researcher").kind == "tool-using"
    assert AGENTS.get("researcher").tool_subset == "researcher"


def test_register_custom_agent():
    def custom(*args, **kwargs):
        return "custom-ran"

    AGENTS.register(
        "test-custom-agent",
        AgentSpec(
            name="test-custom-agent",
            run=custom,
            kind="conversational",
            description="Test-only agent",
        ),
        source="manual",
    )
    try:
        spec = AGENTS.get("test-custom-agent")
        assert spec.run() == "custom-ran"
    finally:
        AGENTS.unregister("test-custom-agent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agent_registry.py -v`
Expected: Import errors (`trinity.agents.registry` does not exist).

- [ ] **Step 3: Create the agent registry**

Create `src/trinity/agents/registry.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_agent_registry.py -v`
Expected: All five tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/trinity/agents/registry.py tests/test_agent_registry.py
git commit -m "feat(agents): add AgentRegistry with conversational, builder, researcher builtins"
```

---

### Task 8: CLI — `trinity plugins list` / `trinity plugins show`

**Files:**
- Modify: `src/trinity/cli.py`
- Create: `tests/test_cli_plugins.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_plugins.py`:

```python
"""Tests for the `trinity plugins` CLI surface."""
from __future__ import annotations

import subprocess
import sys


def _run(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "trinity", *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_plugins_list_without_group_shows_all_groups():
    rc, out, err = _run("plugins", "list")
    assert rc == 0, err
    # Section headings
    assert "providers" in out
    assert "tools" in out
    assert "agents" in out
    # Sample builtins from each group
    assert "claude_sdk" in out
    assert "read_file" in out
    assert "builder" in out


def test_plugins_list_with_group_filters():
    rc, out, err = _run("plugins", "list", "providers")
    assert rc == 0, err
    assert "claude_sdk" in out
    assert "openai" in out
    assert "read_file" not in out  # other groups excluded


def test_plugins_list_unknown_group_errors():
    rc, out, err = _run("plugins", "list", "bogus")
    assert rc != 0
    assert "unknown" in (out + err).lower() or "invalid" in (out + err).lower()


def test_plugins_show_provider():
    rc, out, err = _run("plugins", "show", "providers/claude_sdk")
    assert rc == 0, err
    assert "claude_sdk" in out
    assert "builtin" in out.lower()


def test_plugins_show_unknown_raises():
    rc, out, err = _run("plugins", "show", "providers/missing")
    assert rc != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_plugins.py -v`
Expected: All five tests fail (command `plugins` not recognized by the CLI).

- [ ] **Step 3: Wire the subcommand**

Modify `src/trinity/cli.py`. Immediately after the existing `knowledge` subparser registration (around line 125), add:

```python
    # ── plugins ──────────────────────────────────────────
    p_plug = sub.add_parser("plugins", help="Plugin inspection")
    plug_sub = p_plug.add_subparsers(dest="plug_cmd", required=True)

    p_plug_list = plug_sub.add_parser("list", help="List registered plugins")
    p_plug_list.add_argument(
        "group",
        nargs="?",
        choices=["providers", "tools", "agents"],
        help="Limit output to a single group",
    )

    p_plug_show = plug_sub.add_parser(
        "show", help="Show details for a single plugin (group/name)"
    )
    p_plug_show.add_argument("spec", help="Plugin reference in 'group/name' form")
```

Then, in the dispatch section of `main()` (after the existing `elif args.command == "knowledge":` block), add:

```python
    elif args.command == "plugins":
        _run_plugins(args)
```

Finally, add these helpers at the bottom of the file (just before `if __name__ == "__main__":` if present, else at module end):

```python
def _run_plugins(args):
    """Dispatch `trinity plugins <subcommand>`."""
    if args.plug_cmd == "list":
        _plugins_list(args.group)
    elif args.plug_cmd == "show":
        _plugins_show(args.spec)


def _plugins_list(group: str | None) -> None:
    from trinity.agents.registry import AGENTS
    from trinity.providers.registry import PROVIDERS
    from trinity.tools.registry import TOOLS

    groups = {"providers": PROVIDERS, "tools": TOOLS, "agents": AGENTS}
    if group:
        if group not in groups:
            print(f"Unknown group: {group}. Choose from: {list(groups)}")
            raise SystemExit(2)
        selected = {group: groups[group]}
    else:
        selected = groups

    for label, reg in selected.items():
        print(f"\n{label}:")
        if not reg.names():
            print("  (none registered)")
            continue
        for name in reg.names():
            src = reg.source_of(name)
            desc = getattr(reg.get(name), "description", "") or ""
            if desc:
                print(f"  {name:<28} [{src}]  {desc}")
            else:
                print(f"  {name:<28} [{src}]")


def _plugins_show(spec: str) -> None:
    from trinity.agents.registry import AGENTS
    from trinity.providers.registry import PROVIDERS
    from trinity.tools.registry import TOOLS

    groups = {"providers": PROVIDERS, "tools": TOOLS, "agents": AGENTS}
    if "/" not in spec:
        print(f"Expected 'group/name', got: {spec!r}")
        raise SystemExit(2)
    group, _, name = spec.partition("/")
    if group not in groups:
        print(f"Unknown group: {group}. Choose from: {list(groups)}")
        raise SystemExit(2)
    reg = groups[group]
    if name not in reg:
        print(f"Not registered in {group}: {name!r}")
        print(f"Known: {reg.names()}")
        raise SystemExit(1)
    item = reg.get(name)
    print(f"Group:       {group}")
    print(f"Name:        {name}")
    print(f"Source:      {reg.source_of(name)}")
    for attr in ("description", "kind", "tool_subset", "requires_api_key"):
        if hasattr(item, attr):
            value = getattr(item, attr)
            if value not in (None, ""):
                print(f"{attr.replace('_', ' ').title() + ':':<12} {value}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli_plugins.py -v`
Expected: All five tests PASS.

- [ ] **Step 5: Exercise the CLI manually**

Run: `python -m trinity plugins list`
Expected: Sections for providers, tools, agents — each listing their builtins with `[builtin]` source tags.

Run: `python -m trinity plugins show providers/claude_sdk`
Expected: Name, source, description, `requires_api_key: False`.

- [ ] **Step 6: Commit**

```bash
git add src/trinity/cli.py tests/test_cli_plugins.py
git commit -m "feat(cli): add 'trinity plugins list|show' for plugin inspection"
```

---

### Task 9: Documentation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Append a Plugin Architecture section**

Open `CLAUDE.md` and insert a new section after the existing `### Tool System (tools/)` section:

```markdown
### Plugin Architecture (plugins/)

Trinity routes three extension points through a shared registry layer:
- **Providers** (`trinity.providers.registry.PROVIDERS`) — LLM backends.
- **Tools** (`trinity.tools.registry.TOOLS`) — functions the agent can call.
- **Agents** (`trinity.agents.registry.AGENTS`) — tracks (conversational vs. tool-using).

All three are instances of the generic `Registry[T]` in `trinity/plugins/registry.py`. First-party implementations register as builtins at import time; third parties declare an entry-point group in their `pyproject.toml`:

```toml
[project.entry-points."trinity.providers"]
my_provider = "mypkg:provider_spec"

[project.entry-points."trinity.tools"]
query_postgres = "mypkg:postgres_tool_spec"
```

The entry-point value must resolve to a `ProviderSpec`, `ToolSpec`, or `AgentSpec` (or a callable that returns one — entry points return whatever their target is). Conflicts with builtins are rejected unless the registry's `override=True` is used.

Inspect what's registered with `trinity plugins list` / `trinity plugins show <group>/<name>`.
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: All tests PASS (smoke + registry + discovery + providers + tools + agents + CLI plugins).

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: describe plugin architecture in CLAUDE.md"
```

---

## Self-review

**Spec coverage:**
- Generic registry → Task 2 ✓
- Entry-point discovery → Task 3 ✓
- Spec dataclasses → Task 4 ✓
- Providers migrated → Task 5 ✓
- Tools migrated → Task 6 ✓
- Agents migrated → Task 7 ✓
- CLI inspection → Task 8 ✓
- Docs → Task 9 ✓
- Migration plan for existing first-party code → Tasks 5, 6, 7 (each includes the migration; each preserves existing public API)
- Tight blast radius → no new runtime deps, no changes to message flow, all public symbols preserved
- Transports + memory-backends explicitly deferred → stated in scope exclusions

**Placeholder scan:** No TBDs, no "handle appropriately," no "similar to task N" references. Every code block is complete. Every test has an assertion. Every command has an expected result.

**Type consistency:**
- `Registry[T]`: `register/unregister/get/names/items/source_of/discover/__contains__` — same signatures used across tests and usage.
- `ProviderSpec(name, factory, description, requires_api_key)` — used identically in Task 4 (define) and Task 5 (tests + builtin registrations).
- `ToolSpec(name, definition, handler, subsets, description)` — same across Task 4 and Task 6.
- `AgentSpec(name, run, kind, tool_subset, description)` — same across Task 4 and Task 7.
- `TOOLS`, `PROVIDERS`, `AGENTS` variable names — stable across tests and CLI wiring.

---

## Execution notes

- **Isolation:** Running this in a `git worktree` is recommended but not required. The changes are additive + shim-based, so a rollback via `git revert` is clean.
- **Follow-ups not in scope:**
  - `trinity plugins install <pkg>` (calls `pip install`) — future UX polish.
  - Transport registry (Pillar 3).
  - Memory-backend registry (Pillar 5).
  - MCP tool-source plugin (Pillar 2, drops into `TOOLS` created here).
- **Deferred test coverage:** This plan bootstraps pytest and adds focused registry tests. It does NOT backfill tests for the rest of the codebase. Pillar 4 adds the safety-rails test coverage; broader coverage comes opportunistically.
