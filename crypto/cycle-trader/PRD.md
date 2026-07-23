# PRD — Cycle Trader

**Product:** A standalone application for TJ's BTC cycle trading system ("CY-1").
**Owner:** TJ (sole user; personal book — fully separate from the v4 trading firm's capital and gates).
**Status:** Rules are FROZEN and validated (spec v1.1, 2026-07-23). This app re-implements them with fresh eyes; it does not redesign them.
**Companion doc:** `SPEC.md` — the exact rules, formulas, and must-pass verification fixtures.

---

## 1. Why this exists

TJ trades Bitcoin's macro cycle: one campaign per bear market, entered at on-chain
capitulation prices, confirmed by market structure, exited into the following bull.
The rules were developed iteratively against 15 years of data, corrected three times
by TJ's own chart reads (2015, 2020, 2022), and frozen with hash-anchored discipline
in the v4 repo. Validated record: **4 clean episodes (2014→2025), 4 wins, 0 stop-outs,
+2,417% summed on accumulation capital; a $10k + $2k/mo cash-flow model turned
$82k contributed into ~$470k (5.73x blended)**.

The system currently lives as research scripts + cron alerts inside the v4 trading
repo. It deserves its own app: cleaner code, live episode tracking as a first-class
product, and independence from the firm's infrastructure.

## 2. The one-sentence system

> Accumulate spot BTC at on-chain floor prices during the bear (weekly RSI < 35),
> add reserve cash when market structure confirms the reversal (fresh-low lower-high
> break), sell half at the 1.272 extension of the prior bear, and sell the rest when
> the uptrend's structure breaks — no leverage, ever.

## 3. Users & mode of use

Single user (TJ). The app **signals; the human executes**. v1 places no orders.
TJ receives Telegram alerts, opens the dashboard, and buys/sells spot manually on
his exchange. (Auto-execution is a possible v2, gated behind a separate decision.)

## 4. Product scope (v1)

| # | Capability | Description |
|---|---|---|
| P1 | **Signal engine** | Implements SPEC.md exactly: trigger, accumulation lines, fresh-low LH/BoS detector, ladder, extensions, mirror-exit detector, stop. Deterministic, walk-forward, no lookahead. |
| P2 | **Verification-gate test suite** | The owner's chart reads are executable fixtures (SPEC §10). CI fails if any gate stops reproducing. This is the product's spine — an engine that fails a gate is wrong, full stop. |
| P3 | **Live episode tracker** | Persistent state machine for the current episode (today: EP6, watching, trigger 2026-02-01). Tracks: operative LH, accumulation-line values (refreshed daily), tranche fill status, savings accrual, armed/unarmed exit state. |
| P4 | **Alerting** | Telegram alerts with cooldowns on: RSI approach/trigger, each accumulation-line touch, BoS print, ladder-level touches, breakout, 1.272 print, mirror-exit signal + 50%-bounce fill window, stop touch. Every alert states the rule it fires under and the action it implies. |
| P5 | **Dashboard** | Local, self-contained HTML (no hosted dependency): weekly candles with episode anatomy (LH/BoS lines, fills, exits), live EP6 card with current levels, historical episode cards, full trade table, the frozen rules, and the record incl. rejected variants. Regenerated daily by cron so it is always current when opened from disk. |
| P6 | **Shadow ledger** | Records TJ's actual manual fills against the system's prescribed fills; divergence is visible, never silently reconciled. |
| P7 | **Historical reproduction harness** | One command rebuilds the full 2011→present backtest from raw data and asserts the record in SPEC §11 (regression fixtures). |

### Optional module (build last, or not at all in v1)
| P8 | **Beta sleeve tracker** | The validated 80/20 BTC/beta concept: beta bought on BTC's signal dates, sold ONLY at BTC's armed mirror exit or the episode-low rescue stop. The app tracks a beta position TJ declares (his pick — SOL intended); it never picks the asset (the honest mechanical pick lost in-sample: OP −55.5%). |

## 5. Non-goals (v1) — settled questions, do not reopen without new evidence

- **No leverage.** Owner: "leverage shd be for short term trading, not cycle trading."
  The 3x variant made +3,694% vs spot's +2,417% but carried a liquidation line ABOVE
  the episode-low stop for the dominant tranche in every episode; the corrected 2015
  episode retroactively LIQUIDATES under it. Closed.
- **No order execution.**
- **No altcoin signal generation.** BTC only; the beta sleeve consumes BTC's signals.
- **No parameter search / re-optimization.** Rules are frozen; the app implements,
  it does not fit. Any rule change is an owner-approved amendment with a new spec
  version and must keep every existing verification gate passing.
- **No day/swing trading features.** One campaign per cycle is the product.

## 6. Success criteria

1. **Correctness:** all verification gates (SPEC §10) and regression fixtures
   (SPEC §11) pass from a cold clone with one command.
2. **Liveness:** accumulation lines refresh daily; alerts fire within one polling
   interval (≤1h) of a level touch; the state machine survives restarts.
3. **Auditability:** every signal, level value, and state transition is logged with
   the data it was computed from; the shadow ledger shows prescribed-vs-actual.
4. **Fresh-eyes test:** a developer with no context can read PRD + SPEC, build the
   engine, and hit the gates — this document pair is the complete transfer.

## 7. Operating constraints

- Python 3.12, shared venv `~/venvs/oefr/` (workspace convention), SQLite for state,
  cron for scheduling, Telegram via the existing bot token (env: project `.env`,
  never `~/.profile`).
- Free data only: exchange klines (Bitstamp/Binance), CoinMetrics community API,
  checkonchain-derived balanced-price series (SPEC §8 has sources + fallbacks).
- The historical daily dataset and all validation JSONs exist in the v4 repo under
  `auto-research-trader-v4/docs/superpowers/research/2026-07-21-owner-cycle-system/`
  — copy what's needed at build time; do not depend on that repo at runtime.

## 8. Current live state the app must pick up (as of 2026-07-23)

- **EP6**: triggered 2026-02-01 (weekly RSI 32.4), status **watching**.
- Prior cycle ATH 126,200 · running episode low 57,800.
- Operative lower high **82,850** (week of 2026-05-10; confirmed; unbroken) →
  **BoS trigger: any intraweek trade > 82,850**.
- Accumulation lines (2026-07-22): T1 realized ≈ **52.9k** · T2 midpoint ≈ **45.9k**
  · T3 balanced ≈ **38.9k**. **No tranche filled** — BTC hasn't touched realized
  since the trigger.
- Prospective 1.272 exit if the 57,800 low holds: ≈ **144.8k** (moves with the low).
- Interim alerting for these levels currently runs in the v4 repo
  (`scripts/cycle_watch.py`, hourly cron); this app supersedes it at cutover.

## 9. Milestones

1. **M1 — Engine + gates** (the hard part): data layer, structure engine, exits;
   all gates and regression fixtures green.
2. **M2 — Live tracker + alerts**: EP6 state machine, daily line refresh, Telegram.
   Cut over from v4's `cycle_watch.py` (retire it only after parallel-run agreement).
3. **M3 — Dashboard**: local HTML, daily regen.
4. **M4 — Shadow ledger.**
5. **M5 (optional) — Beta sleeve tracker.**

## 10. Risks

- **Balanced-price sourcing** is the only fragile data dependency (no free API with
  full history). SPEC §8 defines the reference series and a documented ratio
  fallback. Alert loudly on staleness rather than failing silently.
- **n=5 episodes.** The record is anatomy, not statistics; the app must present it
  that way (the dashboard's "read honestly" note is a product requirement).
- **Cycle-scale patience**: worst historical sit-throughs were −49% (2014
  accumulation) and −64% MAE (2019 spot through COVID). The dashboard must show MAE
  history so future drawdowns read as in-distribution, not as failure.
