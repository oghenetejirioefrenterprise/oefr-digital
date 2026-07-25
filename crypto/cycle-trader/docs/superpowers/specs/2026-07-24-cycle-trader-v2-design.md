# Design — Cycle Trader v2: autonomous execution + web app

**Date:** 2026-07-24
**Status:** approved in brainstorm; not yet planned or built
**Owner:** TJ (single user, personal book)
**Implements:** `SPEC.md` v1.2 (frozen rules) · supersedes parts of `PRD.md` (see §10)

---

## 1. Decision record

v1 was signal-only by design: PRD §5 listed "No order execution" as a non-goal and
reserved auto-execution as "a possible v2, gated behind a separate decision."
**TJ made that decision on 2026-07-24.** The choices below are his; the rationale
is recorded so they are not silently relitigated.

| Decision | Choice | Notes |
|---|---|---|
| Autonomy | **Fully autonomous** — no human in the execution loop | Chosen over approve-to-execute. Built on resting exchange-side orders, which is a mechanism for *where* execution happens, not a human-approval step |
| Venue | **Venue-agnostic adapter**, Binance implemented first | v4's `core/executor_binance.py` is the reference for the first adapter |
| Cadence | **Daily**, after the UTC close | Owner: "do not need a sub-daily cron, this is a long term trading plan." Correct — every fill test in SPEC is defined on daily bars |
| Order policy | **Limit orders where possible; market only for breakouts** | Owner instruction; maps onto SPEC §13.2's primitives |
| Hosting | **All on Vercel** + Supabase for state | Daily cron fits the Hobby tier, so this is zero additional cost |
| Clients | **Web only for now** — responsive Next.js | Mobile packaging (PWA / React Native / stores) deferred; single user needs no store distribution |
| Capital | **The modelled plan** — ≈$10k at trigger + ≈$2k/mo | Order sizes land in the hundreds-to-thousands; exchange minimum notional is not a constraint |
| EP6 | **Handled separately**, not a build deadline | EP6 stays on v4's `scripts/cycle_watch.py` alerts until this app is proven |

### Why daily cadence is not a compromise

SPEC defines every fill test on daily bars — "daily low ≤ level", "daily high ≥
level". A daily engine run is therefore the strategy's native resolution. §12's
≤1h polling requirement was written for the v1 product, where a human had to react
to a level touch; once orders rest at the exchange, the matching engine covers
intraday movement. Historical margin is wide: BoS to first ladder fill was ~1 week
in G1 (2015-01-26 → 2015-02-02) and ~3 weeks in G3 (2023-02-13 → 2023-03-09).

### Why not a TypeScript port

**The engine that places live orders must be the identical code the gate suite
verifies.** If G1–G5 validate one implementation and a different one trades real
money, the gates prove nothing. Re-deriving the frozen numerics — the fresh-low
scan, the walk-forward mirror target, the fill semantics — in a second language is
exactly the divergence risk SPEC §10 exists to prevent. Rejected.

---

## 2. Scope

**In scope (v2):** autonomous order placement for CY-1 on a single venue, daily
reconciliation, persistent episode state, journal/audit, Telegram alerting,
read-only web dashboard with a kill switch.

**Out of scope, unchanged from v1 §5:** leverage of any kind · altcoin signal
generation · parameter search or re-optimisation · day/swing trading features ·
any rule change not made through SPEC §9's amendment path.

**Deferred:** mobile apps (PWA or native), the beta sleeve tracker (PRD P8), and
multi-venue execution beyond the first adapter.

---

## 3. Architecture

```
 Vercel Cron (daily, after UTC close)
        │
        ▼
  ┌───────────┐   bars, realized, balanced   ┌────────────┐
  │  data/    │◄─────────────────────────────│ Binance    │
  │ adapters  │                              │ CoinMetrics│
  └─────┬─────┘                              │ checkonchain│
        │ daily bars                          └────────────┘
        ▼
  ┌───────────┐   PURE. no I/O. deterministic.
  │  engine/  │   weekly agg · Wilder RSI · episode lifecycle
  │           │   fresh-low LH scan · levels · exits
  └─────┬─────┘   ← this is what G1–G5 test
        │ desired order set + new state
        ▼
  ┌───────────┐   notional cap · kill switch · dry-run
  │  guard/   │   order-count sanity · price sanity · staleness
  └─────┬─────┘   ← refuses to emit; never modifies
        │
        ▼
  ┌───────────┐   diff(desired, actual) → place/cancel/amend
  │reconciler/│◄──────────────┐
  └─────┬─────┘               │ open orders, balances, trades
        ▼                     │
  ┌───────────┐        ┌──────┴─────┐
  │  venue/   │───────►│ Exchange   │  ← holds the resting orders
  │ adapter   │        │ (Binance)  │
  └─────┬─────┘        └────────────┘
        ▼
  Supabase: state · journal (append-only) · order log
        │
        ├──► Telegram alert (existing bot token, project .env)
        └──► Next.js web app (read-only over Supabase)
```

### Module boundaries

| Module | Responsibility | Depends on | Must NOT |
|---|---|---|---|
| `data/` | Fetch and cache daily OHLC, realized, balanced; report as-of dates and staleness | HTTP, Supabase | Interpret rules |
| `engine/` | Pure function `(bars, on-chain, prior_state) → (new_state, desired_orders)` | nothing | Perform I/O, know about exchanges, read the clock |
| `venue/` | Exchange adapter: `open_orders()`, `balances()`, `trades()`, `place()`, `cancel()` | HTTP, keys | Contain strategy logic |
| `guard/` | Validate the desired order set against interlocks | config | Modify or clamp an order — refuse only |
| `reconciler/` | Diff desired vs actual, emit place/cancel actions | `venue/` | Compute levels |
| `journal/` | Append-only audit of inputs, computations, actions | Supabase | Mutate history |
| `api/` | Vercel functions: `/cron/daily`, `/api/state`, `/api/journal`, `/api/kill` | all | Hold state in memory between runs |
| `web/` | Read-only Next.js dashboard + kill switch | Supabase | Write anything except the kill flag |

**`engine/` is written in pure Python — no pandas, no numpy.** The maths is a
running minimum, Wilder RSI, weekly aggregation, and retracement arithmetic over a
few thousand daily bars. Staying stdlib-only keeps the Vercel Python bundle small
and makes the package trivially importable by CI.

**Gate suite runs in GitHub Actions, not on Vercel** — a full 2011→present rebuild
exceeds serverless function timeouts. CI imports the *same package* Vercel deploys,
so gates still verify the code that trades.

---

## 4. Execution model

**The daily run is a desired-state reconciler, not an event handler.** Each run
computes the complete set of orders that should exist for the current episode
state, reads what does exist at the venue, and issues the difference.

This is chosen deliberately over event-driven placement ("on BoS, place the
ladder"). Reconciliation is idempotent, so a skipped or double-fired cron is
harmless; a crash mid-run self-heals on the next run; and there is no
"did we already place this?" bookkeeping to get wrong.

### Desired order set by state

| Episode state | Resting at the exchange |
|---|---|
| `watching` (pre-BoS) | 3 limit buys at T1 / T2 / T3, **re-priced every run** as the lines move |
| `confirmed` (post-BoS) | ladder limit buys at 0.5 / 0.62 / 0.786 · stop-market at `EL*` · stop-market at the BoS-week high (breakout fallback) |
| `distributing` (Exit 1 crossed) | limit sell at the mirror target, **amended daily** as `low_so_far` falls · stop-market at `EL*` |
| `closed` / `stopped` / `expired` | none — the reconciler cancels everything |

### Order types

Per owner instruction, limit where possible; market only where the system is
chasing a break. Consistent with SPEC §13.2's four primitives.

| CY-1 event | Order type | Primitive (§13.2) |
|---|---|---|
| Accumulation T1 / T2 / T3 | limit buy | buy-limit |
| Ladder 0.5 / 0.62 / 0.786 | limit buy | buy-limit |
| Breakout fallback | **stop-market** | buy-stop |
| Exit 1 @ 1.272 | limit sell | sell-limit |
| Mirror exit target | limit sell, amended daily | sell-limit |
| Mirror 8-week fallback | **market** | SPEC §6.2 states "sell at market" |
| Stop @ `EL*` | **stop-market** | sell-stop |

The stop is market rather than stop-limit deliberately: a stop-limit can be jumped
in a fast breakdown and leave the position unprotected, which defeats the only
capital protection CY-1 has.

### Re-pricing hazard

Accumulation lines move daily, so each run must move three resting limit buys.
Note that "place before cancel" is **not** available here: a resting limit buy locks
the quote balance, so the capital for the replacement order is unavailable until the
original is cancelled. Three rules make the move safe:

1. **Use the venue's atomic cancel-replace** where it exists (Binance:
   `POST /api/v3/order/cancelReplace`). This is the primary path and leaves no
   window without a resting order.
2. **Otherwise cancel-then-place, and re-verify.** The next run's reconciliation
   catches any order that failed to re-place, which is exactly what makes
   desired-state reconciliation the right pattern here.
3. **"Order not found" on cancel means filled, not error.** The reconciler then
   recovers the fill from trade history rather than inferring it.

A line that has not moved materially since the last run is left alone — re-pricing
is skipped unless the level has changed by more than the venue's tick size, to avoid
needless churn and API weight.

Fill quantities always come from the venue's trade history, never from assuming a
resting order filled in full — partial fills rest only the remainder.

---

## 5. State and data

Supabase (Postgres). Serverless functions hold nothing between runs.

| Table | Purpose | Key fields |
|---|---|---|
| `episodes` | One row per episode | `trigger_date`, `trigger_rsi`, `prior_ath`, `episode_low_running`, `el_frozen`, `operative_lh`, `lh_confirmed_at`, `bos_date`, `bos_week_high`, `state` |
| `levels_daily` | Every computed level, per run | `as_of_date`, `realized`, `balanced`, `balanced_source` (`live`\|`ratio_fallback`), `t1`,`t2`,`t3`, ladder levels, `ext_1272`, `mirror_target`, `el_star` |
| `orders` | Order lifecycle | `purpose` (enum: `T1`…`LADDER_050`…`EXIT1`,`MIRROR`,`STOP`,`BREAKOUT`), `side`, `type`, `price`, `qty`, `venue_order_id`, `status`, `fill_price`, `fill_qty` |
| `runs` | One row per cron invocation | `run_id`, `started_at`, `finished_at`, `status`, `data_as_of`, `aborted_reason` |
| `journal` | Append-only audit | `run_id`, `ts`, `event`, `payload` (inputs **and** computed outputs) |
| `config` | Operational flags | `armed`, `kill_switch`, `dry_run`, `notional_cap`, `capital_plan` |
| `shadow_fills` | TJ's manual fills, if any | never merged with system fills (PRD P6) |

`journal` carries the inputs alongside the outputs so any historical signal can be
replayed and audited — SPEC §12's requirement, and the thing that makes a
post-mortem possible after a bad fill.

Data sources are unchanged from SPEC §8: Binance spot klines, CoinMetrics
community API (`CapMrktCurUSD / CapMVRVCur / SplyCur`), checkonchain balanced price
with the documented ratio fallback. Reference history is copied in at build time
from the v4 repo; **no runtime dependency on that repo**.

---

## 6. Failure handling

**Governing rule: a failed run changes nothing. It never cancels.**

If data is stale or the engine cannot compute, the safe state is the orders already
resting — they were computed from good data and still protect the position.
Cancelling on error strips the stop and the exits at exactly the moment the system
is blind. Every failure path is: abort, journal, alert, leave the book untouched.

| Failure | Behaviour |
|---|---|
| Klines / CoinMetrics unreachable | Abort run, alert, orders stay resting |
| Balanced price stale (>**7 days**) or on ratio fallback | Do **not** re-price T2/T3 on approximate data — keep existing orders, alert. Hard-refuse the run past **30 days** stale |
| Level fails a plausibility check | Refuse the whole order set — the signature of bad data, not a real signal. See below |
| Partial fill | Rest only the remainder; quantities from trade history |
| Order vanished between read and cancel | Treat as filled, reconcile from trade history |
| Missed or double-fired cron | No-op; the reconciler is idempotent by construction |
| Exchange reject (min notional, precision, balance) | Journal + alert; no blind retry |
| Clock / timezone | All computation in UTC; the daily run is anchored to the UTC close |

**Level plausibility check.** "Within X% of spot" is the wrong test — accumulation
lines legitimately sit far from spot (T3 is ~35% below spot in EP6 today, and spot
trades *below* realized at a cycle bottom and multiples above it in a bull). Two
checks that actually discriminate data faults from real signals:

1. **Absolute bound** — every computed level must satisfy `0.1 × spot ≤ level ≤
   10 × spot`, and be non-null and positive. This catches zeros, nulls, unit errors
   and parse failures without ever rejecting a genuine level.
2. **Day-over-day bound** — realized and balanced price are slow-moving supply-wide
   aggregates. A move greater than **10% in one day** is a data fault, not a market
   event. Refuse, keep existing orders, alert.

---

## 7. Safety interlocks

All enforced in `guard/`, which can only refuse. A silently-clamped order is a
wrong order.

1. **Trade-only API key with withdrawals disabled** — asserted at startup; the
   adapter refuses to run if the key reports withdrawal permission.
2. **Hard notional cap** in config. Any order set exceeding it aborts the run.
3. **Kill switch** — one flag in Supabase. When set, the next run cancels all
   orders and goes inert. Reachable from the web app in one click.
4. **Dry-run mode** — computes and journals the full desired order set without
   placing. Must run clean for **30 consecutive days** before live arming, with zero
   aborted runs and zero plausibility refusals in that window.
5. **Order-count sanity** — a desired set larger than CY-1 can legitimately want is
   a bug, not a signal. Refuse.
6. **Sizing from the configured capital plan, never from account balance** — so a
   deposit cannot silently resize the ladder.
7. **Starts disarmed.** Arming live is a deliberate, separate action.

No static IP is available on Vercel serverless, so exchange-key IP allow-listing is
not possible. Items 1 and 2 are the compensating controls and are therefore not
optional.

---

## 8. Testing

| Layer | Test |
|---|---|
| Engine | G1–G5 as executable fixtures (SPEC §10), in CI |
| Engine | **Structural regression** against `cy1_lifecycle.json`: LH prices, BoS weeks, fill dates, fill prices, exit dates, exit prices for EP2–EP5. These reconcile exactly. Derived pnl percentages are informational, **not asserted** — owner 2026-07-24: cumulative return is not the point, autonomous execution is |
| Engine | Determinism property: identical inputs → identical outputs |
| Engine | **Synthetic fixtures for paths with no historical coverage** — chiefly the OQ-3 roll (accumulation unfilled at BoS → ladder → breakout), which never occurred in EP2–EP5 and which EP6 may be the first to take |
| Reconciler | Partial fill · cancel/place race · already-filled · missed run · double run |
| Venue | Binance spot **testnet** — full episode replay |
| Guard | One test per interlock proving it refuses |
| System | Dry-run in parallel with live market before arming |

CI fails if any gate stops reproducing. That is PRD P2's requirement and it now
also guards live-money code.

**Only `cy1_lifecycle.json` implements CY-1.** `episodes_dashboard.json` fills the
0.328 level and exits at 1.212/1.618/2.0; `v4_lifecycle.json` is the 3x-perp
variant SPEC §9 rejects. Comparing against either produces nonsense.

---

## 9. Build sequence

| | Milestone | Gate to pass |
|---|---|---|
| **M1** | Engine + gate suite, pure Python, zero I/O | G1–G5 and §11 green in CI |
| **M2** | Data adapters, Supabase state + journal, daily Vercel cron, Telegram alerts — **signals only** | Parallel-run agreement vs v4 `cycle_watch.py` (PRD M2 criterion) |
| **M3** | Venue adapter, reconciler, guard — **dry-run + testnet only** | Testnet episode replays correctly; every interlock provably refuses |
| **M4** | Web app: read-only dashboard + kill switch | Kill switch works before any live order can exist |
| **M5** | **Arm live** | OQ-1 and OQ-3 settled + 30 clean dry-run days |

Real money appears only at M5, behind a kill switch that already exists and
interlocks already proven to fire.

**Each milestone gets its own spec → plan → implementation cycle.** This document is
the umbrella architecture; the first implementation plan covers **M1 only**. M1 is
also the one milestone with no dependency on the open questions in §10, so it can
start immediately.

---

## 10. Blocking open questions, and documents this supersedes

### Blocking before M5

Two of SPEC §14's open items change *which orders exist* and must be settled by the
owner before the executor can be correct:

- ~~**OQ-3 — where unfilled accumulation capital goes.**~~ **RESOLVED 2026-07-24:**
  unfilled accumulation → the **ladder** pool (2:4:8 proportions); unfilled ladder →
  the **breakout**. Confirms SPEC §3/§5 as written; `cy1_lifecycle.json` deviates.
  No gate impact — accumulation filled 3/3 in every historical episode, so the
  branch was never exercised. **This makes it an untested path that EP6 is likely to
  be the first to take** (no tranche filled, BTC far above T1, BoS at 82,850): a
  break of structure without a revisit to realized rolls the entire accumulation
  pool — a third of capital. A synthetic fixture is mandatory before M5.
- **OQ-1 — concurrent episodes.** Still open, still blocking M5. If a new episode
  triggers while a position is open, does the system size a second full allocation?
  Nothing currently says, and an autonomous system will do *something*. EP3/EP4
  overlapped historically, and the cash-flow record gives each a fresh $10k.

OQ-2 (MAE convention), OQ-4 (§11 pnl figures vs the reference) and OQ-5 (EP3
sign-off) are **explicitly non-blocking** per owner 2026-07-24 — they concern the
accuracy of the historical record, not execution behaviour, and the record is not a
product goal. They stay on file and are not work items. **OQ-1 is the sole remaining
blocker on live arming**, because it is the one open question that changes what the
executor does.

### PRD changes required

The following are now wrong and are corrected as part of this design:

- **§5 "No order execution"** — superseded by the 2026-07-24 decision.
- **§7 local cron + §P5 local self-contained HTML** — replaced by Vercel cron,
  Supabase state, and a hosted read-only web app.
- **§3 "the app signals; the human executes"** — the app now executes; the shadow
  ledger's role narrows to recording manual overrides.

SPEC itself is unchanged — v2 alters *how* CY-1 is executed, never the rules.
Nothing here touches §§0–14, and every gate must keep passing.

---

## 11. Risks

- **Autonomy raises the cost of a logic bug** from a missed alert to a wrong trade.
  Mitigated by: gates on the exact deployed code, dry-run before arming, the
  notional cap, and the "failure changes nothing" rule — but not eliminated.
- **Balanced price remains the fragile dependency** (SPEC §8). Under autonomy it is
  worse than in v1: a wrong balanced value moves T2/T3, which are 6/7 of the
  accumulation pool. Hence the refusal-to-reprice-on-stale-data rule.
- **Vercel serverless offers no static IP**, so key allow-listing is unavailable.
- **GitHub/Vercel cron are best-effort schedulers.** Tolerable only because orders
  rest at the exchange; a late run delays an amendment, never a fill.
- **n=5 episodes.** The record is anatomy, not statistics. It exists to make future
  drawdowns readable as in-distribution (worst sit-throughs were −49% and −64% MAE),
  not to forecast returns — and autonomy does not make it more certain. The product
  goal is faithful autonomous execution of the frozen rules, not a return figure.
