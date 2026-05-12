# Trinity Agent — Six Improvements (PRD)

**Status:** ready for implementation
**Author:** TJ (Trinity)
**Date:** 2026-05-06

## Why

Trinity is the agent layer running OEFR Digital. Current pain points:

1. **Memory injection is unfenced on output** — recalled memory could leak its `<active_memory>` wrapper to the user, and a memory entry with adversarial content has no clear "this is data, not directive" boundary.
2. **No handle for inline file/URL/diff references in Telegram messages** — users must request a tool round-trip to get the agent looking at a specific file.
3. **Compaction is naive truncation** — when chat grows past `2 × buffer`, the oldest entries are summarised but the prompt is "compress this conversation" with no structured handoff. The agent later re-asks about things it had already resolved.
4. **No subagent delegation** — long sequential research tasks block one Telegram chat for the full walk; cannot parallelise.
5. **No proactive nudging** — Trinity remembers but doesn't follow up. "I'll check on this tomorrow" is forgotten unless the user re-asks.
6. **No shared work-tracking surface for the autonomous company** — 7 employee personas, but no atomic "I'm working on this, don't double-claim" primitive. Hand-offs between cycles are coded ad-hoc, not declarative.

## What

Six concrete subsystems. Each is independently shippable and feature-flagged where appropriate.

---

### 1. Memory fence scrubber

**Problem.** `app.py` already wraps recall results in `<active_memory>...</active_memory>` and `_safety.sanitize_for_prompt` already strips embedded fence tags from the *injected* content. But there is **no scrubber on the output side** — if the model echoes the `<active_memory>` block in its reply, the user sees it. There is also no streaming-aware scrubber: a fence opening in chunk N and closing in chunk N+5 would leak partial content during streaming.

**Solution.**
- New `trinity/memory/scrubber.py` with a `MemoryFenceScrubber` class:
  - `scrub(text)` — non-streaming case
  - `scrub_chunk(chunk)` — streaming case; holds back the longest possible partial-tag suffix between calls
  - `flush()` — call at end of stream; if a fence opened but never closed, drops the in-span content (Hermes pattern: "leaking partial memory context is worse than a truncated answer")
- Wire into `telegram/streaming.py`:
  - `on_text` → scrub before buffering
  - `finalize(response)` → scrub the final string
- Wire into the agent loop's `on_text` callbacks in `agents/conversational.py` and `agents/builder.py` so the scrubber sits between the provider's stream and Telegram's stream.

**Out of scope.** Reflowing Markdown after scrubbing. The fence is rare-enough that a simple removal is enough.

**Acceptance.**
- Unit test: input `"hello <active_memory>secret</active_memory> world"` → output `"hello  world"`.
- Streaming test: same string split into 1–3 chunks across the fence → output identical to non-streaming.
- Regression: 43 existing tests still pass.

---

### 2. Inline `@`-references

**Problem.** From a phone, you can't run a tool to get the agent to look at a specific file or URL. Today: ask the agent → agent issues `read_file` tool → response. That's two round trips for trivial context-bringing.

**Solution.** Pre-process the incoming text in `app.py` (before classification, after bot-mention strip). Expand the following inline syntaxes into fenced content blocks at the bottom of the message:

| Syntax | Expansion |
|---|---|
| `@file:path/to/x.py` | contents of file (path resolved against workspace root, ~16 KB cap) |
| `@folder:path` | `ls -la` style listing, top 200 entries |
| `@url:https://...` | first 8 KB of fetched body via existing `tools/web.py` |
| `@git:HEAD~3` (or any rev) | `git show <rev> --stat` plus first 8 KB of `git show <rev>` |
| `@diff` | `git diff` working tree |
| `@staged` | `git diff --cached` |

Sensitive-path blocklist (matched as substring, case-insensitive):
`.ssh, .aws, .gnupg, .pgpass, .netrc, .profile, credentials, secrets`. Match → expansion is replaced with `[redacted: sensitive path]` and the agent is told why.

Total expansion budget per message: **24 KB**. Per-reference cap: **8 KB** (file/url) / **16 KB** (file). When the budget is exceeded, later references are skipped with a `[skipped: budget]` marker.

**Files.** New `trinity/context/__init__.py` and `trinity/context/references.py`. Hook in `trinity/app.py` `handle_message` between `text = re.sub(...).strip()` and `classification = router.classify(...)`.

**Acceptance.**
- Unit tests for each prefix using a tmp workspace with stub files.
- Sensitive-path test: `@file:.ssh/id_rsa` → redacted, no content leaked.
- Budget test: 4 large files referenced → first three expanded, fourth marked skipped.

---

### 3. Structured-handoff compaction

**Problem.** `_compress_entries` in `app.py` produces a single-blob summary with the prompt *"You compress chat transcripts."* Trinity's compactor doesn't tell the next-window assistant that "the requests in this summary are already fulfilled — do NOT redo them," doesn't separate Resolved from Pending, and has no failure cooldown.

**Solution.**
- New `trinity/memory/compactor.py`:
  - `compact_history(entries, config) -> CompactionResult | None`
  - Uses `config.agent.router_model` (Haiku — cheap, separate cache).
  - Prompt structure (verbatim from Hermes' working pattern, tightened):
    ```
    You are summarising a conversation handoff. The continuation will be
    handled by a different assistant in a fresh context window.

    Output sections:
      RESOLVED — tasks/questions completed in this window. The next
        assistant must NOT re-fulfil these.
      PENDING — open threads, deferred items, things the user expects later.
      ACTIVE — what was happening in the last 1–2 turns; the immediate context.
      USER PREFERENCES — corrections, style, constraints to carry forward.

    Be dense and factual. No filler. Target ~{target_chars} chars total.
    ```
  - Token budget: target = `0.20 × sum(len(entry) for entry in old_entries)`, ceiling `12_000` chars.
  - Failure cooldown: persisted in `.trinity/state/compactor_state.json`, `last_failure_at` and `failure_count`. After failure, skip compaction for 600s; after 3 consecutive failures escalate to skipping for 3600s.
- Replace the call site in `_save_chat_history` (currently `_compress_entries(...)`) and rewire `_handle_compress` to use the new module.
- The synthetic entry's `user` field becomes `"[compressed handoff]"` (was `"[compressed history]"`) — and the assistant text is the structured summary.

**Acceptance.**
- Unit test with stubbed provider returning a known summary; verify structure preserved, cooldown sets/clears.
- Integration test: simulate 30 saves with buffer=5, confirm bounded oscillation still holds.
- Regression: existing `_handle_compress` smoke still works (refactored to call new module).

---

### 4. `delegate_task` subagent tool

**Problem.** "Research these 5 competitors and summarise" runs sequentially in one chat — 5x the wall time the user sees.

**Solution.**
- New tool `delegate_task` registered in `BUILDER_TOOLS` only (not RESEARCHER).
- Signature: `delegate_task(goal: str, role: "leaf"|"orchestrator" = "leaf", toolset: "researcher"|"builder" = "researcher", max_concurrent: int = 3)`.
- Spawn semantics:
  - `role="leaf"` (default) — runs as a **single** subagent, depth-incremented; that subagent CANNOT spawn (its `delegate_task` is not exposed). Returns the subagent's final text.
  - `role="orchestrator"` — accepts a `goals: list[str]` (max 5) instead of `goal`; spawns up to `max_concurrent` leaves in a `ThreadPoolExecutor`, returns a single concatenated result.
- Depth tracking: `threading.local` named `_DEPTH`, default 0. `delegate_task` increments before spawn, decrements after. Max global depth = 2; spawning past that returns an error, never blocks.
- The subagent uses the **same provider** but a tighter system prompt ("You are a focused subagent; your only job is to satisfy the goal. Reply with the result, no preamble.") and the chosen toolset.

**Files.** `trinity/tools/delegate.py` (new), edit `trinity/tools/registry.py` to register the tool name + handler in `BUILDER_TOOLS`.

**Acceptance.**
- Test: orchestrator with 3 fake goals → 3 subagent invocations, results concatenated.
- Test: leaf inside leaf → returns explicit "delegation depth exceeded" error, no exception.
- Token usage logged via existing `set_usage_path` infra so the user can see subagent cost.

---

### 5. Commitments → Telegram follow-ups

**Problem.** Trinity passively recalls; it doesn't proactively nudge. "I'll check Reddit alternatives tomorrow" is forgotten unless the user asks.

**Solution.**
- New module `trinity/commitments/`:
  - `types.py` — `CommitmentRecord` dataclass:
    ```python
    @dataclass
    class CommitmentRecord:
        id: str                  # uuid
        kind: str                # event_check_in | deadline_check | open_loop
        text: str                # the natural-language promise
        chat_id: str             # where to deliver the nudge
        due_at: str              # ISO timestamp
        dedupe_key: str          # for idempotent merge
        confidence: float        # 0..1
        status: str              # pending | sent | dismissed | snoozed | expired
        created_at: str
        sent_at: str | None = None
        snoozed_until: str | None = None
    ```
  - `store.py` — JSON file `.trinity/state/commitments.json`. Operations: `add_or_merge(record)`, `due_now(t)`, `mark_sent(id)`, `mark_dismissed(id)`, `snooze(id, until)`, `list_by_chat(chat_id, status?)`.
  - `extraction.py` — Haiku extraction pass over the latest `(user, assistant)` exchange. Returns 0..N candidate records.
  - `runtime.py` — Background thread, polls every 60s, dispatches due records to Telegram via the existing `TelegramAPI`.
- Hook in `app.py` post-response background extractor (alongside `_bg_extract`).
- Fast-path keywords:
  - `/commitments` — list this chat's open commitments
  - `/done <id>` — mark sent + dismissed
  - `/snooze <id> <duration>` — snooze (e.g. `/snooze abc123 2h`)

**Files.** `trinity/commitments/{__init__.py,types.py,store.py,extraction.py,runtime.py}`. Edits: `trinity/app.py` (extraction hook + 3 fast paths), `trinity/router.py` (3 fast-path constants + patterns), `trinity/cli.py` (start runtime alongside scheduler).

**Storage.** Single JSON file with atomic writes via existing `_io.atomic_write_json`. Acceptable for ~1000 records; revisit if it grows.

**Acceptance.**
- Test: extraction stub returns one record → store contains it after merge.
- Test: due-now selection respects `due_at` and `status`.
- Test: dedupe — same record extracted twice = one row, latest text/confidence wins.

---

### 6. Kanban subsystem

**Problem.** Seven employees as personas, no shared work surface. Hand-offs between cycles are coded ad-hoc.

**Solution.** Faithful subset of Hermes' kanban, scaled to Trinity's needs.

**Storage.** SQLite at `.trinity/kanban/board.db`, WAL mode.

**Schema (4 tables).**
```sql
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  body TEXT,
  status TEXT NOT NULL DEFAULT 'triage',  -- triage|todo|ready|running|blocked|done|archived
  assignee TEXT,                          -- employee name
  priority INTEGER NOT NULL DEFAULT 3,    -- 1=high, 5=low
  created_by TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  result TEXT,                            -- final summary on completion
  claim_lock TEXT,                        -- uuid of current claimer
  claim_expires TEXT,                     -- ISO; null when not claimed
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  last_failure_error TEXT,
  dedupe_key TEXT UNIQUE                  -- optional idempotency
);
CREATE INDEX idx_tasks_status_assignee ON tasks(status, assignee);

CREATE TABLE task_links (
  parent_id INTEGER NOT NULL,
  child_id INTEGER NOT NULL,
  PRIMARY KEY (parent_id, child_id),
  FOREIGN KEY (parent_id) REFERENCES tasks(id),
  FOREIGN KEY (child_id) REFERENCES tasks(id)
);

CREATE TABLE task_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  author TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE task_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  kind TEXT NOT NULL,                     -- create|claim|complete|block|comment|link|unblock
  payload TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

**Status state machine.**
```
triage  →  todo  (specced)
todo    →  ready  (recompute_ready: all parents in done)
ready   →  running  (atomic claim by assignee)
running →  done | blocked
blocked →  ready  (manual unblock or parent completes)
*       →  archived
```

**Atomic claim.**
```sql
UPDATE tasks
   SET status='running', claim_lock=?, claim_expires=?, started_at=?
 WHERE id=? AND status='ready' AND (claim_lock IS NULL OR claim_expires < ?)
```
`rowcount = 1` → claim succeeded; `0` → lost the race or task not ready.

**recompute_ready.** After any state change, find tasks in `todo` whose all `task_links.parent_id` are `done` (or have no parents) → promote to `ready` and emit `task_events` row.

**build_worker_context(task_id) -> str.**
Returns markdown:
```
## Task #42 — Refactor X
**Assignee:** Closer  **Priority:** P2

<body verbatim>

### Comments
- [Wolf @ 2026-05-05 14:20] thinking we should...
- [Closer @ 2026-05-05 16:01] starting now

### Parent task results
#### Task #38 — Research X
<result of #38>
```

**Tools (added to BUILDER_TOOLS).**
- `board_create_task(title, body?, assignee?, priority?, parents?, dedupe_key?)` → returns task id
- `board_list_tasks(status?, assignee?, limit?)` → list of tasks (id, title, status, assignee)
- `board_show_task(task_id)` → full task + comments + parent results (uses `build_worker_context`)
- `board_claim_task(task_id, claimer)` → bool
- `board_complete_task(task_id, result, summary?)`
- `board_block_task(task_id, reason)`
- `board_comment_task(task_id, author, body)`
- `board_link_tasks(parent_id, child_id)`

**Scheduler integration.** `scheduler/engine.py`:
- Pre-cycle: call `kanban.recompute_ready()`, then claim all `ready` tasks where `assignee == cycle.employee` (up to 3 per tick).
- For each claimed task, prepend `build_worker_context(task_id)` into the cycle's task prompt as the `# Active board tasks` section.
- Post-cycle: if the agent's response contains a `BOARD_COMPLETE: <task_id>` line, call `board_complete_task` with the rest of the response as `result`. (Pattern is opt-in for cycles to use; tools also work.)

**Identity injection.** `employees/loader.py` — `load_full_identity` appends a `# Active Board Tasks` section listing the employee's open tasks (id, title, status). Compact identity is unchanged (chat budget too tight).

**Wiki integration.** `knowledge/wiki.py` `generate_briefing` — add a section "Open tasks: 12 (Wolf 3, Closer 4, Lead Hunter 5)".

**CLI.** `trinity board {create,list,show,assign,complete,block,link,unblock,archive}` for human inspection from terminal.

**Acceptance.**
- Unit test: full lifecycle — create A, B (B parent of A), complete B, expect A promoted ready, claim A, complete A.
- Concurrency test: two threads racing to claim same task — exactly one wins.
- Integration test: scheduler picks up ready task for an employee and runs cycle with worker_context.
- CLI smoke: `trinity board create / list / show`.

**Out of scope (v1).**
- `task_runs` table (no per-step run tracking)
- Workspace materialization (`workspace_kind='scratch'`)
- Diagnostics module (5 distress-signal checks) — defer
- Telegram subscriptions per task — defer
- Multi-board support — single board per workspace

---

## Phasing

| Phase | Items | Risk |
|---|---|---|
| A | Memory scrubber, Inline refs | low |
| B | Compaction (replaces existing brittle code) | medium |
| C | delegate_task | medium |
| D | Commitments | medium-high |
| E | Kanban | high |

Each phase is committed and tested before the next starts. Daemon is restarted **once at the end** to pick up everything atomically.

## Risks + mitigations

- **Compaction failure storms** → 600s cooldown + 3-failure escalation to 3600s.
- **delegate_task budget bombs** → hard depth=2 cap, max_concurrent=3, results truncated at 50KB each.
- **Commitments spam** → confidence threshold 0.6 default, dedupe_key prevents double-fire, runtime polls every 60s (not faster).
- **Kanban deadlocks** → all writes go through `BEGIN IMMEDIATE` with a 5s busy_timeout; CAS on claim_lock is single-row.
- **Disk growth** → kanban + commitments are JSON/SQLite at workspace root; archived tasks stay in DB but are excluded from default queries.

## Success criteria

- All 6 features land with tests passing.
- The dataStructured daemon restarts and stays up for 10+ minutes with the new code.
- Tracker for at least one of: a memory scrubbing event in the logs (no leaked fence in any reply), an `@file:` expansion, a kanban task created and claimed by a cycle, a commitment fired.
- Token cost per turn does not regress more than 10% on a baseline test message.

## Files touched (summary)

```
docs/prds/2026-05-06-trinity-improvements.md       (this PRD)

src/trinity/memory/scrubber.py                     (new — #1)
src/trinity/memory/compactor.py                    (new — #3)
src/trinity/context/__init__.py                    (new — #2)
src/trinity/context/references.py                  (new — #2)
src/trinity/tools/delegate.py                      (new — #4)
src/trinity/commitments/__init__.py                (new — #5)
src/trinity/commitments/types.py                   (new — #5)
src/trinity/commitments/store.py                   (new — #5)
src/trinity/commitments/extraction.py              (new — #5)
src/trinity/commitments/runtime.py                 (new — #5)
src/trinity/kanban/__init__.py                     (new — #6)
src/trinity/kanban/db.py                           (new — #6)
src/trinity/kanban/board.py                        (new — #6)
src/trinity/kanban/cli.py                          (new — #6)

src/trinity/app.py                                 (edit — #1,2,3,5)
src/trinity/router.py                              (edit — #5)
src/trinity/cli.py                                 (edit — #5,6)
src/trinity/config.py                              (edit — knobs for each)
src/trinity/tools/registry.py                      (edit — #4,#6)
src/trinity/scheduler/engine.py                    (edit — #6)
src/trinity/employees/loader.py                    (edit — #6)
src/trinity/knowledge/wiki.py                      (edit — #6)
src/trinity/telegram/streaming.py                  (edit — #1)

tests/test_memory_scrubber.py                      (new — #1)
tests/test_inline_refs.py                          (new — #2)
tests/test_compactor.py                            (new — #3)
tests/test_delegate.py                             (new — #4)
tests/test_commitments.py                          (new — #5)
tests/test_kanban.py                               (new — #6)
```
