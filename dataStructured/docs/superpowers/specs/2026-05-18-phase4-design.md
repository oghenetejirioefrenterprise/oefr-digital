# DataStructured Phase 4 — Scale

**Status:** Approved 2026-05-18 (delegated; PRD gates explicitly overridden — Phase 4 building before Phase 3 has produced ≥10 customers).
**PRD scope:** vertical plugins, multi-product parallel CEO orchestration, self-improving feedback loops, memory cleanup, multi-workspace coordination.

---

## Goal

Move the autonomous loop from "one-product-per-cycle, identical templates per vertical" (Phase 3) to "many-products-in-flight, specialized per vertical, learning from sales" (Phase 4). Plus framework-level improvements (memory cleanup, multi-workspace) that keep the system from drowning in its own state over time.

## Hard rules (still in force)

Same as v1: public data only, no PII, source URL on every row, production code only, test before claiming done, folder-scoped, no new paid SaaS, never discount.

---

## Five sub-projects

### 4.1 — Vertical-specialized harvest plugins

**Status quo:** `data-engineer` agent uses a single generic harvest approach — Google operators + LLM-guided web scraping. Works for most public datasets but is suboptimal for verticals with structured public sources (e.g. real-estate permits often live in municipal portals with consistent schemas; SaaS pricing pages have repeating patterns; vendor compatibility matrices live in standardized formats).

**Phase 4 deliverable:** plugin discovery layer + ONE first plugin (real-estate permits as proof).

**Architecture:**
- New directory: `scripts/harvesters/` — each vertical plugin is a Python module exposing a single `harvest(brief: dict) -> Path` function returning the cleaned CSV path
- New registry: `scripts/harvesters/__init__.py` — maps niche keywords → plugin module name
- `data-engineer` identity update: check the registry first; if niche matches a plugin, dispatch to it; else fall back to generic harvest
- First plugin: `scripts/harvesters/real_estate_permits.py` — harvests building permits from municipal open-data portals (Socrata-based portals are common; many cities expose them via standardized API)

**Scope:** plugin registry + one plugin + data-engineer integration. Additional plugins are added per-niche over time, not in this sub-project.

### 4.2 — Multi-product parallel CEO orchestration

**Status quo:** CEO picks ONE brief per cycle and runs the entire pipeline serially (data-engineer → data-steward → compliance-officer → engineer). On busy days with multiple high-conviction opportunities, the second-best brief waits 24 hours.

**Phase 4 deliverable:** CEO can pick up to N briefs (default 3, configurable) per cycle and dispatch them with bounded concurrency. Each pipeline runs independently; failures in one don't block others.

**Architecture:**
- `scripts/ceo_orchestrator.py` gets a `dispatch_parallel(briefs, max_concurrent=3)` function using `concurrent.futures.ThreadPoolExecutor`
- CEO identity updates: pick up to 3 briefs at score ≥ 6, dispatch in parallel
- Each brief's progress logged independently to `state/products/<slug>/pipeline-status.json`
- Daily DM rolls up all parallel pipelines: "Today: 3 products shipped, 1 blocked on compliance, 0 failed"

**Scope:** add parallel dispatch, update CEO identity, add pipeline-status JSON per product. No fundamental change to downstream agents.

### 4.3 — Self-improving feedback loops

**Status quo:** Agent identities are static. Compliance officer doesn't know which past PASSes produced sales vs which produced returns. Researcher doesn't know which past opportunity scores correlated with actual revenue.

**Phase 4 deliverable:** sales data flows back into agent context. Each cycle, agents that benefit from history (researcher, product-manager, compliance-officer) get a small "reputation snapshot" injected into their prompt.

**Architecture:**
- New script: `scripts/reputation_snapshot.py` — for each agent that subscribes, compiles a JSON file at `state/reputations/<agent>.json` capturing:
  - For researcher: last 30 days' opportunity briefs → products → sales (which niches produced revenue)
  - For product-manager: last 30 days' specs → products → sales (which spec patterns sold)
  - For compliance-officer: last 30 days' verdicts → revocations (zero so far; this just tracks)
- Each agent's identity gets a `## Reputation snapshot` section instructing them to read `state/reputations/<their-name>.json` at start of cycle
- Snapshot regenerated nightly at 23:00 ET by a new `reputation_refresh` cycle

**Scope:** snapshot generation + 3 agent identity updates + 1 new cycle. No new employee.

### 4.4 — Memory cleanup automation

**Status quo:** trinity-agent memory grows unbounded over time. Short-term memories decay (~48h), long-term decay slower (~30d), but no cleanup of stale/superseded entries.

**Phase 4 deliverable:** automated memory consolidation cycle that runs weekly:
- Identifies stale memories (no reference in last N days)
- Identifies superseded memories (newer memory contradicts older claim)
- Compacts redundant memories (similar content, merge into one)

**Architecture:**
- This is a trinity-agent framework change, not a dataStructured-local change
- New CLI command: `trinity memory cleanup [--dry-run]`
- Logic at `~/apps/trinity-agent/src/trinity/memory/cleanup.py` (already exists per tree — extend it)
- New workspace cron: `memory_cleanup` weekly (Sundays 02:00 ET) calling the CLI in dry-run mode first, then real run

**Scope:** trinity-agent framework change + new dataStructured cycle. Will benefit every workspace that uses trinity-agent.

### 4.5 — Multi-workspace coordination

**Status quo:** Each trinity workspace runs in isolation. If OEFR launches a sister LoB tomorrow (different brand, different product category), they share no learnings.

**Phase 4 deliverable:** a config schema for cross-workspace memory sharing + a helper that allows one workspace to publish "shareable lessons" that another workspace can subscribe to.

**Architecture:**
- This is also a trinity-agent framework change
- Add `[memory.shared]` block to TrinityConfig:
  ```toml
  [memory.shared]
  publish_categories = ["compliance_patterns", "buyer_segments"]  # what THIS workspace shares
  subscribe_to_workspaces = []                                     # other workspaces to read from
  shared_storage_path = ""                                         # where shared memories live (e.g., ~/.trinity/shared/)
  ```
- Helper: `trinity memory publish <category>` writes selected memories to shared storage
- Helper: `trinity memory pull <workspace>` pulls shared memories from another workspace's published file into local long-term memory (with a `source_workspace:` tag)
- For dataStructured: configure `publish_categories = ["compliance_patterns", "buyer_segments"]` so future LoBs can benefit
- No actual sister workspace exists yet — this ships the config schema + helpers + dataStructured's published categories; nobody pulls them until a sister launches

**Scope:** trinity-agent framework change (config schema + CLI subcommands) + dataStructured config update.

---

## Order of execution

Dependencies are minimal but logical:

1. **4.1 — Vertical plugins** — independent. Quick proof.
2. **4.3 — Self-improving feedback loops** — independent. Needed reasonably early so other agents start benefiting.
3. **4.2 — Multi-product parallel CEO** — independent. Quality-of-life for CEO; could ship after 4.1/4.3.
4. **4.4 — Memory cleanup** — trinity-agent change; needs careful testing to not lose useful memories.
5. **4.5 — Multi-workspace** — config schema only; no runtime cross-workspace yet.

Will execute in this order.

## Phase 4 success criteria (per PRD)

- ≥ $1K MRR
- ≥ 3 verticals with shipped products
- Multi-product parallelism stable for 30 days (no resource contention, no failure cascades)
- Founder time-to-DataStructured ≤ 30 min/week

These are all temporal / outcome-dependent. The build is the prerequisite; the criteria validate organically.
