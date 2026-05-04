# DataStructured v1 — Design Spec

**Date:** 2026-05-04
**Author:** Brainstormed with founder via superpowers:brainstorming
**Status:** Approved (ready for implementation plan)
**Reference:** [`docs/PRD.md`](../../PRD.md) — full vision and phase roadmap (v1 → full build)

---

## 1. Context

DataStructured is an autonomous, bootstrapped, public-data-as-a-product company. The model is the BuiltWith / Nomad List / Starter Story playbook: harvest public data the founder has rights to surface, structure it for a specific paying audience, sell as one-time digital product, membership, or SaaS.

The company is a **separate line of business** within the founder's parent enterprise (sharing a Stripe account but otherwise isolated — no shared agents, branding, infra, or orchestration with sibling projects).

This spec covers **v1: the minimum viable autonomous loop**. Roles, channels, and capabilities beyond v1 are mapped in the PRD.

---

## 2. Goal

**90-day primary success criterion: the autonomous system runs hands-off and produces value end-to-end.**

- The agent collective executes the data-product pipeline (research → harvest → clean → compliance → ship) without founder intervention except where compliance flags genuine edge cases.
- Revenue is a secondary success criterion: any sales are a bonus, not the gate.

This priority ordering shapes every architectural choice in the spec — when in doubt, optimize for the system running reliably without the founder, not for polish or marketing reach.

---

## 3. Architecture

### 3.1 Built on trinity-agent

Implementation framework: [`~/apps/trinity-agent`](../../../../trinity-agent) — a portable AI agent framework that lives in the workspace, talks through Telegram, and includes a 3-tier memory system, built-in scheduler, employee templates, and pluggable LLM providers.

trinity-agent provides for free:
- Employee personas with identity files (`.trinity/employees/<name>/identity.md`)
- Cron-based scheduler defined in `trinity.toml` (`[scheduler.cycles.*]`)
- Telegram bot with live tool streaming, typing indicators, message routing
- Three-tier memory (short / long / permanent) with seven decay segments
- Knowledge/wiki briefing auto-injected into agent prompts
- Daemon lifecycle (`trinity start --daemon`, `trinity stop`, `@reboot` recovery)
- Plugin architecture for custom tools and providers

### 3.2 Workspace layout

```
~/apps/dataStructured/
├── trinity.toml                          # company, auth, employees, scheduler config
├── .env                                  # secrets (Telegram token, Stripe keys)
├── .trinity/                             # auto-managed by trinity-agent
│   ├── employees/<name>/identity.md      # six v1 employee personas
│   ├── memory/{short-term,long-term,permanent}/
│   ├── knowledge/                        # wiki + briefings
│   ├── chat-history/, sessions/, state/, logs/
├── state/                                # domain artifacts (NOT trinity internal state)
│   ├── opportunities/{date}-{slug}.json
│   ├── datasets/{slug}/raw-{date}.csv + raw-{date}.metadata.json
│   ├── datasets/{slug}/clean-{date}.csv + quality-report.json
│   ├── datasets/{slug}/provenance.json
│   ├── ethics-ledger/{date}-{slug}.json  # one file per decision, append-only
│   ├── products/{slug}/spec.json
│   ├── products/{slug}/launch-report.json
│   ├── distribution-queue.json
│   └── _schemas/{type}.schema.json       # JSON schemas for validation
├── tests/                                # pytest fixtures + stub LLM provider
├── scripts/                              # Stripe + Gumroad automation scripts
├── docs/
│   ├── PRD.md
│   └── superpowers/specs/2026-05-04-datastructured-design.md
└── README.md
```

### 3.3 The 6 v1 employees

| Employee | Trinity template | One-line role |
|---|---|---|
| `ceo` | `ceo.md` | Strategic orchestrator + sole comms layer |
| `opportunity-researcher` | `research_ic.md` (modified) | Wide-scope demand discovery |
| `data-engineer` | `custom.md` | Public-data harvester (Google operators + AI) |
| `data-steward` | `custom.md` | Quality gate (clean / dedupe / validate) |
| `compliance-officer` | `custom.md` | Hard ethics & legal gate (PASS / FAIL) |
| `engineer` | `custom.md` | Stripe Payment Link + Gumroad listing shipper |

Roles deliberately **not** created in v1 (mapped to PRD phases 2-3): `product-manager`, `marketing-lead`, `partnerships-lead`, `cfo`, `customer-success`. CEO covers product packaging; marketing/distribution waits until the loop is proven.

### 3.4 Execution modes (both supported)

1. **One-shot:** `trinity run "do today's work" -e ceo` — CEO reads state, decides, dispatches downstream employees in-session, sends DM.
2. **Daemon + scheduler:** `trinity start --daemon` runs continuously and fires cycles defined in `trinity.toml`.
3. **Telegram-driven (DM-only):** founder DMs the bot; messages route to CEO; CEO responds (and may dispatch downstream employees on demand).

### 3.5 Cron schedule

Selected to avoid contention with the 30+ active cycles already running on the host machine.

| Time (ET) | Cycle | Employee | Purpose |
|---|---|---|---|
| `0 13 * * *` | `research_scan` | `opportunity-researcher` | Daily wide demand-discovery scan |
| `0 19 * * *` | `ceo_pipeline` | `ceo` | Read briefs, run pipeline, send daily DM |

These slots fall in the cleanest windows: 13:00 ET (clear midday) and 19:00 ET (clear evening).

### 3.6 Communication model

**DM-only. CEO is the sole employee that talks to the founder.**

| Direction | When | Channel |
|---|---|---|
| CEO → founder | End of 19:00 cycle | Telegram DM (one daily summary) |
| CEO → founder | Mid-cycle critical events only | Telegram DM (compliance NEEDS FOUNDER REVIEW, smoke-test failure, daemon error) |
| Founder → CEO | Anytime | Telegram DM |
| Other employees → founder | Never | — |

Other employees write to disk + Trinity memory; CEO reads their output and consolidates.

### 3.7 Storefront integration

| Channel | Mechanism | Notes |
|---|---|---|
| Stripe Payment Link | `engineer` calls Stripe API to create product, price, and customized Payment Link | Same Stripe account as parent enterprise; products prefixed `dsl_` for namespace separation |
| Gumroad listing | `engineer` runs Playwright script to log in and mirror the listing | Browser-only (write API deprecated). Browser-rate, not bot-rate. |
| Custom subdomain | **Not in v1.** | PRD phase 2 — branded site on a subdomain once loop is proven. |

---

## 4. Components: the 6 employees

(Full identity files written during implementation. This section captures the design-level mission, boundaries, and contracts.)

### 4.1 `ceo`

- **Mission:** Pick the highest-impact next move every cycle. Orchestrate the pipeline. Be the one voice the founder talks to.
- **Does:** Reads state, decides what to dispatch, spawns downstream employees in-session, drafts product packaging copy, sends one daily DM, handles ad-hoc DMs.
- **Does NOT:** Harvest data, validate datasets, run ethics checks, ship via API/browser. Delegates everything operational.
- **Hard rules:** One move per cycle. Dispatch over do-it-yourself. Never discount — only stack value. Production code only. Test before claiming done.
- **Inputs:** `state/` artifacts, Trinity memory, founder DMs.
- **Outputs:** Daily DM, ad-hoc DM responses, Trinity memory writes, draft product specs.
- **Template basis:** Trinity `ceo.md` with light additions (dispatch-via-subprocess pattern, daily-DM structure).

### 4.2 `opportunity-researcher`

- **Mission:** Find paying-audience niches with **obvious** demand across ANY vertical. Surface 3-5 sharp briefs per run.
- **Does:** Scans Reddit, Indie Hackers, Gumroad trending, AppSumo, X, YouTube comments, beehiiv/Substack directories for "I'd pay for X data" signals. Cross-references competitor pricing. Scores each. Writes one JSON brief per opportunity.
- **Does NOT:** Pick which to pursue (CEO does), harvest data (engineer does), bias toward founder's vertical (scope is wide-open).
- **Hard rules:** Surface evidence (quote + URL on every claim). Reject niches needing private/auth-walled data. No padding — "no signal today" is acceptable. Every brief gets a 1-10 score with one-sentence justification.
- **Inputs:** 13:00 cron trigger; Trinity memory (skip recently-rejected niches).
- **Outputs:** `state/opportunities/{date}-{slug}.json` (3-5 per run).
- **Template basis:** Trinity `research_ic.md`, narrowed to commercial-signal scanning.

### 4.3 `data-engineer`

- **Mission:** Convert an approved brief into a structured raw dataset using Google search operators + AI synthesis.
- **Does:** Builds 8-15 search queries from the brief. Fetches pages (browser-rendered when needed). Synthesizes rows with `source_url` on every entry. Writes provenance documenting tool chain + queries + gaps.
- **Does NOT:** Decide which brief to harvest (CEO), clean or dedupe (steward), approve for sale (compliance), polish copy (CEO).
- **Hard rules:** Public data only — login pages get rejected. Respect robots.txt + browser-rate. No PII fields. No copyrighted content verbatim. Source URL non-negotiable per row.
- **Inputs:** An opportunity brief CEO has marked APPROVED.
- **Outputs:** `state/datasets/{slug}/raw-{date}.csv` (data payload) + `raw-{date}.metadata.json` (handoff signal) + `provenance.json`.
- **Template basis:** Trinity `custom.md`.

### 4.4 `data-steward`

- **Mission:** Turn raw harvest into product-grade dataset. Sign explicitly or reject explicitly.
- **Does:** Schema fix → dedupe (exact + fuzzy) → null/garbage scrub → source URL liveness sample → cross-source corroboration on high-stakes fields → outlier detection → format normalization → refresh-cadence tag. Logs every transformation with row delta.
- **Does NOT:** Harvest (engineer), check legal/ethics (compliance), silently drop rows.
- **Hard rules:** Signal:noise ≥ 70% — if dropping > 30%, REJECT. Every transformation logged. No ambiguous handoffs.
- **Inputs:** Raw dataset + metadata from data-engineer.
- **Outputs:** `state/datasets/{slug}/clean-{date}.csv` (data payload) + `quality-report.json` (status: APPROVED or REJECTED).
- **Template basis:** Trinity `custom.md`.

### 4.5 `compliance-officer`

- **Mission:** Hard ethics & legal gate. PASS or FAIL or NEEDS FOUNDER REVIEW. Never ambiguous.
- **Does:** 7-question audit on every clean dataset: (1) public access, (2) PII, (3) robots.txt/ToS, (4) no copyright verbatim, (5) dual-use/sensitive, (6) subject-objection (Putnam test), (7) GDPR/CCPA. Writes append-only ledger entry.
- **Does NOT:** Clean data (steward), ship products (engineer), override founder on FOUNDER REVIEW outcome.
- **Hard rules:** PII = automatic FAIL. Auth/paywall source = automatic FAIL. No PASS without all 7 questions answered. No retro-PASS edits — only REVOCATION entries (new file referencing the original). Surface gray areas as NEEDS FOUNDER REVIEW.
- **Inputs:** Clean dataset + quality report from data-steward.
- **Outputs:** `state/ethics-ledger/{date}-{slug}.json` with `verdict` field.
- **Template basis:** Trinity `custom.md`.

### 4.6 `engineer`

- **Mission:** Take CEO's product spec → live Stripe Payment Link + live Gumroad listing → entry in distribution queue. Zero human touch.
- **Does:** Reads `products/{slug}/spec.json`. Creates Stripe product + price + customized Payment Link via API. Runs Playwright to log into Gumroad and mirror listing. Uploads asset(s). Smoke-tests buy flow from a fresh browser session. Appends to `distribution-queue.json` only if smoke test passes.
- **Does NOT:** Write product copy from scratch (CEO drafts), run marketing, modify domain/DNS without founder approval, manage subscription billing (one-time only in v1).
- **Hard rules:** Production code only — no Lorem Ipsum, no "coming soon." Smoke test must pass before queue write. Stripe products prefixed `dsl_`. Browser-first for Gumroad. No new dependencies without justification.
- **Inputs:** CEO-written `state/products/{slug}/spec.json`.
- **Outputs:** Live Stripe Payment Link + Gumroad URL + `state/products/{slug}/launch-report.json` + entry in `distribution-queue.json`.
- **Template basis:** Trinity `custom.md` + Claude SDK builder tools (shell, fs, web fetch).

### 4.7 Boundary invariant

The handoff chain is strictly linear with deterministic JSON artifacts: brief → raw CSV+metadata → clean CSV+quality-report → ethics-ledger entry → product spec → launch report. No employee runs without its predecessor's artifact in place; no employee skips its successor by doing their job. CEO is the only orchestrator that crosses these boundaries (and only by *dispatching*, not *doing*).

---

## 5. Data flow

### 5.1 Artifact catalog

| # | Artifact | Format | Path |
|---|---|---|---|
| 1 | Opportunity brief | JSON | `state/opportunities/{date}-{slug}.json` |
| 2 | Raw dataset | CSV (payload) + JSON sidecar | `state/datasets/{slug}/raw-{date}.csv` + `raw-{date}.metadata.json` |
| 3 | Provenance | JSON | `state/datasets/{slug}/provenance.json` |
| 4 | Clean dataset | CSV (payload) + JSON sidecar | `state/datasets/{slug}/clean-{date}.csv` + `quality-report.json` |
| 5 | Ethics ledger entry | JSON | `state/ethics-ledger/{date}-{slug}.json` (one file per decision) |
| 6 | Product spec | JSON | `state/products/{slug}/spec.json` |
| 7 | Launch report | JSON | `state/products/{slug}/launch-report.json` |
| 8 | Distribution queue | JSON | `distribution-queue.json` |

CSV survives only as the **customer payload** for datasets — what gets emailed, uploaded to Gumroad, delivered as the product. Agents make handoff decisions against the JSON sidecar.

### 5.2 Standard JSON envelope

Every artifact JSON contains:

```json
{
  "version": 1,
  "type": "opportunity_brief",          // or raw_dataset_metadata, quality_report, ...
  "slug": "...",
  "created": "2026-05-04T13:00:00Z",
  "created_by": "opportunity-researcher",
  "status": "PROPOSED",                 // type-specific enum
  "summary": "One-sentence human-readable narrative.",
  "...type-specific fields...": "..."
}
```

All JSON is pretty-printed (2-space indent), schema-validated on write, and versioned for forward evolution.

### 5.3 Daily cycle

```
13:00 ET ─▶ opportunity-researcher fires
              writes 3-5 briefs to state/opportunities/
              exits silently (no DM)

14:00-18:59 ET ─▶ quiet (founder may DM CEO ad-hoc anytime)

19:00 ET ─▶ ceo fires
              1. Read state/opportunities/ (PROPOSED briefs)
              2. Cross-reference Trinity memory (skip recently-tried)
              3. Score + pick ONE (or zero, if threshold not met)
              4. Update brief: status: APPROVED
              5. Dispatch data-engineer ───▶ raw CSV + metadata
              6. Dispatch data-steward  ───▶ clean CSV + quality-report (APPROVED or REJECTED)
                  ├── REJECTED ─▶ retry engineer once with critique; second REJECT halts brief
              7. Dispatch compliance-officer ─▶ ethics-ledger entry (PASS / FAIL / NEEDS FOUNDER REVIEW)
                  ├── FAIL                ─▶ archive brief as KILLED, move to next-best
                  ├── NEEDS FOUNDER REVIEW ─▶ halt brief, surface in DM
              8. CEO writes spec.json
              9. Dispatch engineer ─▶ Stripe Payment Link + Gumroad listing + smoke test
                  └─ smoke test passes ─▶ append to distribution-queue.json
              10. CEO sends one DM to founder with cycle summary
```

### 5.4 Inter-employee dispatch

CEO orchestrates by spawning subprocess Trinity invocations:

```bash
trinity run "Harvest dataset for opportunity {slug}. Brief: state/opportunities/{date}-{slug}.json" -e data-engineer
```

Each subprocess shares the workspace (and Trinity memory). Disk is the source of truth — CEO reads artifacts from disk, not stdout. Token budget per cycle is bounded by the sum of subprocess invocations.

### 5.5 Trinity memory writes

| Employee | Memory segments touched |
|---|---|
| `ceo` | `decisions`, `lessons`, `relationships` (founder feedback patterns) |
| `opportunity-researcher` | `signals`, `corrections` (when CEO rejected — why) |
| `data-engineer` | `skills` (which queries worked for which domain types), `corrections` |
| `data-steward` | `corrections` (engineer patterns repeatedly cleaned) |
| `compliance-officer` | `audits`, `lessons` (gray-area patterns to surface earlier) |
| `engineer` | `skills` (Stripe/Gumroad gotchas), `corrections` (smoke-test root causes) |

Trinity defaults handle promotion + decay.

---

## 6. Error handling

### 6.1 Failure taxonomy

| Class | Examples | Default response |
|---|---|---|
| Soft (in-protocol) | researcher: no signal; steward: REJECTED; compliance: FAIL; engineer: smoke fail | Status field carries failure; pipeline halts at step; CEO summarizes in DM |
| Hard (out-of-protocol) | exception, subprocess non-zero, schema validation fail, API rate limit, network timeout | Logged to `.trinity/logs/`; pipeline step marked FAILED; blocker in DM |
| Founder-required | NEEDS FOUNDER REVIEW; engineer requests domain change; repeated soft-fail on same brief | Pipeline pauses; CEO DMs immediately; resumes when founder DMs decision |
| Cycle-skip | daemon crashed mid-cycle; cron didn't fire | Next cycle reads state, picks up where last left off; Trinity logs surface gap |

### 6.2 Retry policy

- **One retry per pipeline step**, then halt the brief.
- Retry input includes the prior failure's `unblocker` / `failure_reason` (when present) so the agent can adapt.
- After second failure, brief moves to BLOCKED state, never auto-retried — only founder unblocks.
- Compliance verdicts (PASS / FAIL / NEEDS FOUNDER REVIEW) are terminal — no retry.

### 6.3 Cross-cutting safeguards

- **Atomic JSON writes:** write to `path.tmp` → fsync → rename to final path. Readers never see partial files.
- **Schema validation on write:** every artifact JSON validates against `state/_schemas/{type}.schema.json` before write. Validation failure throws.
- **Append-only ethics ledger:** one file per decision; even REVOCATIONs are new files (`revokes: "{date}-{slug}.json"`).
- **Idempotent dispatches:** CEO checks for existing artifact before dispatching; if present, skips that step.
- **Trinity tool result cap:** 50KB per tool call (Trinity default).
- **Hard cycle limits:** `max_token_budget_per_cycle` and `max_retries_per_step` enforced as preflight checks in CEO; cycle aborts gracefully if exceeded.

### 6.4 Recovery patterns

- **Daemon dies mid-cycle:** subprocess artifacts already on disk persist. Next 19:00 cron run resumes at the missing-artifact step (idempotent dispatch).
- **Daemon doesn't restart:** `@reboot trinity start --daemon` line in user crontab handles boot recovery. Missing daily DM is the founder's manual signal.
- **Founder resolves NEEDS FOUNDER REVIEW:** founder DMs decision; CEO writes a `founder-decision-{date}-{slug}.json` linked file (ledger stays append-only); pipeline resumes at compliance-PASS branch.
- **Engineer URL 404s:** smoke test catches; not appended to queue; surfaced in DM.
- **Stripe API outage:** engineer retries with backoff (60s, 180s, 600s); third fail = halt + DM.
- **Gumroad session expired:** Playwright catches; halt + DM "Gumroad needs manual login refresh." (PRD phase 2: scheduled keepalive cycle.)

### 6.5 Daily DM structure

```
📊 DataStructured — {date}
══════════════════════════════
ADVANCED TODAY:
- {what moved forward}

SHIPPED:
- {product name}: {Stripe URL}, {Gumroad URL}

BLOCKED (needs you):
- {brief slug}: NEEDS FOUNDER REVIEW — {one-line reason}
- {brief slug}: smoke test failed — {one-line reason}

RUNNING TOMORROW:
- {next opportunity or "idle — research only"}

CYCLE COST: {tokens used} / {budget}
```

Mid-cycle DMs only fire for: compliance NEEDS FOUNDER REVIEW, engineer smoke-test failure, daemon-level errors.

---

## 7. Testing

Five layers, costs ascending toward the top.

### 7.1 Schema + pure-function (CI, every commit)

| Target | Verifies |
|---|---|
| JSON schemas | Positive + negative cases per artifact type (e.g. PASS without 7 questions = rejected) |
| Atomic write helper | Concurrent reads never see partial writes |
| Stripe product ID generator | Slug → `dsl_<slug>` deterministic and idempotent |
| Distribution queue append | Concurrent appends preserve JSON validity (file lock) |
| CSV ↔ JSON sidecar generator | Row count, columns, sample row correct |

Target runtime: <5s. No network, no LLM.

### 7.2 Agent contract tests (CI, stub LLM provider)

Each employee has a contract test that:
- Provides a canned LLM response via stub provider
- Asserts the produced artifact validates against its schema
- Asserts required fields are populated (e.g. compliance writes all 7 audit answers)
- Does NOT assert reasoning quality (that's eval territory)

Stub provider lives at `tests/_stub_provider.py`, registered via Trinity's plugin entry-point system.

### 7.3 Integration smoke (nightly, 04:30 ET)

| Test | Verifies |
|---|---|
| Trinity daemon lifecycle | Start → PID file → stop → clean shutdown |
| Stripe test-mode E2E | Engineer creates test product + Payment Link; URL returns HTTP 200 with expected DOM |
| Telegram bot ping | DM the bot "ping" → expect "pong" within 30s |
| Full pipeline dry-run | Seed test fixture brief → trigger CEO `--dry-run` → assert all 5 downstream artifacts produced with correct statuses |

### 7.4 Live eval (weekly, hand-reviewed, Sunday 05:00 ET)

| Scenario | Expected behavior |
|---|---|
| 5 synthetic opportunity briefs (3 strong, 2 weak) | Researcher scores strong ≥7, weak ≤4 |
| 3 synthetic raw datasets (1 with PII, 1 with copyright, 1 clean) | Compliance: FAIL, FAIL, PASS |
| 1 synthetic clean dataset + brief | CEO produces sane spec.json (price, bonus stack, one-time format) |
| 1 synthetic spec | Engineer produces valid Stripe test-mode Payment Link |

Output saved to `tests/eval-runs/{date}.json` for trend tracking.

### 7.5 Production observability (continuous — the daily DM is itself a liveness test)

| Signal | What it tells us |
|---|---|
| Daily CEO DM at 19:00 ± 30 min | Cron fired, daemon alive, CEO ran, Telegram works |
| `ADVANCED TODAY` populated | Pipeline moving (not just researcher idling) |
| `BLOCKED (needs you)` empty | No human intervention pending |
| `CYCLE COST` within budget | Token spend healthy |
| Schema validation failures = 0 in `.trinity/logs/` | Agents producing valid artifacts |

Missing DM by 19:30 ET = founder's signal to investigate.

### 7.6 What we don't test

- LLM reasoning quality per-call (tested via weekly eval, not unit)
- Real Stripe / real Gumroad in CI (only test mode + manual eval)
- Researcher's actual web scrapes (canned responses for tests)
- Telegram bot in CI (only nightly smoke)

---

## 8. Out of scope for v1 (mapped to PRD phases)

- `product-manager`, `marketing-lead`, `partnerships-lead`, `cfo`, `customer-success` agents
- Custom subdomain storefront
- Recurring billing / subscription products
- Affiliate tracking
- Customer support inbox automation
- Multi-channel Telegram reporting (groups, separate compliance channel)
- Cross-vertical specialized harvest tools (PRD phase 4)
- Self-improving feedback loops (PRD phase 4)

See [`docs/PRD.md`](../../PRD.md) for full phase roadmap.

---

## 9. Naming and branding

- **Working name:** DataStructured (matches folder).
- **Easy rename:** brand lives in `README.md`, `trinity.toml` `[company]` section, and the 6 employee identity files. `mv` the folder + `sed` across these to rename.
- **Domain:** TBD by founder. Subdomain not in v1; PRD phase 2 introduces a custom subdomain (e.g., `data.<owned-domain>`) for the storefront.

---

## 10. Open implementation decisions (deferred to writing-plans phase)

- Exact Trinity employee identity file content (this spec captures intent; identity prose is implementation)
- JSON schema files (full schemas per artifact type)
- Specific Stripe API integration code (Python SDK call structure, webhook handler if any)
- Gumroad Playwright script (selectors, login flow)
- Crontab `@reboot` line vs systemd unit for daemon supervision
- Stub LLM provider implementation details
- CI runner choice (GitHub Actions vs local pre-commit)
