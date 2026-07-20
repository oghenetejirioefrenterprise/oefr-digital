# Per-Agent LLM Switcher (`/model`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Trinity's read-only Telegram `/model` command into an inline-keyboard wizard that sets provider/model/reasoning-effort per agent (`/model` targets `trinity`; `/model@<agent>` targets a persona), persisted globally and honored by both the Telegram bot and cron cycles.

**Architecture:** A persisted JSON overlay (`agent-models.json`) maps each agent to `{provider, model, effort}`, layered over the env defaults in `config.py`. A new `runtime_config.resolve_agent_llm(agent)` reads that overlay at call time; `run_agent` / `run_agent_streaming` / `run_agent_sdk` dispatch on the resolved provider instead of the import-time `TRINITY_PROVIDER` constant. A new pure `model_switcher.py` owns the wizard (callback-data codec, keyboards, step logic); `telegram_bot.py` adds the Telegram transport (inline keyboards + callback queries) and wires the command.

**Tech Stack:** Python 3.12, `pytest` (+ `pytest-asyncio` already used), Telegram Bot API over `requests`, subprocess-driven provider CLIs (Claude/Codex/Grok).

## Global Constraints

- Python target: 3.12; use `from __future__ import annotations`.
- Tests live in `trinity/tests/`, use `pytest`, and bootstrap imports with `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` then bare-name imports (`import agent`, `import runtime_config`).
- Tests must NEVER read or write the real state file — always monkeypatch the state path to a `tmp_path`.
- Persist writes atomically: temp file + `os.replace` (mirror `agent.py` `_open_provider_breaker`).
- Reads of the overlay must tolerate missing/corrupt files and fall back to env defaults — never raise.
- Telegram `callback_data` must stay ≤ 64 bytes.
- Callback queries are guarded by the SAME TJ-only allowlist as messages (`AccessControl.allowed_users`).
- Valid agent keys = `agent.PERSONA_OVERRIDES` keys ∪ `{"trinity"}`.
- The Claude `--print` path takes no reasoning-effort knob; its wizard skips the effort step.
- Env defaults (in `config.py`): `TRINITY_PROVIDER` (default `"claude"`), `TRINITY_MODEL` (default `"claude-fable-5"`), `TRINITY_REASONING_EFFORT` (default `"high"`).
- Commit after every task with a message scoped `feat(trinity): …` / `test(trinity): …`, ending with the repo's required trailers:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi
  ```

---

### Task 1: Model catalog & switcher constants in `config.py`

**Files:**
- Modify: `trinity/config.py` (append after the fallback/model block, ~line 92)
- Test: `trinity/tests/test_model_catalog.py`

**Interfaces:**
- Produces:
  - `MODEL_CATALOG: dict[str, list[tuple[str, str]]]` — provider → `[(model_id, label)]`
  - `PROVIDER_SUPPORTS_EFFORT: dict[str, bool]`
  - `PROVIDER_LABELS: dict[str, str]` — short button label
  - `PROVIDER_DISPLAY: dict[str, str]` — long display name
  - `EFFORT_LEVELS: list[str]`
  - `AGENT_MODELS_STATE: Path`

- [ ] **Step 1: Write the failing test**

Create `trinity/tests/test_model_catalog.py`:

```python
"""Integrity checks for the /model switcher catalog constants."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


def test_every_provider_has_labels_and_effort_flag():
    for provider in config.MODEL_CATALOG:
        assert provider in config.PROVIDER_LABELS
        assert provider in config.PROVIDER_DISPLAY
        assert provider in config.PROVIDER_SUPPORTS_EFFORT


def test_every_provider_has_at_least_one_model():
    for provider, models in config.MODEL_CATALOG.items():
        assert models, f"{provider} has no models"
        for entry in models:
            assert len(entry) == 2
            model_id, label = entry
            assert isinstance(model_id, str) and model_id
            assert isinstance(label, str) and label


def test_claude_does_not_support_effort():
    assert config.PROVIDER_SUPPORTS_EFFORT["claude"] is False
    assert config.PROVIDER_SUPPORTS_EFFORT["codex"] is True
    assert config.PROVIDER_SUPPORTS_EFFORT["grok"] is True


def test_effort_levels_and_state_path():
    assert config.EFFORT_LEVELS == ["low", "medium", "high"]
    assert config.AGENT_MODELS_STATE.name == "agent-models.json"
    assert config.AGENT_MODELS_STATE.parent.name == "state"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "trinity" && python -m pytest tests/test_model_catalog.py -v`
Expected: FAIL — `AttributeError: module 'config' has no attribute 'MODEL_CATALOG'`

- [ ] **Step 3: Add the constants to `config.py`**

Insert immediately after the `TRINITY_FAILOVER_COOLDOWN_SECONDS = ...` block (before `GROK_BIN = ...`, ~line 96):

```python
# ── /model switcher catalog ──────────────────────────────────────
# provider -> [(model_id, human_label)]. Editing this list is the only
# change needed to offer a new model in the Telegram /model switcher.
MODEL_CATALOG: dict[str, list[tuple[str, str]]] = {
    "claude": [
        ("claude-fable-5", "Fable 5"),
        ("claude-opus-4-8", "Opus 4.8"),
        ("claude-sonnet-5", "Sonnet 5"),
        ("claude-haiku-4-5-20251001", "Haiku 4.5"),
    ],
    "codex": [
        ("gpt-5.6-sol", "gpt-5.6-sol"),
        ("gpt-5.6", "gpt-5.6"),
    ],
    "grok": [
        ("grok-4.5", "Grok 4.5"),
    ],
}

# Providers whose CLIs accept a reasoning-effort knob. Claude's --print
# path does not, so its wizard skips the effort step.
PROVIDER_SUPPORTS_EFFORT: dict[str, bool] = {
    "claude": False, "codex": True, "grok": True,
}

# Short labels for inline-keyboard buttons.
PROVIDER_LABELS: dict[str, str] = {
    "claude": "Claude", "codex": "Codex", "grok": "Grok",
}

# Long display names for confirmation lines.
PROVIDER_DISPLAY: dict[str, str] = {
    "claude": "Anthropic Claude",
    "codex": "OpenAI Codex",
    "grok": "xAI Grok",
}

# Reasoning-effort levels offered in the switcher (codex/grok only).
EFFORT_LEVELS: list[str] = ["low", "medium", "high"]

# Persisted per-agent LLM assignments (overlay on the env defaults above).
AGENT_MODELS_STATE = WORKSPACE / "state" / "agent-models.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "trinity" && python -m pytest tests/test_model_catalog.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add trinity/config.py trinity/tests/test_model_catalog.py
git commit -m "feat(trinity): add /model switcher catalog constants

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi"
```

---

### Task 2: `runtime_config.py` — per-agent LLM resolver & persistence

**Files:**
- Create: `trinity/runtime_config.py`
- Test: `trinity/tests/test_runtime_config.py`

**Interfaces:**
- Consumes: `config.MODEL_CATALOG`, `config.AGENT_MODELS_STATE`, `config.TRINITY_PROVIDER/MODEL/REASONING_EFFORT`
- Produces:
  - `resolve_agent_llm(agent: str | None) -> tuple[str, str, str]` → `(provider, model, effort)`
  - `set_agent_llm(agent: str, provider: str, model: str, effort: str) -> None`
  - `reset_agent_llm(agent: str) -> None`
  - `load_overrides() -> dict`
  - `DEFAULT_AGENT = "trinity"`

- [ ] **Step 1: Write the failing test**

Create `trinity/tests/test_runtime_config.py`:

```python
"""Overlay/persistence behavior for per-agent LLM assignments."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import runtime_config  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    state = tmp_path / "state" / "agent-models.json"
    monkeypatch.setattr(runtime_config, "AGENT_MODELS_STATE", state)
    # Deterministic env defaults, independent of the shell.
    monkeypatch.setattr(runtime_config, "TRINITY_PROVIDER", "claude")
    monkeypatch.setattr(runtime_config, "TRINITY_MODEL", "claude-fable-5")
    monkeypatch.setattr(runtime_config, "TRINITY_REASONING_EFFORT", "high")
    return state


def test_absent_agent_falls_back_to_env_defaults():
    assert runtime_config.resolve_agent_llm("morpheus") == (
        "claude", "claude-fable-5", "high",
    )


def test_none_agent_resolves_to_trinity():
    assert runtime_config.resolve_agent_llm(None) == (
        "claude", "claude-fable-5", "high",
    )


def test_set_then_resolve_roundtrip():
    runtime_config.set_agent_llm("morpheus", "grok", "grok-4.5", "high")
    assert runtime_config.resolve_agent_llm("morpheus") == (
        "grok", "grok-4.5", "high",
    )
    # Other agents untouched.
    assert runtime_config.resolve_agent_llm("oracle")[0] == "claude"


def test_partial_entry_fills_missing_effort_from_default():
    runtime_config.set_agent_llm("oracle", "codex", "gpt-5.6", "low")
    data = runtime_config.load_overrides()
    del data["oracle"]["effort"]
    runtime_config._write(data)
    provider, model, effort = runtime_config.resolve_agent_llm("oracle")
    assert (provider, model) == ("codex", "gpt-5.6")
    assert effort == "high"  # filled from default


def test_reset_restores_default():
    runtime_config.set_agent_llm("neo", "grok", "grok-4.5", "medium")
    runtime_config.reset_agent_llm("neo")
    assert runtime_config.resolve_agent_llm("neo") == (
        "claude", "claude-fable-5", "high",
    )


def test_corrupt_file_falls_back(_isolate_state):
    _isolate_state.parent.mkdir(parents=True, exist_ok=True)
    _isolate_state.write_text("{not json", encoding="utf-8")
    assert runtime_config.load_overrides() == {}
    assert runtime_config.resolve_agent_llm("trinity")[0] == "claude"


def test_unknown_provider_in_entry_falls_back():
    runtime_config.set_agent_llm("neo", "grok", "grok-4.5", "high")
    data = runtime_config.load_overrides()
    data["neo"]["provider"] = "bogus"
    runtime_config._write(data)
    assert runtime_config.resolve_agent_llm("neo") == (
        "claude", "claude-fable-5", "high",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "trinity" && python -m pytest tests/test_runtime_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'runtime_config'`

- [ ] **Step 3: Create `trinity/runtime_config.py`**

```python
#!/usr/bin/env python3
"""Per-agent LLM assignment overlay for Trinity.

The Telegram /model switcher writes an ``agent -> {provider, model, effort}``
map to ``AGENT_MODELS_STATE``. Dispatch resolves each agent's LLM at call time
by overlaying that map on the env defaults from ``config``. Agents absent from
the file fall back to the env baseline, so deleting the file restores pure env
behavior.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (  # noqa: E402
    AGENT_MODELS_STATE,
    MODEL_CATALOG,
    TRINITY_MODEL,
    TRINITY_PROVIDER,
    TRINITY_REASONING_EFFORT,
)

DEFAULT_AGENT = "trinity"


def _agent_key(agent: str | None) -> str:
    return agent or DEFAULT_AGENT


def load_overrides() -> dict:
    """Return the persisted overlay, or {} if missing/corrupt."""
    try:
        data = json.loads(AGENT_MODELS_STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def resolve_agent_llm(agent: str | None) -> tuple[str, str, str]:
    """Return (provider, model, effort) for an agent.

    Overlays the persisted assignment on the env defaults. A partial entry
    fills missing keys from the defaults. An unknown provider falls back
    wholesale to the env baseline.
    """
    entry = load_overrides().get(_agent_key(agent), {})
    provider = entry.get("provider") or TRINITY_PROVIDER
    if provider not in MODEL_CATALOG:
        return TRINITY_PROVIDER, TRINITY_MODEL, TRINITY_REASONING_EFFORT
    model = entry.get("model") or (
        TRINITY_MODEL if provider == TRINITY_PROVIDER
        else MODEL_CATALOG[provider][0][0]
    )
    effort = entry.get("effort") or TRINITY_REASONING_EFFORT
    return provider, model, effort


def set_agent_llm(agent: str, provider: str, model: str, effort: str) -> None:
    """Persist one agent's assignment atomically."""
    data = load_overrides()
    data[_agent_key(agent)] = {
        "provider": provider,
        "model": model,
        "effort": effort,
    }
    _write(data)


def reset_agent_llm(agent: str) -> None:
    """Remove one agent's override, restoring env defaults."""
    data = load_overrides()
    if data.pop(_agent_key(agent), None) is not None:
        _write(data)


def _write(data: dict) -> None:
    AGENT_MODELS_STATE.parent.mkdir(parents=True, exist_ok=True)
    pending = AGENT_MODELS_STATE.with_suffix(".json.tmp")
    pending.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, AGENT_MODELS_STATE)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "trinity" && python -m pytest tests/test_runtime_config.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add trinity/runtime_config.py trinity/tests/test_runtime_config.py
git commit -m "feat(trinity): per-agent LLM resolver and persistence

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi"
```

---

### Task 3: Parameterize model + effort through the provider paths in `agent.py`

Behavior is preserved via defaults — this task adds parameters without changing dispatch yet. This makes Task 4's flip a small, low-risk change.

**Files:**
- Modify: `trinity/agent.py` — command builders and run functions
- Test: `trinity/tests/test_provider_params.py`

**Interfaces:**
- Produces (new/extended signatures):
  - `_codex_command(model: str | None = None, effort: str | None = None, streaming: bool = False)`
  - `_grok_command(prompt_file, max_turns=30, streaming=False, model=None, effort=None)`
  - `_run_agent_codex(..., model=None, effort=None)`
  - `_run_agent_grok(..., model=None, effort=None)`
  - `_run_agent_streaming_codex(task, persona=None, on_event=None, model=None, effort=None)`
  - `_run_agent_streaming_grok(task, persona=None, on_event=None, model=None, effort=None)`
  - `_run_agent_claude(..., model=None)` and `_run_agent_streaming_claude(task, persona=None, on_event=None, model=None)` — both now pass `--model` when `model` is set.

- [ ] **Step 1: Write the failing test**

Create `trinity/tests/test_provider_params.py`:

```python
"""Model/effort parameters reach the provider CLI command lines."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402


def test_codex_command_uses_model_and_effort():
    cmd = agent._codex_command(model="gpt-5.6", effort="low")
    assert "gpt-5.6" in cmd
    assert any('model_reasoning_effort="low"' in part for part in cmd)


def test_codex_command_defaults_to_env_when_unset():
    cmd = agent._codex_command()
    assert agent.TRINITY_MODEL in cmd
    assert any(
        f'model_reasoning_effort="{agent.TRINITY_REASONING_EFFORT}"' in part
        for part in cmd
    )


def test_grok_command_uses_model_and_effort():
    cmd = agent._grok_command("/tmp/p.md", model="grok-4.5", effort="medium")
    assert "grok-4.5" in cmd
    i = cmd.index("--reasoning-effort")
    assert cmd[i + 1] == "medium"


def test_claude_command_includes_model_flag_when_set(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(agent.subprocess, "run", fake_run)
    monkeypatch.setattr(agent, "load_identity", lambda: "id")
    monkeypatch.setattr(agent, "load_daily_context", lambda: "ctx")
    monkeypatch.setattr(agent, "_log_session", lambda *a, **k: None)

    agent._run_agent_claude("hi", model="claude-opus-4-8", print_output=False)
    cmd = captured["cmd"]
    i = cmd.index("--model")
    assert cmd[i + 1] == "claude-opus-4-8"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "trinity" && python -m pytest tests/test_provider_params.py -v`
Expected: FAIL — `_codex_command()` has no `effort` kwarg / `--model` not in Claude command.

- [ ] **Step 3: Edit `_codex_command`**

Replace the function (currently at `agent.py:940`):

```python
def _codex_command(
    model: str | None = None,
    effort: str | None = None,
    streaming: bool = False,
) -> list[str]:
    """Build the non-interactive Codex invocation used by Trinity."""
    command = [
        CODEX_BIN, "exec", "--ephemeral",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "--model", model or TRINITY_MODEL,
        "-c", f'model_reasoning_effort="{effort or TRINITY_REASONING_EFFORT}"',
        "-C", str(WORKSPACE),
    ]
    if streaming:
        command.append("--json")
    command.append("-")
    return command
```

- [ ] **Step 4: Edit `_run_agent_codex`**

Change the signature and the command call. Signature (currently `agent.py:958`) becomes:

```python
def _run_agent_codex(
    task: str,
    persona: str | None = None,
    max_turns: int = 30,
    print_output: bool = True,
    lightweight: bool = False,
    model: str | None = None,
    effort: str | None = None,
) -> str:
```

Inside, replace the `_codex_command(model=effective_model)` call with:

```python
        result = subprocess.run(
            _codex_command(model=effective_model, effort=effort), input=full_prompt,
            capture_output=True, text=True, timeout=CLAUDE_TIMEOUT,
            cwd=str(WORKSPACE), env=_shell_env(),
        )
```

- [ ] **Step 5: Edit `_run_agent_streaming_codex`**

Signature (currently `agent.py:994`) becomes:

```python
def _run_agent_streaming_codex(
    task: str,
    persona: str | None = None,
    on_event: callable = None,
    model: str | None = None,
    effort: str | None = None,
) -> str:
```

Replace the `_build_full_prompt(...)` call's `runtime_model=TRINITY_MODEL` with `runtime_model=model or TRINITY_MODEL`, and the `_codex_command(streaming=True)` call with `_codex_command(model=model, effort=effort, streaming=True)`:

```python
    full_prompt = _build_full_prompt(
        task, persona, lightweight=False,
        runtime_provider="codex", runtime_model=model or TRINITY_MODEL,
    )
    proc = None
    try:
        proc = subprocess.Popen(
            _codex_command(model=model, effort=effort, streaming=True),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(WORKSPACE), env=_shell_env(),
        )
```

- [ ] **Step 6: Edit `_grok_command`**

Replace the function (currently `agent.py:1039`):

```python
def _grok_command(prompt_file: str, max_turns: int = 30,
                  streaming: bool = False, model: str | None = None,
                  effort: str | None = None) -> list[str]:
    """Build the non-interactive Grok invocation used by Trinity."""
    return [
        GROK_BIN,
        "--prompt-file", prompt_file,
        "--model", model or TRINITY_MODEL,
        "--reasoning-effort", effort or TRINITY_REASONING_EFFORT,
        "--permission-mode", "bypassPermissions",
        "--cwd", str(WORKSPACE),
        "--output-format", "streaming-json" if streaming else "plain",
        "--max-turns", str(max_turns),
        "--check",
    ]
```

- [ ] **Step 7: Edit `_run_agent_grok` and `_run_agent_streaming_grok`**

`_run_agent_grok` (currently `agent.py:1057`): add `effort: str | None = None` to the signature (after `model`), and change its command build to pass effort:

```python
        result = subprocess.run(
            _grok_command(prompt_path, max_turns=max_turns,
                          model=effective_model, effort=effort),
            capture_output=True, text=True, timeout=CLAUDE_TIMEOUT,
            cwd=str(WORKSPACE), env=_shell_env(),
        )
```

`_run_agent_streaming_grok` (currently `agent.py:1110`): add `model: str | None = None, effort: str | None = None` to the signature (after `on_event`), change the prompt build to `runtime_model=model or TRINITY_MODEL`, and the Popen command to:

```python
        proc = subprocess.Popen(
            _grok_command(prompt_path, streaming=True, model=model, effort=effort),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(WORKSPACE), env=_shell_env(),
        )
```

- [ ] **Step 8: Edit the Claude paths to pass `--model`**

`_run_agent_claude` (currently `agent.py:433`): add `model: str | None = None` to the signature (after `lightweight`). Replace the CLI arg list in its `subprocess.run(...)` with a built command that inserts `--model` when set:

```python
        cmd = [CLAUDE_BIN, "--permission-mode", CLAUDE_PERMISSION_MODE, "--print"]
        if model:
            cmd += ["--model", model]
        cmd.append("-")
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
            cwd=str(WORKSPACE),
            env=_shell_env(),
        )
```

`_run_agent_streaming_claude` (currently `agent.py:547`): add `model: str | None = None` to the signature (after `on_event`). Replace its `subprocess.Popen([...])` arg list with:

```python
        cmd = [
            CLAUDE_BIN,
            "--permission-mode", CLAUDE_PERMISSION_MODE,
            "--print",
            "--output-format", "stream-json",
            "--verbose",
        ]
        if model:
            cmd += ["--model", model]
        cmd.append("-")
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(WORKSPACE),
            env=_shell_env(),
        )
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd "trinity" && python -m pytest tests/test_provider_params.py tests/test_sdk_diagnostics.py -v`
Expected: PASS (new tests green; existing SDK diagnostics unbroken)

- [ ] **Step 10: Commit**

```bash
git add trinity/agent.py trinity/tests/test_provider_params.py
git commit -m "feat(trinity): thread model+effort through provider command paths

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi"
```

---

### Task 4: Dispatch on the resolved per-agent LLM in `agent.py`

**Files:**
- Modify: `trinity/agent.py` — `run_agent`, `run_agent_streaming`, `run_agent_sdk`, `_dispatch_provider_sdk`
- Test: `trinity/tests/test_dispatch_routing.py`

**Interfaces:**
- Consumes: `runtime_config.resolve_agent_llm` (imported into `agent`), the Task 3 provider signatures.
- Produces: `run_agent` / `run_agent_streaming` / `run_agent_sdk` route on the resolved provider and pass resolved `model`/`effort`.

- [ ] **Step 1: Write the failing test**

Create `trinity/tests/test_dispatch_routing.py`:

```python
"""run_agent* dispatch on the per-agent resolved provider, not the env const."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402


def _capture(monkeypatch, name):
    calls = {}

    def fake(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return "OK"

    monkeypatch.setattr(agent, name, fake)
    return calls


def test_run_agent_routes_to_resolved_grok(monkeypatch):
    monkeypatch.setattr(
        agent, "resolve_agent_llm",
        lambda persona: ("grok", "grok-4.5", "medium"),
    )
    calls = _capture(monkeypatch, "_run_agent_grok")
    assert agent.run_agent("task", persona="morpheus", print_output=False) == "OK"
    assert calls["kwargs"]["model"] == "grok-4.5"
    assert calls["kwargs"]["effort"] == "medium"


def test_run_agent_streaming_routes_to_resolved_codex(monkeypatch):
    monkeypatch.setattr(
        agent, "resolve_agent_llm",
        lambda persona: ("codex", "gpt-5.6", "high"),
    )
    calls = _capture(monkeypatch, "_run_agent_streaming_codex")
    assert agent.run_agent_streaming("task", persona="oracle") == "OK"
    assert calls["kwargs"]["model"] == "gpt-5.6"
    assert calls["kwargs"]["effort"] == "high"


def test_run_agent_streaming_claude_gets_model(monkeypatch):
    monkeypatch.setattr(
        agent, "resolve_agent_llm",
        lambda persona: ("claude", "claude-opus-4-8", "high"),
    )
    calls = _capture(monkeypatch, "_run_agent_streaming_claude")
    assert agent.run_agent_streaming("task", persona=None) == "OK"
    assert calls["kwargs"]["model"] == "claude-opus-4-8"


def test_run_agent_sdk_uses_resolved_primary(monkeypatch):
    monkeypatch.setattr(
        agent, "resolve_agent_llm",
        lambda persona: ("grok", "grok-4.5", "low"),
    )
    seen = {}

    def fake_dispatch(provider, task, persona, max_turns, print_output,
                      lightweight, model, effort=None):
        seen["provider"] = provider
        seen["model"] = model
        seen["effort"] = effort
        return "OK"

    monkeypatch.setattr(agent, "_dispatch_provider_sdk", fake_dispatch)
    # No breaker open.
    monkeypatch.setattr(agent, "_breaker_fallback", lambda *a: None)
    monkeypatch.setattr(agent, "_provider_failed", lambda *a: False)
    assert agent.run_agent_sdk("task", persona="morpheus", print_output=False) == "OK"
    assert seen["provider"] == "grok"
    assert seen["model"] == "grok-4.5"
    assert seen["effort"] == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "trinity" && python -m pytest tests/test_dispatch_routing.py -v`
Expected: FAIL — `agent` has no `resolve_agent_llm`; `_dispatch_provider_sdk` has no `effort` param; routing ignores resolver.

- [ ] **Step 3: Import the resolver into `agent.py`**

Add to the imports near the top of `agent.py` (after the `from config import (...)` block that ends ~line 55):

```python
from runtime_config import resolve_agent_llm
```

- [ ] **Step 4: Rewrite `run_agent` and `run_agent_streaming`**

Replace both functions (currently `agent.py:1170` and `agent.py:1185`):

```python
def run_agent(
    task: str,
    persona: str | None = None,
    max_turns: int = 30,
    print_output: bool = True,
    lightweight: bool = False,
) -> str:
    """Provider-dispatched non-streaming agent entry point (per-agent LLM)."""
    provider, model, effort = resolve_agent_llm(persona)
    if provider == "grok":
        return _run_agent_grok(
            task, persona, max_turns, print_output, lightweight,
            model=model, effort=effort,
        )
    if provider == "codex":
        return _run_agent_codex(
            task, persona, max_turns, print_output, lightweight,
            model=model, effort=effort,
        )
    return _run_agent_claude(
        task, persona, max_turns, print_output, lightweight, model=model,
    )


def run_agent_streaming(
    task: str,
    persona: str | None = None,
    on_event: callable = None,
) -> str:
    """Provider-dispatched streaming agent entry point (per-agent LLM)."""
    provider, model, effort = resolve_agent_llm(persona)
    if provider == "grok":
        return _run_agent_streaming_grok(
            task, persona, on_event, model=model, effort=effort,
        )
    if provider == "codex":
        return _run_agent_streaming_codex(
            task, persona, on_event, model=model, effort=effort,
        )
    return _run_agent_streaming_claude(task, persona, on_event, model=model)
```

- [ ] **Step 5: Add `effort` to `_dispatch_provider_sdk`**

Replace the function (currently `agent.py:1248`):

```python
def _dispatch_provider_sdk(
    provider: str,
    task: str,
    persona: str | None,
    max_turns: int,
    print_output: bool,
    lightweight: bool,
    model: str | None,
    effort: str | None = None,
) -> str:
    """Call one provider without applying failover recursively."""
    effective_model = _fallback_model(provider, model)
    if provider == "grok":
        return _run_agent_grok(
            task, persona, max_turns, print_output, lightweight,
            model=effective_model, effort=effort,
        )
    if provider == "codex":
        return _run_agent_codex(
            task, persona, max_turns, print_output, lightweight,
            model=effective_model, effort=effort,
        )
    return _run_agent_sdk_claude(
        task, persona, max_turns, print_output, lightweight,
        model=effective_model,
    )
```

- [ ] **Step 6: Route `run_agent_sdk` on the resolved primary**

In `run_agent_sdk` (currently `agent.py:1330`), replace the first two lines of the body:

```python
    primary = TRINITY_PROVIDER
    fallback = TRINITY_FALLBACK_PROVIDER
```

with:

```python
    primary, resolved_model, resolved_effort = resolve_agent_llm(persona)
    if model is None:
        model = resolved_model
    fallback = TRINITY_FALLBACK_PROVIDER if primary != TRINITY_FALLBACK_PROVIDER else TRINITY_PROVIDER
```

Then pass `effort` on the two primary dispatch calls in this function. Change the breaker-open dispatch call and the main dispatch call to include `effort=resolved_effort`:

```python
        return _dispatch_provider_sdk(
            active_breaker, task, persona, max_turns, print_output, lightweight,
            model, effort=None,
        )
```

(breaker path uses the fallback provider → default effort), and:

```python
    result = _dispatch_provider_sdk(
        primary, task, persona, max_turns, print_output, lightweight, model,
        effort=resolved_effort,
    )
```

Leave the fallback dispatch call (`fallback_result = _dispatch_provider_sdk(fallback, ...)`) passing `None` for model and no effort (defaults to the fallback provider's env effort).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd "trinity" && python -m pytest tests/test_dispatch_routing.py tests/test_provider_params.py tests/test_sdk_diagnostics.py -v`
Expected: PASS (routing green; earlier tasks still green)

- [ ] **Step 8: Commit**

```bash
git add trinity/agent.py trinity/tests/test_dispatch_routing.py
git commit -m "feat(trinity): dispatch on per-agent resolved LLM

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi"
```

---

### Task 5: `model_switcher.py` — pure wizard (codec + keyboards + step logic)

**Files:**
- Create: `trinity/model_switcher.py`
- Test: `trinity/tests/test_model_switcher.py`

**Interfaces:**
- Consumes: `config` catalog constants; `runtime_config.set_agent_llm/reset_agent_llm/resolve_agent_llm`.
- Produces:
  - `encode_cb(agent, step, value="") -> str`
  - `parse_cb(data) -> dict | None` → `{"agent","step","value"}`
  - `provider_keyboard(agent) -> dict`, `model_keyboard(agent, provider) -> dict`, `effort_keyboard(agent, provider, model_idx) -> dict`
  - `open_text(agent) -> str`, `current_summary(agent) -> str`, `agent_label(agent) -> str`
  - `apply_callback(cb: dict) -> dict` → `{"text": str, "reply_markup": dict | None, "done": bool}`

- [ ] **Step 1: Write the failing test**

Create `trinity/tests/test_model_switcher.py`:

```python
"""Wizard codec, keyboards, and step transitions."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import runtime_config  # noqa: E402
import model_switcher as ms  # noqa: E402
import config  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    state = tmp_path / "state" / "agent-models.json"
    monkeypatch.setattr(runtime_config, "AGENT_MODELS_STATE", state)
    monkeypatch.setattr(runtime_config, "TRINITY_PROVIDER", "claude")
    monkeypatch.setattr(runtime_config, "TRINITY_MODEL", "claude-fable-5")
    monkeypatch.setattr(runtime_config, "TRINITY_REASONING_EFFORT", "high")
    return state


def test_cb_roundtrip():
    data = ms.encode_cb("opportunity_scout", "model", "codex:1")
    assert ms.parse_cb(data) == {
        "agent": "opportunity_scout", "step": "model", "value": "codex:1",
    }


def test_cb_rejects_foreign_and_malformed():
    assert ms.parse_cb("xx|a|b|c") is None
    assert ms.parse_cb("ml|a|bogus|c") is None
    assert ms.parse_cb("garbage") is None


def test_all_generated_callback_data_within_64_bytes():
    longest_agent = "opportunity_scout"  # longest real persona key
    for kb in [
        ms.provider_keyboard(longest_agent),
        ms.model_keyboard(longest_agent, "claude"),
        ms.effort_keyboard(longest_agent, "codex", 0),
    ]:
        for row in kb["inline_keyboard"]:
            for btn in row:
                assert len(btn["callback_data"].encode()) <= 64, btn


def test_provider_tap_shows_model_keyboard():
    cb = ms.parse_cb(ms.encode_cb("morpheus", "prov", "codex"))
    result = ms.apply_callback(cb)
    assert result["done"] is False
    labels = [b["text"] for row in result["reply_markup"]["inline_keyboard"]
              for b in row]
    assert "gpt-5.6-sol" in labels


def test_codex_model_tap_shows_effort_step():
    cb = ms.parse_cb(ms.encode_cb("morpheus", "model", "codex:0"))
    result = ms.apply_callback(cb)
    assert result["done"] is False
    labels = [b["text"] for row in result["reply_markup"]["inline_keyboard"]
              for b in row]
    assert "High" in labels


def test_claude_model_tap_finalizes_without_effort():
    cb = ms.parse_cb(ms.encode_cb("oracle", "model", "claude:1"))  # Opus 4.8
    result = ms.apply_callback(cb)
    assert result["done"] is True
    assert result["reply_markup"] is None
    assert runtime_config.resolve_agent_llm("oracle")[:2] == (
        "claude", "claude-opus-4-8",
    )


def test_effort_tap_persists_full_assignment():
    cb = ms.parse_cb(ms.encode_cb("morpheus", "eff", "grok:0:medium"))
    result = ms.apply_callback(cb)
    assert result["done"] is True
    assert runtime_config.resolve_agent_llm("morpheus") == (
        "grok", "grok-4.5", "medium",
    )


def test_reset_tap_clears_override():
    runtime_config.set_agent_llm("neo", "grok", "grok-4.5", "low")
    cb = ms.parse_cb(ms.encode_cb("neo", "reset"))
    result = ms.apply_callback(cb)
    assert result["done"] is True
    assert runtime_config.resolve_agent_llm("neo")[0] == "claude"


def test_bad_selection_returns_error_without_crash():
    cb = ms.parse_cb(ms.encode_cb("neo", "model", "codex:99"))
    result = ms.apply_callback(cb)
    assert result["done"] is True
    assert "⚠️" in result["text"] or "Unknown" in result["text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "trinity" && python -m pytest tests/test_model_switcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'model_switcher'`

- [ ] **Step 3: Create `trinity/model_switcher.py`**

```python
#!/usr/bin/env python3
"""Pure wizard logic for the Telegram /model switcher.

No Telegram/transport imports — this module decides what text and inline
keyboard each tap should produce, and persists the final choice via
runtime_config. telegram_bot.py owns the transport and calls apply_callback.

callback_data format: ``ml|<agent>|<step>|<value>`` (<= 64 bytes).
Steps: prov | model | eff | reset | back.
  - prov   value = provider
  - model  value = "<provider>:<model_index>"
  - eff    value = "<provider>:<model_index>:<effort>"
  - reset  value = ""
  - back   value = "prov"  or  "model:<provider>"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (  # noqa: E402
    EFFORT_LEVELS,
    MODEL_CATALOG,
    PROVIDER_DISPLAY,
    PROVIDER_LABELS,
    PROVIDER_SUPPORTS_EFFORT,
    TRINITY_REASONING_EFFORT,
)
from runtime_config import (  # noqa: E402
    reset_agent_llm,
    resolve_agent_llm,
    set_agent_llm,
)

CB_PREFIX = "ml"
_STEPS = {"prov", "model", "eff", "reset", "back"}


# ── codec ────────────────────────────────────────────────────────

def encode_cb(agent: str, step: str, value: str = "") -> str:
    return f"{CB_PREFIX}|{agent}|{step}|{value}"


def parse_cb(data: str) -> dict | None:
    parts = (data or "").split("|")
    if len(parts) != 4 or parts[0] != CB_PREFIX:
        return None
    _, agent, step, value = parts
    if step not in _STEPS or not agent:
        return None
    return {"agent": agent, "step": step, "value": value}


# ── display helpers ──────────────────────────────────────────────

def agent_label(agent: str) -> str:
    return agent.replace("_", " ").title()


def _summary(provider: str, model: str, effort: str) -> str:
    parts = [PROVIDER_DISPLAY.get(provider, provider), model]
    if PROVIDER_SUPPORTS_EFFORT.get(provider):
        parts.append(f"effort={effort}")
    return " · ".join(parts)


def current_summary(agent: str) -> str:
    return _summary(*resolve_agent_llm(agent))


def open_text(agent: str) -> str:
    return (
        f"{agent_label(agent)} → LLM config\n"
        f"Current: {current_summary(agent)}\n\n"
        f"Pick a provider:"
    )


# ── keyboards ────────────────────────────────────────────────────

def _btn(text: str, agent: str, step: str, value: str = "") -> dict:
    return {"text": text, "callback_data": encode_cb(agent, step, value)}


def provider_keyboard(agent: str) -> dict:
    row = [_btn(PROVIDER_LABELS[p], agent, "prov", p) for p in MODEL_CATALOG]
    return {"inline_keyboard": [
        row,
        [_btn("♻️ Reset to default", agent, "reset")],
    ]}


def model_keyboard(agent: str, provider: str) -> dict:
    rows = [
        [_btn(label, agent, "model", f"{provider}:{i}")]
        for i, (_mid, label) in enumerate(MODEL_CATALOG[provider])
    ]
    rows.append([_btn("← Back", agent, "back", "prov")])
    return {"inline_keyboard": rows}


def effort_keyboard(agent: str, provider: str, model_idx: int) -> dict:
    row = [
        _btn(effort.capitalize(), agent, "eff", f"{provider}:{model_idx}:{effort}")
        for effort in EFFORT_LEVELS
    ]
    return {"inline_keyboard": [
        row,
        [_btn("← Back", agent, "back", f"model:{provider}")],
    ]}


# ── step engine ──────────────────────────────────────────────────

def _error(text: str = "⚠️ Unknown selection — start over with /model.") -> dict:
    return {"text": text, "reply_markup": None, "done": True}


def _finalize(agent: str, provider: str, model: str, effort: str) -> dict:
    set_agent_llm(agent, provider, model, effort)
    return {
        "text": f"✅ {agent_label(agent)} now runs {_summary(provider, model, effort)}",
        "reply_markup": None,
        "done": True,
    }


def _model_from_idx(provider: str, idx_raw: str):
    if provider not in MODEL_CATALOG:
        return None
    try:
        idx = int(idx_raw)
    except (TypeError, ValueError):
        return None
    models = MODEL_CATALOG[provider]
    if not 0 <= idx < len(models):
        return None
    return idx, models[idx][0]


def apply_callback(cb: dict) -> dict:
    agent, step, value = cb["agent"], cb["step"], cb["value"]

    if step == "reset":
        reset_agent_llm(agent)
        return {
            "text": f"♻️ {agent_label(agent)} reset to default LLM "
                    f"({current_summary(agent)})",
            "reply_markup": None,
            "done": True,
        }

    if step == "back":
        if value == "prov":
            return {"text": open_text(agent),
                    "reply_markup": provider_keyboard(agent), "done": False}
        if value.startswith("model:"):
            provider = value.split(":", 1)[1]
            if provider not in MODEL_CATALOG:
                return _error()
            return {"text": f"{PROVIDER_LABELS[provider]} → pick a model:",
                    "reply_markup": model_keyboard(agent, provider), "done": False}
        return _error()

    if step == "prov":
        if value not in MODEL_CATALOG:
            return _error()
        return {"text": f"{PROVIDER_LABELS[value]} → pick a model:",
                "reply_markup": model_keyboard(agent, value), "done": False}

    if step == "model":
        provider, _, idx_raw = value.partition(":")
        resolved = _model_from_idx(provider, idx_raw)
        if resolved is None:
            return _error()
        idx, model = resolved
        if PROVIDER_SUPPORTS_EFFORT.get(provider):
            return {"text": f"{PROVIDER_LABELS[provider]} {model} → reasoning effort:",
                    "reply_markup": effort_keyboard(agent, provider, idx),
                    "done": False}
        return _finalize(agent, provider, model, TRINITY_REASONING_EFFORT)

    if step == "eff":
        provider, idx_raw, effort = (value.split(":") + ["", "", ""])[:3]
        resolved = _model_from_idx(provider, idx_raw)
        if resolved is None or effort not in EFFORT_LEVELS:
            return _error()
        _idx, model = resolved
        return _finalize(agent, provider, model, effort)

    return _error()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "trinity" && python -m pytest tests/test_model_switcher.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add trinity/model_switcher.py trinity/tests/test_model_switcher.py
git commit -m "feat(trinity): pure wizard engine for the /model switcher

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi"
```

---

### Task 6: Telegram transport primitives (inline keyboards + callbacks)

**Files:**
- Modify: `trinity/telegram_bot.py` — `TelegramAPI.get_updates`, `send_message`, `edit_message`; add `answer_callback_query`
- Test: `trinity/tests/test_telegram_api.py`

**Interfaces:**
- Produces:
  - `send_message(..., reply_markup: dict | None = None)` — includes `reply_markup` in the first chunk's payload.
  - `edit_message(chat_id, message_id, text, reply_markup: dict | None = None)` — includes `reply_markup` when provided.
  - `answer_callback_query(callback_id: str, text: str = "") -> dict`
  - `get_updates` requests `allowed_updates: ["message","callback_query"]`.

- [ ] **Step 1: Write the failing test**

Create `trinity/tests/test_telegram_api.py`:

```python
"""TelegramAPI sends inline keyboards and answers callbacks."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import telegram_bot as tb  # noqa: E402


class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return {"result": self._payload}

    def raise_for_status(self):
        pass


class _FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, json=None, **kw):
        self.posts.append((url, json))
        return _FakeResp({"message_id": 42})

    def get(self, url, params=None, **kw):
        self.gets.append((url, params))
        return _FakeResp([])


def _api(monkeypatch):
    api = tb.TelegramAPI.__new__(tb.TelegramAPI)
    api.base = "https://api.telegram.org/botTОKEN"
    api.session = _FakeSession()
    return api


def test_send_message_includes_reply_markup(monkeypatch):
    api = _api(monkeypatch)
    kb = {"inline_keyboard": [[{"text": "x", "callback_data": "ml|a|prov|codex"}]]}
    api.send_message(123, "hi", reply_markup=kb)
    url, payload = api.session.posts[-1]
    assert url.endswith("/sendMessage")
    assert payload["reply_markup"] == kb


def test_edit_message_includes_reply_markup(monkeypatch):
    api = _api(monkeypatch)
    kb = {"inline_keyboard": [[{"text": "y", "callback_data": "ml|a|back|prov"}]]}
    api.edit_message(123, 7, "updated", reply_markup=kb)
    url, payload = api.session.posts[-1]
    assert url.endswith("/editMessageText")
    assert payload["reply_markup"] == kb


def test_answer_callback_query_posts(monkeypatch):
    api = _api(monkeypatch)
    api.answer_callback_query("cbid", "done")
    url, payload = api.session.posts[-1]
    assert url.endswith("/answerCallbackQuery")
    assert payload["callback_query_id"] == "cbid"
    assert payload["text"] == "done"


def test_get_updates_allows_callback_queries(monkeypatch):
    api = _api(monkeypatch)
    api.get_updates(offset=1, timeout=1)
    _url, params = api.session.gets[-1]
    assert "callback_query" in params["allowed_updates"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "trinity" && python -m pytest tests/test_telegram_api.py -v`
Expected: FAIL — `send_message()` has no `reply_markup`; no `answer_callback_query`; `allowed_updates` lacks `callback_query`.

- [ ] **Step 3: Edit `get_updates`**

In `TelegramAPI.get_updates` (currently `telegram_bot.py:129`), change the `allowed_updates` param:

```python
            params={"offset": offset, "timeout": timeout,
                    "allowed_updates": '["message","callback_query"]'},
```

- [ ] **Step 4: Edit `send_message` to accept `reply_markup`**

Replace the signature and payload build in `send_message` (currently `telegram_bot.py:138`):

```python
    def send_message(self, chat_id: int | str, text: str,
                     reply_to: int | None = None,
                     parse_mode: str | None = None,
                     reply_markup: dict | None = None) -> dict:
        """Send a message, auto-chunking if over 4096 chars."""
        chunks = _chunk_text(text, 4096)
        result = None
        for i, chunk in enumerate(chunks):
            payload = {"chat_id": chat_id, "text": chunk}
            if reply_to and result is None:
                payload["reply_to_message_id"] = reply_to
            if parse_mode:
                payload["parse_mode"] = parse_mode
            # Attach the keyboard only to the first chunk.
            if reply_markup and i == 0:
                payload["reply_markup"] = reply_markup
            r = self.session.post(f"{self.base}/sendMessage", json=payload)
            if r.status_code == 200:
                result = r.json().get("result", {})
            else:
                log.warning("sendMessage failed: %s %s", r.status_code, r.text[:200])
                if parse_mode:
                    payload.pop("parse_mode")
                    r = self.session.post(f"{self.base}/sendMessage", json=payload)
                    if r.status_code == 200:
                        result = r.json().get("result", {})
        return result or {}
```

- [ ] **Step 5: Edit `edit_message` to accept `reply_markup`**

Replace `edit_message` (currently `telegram_bot.py:192`):

```python
    def edit_message(self, chat_id: int | str, message_id: int, text: str,
                     reply_markup: dict | None = None) -> dict:
        """Edit an existing message (optionally replacing its keyboard)."""
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[:4096],
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        r = self.session.post(f"{self.base}/editMessageText", json=payload)
        if r.status_code == 200:
            return r.json().get("result", {})
        return {}

    def answer_callback_query(self, callback_id: str, text: str = "") -> dict:
        """Acknowledge a callback query (clears the button's loading spinner)."""
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        r = self.session.post(f"{self.base}/answerCallbackQuery", json=payload)
        if r.status_code == 200:
            return r.json().get("result", {})
        return {}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd "trinity" && python -m pytest tests/test_telegram_api.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add trinity/telegram_bot.py trinity/tests/test_telegram_api.py
git commit -m "feat(trinity): inline keyboard + callback query transport

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi"
```

---

### Task 7: Wire `/model` command + callback handling into the bot

**Files:**
- Modify: `trinity/telegram_bot.py` — imports, replace the read-only `/model` block, add `_handle_model_command` + `handle_callback`, extend `AccessControl`, wire the run loop
- Test: `trinity/tests/test_model_command.py`

**Interfaces:**
- Consumes: `model_switcher.{parse_cb, apply_callback, provider_keyboard, open_text, current_summary, agent_label}`, `runtime_config.reset_agent_llm`, `agent.PERSONA_OVERRIDES`, the Task 6 API methods.
- Produces:
  - `VALID_AGENTS: set[str]`
  - `_handle_model_command(api, chat_id, reply_to, clean_text) -> None`
  - `handle_callback(api, cq, bot_username) -> None`
  - `AccessControl.callback_allowed(update) -> bool`
  - run loop dispatches `callback_query` updates (allowlist-guarded) and routes `/model` messages to `_handle_model_command`.

- [ ] **Step 1: Write the failing test**

Create `trinity/tests/test_model_command.py`:

```python
"""Command parsing + callback routing for the /model switcher."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import runtime_config  # noqa: E402
import telegram_bot as tb  # noqa: E402


class _RecordingAPI:
    def __init__(self):
        self.sent = []
        self.edited = []
        self.answered = []

    def send_message(self, chat_id, text, reply_to=None, parse_mode=None,
                     reply_markup=None):
        self.sent.append({"text": text, "reply_markup": reply_markup})
        return {"message_id": 1}

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        self.edited.append({"text": text, "reply_markup": reply_markup})
        return {}

    def answer_callback_query(self, callback_id, text=""):
        self.answered.append(text)
        return {}


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    state = tmp_path / "state" / "agent-models.json"
    monkeypatch.setattr(runtime_config, "AGENT_MODELS_STATE", state)
    monkeypatch.setattr(runtime_config, "TRINITY_PROVIDER", "claude")
    monkeypatch.setattr(runtime_config, "TRINITY_MODEL", "claude-fable-5")
    monkeypatch.setattr(runtime_config, "TRINITY_REASONING_EFFORT", "high")


def test_bare_model_opens_wizard_for_trinity():
    api = _RecordingAPI()
    tb._handle_model_command(api, 100, 5, "/model")
    assert api.sent
    assert api.sent[-1]["reply_markup"]["inline_keyboard"]
    assert "Trinity" in api.sent[-1]["text"]


def test_model_at_agent_targets_persona():
    api = _RecordingAPI()
    tb._handle_model_command(api, 100, 5, "/model@morpheus")
    assert "Morpheus" in api.sent[-1]["text"]


def test_unknown_agent_rejected():
    api = _RecordingAPI()
    tb._handle_model_command(api, 100, 5, "/model@nobody")
    assert "Unknown agent" in api.sent[-1]["text"]
    assert api.sent[-1]["reply_markup"] is None


def test_reset_shortcut_clears_override():
    runtime_config.set_agent_llm("morpheus", "grok", "grok-4.5", "high")
    api = _RecordingAPI()
    tb._handle_model_command(api, 100, 5, "/model@morpheus reset")
    assert runtime_config.resolve_agent_llm("morpheus")[0] == "claude"
    assert "reset" in api.sent[-1]["text"].lower()


def test_handle_callback_advances_and_edits():
    api = _RecordingAPI()
    cq = {
        "id": "cb1",
        "data": tb.encode_cb("morpheus", "prov", "grok"),
        "message": {"chat": {"id": 100}, "message_id": 9},
    }
    tb.handle_callback(api, cq, "tejiritrinity_bot")
    assert api.answered  # spinner cleared
    assert api.edited[-1]["reply_markup"]["inline_keyboard"]


def test_callback_allowed_matches_allowlist():
    acl = tb.AccessControl(
        {"groupAllowFrom": [1366707521]}, "tejiritrinity_bot",
    )
    good = {"callback_query": {"from": {"id": 1366707521}}}
    bad = {"callback_query": {"from": {"id": 999}}}
    assert acl.callback_allowed(good) is True
    assert acl.callback_allowed(bad) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "trinity" && python -m pytest tests/test_model_command.py -v`
Expected: FAIL — `telegram_bot` has no `_handle_model_command` / `handle_callback` / `encode_cb` / `AccessControl.callback_allowed`.

- [ ] **Step 3: Extend the imports in `telegram_bot.py`**

Change the `from agent import ...` line (currently `telegram_bot.py:46`) to also import the persona map:

```python
from agent import run_agent, run_agent_streaming, PERSONA_OVERRIDES
```

Add below the existing `from ... import` block (after the `knowledge.wiki` import ~line 48):

```python
from runtime_config import reset_agent_llm
from model_switcher import (
    apply_callback,
    current_summary,
    encode_cb,
    parse_cb,
    provider_keyboard,
    open_text,
    agent_label,
)

# Valid /model targets: every persona plus the default trinity agent.
VALID_AGENTS = set(PERSONA_OVERRIDES) | {"trinity"}
```

- [ ] **Step 4: Add the `/model` command handler**

Add this function just above `handle_message` (before `telegram_bot.py:550`):

```python
def _handle_model_command(api: "TelegramAPI", chat_id, reply_to,
                          clean_text: str) -> None:
    """Open the LLM switcher wizard, or handle a text `reset` shortcut.

    Grammar:  /model            -> target 'trinity'
              /model@<agent>     -> target that persona
              /model@<agent> reset  or  /model reset  -> clear override
    """
    body = clean_text[len("/model"):].strip()
    agent = "trinity"
    rest = ""
    if body.startswith("@"):
        token = body[1:].split(None, 1)
        agent = token[0].lower()
        rest = (token[1].strip().lower() if len(token) > 1 else "")
    else:
        rest = body.lower()

    if agent not in VALID_AGENTS:
        valid = ", ".join(sorted(VALID_AGENTS))
        api.send_message(chat_id, f"Unknown agent '{agent}'. Valid targets: {valid}",
                         reply_to=reply_to)
        return

    if rest == "reset":
        reset_agent_llm(agent)
        api.send_message(
            chat_id,
            f"♻️ {agent_label(agent)} reset to default LLM ({current_summary(agent)})",
            reply_to=reply_to,
        )
        return

    api.send_message(chat_id, open_text(agent), reply_to=reply_to,
                     reply_markup=provider_keyboard(agent))


def handle_callback(api: "TelegramAPI", cq: dict, bot_username: str) -> None:
    """Advance the /model wizard in response to an inline-button tap."""
    cb_id = cq.get("id")
    parsed = parse_cb(cq.get("data", ""))
    message = cq.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    msg_id = message.get("message_id")
    if not parsed:
        api.answer_callback_query(cb_id, "Expired control — send /model again.")
        return
    result = apply_callback(parsed)
    api.answer_callback_query(cb_id)
    if chat_id and msg_id:
        api.edit_message(chat_id, msg_id, result["text"],
                         reply_markup=result.get("reply_markup"))
```

- [ ] **Step 5: Replace the read-only `/model` block inside `handle_message`**

Replace the existing block (currently `telegram_bot.py:609-624`, the comment `# Runtime metadata...` through the `return`):

```python
    # /model — open the per-agent LLM switcher wizard.
    low = clean_text.lower()
    if low == "/model" or low.startswith("/model@") or low.startswith("/model "):
        _handle_model_command(api, chat_id, message_id, clean_text)
        return
```

- [ ] **Step 6: Add `callback_allowed` to `AccessControl`**

Add this method to the `AccessControl` class (after `_is_mentioned`, ~`telegram_bot.py:307`):

```python
    def callback_allowed(self, update: dict) -> bool:
        """Only allowlisted users may drive inline-keyboard controls."""
        cq = update.get("callback_query", {})
        user_id = str(cq.get("from", {}).get("id", ""))
        return user_id in self.allowed_users
```

- [ ] **Step 7: Wire callbacks into the run loop**

In `run_bot`, replace the per-update body (currently `telegram_bot.py:969-981`, the `for update in updates:` block) with:

```python
        for update in updates:
            update_id = update.get("update_id", 0)
            offset = max(offset, update_id)
            save_offset(offset)

            cq = update.get("callback_query")
            if cq:
                if acl.callback_allowed(update):
                    try:
                        handle_callback(api, cq, bot_username)
                    except Exception as e:
                        log.error("Callback error: %s", e, exc_info=True)
                else:
                    api.answer_callback_query(cq.get("id"), "Not authorized.")
                continue

            if not acl.should_respond(update):
                continue

            msg = update.get("message", {})
            if msg:
                pool.dispatch(msg)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd "trinity" && python -m pytest tests/test_model_command.py -v`
Expected: PASS (6 passed)

- [ ] **Step 9: Run the full trinity test suite**

Run: `cd "trinity" && python -m pytest tests/ -v`
Expected: PASS (all tasks' tests green; `test_sdk_diagnostics.py` unbroken)

- [ ] **Step 10: Manual smoke check (no live send)**

Run: `cd "trinity" && python -c "import telegram_bot, model_switcher, runtime_config; print('imports OK'); print(model_switcher.open_text('morpheus'))"`
Expected: prints `imports OK` and a wizard header for Morpheus.

- [ ] **Step 11: Commit**

```bash
git add trinity/telegram_bot.py trinity/tests/test_model_command.py
git commit -m "feat(trinity): wire /model switcher wizard into the Telegram bot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HArE5Sh1BmuiJxFeXL9KYi"
```

---

## Post-Implementation Manual Verification (TJ / operator)

These require a live bot and are done after merge, not in the automated suite:

1. `python trinity/telegram_bot.py --test` → connectivity OK.
2. Restart the bot (`systemctl restart trinity-telegram` or foreground run).
3. DM `/model` → wizard appears with provider buttons; tap Codex → model list → effort → confirm; verify `~/.openclaw/workspace/state/agent-models.json` shows the `trinity` entry.
4. DM `/model@morpheus` → set Grok; then trigger a Morpheus reply and confirm it runs on Grok (check `trinity/chat-history` / session log provider line).
5. DM `/model@morpheus reset` → entry removed; Morpheus back on the env default.
6. From a non-allowlisted account (if available), tapping a stale button is rejected with "Not authorized."

---

## Self-Review (completed by plan author)

**Spec coverage:**
- Core model / overlay file → Tasks 1–2. ✅
- Approach A resolver at call time → Tasks 2, 4. ✅
- Wizard flow (provider→model→effort, Claude skips effort, reset) → Task 5. ✅
- `MODEL_CATALOG` + `PROVIDER_SUPPORTS_EFFORT` → Task 1. ✅
- Telegram plumbing (allowed_updates, reply_markup, answer_callback_query, callback handler, TJ-only allowlist) → Tasks 6–7. ✅
- Command parsing (`/model`, `/model@<agent>`, reset, unknown-agent error) → Task 7. ✅
- Dispatch refactor incl. streaming Codex/Grok hardcoded model/effort + Claude `--model` + `run_agent_sdk` per-persona → Tasks 3–4. ✅
- Persistence & concurrency (atomic write, tolerant read) → Task 2. ✅
- Testing (unit + integration + manual) → per-task tests + manual section. ✅
- Out-of-scope items intentionally excluded. ✅

**Placeholder scan:** none — every step carries real code and exact commands.

**Type consistency:** `resolve_agent_llm` returns `(provider, model, effort)` everywhere; `apply_callback` returns `{"text","reply_markup","done"}` consumed identically in `handle_callback`; `_dispatch_provider_sdk` gains `effort` used by all callers; provider run-fn `model`/`effort` kwargs match across Tasks 3–4.
