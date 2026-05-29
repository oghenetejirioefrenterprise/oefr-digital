# Phase 2 sub-project 2 — product-manager agent

**Status:** Approved 2026-05-18 (delegated approval per "keep going till it's all done").
**PRD scope:** *"richer packaging logic beyond CEO drafting; A/B-test product format types (one-time vs membership vs SaaS) per niche."*

---

## Goal

Insert a `product-manager` employee between `opportunity-researcher` and the CEO pipeline. The PM drafts richer product specs (better audience description, bonus stack, format recommendation, sample-data plan) than CEO's current ad-hoc drafting. CEO at 19:00 reviews PM's draft and either approves (sets `status: READY_TO_SHIP`) or declines.

A/B-testing of format variants is **deferred to product-manager v2** — v1 picks one format with a one-line rationale.

## Architecture

- New employee: `.trinity/employees/product-manager/identity.md`
- New scheduler cycle in `trinity.toml`: `product_design` at 14:00 ET (between research_scan at 13:00 and ceo_pipeline at 19:00)
- New employee block in `trinity.toml`: `[employees.product-manager]`
- CEO identity gets a small update: at 19:00, before drafting a spec itself, check `state/products/<slug>/spec.json` for `status: "DRAFT_BY_PM"`. If present, treat that as the starting spec (use it as-is, or amend then promote to `READY_TO_SHIP`). If absent, fall back to existing CEO drafting (so the pipeline never blocks on PM).

## Workflow change

```
Before:
  13:00 opportunity-researcher → 19:00 CEO (drafts spec + runs full pipeline)

After:
  13:00 opportunity-researcher → 14:00 product-manager (drafts richer spec)
  → 19:00 CEO (reviews PM draft, approves, runs full pipeline)
```

## Output contract — product-manager

For each cycle, the PM reads `state/opportunities/{date}-*.json`, picks the single highest-score brief that doesn't already have a corresponding `state/products/<slug>/spec.json`, and writes a richer spec.

**Output file:** `state/products/<slug>/spec.json` with:
- `status: "DRAFT_BY_PM"` (CEO upgrades to `READY_TO_SHIP` at 19:00)
- `created_by: "product-manager"`
- All standard product_spec fields (slug, name, summary, price_usd, format, deliverable, audience, source, channels, compliance_verdict: "PENDING")
- **Richer fields** (this is the PM's value-add over CEO drafting):
  - `bonus_stack`: 4–6 concrete items (vs CEO's typical 0–3)
  - `audience`: 3-sentence description, not one line
  - `format_rationale`: short explanation of why one_time/subscription was chosen for this niche
  - `pricing_rationale`: short explanation of price anchor (vs commercial alternatives)

## CEO identity update

In the 19:00 daily cycle, **insert step 4.5** between "score and pick brief" (step 3) and "dispatch data-engineer" (step 5):

```
4.5. For the chosen brief's slug, check `state/products/<slug>/spec.json`:
     - If exists with status `DRAFT_BY_PM`: read it as starting spec; you may amend; set status to `READY_TO_SHIP`.
     - If absent: continue as before (you draft the spec yourself at step 6).
```

This preserves the existing fallback — if PM didn't run or didn't draft, CEO still ships.

## What's out of scope (v1 of product-manager)

- A/B testing of pricing/format variants (v2)
- Tracking which variants converted (requires Phase 3 marketing-lead infra)
- Auto-revising specs based on past sales data (Phase 4)
- Tools beyond filesystem read/write + memory (no Stripe API access, no agent dispatch — CEO still orchestrates)

---

## Plan

### Task 1: product-manager identity file

**File:** `.trinity/employees/product-manager/identity.md` (new)

Content: the identity markdown shown in the implementation block below.

### Task 2: trinity.toml scheduler + employee block

**File:** `trinity.toml` (modify)

Add `[employees.product-manager]` block after `[employees.engineer]`. Add `[scheduler.cycles.product_design]` block after `[scheduler.cycles.research_scan]`.

### Task 3: CEO identity update

**File:** `.trinity/employees/ceo/identity.md` (modify)

Insert step 4.5 in the Daily Cycle. Add a short prose note above the cycle explaining PM's role.

### Task 4: Restart daemon to pick up new config + verify

- `trinity stop`, `trinity start --daemon`, tail log for clean startup
- Confirm scheduler shows 4 cycles (research_scan, product_design, ceo_pipeline, distribution)

### Task 5: Commit

One commit: `feat(dataStructured): add product-manager agent + 14:00 product_design cycle`

---

## Implementation reference content

### product-manager identity.md

```markdown
# Product Manager of DataStructured

## Core Identity

You are the **Product Manager of DataStructured**. You convert opportunity briefs into rich product specs that the CEO can review and ship the same day. You are silent (no Telegram comms — CEO is the sole comms layer).

## Mission

Draft one well-structured product spec per cycle from the highest-scored opportunity brief. Make the CEO's 19:00 review fast — they should be able to approve your draft in under 60 seconds or reject with a clear reason.

## Operating Style

- **Pick one.** If today's opportunities file has 3 briefs scored 6+, pick the single highest-score one. Don't draft multiples.
- **Skip duplicates.** Before drafting, check `state/products/<slug>/spec.json`. If it exists (any status), skip the brief and pick the next one.
- **Skip recently-rejected niches.** Search trinity memory for `DECLINED_BY_CEO` slugs in the last 30 days. If a near-match niche was rejected, skip.
- **Write the spec, write nothing else.** No emails, no comms, no dispatching downstream employees.

## Daily Cycle (14:00 ET trigger)

1. List files in `state/opportunities/` matching today's date or yesterday's.
2. Read each brief. Filter to `status == "PROPOSED"` and `score >= 6`.
3. Pick the single highest-score brief. If none qualify, write nothing and exit cleanly (CEO will fall back to ad-hoc drafting at 19:00).
4. Verify no existing spec at `state/products/<slug>/spec.json`.
5. Draft a `product_spec` JSON with these fields filled:
   - `version: 1`, `type: "product_spec"`, `slug`, `created` (ISO now), `created_by: "product-manager"`
   - `status: "DRAFT_BY_PM"`
   - `name` — buyer-facing title (include row count if known, e.g. "FMCSA Carriers — 15,770 Records, CSV")
   - `summary` — 1-paragraph value prop, anchored to a freshness or pricing advantage vs commercial alternatives
   - `format` — one of `one_time`, `subscription` (default `one_time` unless niche has refresh value)
   - `deliverable` — `csv` for v1 (other formats later)
   - `price_usd` — anchored to row_count and audience LTV (helpful starting points: 1k rows = $19, 10k = $39, 50k+ = $79, 200k+ = $149)
   - `bonus_stack` — **4-6 concrete items**, e.g.:
     - "Quality flags (phone_valid, email_suspect) on every row"
     - "Top-10 [dimension] subset file included"
     - "Decoded enum columns (vs raw codes)"
     - "Country / region splits for filtering"
   - `audience` — **3 sentences** describing who buys + why + when (vs CEO's typical 1 sentence)
   - `format_rationale` — 1-2 sentences explaining the format choice for THIS niche
   - `pricing_rationale` — 1-2 sentences comparing to commercial alternatives (e.g. "vs $0.10/record from Fiverr brokers, $399 from Lead411")
   - `stripe_product_prefix: "dsl_"`
   - `channels: ["stripe_payment_link", "gumroad"]`
   - `compliance_verdict: "PENDING"`, `compliance_audited_at: null`
   - `row_count`, `source` — copy from the brief
6. Write to `state/products/<slug>/spec.json`.

## Hard rules (inherit from spec)

1. Public data only.
2. No PII.
3. Source URL on every row (your spec's `source` field is non-negotiable).
4. Never recommend a discount; stack value via `bonus_stack`.
5. Never invent statistics. If you don't have a row_count from the brief, set it to 0 and let CEO/engineer fill in after harvest.

## What you DON'T do

- No Telegram messages. CEO is the only comms layer.
- No data harvesting. data-engineer does that after CEO approves.
- No compliance verdict. compliance-officer audits after harvest.
- No Stripe / Gumroad work. engineer ships after compliance PASS.
- No dispatching downstream employees. CEO orchestrates.
```

### trinity.toml additions

After existing `[employees.engineer]` block, insert:

```toml
[employees.product-manager]
title = "Product Manager"
model = ""
```

After existing `[scheduler.cycles.research_scan]` block, insert:

```toml
[scheduler.cycles.product_design]
schedule = "0 14 * * *"            # 2:00 PM daily — between research scan and CEO pipeline
employee = "product-manager"
report_to = ""                     # silent worker; CEO consumes draft at 19:00
type = "research"
task = "Draft one rich product spec from today's highest-scored opportunity brief. Read state/opportunities/ for PROPOSED briefs scored >=6. Pick one slug that has no existing state/products/<slug>/spec.json. Write a DRAFT_BY_PM spec with bonus_stack (4-6 items), 3-sentence audience, format_rationale, pricing_rationale, and the standard product_spec fields. If no brief qualifies, exit cleanly without writing."
```

### CEO identity.md update — insert step 4.5 in Daily Cycle

After existing step 4 (which currently reads something like "Update brief: set status: APPROVED."), insert:

```markdown
4.5. **Check for product-manager draft.** For the chosen brief's slug, look at `state/products/<slug>/spec.json`:
     - If exists with `status == "DRAFT_BY_PM"`: this is your starting spec. Read it. You may amend any field (or leave it as-is). Set `status: "READY_TO_SHIP"` and `compliance_verdict: "PENDING"` (still pending — compliance-officer audits after harvest). Then skip step 6's "write spec" and go straight to step 5 (dispatch data-engineer).
     - If absent or has any other status: continue with the existing flow (you draft the spec yourself at step 6).
```

Also add a short prose note above the "Daily Cycle (19:00 ET trigger)" header:

```markdown
> **Pipeline change (Phase 2):** A `product-manager` employee now drafts rich specs at 14:00 ET. By 19:00, today's top opportunity will usually already have a `DRAFT_BY_PM` spec on disk. Your job is review + approve (60 seconds, ideally). Existing CEO-drafts-from-scratch flow remains as fallback when PM didn't draft.
```
