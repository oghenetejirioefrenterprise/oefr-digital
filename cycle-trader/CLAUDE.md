# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Cycle Trader** — a standalone app for TJ's frozen BTC macro-cycle system ("CY-1"):
accumulate spot BTC at on-chain floor prices during the bear, add reserve cash on a
market-structure break, exit half at the 1.272 extension and the rest on an armed
mirror exit. Personal book — **fully separate from the v4 trading firm's capital,
allocator, and gates.**

**Current state: M1 complete.** The engine and its gate suite are built and green.

```bash
source ~/venvs/oefr/bin/activate
cd ~/apps/cycle-trader && pytest -q          # ~322 tests, a few seconds
```

- `engine/` — pure Python, stdlib only, **zero I/O and no clock**. `types, bars,
  rsi, lines, fills, lifecycle, structure, levels, orders, context, engine`.
  `engine.engine.compute(bars, onchain, prior_state, asof, ...)` is the single
  public entry point M2 calls daily.
- `data/loaders.py` — **test-only**. `engine/` must never import it; CI enforces
  this with an AST purity gate (`tests/test_engine_purity.py`, deny-by-default,
  recursive).
- `data/reference/` — frozen snapshots (OHLC, CoinMetrics, checkonchain, the CY-1
  reference lifecycle). Copied in at build time; **no runtime dependency on the v4
  repo**.
- `tests/gates/` — G1–G5 plus the EP2–EP5 structural regression and the OQ-3
  synthetic fixture.
- CI lives at the **repo root**, `~/apps/.github/workflows/cycle-trader-gates.yml`
  — GitHub only reads workflows from there, and the repo is `~/apps`. It has
  **never run**: `master` is well ahead of `origin`, and `oefr-digital` is a
  **public** repo, so pushing makes the logs public. That is the owner's call.

**M2 has not started.** No exchange adapter, no Supabase, no cron, no web app.

This directory is *not* its own git repo. It is tracked inside the `~/apps` repo
(`git rev-parse --show-toplevel` → `/home/oghenetejiri/apps`), so scope commits to
these paths and prefix them `feat(cycle-trader):` / `docs(cycle-trader):` per the
existing log. **Other sessions commit to this monorepo concurrently — never
`git add -A`.**

## The Two Documents

- **`SPEC.md` is normative** (v1.2, 2026-07-24). It is the complete rule set —
  trigger, accumulation lines, lower-high/BoS detector, ladder, exits, stop.
  **It is a derived restatement, not the hash-anchored artifact.** The registered
  blobs (`d0b2f3a` → `46d3527`, v4 `config/preregistration.json` gate `CY-1`) point
  at v4's `CY-1-FROZEN-SPEC.md`, a document half this length. Roughly half of
  SPEC.md — the 26-week clustering, the episode-low definition, fill/gap semantics,
  the cost convention, the §11 fill table — exists only here and never went through
  §9's amendment path. Read its **§13** (clarifications that override the older
  prose, incl. the stop's real scope and fill-direction semantics) and **§14** (five
  open items needing TJ's decision) before implementing anything.
- **`PRD.md`** is scope: capabilities P1–P8, non-goals, milestones M1–M5, and the
  live EP6 state the app must pick up.

Read both before writing any engine code. Together they are designed as a complete
transfer to a developer with no context (PRD §6.4).

## Non-Negotiable Rules

1. **Gates beat prose.** Where SPEC's wording and a §10 verification gate disagree,
   the gate wins. An engine that fails any gate is wrong no matter how reasonable
   its reading is. G1–G5 are the owner's own chart reads — G1 (2015) is what forced
   Amendment 1; G5 is live EP6.
2. **This app implements; it does not fit.** No parameter search, no
   re-optimization, no "improving" a constant. `R_e = 15` and `1.272` are frozen
   owner choices, not tunables.
   *Accuracy note (measured 2026-07-25, SPEC §13.3a):* earlier wording here called
   these "the unique gate-passing values". For `R_e` that is false — 13.8 through
   15.0 all pass the full suite, so 15 is the upper **edge** of a passing interval.
   `QUIET_WEEKS = 26` sits in an even wider plateau (§13.5). The rule is unchanged
   — **do not tune them** — but do not cite them as gate-derived either. What the
   gates prove is that R10 and R20 both fail, not that 15 is singular.
3. **Amendment by addition only.** Rule changes require owner approval, a new spec
   version + hash, an appended (never edited) amendment entry, and every prior gate
   still passing. Historical records get withdrawn with a reason or appended — never
   restated.
4. **No leverage, no order execution, no altcoin signal generation.** SPEC §9 and
   PRD §5 list the settled/rejected variants (3x perps, 1.212, 0.328 ladder level,
   flat R=25, TP1-anchored arming, …). Don't relitigate them without new evidence.
5. **Walk-forward, no lookahead.** Accumulation lines move daily and fills are tested
   against *that day's* line value; LH confirmation must strictly precede any use of
   the candidate; the mirror exit's 50% target recomputes as the low falls. Any
   convenience that peeks ahead silently breaks the gates.
6. **The app executes autonomously** (owner decision 2026-07-24; v1's "no order
   execution" is superseded). Orders are **resting exchange-side** — limit where
   possible, market only for breakouts and the stop. The daily run is a
   **desired-state reconciler**, so it is idempotent and self-healing. **A failed
   run changes nothing and never cancels** — resting orders are the safe state when
   the system is blind. Design:
   `docs/superpowers/specs/2026-07-24-cycle-trader-v2-design.md`. The shadow ledger
   narrows to manual overrides and still never merges them with system fills.

## Data

Free sources only (SPEC §8):

| Series | Source |
|---|---|
| BTC daily OHLC | Bitstamp → Binance splice @ 2017-08-17; live via Binance spot klines |
| Realized price | CoinMetrics community API — derive `CapMrktCurUSD / CapMVRVCur / SplyCur` (the community feed has no `CapRealUSD`) |
| Balanced price | checkonchain full-history snapshot, taken at build time; ratio fallback ≈ realized × 0.735, flagged **stale/approx** in every surface that uses it |
| Weekly RSI-14 | computed — Wilder smoothing on weekly closes, ISO Monday-anchored UTC weeks |

The `bitcoin-data.com` balanced-price endpoint is **rejected** (4-year window, wrong
transferred convention). Balanced price is the one fragile dependency — alert loudly
on staleness rather than degrading silently.

Reference datasets live in the v4 repo at
`~/apps/crypto/auto-research-trader-v4/docs/superpowers/research/2026-07-21-owner-cycle-system/dashboard-data/`.
**Only `cy1_lifecycle.json` implements CY-1** — it is the reference implementation
and the thing to reproduce. `episodes_dashboard.json` fills the 0.328 level and
exits at 1.212/1.618/2.0; `v4_lifecycle.json` is the 3x-perp/BoS-sale variant that
SPEC §9 rejects. Comparing against either produces nonsense. `btc_daily_full.json`
is the OHLC history. Those JSONs label weeks by **Sunday close** while SPEC labels
by **ISO Monday** — normalise before diffing (SPEC §13.10).
**Copy what you need at build time; never depend on that repo at runtime.**

## Relationship to the v4 Repo

CY-1 is registered in v4's preregistration but is explicitly out of v4's nightly
evaluator scope and out of its capital/gate accounting. Interim alerting runs there
today — `scripts/cycle_watch.py`, hourly cron at `:20`, ~110 lines, state in
`status/cycle_watch.json`, 12h cooldowns, hard-coded `BAL_RATIO = 0.7351`. This app
supersedes it. **Retire the v4 cron only after a parallel run shows agreement** (PRD
M2). Do not edit v4 code from here.

## Environment

- Python 3.12, shared venv: `source ~/venvs/oefr/bin/activate` (local + CI)
- **Runtime: Vercel serverless + Vercel cron, daily after the UTC close.** State,
  journal and order log in **Supabase**. No SQLite, no local cron (superseded
  2026-07-24)
- **`engine/` is pure Python — no pandas, no numpy.** Keeps the serverless bundle
  small; the maths is a running min, Wilder RSI, weekly aggregation and retracement
  arithmetic
- **Gate suite runs in GitHub Actions, not on Vercel** — a full 2011→present rebuild
  exceeds function timeouts. CI imports the same package Vercel deploys, so the
  gates verify the code that actually trades
- Telegram via the existing bot token — secrets go in **this project's `.env`**, never
  `~/.profile` (workspace convention)
- Web app is a hosted read-only Next.js dashboard over Supabase; its only write path
  is the kill switch. Mobile deferred

## What the M1 build learned — read before adding assertions

Seven measured claims in `SPEC.md` had to be corrected during M1, and the pattern
never varied: **computed numbers were right every time; transcribed and attributed
ones were wrong.** Two rules follow, and they cost real time to learn.

1. **Read values off the engine, never paste them.** A 10-decimal boundary relayed
   between agents was already past the true edge and would have failed on correct
   code.
2. **Verify *which* test fails, not merely that one does.** Four of the seven
   corrections were attribution errors — the right number credited to the wrong
   gate. §13.3a and §13.9a both carry the scars.

Two structural blind spots worth knowing:

- **Mutation testing kills changes to code that exists and is blind to code that
  is missing.** The build's first Critical (a breakout order re-arming after it
  filled, unbounded) had no line to mutate. A reviewer walking the state machine
  found it; 34/34 mutants had not.
- **A constant measured on one gate is a fact about that gate, not about the
  record.** Three frozen constants turned out to be *edges or plateaus* rather
  than the unique values SPEC claimed — see §13.3a, §13.5, §13.9a.

A shared mutation harness lives in the SDD workspace; it refuses ambiguous
patterns (an identically-worded line in a neighbouring function silently mutated
the wrong one) and compiles at `optimize=2`, so it cannot measure mutations to
`assert` lines.

## Build Order

Revised 2026-07-24 for autonomous execution:

**M1** engine + gates (pure Python, zero I/O) → **M2** data adapters + Supabase +
daily cron + Telegram, *signals only*, v4 cutover → **M3** venue adapter +
reconciler + guard, *dry-run and testnet only* → **M4** web app + kill switch →
**M5** arm live.

Real money appears only at M5, and only after **SPEC §14 OQ-3 and OQ-1 are settled**
— both change which orders exist, so the executor cannot be correct until they are.
The gate suite (PRD §P2) is the spine: it must run from a cold clone with one
command, and CI fails if any gate stops reproducing.

Live EP6 numbers (operative LH, line values, fill status) are in PRD §8 as of
2026-07-23 — treat them as a starting fixture that goes stale, not as truth. G5 is
the version that must stay executable.
