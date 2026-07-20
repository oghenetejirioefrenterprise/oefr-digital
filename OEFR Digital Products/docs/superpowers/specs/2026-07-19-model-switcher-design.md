# Design: Per-Agent LLM Switcher for Trinity's `/model` command

**Date:** 2026-07-19
**Status:** Approved (design), pending implementation plan
**Area:** `trinity/telegram_bot.py`, `trinity/agent.py`, `trinity/config.py`, new `trinity/runtime_config.py`

## Problem

Today `/model` in Trinity's Telegram bot is **read-only** — it reports the
configured provider/model/reasoning effort and nothing more
(`trinity/telegram_bot.py:610`). Provider/model/effort are import-time
environment constants in `config.py` (`TRINITY_PROVIDER`, `TRINITY_MODEL`,
`TRINITY_REASONING_EFFORT`), and `run_agent_streaming` — the Telegram path —
dispatches purely on the `TRINITY_PROVIDER` constant with no runtime override.

Separately, "agents" (personas — the `PERSONA_OVERRIDES` keys such as
`morpheus`, `oracle`, `neo`, `seo_operator`, `needle_mover`, `second_brain`, …,
plus the default `trinity`) are auto-selected per Telegram group and per cron
cycle. They are not user-switchable, and there is no
way to give a specific agent its own LLM.

TJ wants `/model` to **switch** Trinity's LLM, with the **agent as the target**
of the switch, selected via a `@persona` suffix on the command.

## Core model: per-agent LLM assignment

The redesign treats the **agent as the target** and the **LLM (provider → model
→ effort) as what you set for it**. `/model` configures the default `trinity`
agent; `/model@<agent>` configures that specific agent.

A single persisted JSON overlay, keyed by agent, is layered over the env
defaults:

```json
// ~/.openclaw/workspace/state/agent-models.json
{
  "trinity":   { "provider": "claude", "model": "claude-fable-5", "effort": "high" },
  "morpheus":  { "provider": "grok",   "model": "grok-4.5",       "effort": "high" },
  "oracle":    { "provider": "claude", "model": "claude-opus-4-8" }
}
```

Rules:
- Any agent **absent** from the file resolves to `TRINITY_PROVIDER` /
  `TRINITY_MODEL` / `TRINITY_REASONING_EFFORT`.
- A partial entry (e.g. missing `effort`) fills the missing keys from the env
  defaults.
- The file holds only **deviations** from the env baseline. Deleting it restores
  pure env behavior — nothing breaks.
- Scope is **global and persisted**: an assignment applies to both the Telegram
  bot (when that persona is active in a group) and the matching cron cycle, and
  survives restarts.

Valid agent keys are the persona keys plus `trinity` (default). Source of truth:
`agent.PERSONA_OVERRIDES` keys ∪ `{"trinity"}`.

## Architecture: resolver read at call time (approach A)

A new `trinity/runtime_config.py` exposes:

```python
def resolve_agent_llm(agent: str | None) -> tuple[str, str, str]:
    """Return (provider, model, effort) for an agent, overlaying the persisted
    agent-models.json on the env defaults. agent=None resolves to 'trinity'."""

def set_agent_llm(agent: str, provider: str, model: str, effort: str) -> None:
    """Persist one agent's assignment (atomic temp-file + replace)."""

def reset_agent_llm(agent: str) -> None:
    """Remove one agent's override, restoring env defaults."""

def load_overrides() -> dict: ...   # tolerant read; {} on missing/corrupt
```

- `run_agent`, `run_agent_streaming`, and `run_agent_sdk` **stop dispatching on
  the import-time `TRINITY_PROVIDER` constant**. Instead they map their
  `persona` argument to an agent key (`None` → `"trinity"`), call
  `resolve_agent_llm`, and dispatch to the matching provider path with the
  resolved model + effort.
- The long-running Telegram bot re-reads the file each message (cheap JSON read).
  Fresh cron processes read it at dispatch. No cross-process signalling needed —
  the file is the single source of truth.

**Alternatives rejected:**
- Mutating module constants in-process — doesn't cross to cron processes; racy
  across the bot's per-chat worker threads.
- Re-exec with env vars — heavyweight; loses the long-poll loop.

## Interaction: inline-keyboard wizard

`/model` or `/model@<agent>` opens a wizard message that edits itself in place as
buttons are tapped.

```
Trinity → LLM config
Current: Anthropic Claude · claude-fable-5

Pick a provider:
[ Claude ]  [ Codex ]  [ Grok ]
```
→ tap **Codex** →
```
Codex → pick a model:
[ gpt-5.6-sol ]  [ gpt-5.6 ]
[ ← Back ]
```
→ tap a model →
```
Codex gpt-5.6-sol → reasoning effort:
[ Low ]  [ Medium ]  [ High ]
[ ← Back ]
```
→ tap effort → persists →
```
✅ Trinity now runs OpenAI Codex · gpt-5.6-sol · effort=high
```

Behavior:
- **Effort step is skipped for Claude** (the Claude path takes no reasoning-effort
  knob — matches today's `/model` report). Choosing a Claude model persists
  immediately with the env-default effort recorded but unused.
- A `[ Reset to default ]` button on the provider screen clears the agent's
  override.
- `callback_data` encodes the full path compactly: `ml|<agent>|<step>|<value>`
  where `step ∈ {prov, model, eff, reset, back}` (≤64 bytes, Telegram's limit).
  The target agent travels in every callback so taps are stateless.
- Model lists come from a new `MODEL_CATALOG` in `config.py`
  (`provider -> [(model_id, label)]`) plus `PROVIDER_SUPPORTS_EFFORT`
  (`{"codex": True, "grok": True, "claude": False}`). Adding a model is a
  one-line config edit.

### Initial `MODEL_CATALOG` (editable in config)

- **claude:** `claude-fable-5` (Fable 5), `claude-opus-4-8` (Opus 4.8),
  `claude-sonnet-5` (Sonnet 5), `claude-haiku-4-5-20251001` (Haiku 4.5)
- **codex:** `gpt-5.6-sol` (gpt-5.6-sol), `gpt-5.6` (gpt-5.6)
- **grok:** `grok-4.5` (Grok 4.5)

Effort values offered: `low`, `medium`, `high` (codex/grok only).

## Telegram plumbing (new)

The bot currently receives only `message` updates and cannot render buttons.
Additions to `trinity/telegram_bot.py`:

- `get_updates` → `allowed_updates: ["message","callback_query"]`.
- `send_message` / `edit_message` gain an optional `reply_markup` param.
- New `TelegramAPI.answer_callback_query(callback_id, text="")` (stops the
  Telegram loading spinner) and `edit_message_reply_markup(...)`.
- The bot dispatch loop gains a `callback_query` branch routed to a new
  `handle_callback(api, cq, bot_username)`.
- **Security:** callbacks are guarded by the **same TJ-only allowlist** as
  messages. A `callback_query` carries its own `from.id`; reject if not allowed,
  answering the callback with a terse denial so the spinner clears.

## Command parsing

- `/model` → target agent `trinity`.
- `/model@<agent>` → target that agent. Unknown agent → reply listing valid
  agent keys; no wizard opened.
- `/model@<agent> reset` (text shortcut) → clears that agent's override without
  opening the wizard.
- The existing `@tejiritrinity_bot` / `@<bot_username>` stripping stays; the
  `@<agent>` suffix is **preserved** and parsed by the `/model` handler.
- Note: in group chats Telegram's `/cmd@name` routing is designed for bot
  usernames; `@<agent>` is still delivered as message text and parsed by us. DMs
  (TJ's primary path) have no routing quirk.

## Dispatch refactor detail

- `run_agent` / `run_agent_streaming` (`trinity/agent.py`): resolve per persona
  at call time and route to the correct provider path with resolved
  model/effort. The **streaming Codex/Grok paths currently hardcode
  `TRINITY_MODEL` / `TRINITY_REASONING_EFFORT`** (`_run_agent_streaming_codex`,
  `_run_agent_streaming_grok`) — these are parameterized to accept the resolved
  values.
- `run_agent_sdk` (cron entry, `trinity/agent.py`): resolves per its persona so
  `/model@morpheus` changes the Morpheus cron cycle's LLM. Failover still derives
  its fallback from the **resolved** primary provider using the existing
  `TRINITY_FALLBACK_PROVIDER` / `TRINITY_FALLBACK_MODEL` defaults; the circuit
  breaker keys on the resolved primary.

## Persistence & concurrency

- Atomic write: temp file + `os.replace`, matching the existing provider circuit
  breaker (`agent.py` `_open_provider_breaker`).
- Reads tolerate a missing or corrupt file and fall back to env defaults.
- State lives at `WORKSPACE / "state" / "agent-models.json"`.

## Testing

- **Unit**
  - `resolve_agent_llm`: overlay logic for present / absent / partial / corrupt
    file; `agent=None` → `trinity`; unknown agent handling.
  - callback_data encode/parse round-trip; rejects malformed / oversized data.
  - `MODEL_CATALOG` integrity: every model id belongs to a real provider; every
    catalog provider has ≥1 model; `PROVIDER_SUPPORTS_EFFORT` covers all
    providers.
- **Integration**
  - Simulated `callback_query` update advances the wizard through
    provider→model→effort and writes the file; `resolve_agent_llm` reflects it.
  - Claude path skips effort and persists on model choice.
  - Reset clears the override.
  - Non-TJ `from.id` on a callback is rejected.
- **Manual**
  - `python trinity/telegram_bot.py --test` connectivity.
  - Live `/model` and `/model@morpheus` in DM; confirm persisted file and that a
    subsequent message uses the new LLM.

## Out of scope

- Per-chat (as opposed to global) assignments.
- Switching reasoning effort for Claude.
- A UI for editing `MODEL_CATALOG` (config-file edit only).
- Auto-discovery of available models from provider CLIs.
