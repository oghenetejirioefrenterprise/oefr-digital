# Memory "Database" Investigation, Recommendations & Migration

**Date:** 2026-05-28
**Status:** Implemented (memory store migrated to SQLite+FTS5)
**Scope:** The persistence layer of Trinity Agent — primarily the three-tier
memory system, with notes on commitments / usage / chat-history.

---

## 1. Executive summary

Trinity has five persistence stores. One — the **kanban board** — was already on
embedded SQLite (WAL, indexes, `BEGIN IMMEDIATE`) and is the in-repo gold
standard. The other four were hand-rolled JSON/Markdown stores. The headline
**memory system** (the "gets smarter every day" feature) was the worst:

- Every write rewrote a monolithic `index.json` (**O(N) per op, O(N²) over a run**).
- A logical **read** (`recall_memory`) rewrote both the `.md` file *and* the whole
  index just to bump an access counter.
- **Search re-opened and re-parsed every `.md` file on disk on every query.**
- The only lock was an in-process `threading.Lock`, giving **zero protection**
  against the separate CLI processes (`trinity memory/run`) that mutate the same
  files concurrently with the daemon → silent lost updates and ID collisions.

An adversarially-verified audit (30 agents, findings cross-checked and
severity-adjusted; 5 plausible-but-false findings rejected) plus a real benchmark
confirmed this. **Recommendation: migrate the memory store to embedded SQLite +
FTS5, mirroring `kanban/db.py`** — *not* a rewrite in another language. This was
implemented behind the unchanged public API.

### Benchmark (real code, before vs after)

| Operation | Old (files + index.json) | New (SQLite + FTS5) | Speedup |
|-----------|--------------------------|---------------------|---------|
| store 3,000 memories | **186 s, O(N²)** | **4.4 s, ~linear** | **~42×** |
| store / op | 11.5 ms (and rising) | 1.4 ms (flat) | — |
| recall by id / op | ~21 ms | 0.85 ms | **~25×** |
| keyword search / query | 58–584 ms | 11–27 ms | **5–20×** |
| scaling 1k→3k (store) | 16.1× (quadratic) | 3.3× (linear) | root cause fixed |

---

## 2. What the "database" actually is

| Store | File | Backend | Status before |
|-------|------|---------|---------------|
| Kanban | `kanban/db.py` | SQLite (WAL, indexes, BEGIN IMMEDIATE) | ✅ Gold standard |
| **Memory** | `memory/store.py` + `search.py` | Markdown files + monolithic `index.json` | ❌ Migrated → SQLite |
| Commitments | `commitments/store.py` | single `commitments.json`, full rewrite/op | ⚠️ Low-severity follow-up |
| Chat history | `app.py` | per-`chat_id` JSON, full read+rewrite/turn | ⚠️ Bounded; low priority |
| Usage | `agents/base.py` | `state/usage.json`, rewrite/agent-run | ⚠️ Low priority |

---

## 3. Verified findings (audit + adversarial verification)

Severity is the *adjusted* level after a skeptical verifier re-read the code for a
**single-user** system. All are real; the migration fixes the memory ones.

| # | Finding | Sev | Fixed by migration? |
|---|---------|-----|---------------------|
| 1 | In-process `threading.Lock` only → cross-process lost updates (memory, commitments, usage) | high | ✅ memory (SQLite WAL+BEGIN IMMEDIATE serialises across processes) |
| 2 | `_next_id` collision → two processes derive the same id, one `.md` silently overwritten (data loss) | high | ✅ id generated inside `BEGIN IMMEDIATE`; PK uniqueness |
| 3 | Full `index.json` rewrite + fsync on **every** store/recall/update/forget/promote (O(N²)) | high | ✅ single-row INSERT/UPDATE |
| 4 | Write-on-read: `recall_memory` rewrites `.md` + whole index on a read | medium | ✅ one `UPDATE ... RETURNING`, no file write |
| 5 | Search re-parses every `.md` on every query (no FTS, no cached body) | medium | ✅ FTS5 indexed match |
| 6 | `cleanup` `unlink()`s `.md` files but never updates the index → ghost rows; can delete **permanent**/open-issue memories irreversibly; `trinity memory cleanup` deleted by default (`dry_run=False` at CLI) | high | ✅ routes deletes through `forget_memory`; protects permanent/open-issue; CLI now dry-run unless `--apply` |
| 7 | `update_memory_metadata` wrote the `.md` **outside** the lock → file/index divergence (TOCTOU) | medium | ✅ single atomic statement |
| 8 | Non-atomic `.md` writes (`write_text`, no tmp+rename) | medium | ✅ DB is atomic; export uses atomic rename |
| 9 | `_load_index` swallows a parse error and returns `[]` → next save wipes the catalog | medium | ✅ SQLite raises on corruption, never silently empties |
| 10 | `_write_memory_file` dropped falsy fields (`importance: 0.0`) via `if meta[key]` | low | ✅ stored as a real column; export uses presence check |
| 11 | No secret scrubbing on the **write** path — a pasted key persisted plaintext & re-surfaced into the prompt | medium | ✅ `redact()` wired into `store_memory`/`update_memory` |
| 12 | `recall` resets the decay clock + inflates promotion signal on every read | low | partial — added side-effect-free `get_memory`; readers (search/briefing) use it |
| 13 | Briefing does ~9 full-index scans, regenerated after every `log_*` | medium | improved — indexed `WHERE kind=?` SELECTs (debounce still a follow-up) |
| 14 | commitments/usage full-file rewrite per op | low | follow-up (documented) |
| 15 | compactor failure-state RMW unlocked | low | follow-up (documented) |

**Rejected by the verifier** (kept us honest): a "chat-history concurrent writer"
race (the writers are serialised through one per-chat worker thread), a
"write-on-read fires on every reply" claim (the routine pre-reply recall path is
read-only — `recall_memory` only runs on an explicit `memory_recall` tool call),
a "decay/promotion full-scan amplification" (those functions are dead code), and
two frontmatter-coercion impact claims (the index, not the parser, is
authoritative for the affected fields).

---

## 4. Options considered

| Option | Verdict |
|--------|---------|
| **1. Optimize files in place** (cross-process flock + in-memory cache + dirty tracking) | Rejected as the destination — masks the O(N) design instead of fixing it; cross-process cache invalidation is as hard as a DB. Good *stopgap* only. |
| **2. Embedded SQLite + FTS5** (mirror `kanban/db.py`), Markdown kept as a synced export | **Chosen.** Fixes all root causes at once; pattern already proven in-repo; SQLite is C and already a dependency; FTS5 confirmed (sqlite 3.45.1). |
| **3. Rewrite the harness/storage in Go or Rust** | **Rejected.** See below. |

### Language-rewrite verdict: NOT JUSTIFIED

The cost was **algorithmic and I/O-bound, not CPU-bound**. A faster interpreter
running an O(N) full-file rewrite is still O(N). The actual fix — SQLite — is
written in C, already linked into CPython, and already used by the kanban board:
you get C-speed B-tree + FTS5 and correct cross-process locking *without leaving
Python*. The workload is single-user and low-QPS (one human over Telegram + a few
cron cycles), so there is no throughput ceiling a compiled language would lift,
and the surrounding stack (providers, plugin registries, Telegram bot, scheduler,
Claude Agent SDK) is all Python. A Go/Rust sidecar would add a second process and
an IPC boundary for **zero** user-perceptible gain. Hence the work went into
storage *design*, and **no fork was created**.

---

## 5. What was implemented

**New:** `src/trinity/memory/db.py` — connection/schema helpers mirroring
`kanban/db.py`: `journal_mode=WAL`, `busy_timeout=5000`, per-connection
`synchronous=NORMAL`, `BEGIN IMMEDIATE` write transactions. One `memories` table
(one row per memory incl. `content`), indexes on `tier` / `(kind,status)` /
`scope` / `created`, an external-content **FTS5** table over `summary`+`content`
kept in sync by triggers, and a `schema_meta` table for migration versioning.

**Rewritten:** `src/trinity/memory/store.py` — every public function
(`init_memory`, `store_memory`, `recall_memory`, `update_memory`,
`forget_memory`, `promote_memory`, `list_memories`, `update_memory_metadata`,
`query_by_kind`, plus constants `TIERS`/`SEGMENTS`/`SEGMENT_WEIGHTS`/
`SEGMENT_DECAY_MODIFIERS`) keeps its **exact signature and return shape**, now
backed by SQLite. Additions:
- `get_memory(trinity_dir, id)` — side-effect-free content accessor (no
  decay-clock reset), used by search/briefing.
- `search_rows(trinity_dir, words)` — FTS5 candidate retrieval for `search.py`.
- IDs generated inside `BEGIN IMMEDIATE` via `MAX(CAST(...))` (collision-proof,
  O(today) in C); writes use `... RETURNING *` to avoid an extra SELECT.
- `redact()` applied to content on store/update (secret-at-rest).
- One-time idempotent migrator: imports a legacy `index.json` + tier `.md` files
  into the DB on first init (guarded cross-process by `schema_meta`), then renames
  `index.json` → `index.json.migrated`. **Verified on a copy of the real global
  store (5 memories, content intact).**

**Markdown is now a synced, non-authoritative export** (DB is source of truth):
written with an atomic rename but **no fsync** (it's regenerable), and **never
read on the hot path** — so the human-readable files and the 3 AM git backup are
preserved without costing performance.

**Updated consumers:**
- `memory/search.py` — FTS5 candidates, identical ranking formula
  (`keyword_overlap × effective_importance`) and output shape.
- `knowledge/wiki.py` — `_memory_content_for_entry` uses `get_memory`; dropped the
  cross-module `_parse_memory_file` / `_tier_dir` imports.
- `memory/cleanup.py` — deletions route through `forget_memory` (DB row + export
  removed together; no ghosts); permanent tier and open issues are protected.
- `cli.py` — `trinity memory cleanup` is **dry-run by default**; `--apply` deletes.
- `_io.py` — `atomic_write_text(..., fsync=False)` for regenerable artifacts.
- `.gitignore` — ignores `memory.db*` (+ WAL/SHM) and `index.json[.migrated]`.

**Tests:** `tests/test_memory_store.py` (23 tests) covers the CRUD contract, FTS
search + scope filtering, the one-time migration (+ idempotency), and explicit
regressions for write-on-read, ID collisions under concurrency, secret redaction,
falsy-field preservation, and side-effect-free `get_memory`. Full suite: **136 pass.**

---

## 6. Migration safety

- Triggered automatically on first `init_memory` per workspace; the daemon does
  this on restart.
- **Non-destructive:** `index.json` is renamed to `index.json.migrated` (not
  deleted) and the `.md` files stay in place (they become the export). Rollback =
  delete `memory.db*` and rename `index.json.migrated` back.
- Idempotent and cross-process safe (`schema_meta.legacy_migrated` guard,
  `INSERT OR IGNORE`).

---

## 7. Follow-ups — IMPLEMENTED (2026-05-29)

The recommended follow-ups were subsequently applied:

1. **Commitments → SQLite** — `commitments/db.py` (new, WAL + BEGIN IMMEDIATE,
   mirrors kanban) + `commitments/store.py` rewritten on SQLite with the same
   public API (`add_or_merge`/`list_records`/`due_now`/`update_status`/
   `purge_terminal`) and a one-time migration from `commitments.json`.
2. **Usage counter cross-process safe** — `_persist_usage` (agents/base.py) now
   wraps its read-modify-write in a new `_io.file_lock` (fcntl advisory lock),
   so concurrent CLI/daemon writers no longer drop token increments.
3. **Chat history** — the audit's concurrency claim was *rejected* (a single
   per-chat worker thread serialises writes), and the file is bounded by
   compaction, so a full JSONL rewrite was unwarranted. Added a defensive
   `file_lock` around `_save_chat_history`'s read-append-write for cross-process
   safety; format unchanged.
4. **Briefing** — the per-write O(N) cost was already removed by the SQLite
   migration (indexed `WHERE kind=?` instead of full-index reparse). Collapsed
   `generate_briefing`'s four issue-status queries into one query + Python
   partition.
5. **Decouple decay from reads** — added a `last_reinforced` column;
   `effective_importance` now decays from `last_reinforced` (set on store/update,
   **not** on `recall`), so reading a memory no longer resets its decay clock.
   `db._ensure_columns` adds + backfills the column on existing DBs.
6. **Cross-workspace `pull` ingests into the DB** — `cmd_memory_pull` now calls
   `store_memory` for each shared `.md` (previously it only wrote files the DB
   never read). `file_lock` also guards the compactor failure-state RMW.

New tests cover the decay-decouple behaviour and the commitments migration;
full suite: **142 passing.**
6. **Cross-workspace sharing (`trinity memory publish` / `pull`)** still operates
   on the Markdown export. `publish` (cli.py) reads the long-term `.md` files —
   fine, the export carries current content. But `pull` writes `shared_*.md`
   files into `long-term/` **without inserting them into the DB**, so pulled
   memories are invisible to the SQLite-backed store (search/recall/list).
   Follow-up: have `pull` ingest via `store_memory`, and `publish` query the DB
   by category, instead of touching the export files directly. (Config-gated
   feature, out of scope for this change.) This is why the synced Markdown
   export was **kept** rather than removed — it has a live consumer.

## 8. Post-implementation review

An adversarial review workflow (9 agents) checked the implementation before it
went live. It caught a real flaw: cleanup originally *selected* deletion
candidates from the Markdown export, whose `last_accessed` is now frozen (recall
no longer rewrites it), so `cleanup --apply` could have deleted hot,
frequently-recalled memories. Fixed by making cleanup fully DB-driven (it now
reads the live `last_accessed`). Also fixed: `trinity status` read the now-renamed
`index.json` (switched to `list_memories`), and the migrator could import empty
content for a missing `.md` (falls back to the summary). A `simplify` pass then
deduped the read-path boilerplate (`_read` context manager), collapsed the
4×-table-read in `run_cleanup` to a single fetch, and removed a redundant helper.
Final: **139 tests pass.**
