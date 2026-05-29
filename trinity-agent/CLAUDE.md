# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Trinity Agent is a portable AI agent framework that lives in your workspace, talks through Telegram, and gets smarter every day via a three-tier memory system. It routes incoming messages to specialized "employee" personas, each backed by configurable LLM providers.

## Commands

```bash
# Install (editable, from repo root)
pip install -e .

# Run CLI
trinity init                          # Interactive setup wizard
trinity start                         # Start Telegram bot + scheduler (foreground)
trinity start --daemon                # Start in background
trinity stop                          # Stop a running daemon
trinity restart                       # Stop + start as daemon
trinity restart --foreground          # Stop + start in foreground
trinity run "do something" -e ceo     # One-shot task with specific employee
trinity status                        # Show workspace state
trinity employee list|add|edit|remove # Manage employees
trinity auth status|switch <provider> # Manage LLM provider
trinity memory search <query>         # Search memories
trinity memory stats                  # Memory statistics
trinity knowledge <args>              # Knowledge base CLI

# Run as module
python -m trinity --workspace /path start
```

No test suite exists yet. No linter configuration.

## Architecture

### Setup Wizard (cli.py `cmd_init`)

The `trinity init` wizard handles 4 steps: auth provider, company identity, employees, and Telegram. Smart secret detection: if the user pastes a raw token/key instead of an env var name, the wizard writes it to `.env` and references the env var in `trinity.toml`. All CLI commands (`start`, `run`, etc.) auto-load `.env` via `_load_dotenv()` at startup — no manual sourcing needed.

### Workspace Awareness

Both identity loading modes (`load_full_identity`, `load_compact_identity`) inject the workspace root path into the agent's system prompt so it knows where it lives and defaults file operations there. The agent can be directed outside the workspace if needed — it's a default, not a lockdown.

### Message Pipeline (app.py)

Every Telegram message flows through this pipeline:

1. **Router** (`router.py`) — Two-stage intent classification:
   - Stage 1: Regex pattern matching (instant, no API call) for feedback commands, wiki queries, status
   - Stage 2: Haiku LLM classification for ambiguous messages → `CONVERSATION`, `ACTION`, or `MEMORY`

2. **Track 1 — Conversational** (`agents/conversational.py`) — Single API call, no tools, streaming. Uses compact employee identity (truncated to ~500 chars). Fast and cheap.

3. **Track 2 — Builder/Action** (`agents/builder.py`) — Full agentic loop with tools. Uses complete employee identity. Runs up to `max_turns` (default 30) iterations of: send → tool_use → execute → repeat.

4. **Fast paths** — Feedback (fp/wontfix/fixed/ack), wiki queries, and status bypass the agent entirely.

### Core Agent Loop (agents/base.py)

`run_agent()` is the shared loop for all tool-using agents. It handles:
- Message accumulation with structured content blocks (text + tool_calls)
- Tool result capping at 50KB per result
- Token usage tracking persisted to `.trinity/state/usage.json`
- Streaming support via `on_text`/`on_tool` callbacks

### Provider Abstraction (providers/)

All LLM interaction goes through the `Provider` ABC (`providers/base.py`), which defines `chat()` and `stream()`. Four implementations:

| Provider | Config value | Notes |
|----------|-------------|-------|
| `ClaudeSDKProvider` | `claude_sdk` | Uses Claude Agent SDK, handles own agent loop. Supports `on_tool`/`on_text` callbacks for live tool streaming. |
| `AnthropicProvider` | `anthropic_api` | Direct Anthropic API |
| `OpenAIProvider` | `openai` | OpenAI-compatible |
| `OpenRouterProvider` | `openrouter` | OpenAI-compatible, custom base URL |

The factory (`providers/factory.py`) instantiates the correct provider from `AuthConfig`.

**SDK Provider note:** The `ClaudeSDKProvider` runs its own agent loop internally — `run_agent()` in `base.py` sees a single `end_turn` response. Tool-use events are surfaced via optional `on_tool`/`on_text` callbacks set on the provider instance before each call (wired by `_set_provider_callbacks()` in `app.py`).

### Live Telegram Streaming (telegram/streaming.py)

The `StreamState` class provides real-time feedback in Telegram while the agent works:

- **Typing indicator** — A background thread sends `typing` chat actions every 4 seconds, keeping the "typing..." status visible in the chat header for the full duration.
- **Tool activity feed** — Each tool call immediately updates the status message with human-readable labels (e.g. `📄 Reading config.py`, `▶️ Running npm test`). Labels are defined in `_TOOL_LABELS` for both Trinity's own tools and Claude SDK built-in tools.
- **Text streaming** — Accumulated text chunks are pushed to the status message, throttled to every 3 seconds.
- **Finalize** — The status message is replaced with the final response, auto-chunked at 4096 chars.

### Two-Scope, Three-Tier Memory System (memory/)

Memory has two scopes:

- **Local** (`<workspace>/.trinity/memory/`) — Project-specific memory, isolated per agent instance. New memories always write here.
- **Global** (`~/.trinity/memory/`) — Shared across all agent instances. Automatically included in search/recall unless the workspace IS the home directory (avoids double-reading).

`global_trinity_dir` in `TrinityConfig` is set automatically by `load_config()`. Search and recall merge results from both scopes, deduplicated by ID, with a `source` field (`"local"` or `"global"`) on each result.

Within each scope, memories are organized into three tiers. Each scope is an **embedded SQLite database** at `<scope>/memory/memory.db` (WAL + `busy_timeout` + `BEGIN IMMEDIATE`, mirroring `kanban/db.py`) with an **FTS5** full-text index over `summary`+`content`. `memory/db.py` holds the connection/schema helpers; `memory/store.py` is the SQLite-backed CRUD layer (public API unchanged). This replaced the old "Markdown files + monolithic `index.json`" design, which rewrote the whole index on every op (O(N²)), rewrote files on reads, re-parsed every file per search, and had no cross-process safety — see `docs/superpowers/specs/2026-05-28-memory-db-investigation.md`. The Markdown files under `memory/{tier}/` are kept as a **synced, human-readable export** (source of truth is the DB; never read on the hot path). On first init, a legacy `index.json` + `.md` layout is migrated into the DB automatically (idempotent; `index.json` renamed to `.migrated`). Use `store.get_memory()` for side-effect-free reads and `store.recall_memory()` only for a deliberate reinforcement read (it bumps access stats). Secret-shaped substrings are redacted before persistence.

- **short-term** — New memories land here, decay after 48h by default
- **long-term** — Promoted from short-term when score exceeds `promotion_threshold`
- **permanent** — Manually promoted, never decay

Seven segments with different weights and decay rates: `corrections` (0.95), `preferences` (0.85), `relationships` (0.8), `skills` (0.75), `facts` (0.7), `projects` (0.6), `context` (0.5).

Pre-reply recall (`memory/recall.py`) runs before every response with three engines: `local` (keyword search), `sdk` (LLM-driven with tool use), or `hybrid` (local first, SDK fallback). All engines search both local and global scopes.

### Knowledge / Second Brain (knowledge/wiki.py)

A view layer over the memory system. Wiki entries are memories tagged with `kind` metadata: `issue`, `decision`, `audit`, `lesson`, `signal`, `correction`. Generates a compact briefing (~2K chars) injected into every agent's identity prompt.

### Employee System (employees/)

Each employee has an `identity.md` in `.trinity/employees/<name>/`. Templates in `templates/employees/` provide starting identities for roles: CEO, CMO, CTO, CFO, COO, Research IC, SEO Operator, Product Mgr, Custom.

Two loading modes:
- **Full identity** — Complete identity.md + company + briefing + workspace path + memories (Track 2)
- **Compact identity** — First 500 chars + company name + workspace path + briefing (Track 1)

### Telegram Bot (telegram/)

- `bot.py` — Long-polling loop with per-chat worker threads (one thread per `chat_id`, messages within a chat are sequential, different chats run in parallel)
- `acl.py` — Access control (allowlist by user ID)
- `streaming.py` — Live status updates with typing indicator, tool activity feed, and text streaming
- `api.py` — Thin wrapper around Telegram Bot API (includes `send_chat_action` for typing indicators)

### Scheduler (scheduler/engine.py)

Background cron engine that checks cycles every 60 seconds. Cycles are defined in `trinity.toml` with standard 5-field cron expressions. Each cycle runs in its own thread with a specific employee and reports results to a Telegram group.

### Tool System (tools/)

Tools are registered in `tools/registry.py` with Anthropic-format schemas and handler functions. Tool subsets control access per role:
- `BUILDER_TOOLS` — filesystem, search, shell, git, knowledge, telegram
- `RESEARCHER_TOOLS` — read-only filesystem, search, web, memory, telegram
- `MEMORY_TOOLS` — memory CRUD operations

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

## Configuration

All config lives in `trinity.toml` at the workspace root (parsed with `tomllib`). The `TrinityConfig` dataclass in `config.py` provides typed access with sensible defaults. Key sections: `[company]`, `[auth]`, `[agent]`, `[telegram]`, `[memory]`, `[scheduler]`, `[employees]`, `[workspace]`.

Project-specific secrets (bot tokens, API keys) go in `.env` in the workspace root. The CLI auto-loads `.env` on startup — values only set if not already in `os.environ`.

## Daemon Lifecycle

- `trinity start --daemon` — Forks to background, writes PID to `.trinity/state/trinity.pid`, logs to `.trinity/logs/daemon.log`
- `trinity stop` — Reads PID file, sends SIGTERM, waits up to 5s, falls back to SIGKILL, cleans up PID file
- `trinity restart` — Stops then starts as daemon (use `--foreground` for foreground restart)

## Runtime State

All runtime state lives under `.trinity/`:
- `employees/<name>/identity.md` — Employee persona definitions
- `memory/{short-term,long-term,permanent}/` — Memory files (YAML frontmatter + markdown)
- `memory/index.json` — Memory index for fast lookup
- `knowledge/` — Legacy flat files + signals
- `views/briefing.md` — Generated briefing
- `chat-history/<chat_id>.json` — Rolling per-chat history
- `sessions/<date>.md` — Daily session logs
- `state/` — PID file, offset, scheduler state, usage tracking
- `logs/` — Daemon logs
