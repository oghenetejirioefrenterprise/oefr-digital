# SMB Crypto Agent — Design Spec

**Date:** 2026-04-21
**Location:** `~/apps/crypto/smb-crypto-agent/`
**Status:** Approved, ready for implementation plan

## Goal

Build a standalone, crypto-native autonomous trading agent whose playbook is distilled from the 1,704 SMB Capital YouTube transcripts in `~/apps/SMB_youtube_transcripts/`. The agent trades liquid crypto assets on:

- **Hyperliquid** — perps (primary) and HYPE spot where viable
- **Binance** — spot and USDⓈ-M futures (perps)

Options-based content from the source corpus is out of scope — options do not translate cleanly to crypto venues yet. Stock-mechanics content is adapted to crypto analogues (funding, liquidations, unlocks, ETF flow, protocol upgrades) where translatable.

## Non-goals

- No integration into `auto-research-trader-v4/` — this is a separate agent.
- No reuse of `smb-ict-agent/` code beyond pattern inspiration — fresh repo.
- No options execution; options content is captured only as `context/` reference.
- No discount/coupon/promotional logic (per OEFR operating rules — irrelevant here anyway).

## Runtime shape (Hybrid)

Deterministic detectors emit candidates, a Claude Sonnet 4.6 judge reviews each candidate against its playbook plus current market context, risk coordinator gates, allocator sizes, venue executes.

```
data fetch → detector.find_candidates() → risk_coordinator.can_enter()
  → judge.evaluate(candidate, playbook, market_context) → BUY | SKIP | WAIT
  → allocator.size(candidate) → venue.place_order(paper|live)
  → db.insert(signal, decision, order)
```

The judge runs on the existing Anthropic subscription (Claude Sonnet 4.6), no API cost. Every judge decision is logged for later review — the "trade review" discipline baked into the system.

## Repo layout

```
~/apps/crypto/smb-crypto-agent/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   ├── runtime.json          # mode: paper|live, venues_enabled, pairs
│   ├── allocation.json       # per-strategy and per-venue capital %
│   └── risk.json             # caps, drawdown halt, daily-loss halt
├── ingestion/
│   ├── run_ingest.py         # orchestrates the subagent wave
│   ├── taxonomy.md           # controlled vocab for categories
│   ├── manifest.jsonl        # one line per transcript: classification summary
│   ├── summaries.jsonl       # one line per transcript: full-read structured summary
│   └── sources/              # index/symlinks into SMB_youtube_transcripts/
├── knowledge_base/
│   ├── INDEX.md
│   ├── principles/           # non-strategy wisdom (risk mgmt, review, game planning)
│   ├── setups/               # one file per distilled setup
│   └── context/              # equity-only concepts retained as reference, not tradeable
├── strategies/               # one directory per runnable setup
│   └── <setup_name>/
│       ├── detector.py
│       ├── playbook.md       # copy/link from knowledge_base/setups/
│       └── bot.py
├── core/
│   ├── judge.py              # Claude Sonnet 4.6 decision layer
│   ├── risk_coordinator.py   # v4-style gating
│   ├── allocator.py          # reads allocation.json
│   ├── venues/
│   │   ├── base.py           # unified Venue interface
│   │   ├── hyperliquid.py    # HL perps (+ HYPE spot where viable)
│   │   ├── binance_spot.py
│   │   └── binance_futures.py
│   ├── data/                 # OHLCV, orderbook, funding, liquidation fetchers
│   └── indicators.py         # shared TA primitives
├── db/
│   └── research.db           # sqlite: signals, trades, judge_decisions, equity
├── scripts/
│   ├── init_db.py
│   ├── run_all.py            # orchestrator (paper or live)
│   ├── backtest.py
│   └── daily_digest.py
├── tests/
├── logs/
└── status/                   # lock files: HALTED, per-strategy liveness
```

## Ingestion pipeline

**Phase 1 — fan-out (parallel full read).** 1,704 transcripts sharded at ~50 per subagent → ~35 subagent tasks, dispatched in parallel waves of 10–12. Each subagent reads every assigned transcript in full and emits one JSON line per transcript with this schema:

```json
{
  "file": "filename.transcript.md",
  "video_id": "...",
  "title": "...",
  "categories": ["breaking_news", "pullback", "risk_mgmt"],
  "equity_only": false,
  "crypto_translatable": true,
  "tactical_score": 0,
  "setups": [
    {
      "name": "Breaking News Long on CPI Beat",
      "preconditions": "...",
      "entry_trigger": "...",
      "invalidation": "...",
      "targets": "...",
      "timeframe": "intraday|swing|scalp",
      "confidence": "high|med|low",
      "crypto_adaptation_notes": "...",
      "quotes": ["short verbatim rule-encoding lines"]
    }
  ],
  "principles": ["short extracted lessons that aren't full setups"],
  "skip_reason": null
}
```

Controlled vocab for `categories` lives in `ingestion/taxonomy.md` so subagents don't invent tags. Seed list: `breaking_news`, `trend_day`, `pullback`, `second_chance`, `fashionably_late`, `imbalance_scalp`, `relative_strength`, `game_planning`, `risk_mgmt`, `trade_review`, `fade_the_extended`, `opening_range`, `liquidity_sweep`, `basket_execution` (extensible).

Options-heavy content: the *mechanic* (e.g., "fade the extended move", "pay for the trade") is extracted to principles; option-specific expression is dropped. Equity-only setups with no crypto analog get `equity_only: true` and a `skip_reason`.

Output is appended to `ingestion/summaries.jsonl`.

**Phase 2 — synthesis (parallel, smaller fan-out).** One subagent per `category` cluster (~15–20 tasks). Each reads the `summaries.jsonl` rows for its category and produces:

- `knowledge_base/setups/<setup_name>.md` — distilled canonical playbook for the setup. Deduplicates across many transcripts, keeps the best-articulated version as canonical and cites all source files.
- `knowledge_base/principles/*.md` — for non-setup wisdom aggregated across the corpus.
- Updates `knowledge_base/INDEX.md`.

**Phase 3 — strategy scaffolding.** For every setup with `confidence ∈ {high, med}` and `tactical_score ≥ 3`, scaffold `strategies/<setup>/` with a `detector.py` stub, a copied/linked `playbook.md`, and a skeleton `bot.py`. Implementation of the detector logic is a separate task per setup.

**Expected wall-clock:** ~15–30 min for Phase 1, ~10–15 min for Phase 2.

## Knowledge base schema

Every setup file follows the same schema so the judge parses them consistently:

```markdown
# <Setup Name>
**Category:** ...  **Timeframe:** ...  **Confidence:** ...  **Venues:** HL perps | Binance spot | Binance futures
**Adapted from:** [list of source transcript files]

## Preconditions
## Entry trigger
## Invalidation
## Targets
## Sizing notes
## Crypto adaptation notes
## Common mistakes (from review transcripts)
## Example(s)
```

The judge prompt template pulls only the one setup file for the candidate plus the relevant `principles/*.md` files — keeping context tight.

## Runtime components

### `core/venues/base.py`

Unified `Venue` interface so strategies are venue-agnostic:

```python
class Venue(Protocol):
    name: str
    kind: Literal["perp", "spot"]
    async def balances() -> Balances
    async def quote(symbol) -> Quote           # bid, ask, mid, spread
    async def ohlcv(symbol, tf, limit) -> DataFrame
    async def orderbook(symbol, depth) -> Orderbook
    async def funding(symbol) -> float | None  # None for spot
    async def place_order(order) -> OrderResult
    async def cancel(order_id) -> bool
    async def positions() -> list[Position]
```

Four implementations: `hyperliquid` (perps + HYPE spot), `binance_spot`, `binance_futures`.

### Paper mode

Paper mode wraps a real venue client and routes `place_order` to `logs/paper_orders.jsonl` while still mutating DB state (signal, decision, open position, fills simulated at quote mid or configurable slippage model). Every other layer — detection, judge call, risk coordinator, allocator, indicators, data fetches — runs identically in paper and live. This matches the v4 "paper executes the full stack" rule.

### `core/judge.py`

Inputs to the judge per candidate:

- The candidate dict from the detector.
- The full playbook markdown for the candidate's setup.
- Relevant `principles/*.md` slices (static selection per setup).
- Recent market context: last 50 bars on 3 timeframes, current funding, recent liquidation pulse, BTC/ETH backdrop regime.
- Current open positions and strategy exposure.

Output:

```json
{
  "decision": "BUY | SKIP | WAIT",
  "confidence": 0.0,
  "reasoning": "...",
  "size_multiplier": 0.5
}
```

`size_multiplier ∈ [0.5, 1.0]` lets the judge down-weight a candidate it agrees with but doesn't love. Every call is logged to `db.judge_decisions` (candidate, prompt digest, response, outcome when realized).

### `core/risk_coordinator.py`

Hard gates evaluated before any entry — strategies call `risk_coordinator.can_enter(candidate)` before asking the judge:

- Halt immediately if `status/HALTED.lock` present.
- Daily realized loss cap (from `risk.json`).
- Account drawdown cap (cumulative, from equity snapshots).
- Per-venue, per-strategy, per-symbol exposure caps.
- Correlation cap: refuse to stack N long-beta positions when BTC is already long.
- Funding-rate guardrail for perp entries: skip if funding is catastrophically against the direction.

### `core/allocator.py`

Reads `config/allocation.json`:

```json
{
  "total_equity_usdt": 10000,
  "per_strategy": {
    "breaking_news": 0.20,
    "pullback": 0.15,
    "trend_day": 0.15
  },
  "per_venue": { "hyperliquid": 0.50, "binance_spot": 0.30, "binance_futures": 0.20 },
  "max_leverage": { "hyperliquid": 3.0, "binance_futures": 2.0, "*_spot": 1.0 }
}
```

Strategies never hard-code size — always `allocator.size(candidate)`.

### `scripts/run_all.py`

Orchestrator. Each strategy runs as its own coroutine/thread with its own cycle interval (scalps every 1m, swings every 15m, news-listener always-on). PnL snapshot thread writes equity to DB every N minutes. Health thread touches `status/<strategy>.lock` each tick for liveness probes.

## Data and venues

- **Hyperliquid:** info API (WebSocket + REST). Perps OHLCV, orderbook, funding, liquidations. Used for detection and execution.
- **Binance:** REST + WebSocket for spot and USDⓈ-M futures.
- **Crypto-native feature layer** (not in SMB corpus — this is the crypto adaptation side), available to every detector and to the judge's market-context payload:
  - `funding_rate` (current plus 8h history)
  - `liquidation_pulse` (recent long vs short liquidation bursts)
  - `basis` (perp mid minus spot mid)
  - `open_interest_delta`
  - `btc_regime` (trending / chop / extended — provides the "what market are we in" backdrop)
- **News catalysts:** lightweight RSS/webhook hook pulling from existing workspace macro-calendar and token-unlock sources. Wired as optional inputs; strategies that depend on them skip if absent.

## Testing and operations

- **Unit tests** per detector with synthetic OHLCV fixtures (should-trigger / should-not-trigger).
- **Judge tests** — assert the prompt assembles correctly from candidate + playbook; snapshot Claude responses on fixed inputs so regressions are visible.
- **Venue smoke tests** — paper-mode integration tests hitting read-only endpoints on each venue.
- **Backtester** (`scripts/backtest.py`) — replays OHLCV through detectors. Judge is configurable: skip, or call judge with cached market-context snapshots. Results to `db.backtest_runs`.
- **Ops files:** `status/HALTED.lock`, `status/<strategy>.lock` (liveness), `logs/paper_orders.jsonl`, `logs/judge.log`, `db/research.db`.
- **Daily digest:** `scripts/daily_digest.py` posts a Telegram summary (signals produced, judge BUY/SKIP breakdown, paper PnL, top reasoning snippets).
- **Secrets:** all in `smb-crypto-agent/.env` per the crypto workspace rule. Never `~/.profile` for this project.

## Build sequence

1. Scaffold repo skeleton, `CLAUDE.md`, `requirements.txt`, config files.
2. Ingestion Phase 1 — dispatch ~35-subagent wave, produce `summaries.jsonl`.
3. Ingestion Phase 2 — category synthesis, produce `knowledge_base/setups/*.md` and `INDEX.md`.
4. Build `core/venues/base.py` + all four venue implementations + paper wrapper + smoke tests.
5. Build `core/risk_coordinator.py`, `core/allocator.py`, `core/judge.py` with unit tests.
6. Build `core/indicators.py` + shared data-fetch helpers.
7. Scaffold `strategies/<setup>/` for every high/med-confidence setup.
8. Implement detectors for the top 5–8 setups (highest confidence, cleanest crypto translation). Rest stay stubbed until validated.
9. Wire `scripts/run_all.py` + backtester + `init_db.py`.
10. Paper-mode dry run for 24–48 h, review judge decisions, iterate detectors.

## Open follow-ups (deliberately deferred)

- Second-pass implementation of the remaining stubbed detectors once the first cohort has paper results.
- Integration of news/unlock calendar feeds if workspace sources prove reliable.
- Live-mode activation gate (`SMB_LIVE_CONFIRMED=yes` + explicit allocation review) — live mode is not in scope for initial delivery.
