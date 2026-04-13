# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Autonomous SPX options trading agent that connects to IBKR via ib-gateway, scans for setups, places trades, monitors positions, and exits automatically. Runs as a Docker container alongside a Streamlit monitoring dashboard.

## Commands

```bash
# Start both agent + dashboard
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# View agent logs
docker logs -f options-agent

# Stop everything
docker compose down

# Run dashboard locally (outside Docker)
streamlit run dashboard/app.py --server.port=8502

# Run agent locally (requires ib-gateway accessible)
python agent.py

# Run historical backtest
python -m backtest.run_backtest --strategy bwb --start 2020-01-01 --end 2024-12-31 --capital 10000
python -m backtest.run_backtest --strategy all --start 2020-01-01 --end 2024-12-31
python -m backtest.run_backtest --download-only   # just fetch the dataset

# Run forward test (paper trading with live IBKR data)
python -m backtest.forward_test --strategy both --interval 60

# Run end-to-end trade test on paper account
python test_trades.py

# Wiki tools
python wiki_tools.py search "VIX spike"
python wiki_tools.py lint
python wiki_tools.py stats
python wiki_tools.py validate
python wiki_ingest.py <source_file> [--source-name NAME] [--dry-run]

# Run tests
python -m pytest tests/

# Kronos regime-router bakeoff (research-only, requires requirements-kronos.txt)
pip install -r requirements-kronos.txt  # torch, transformers, safetensors, scikit-learn
python -m backtest.kronos_bakeoff --start 2010-01-01 --end 2024-12-31 --samples 500
python -m backtest.kronos_bakeoff --models mini,small --samples 200 --device cpu --save-samples

# Kronos regime-router uplift test (Stage 2, research-only, requires requirements-kronos.txt)
python -m backtest.kronos_router_uplift --start 2020-01-01 --end 2024-12-31
python -m backtest.kronos_router_uplift --start 2020-01-01 --end 2022-12-31 --rebalance-step 10 --samples 50
python -m backtest.kronos_router_uplift --capital 25000 --device cpu --kronos-repo /path/to/Kronos

# Kronos overlay calibration sweep (Stage 2.5, research-only, requires requirements-kronos.txt)
python -m backtest.kronos_router_sweep --start 2020-01-01 --end 2024-12-31
python -m backtest.kronos_router_sweep --start 2020-01-01 --end 2022-12-31 --samples 15
python -m backtest.kronos_router_sweep --device cpu --dd-tolerance 10 --concentration-threshold 0.80
```

No linter, no build step. Python 3.12, dependencies in `requirements.txt`.
Kronos research deps isolated in `requirements-kronos.txt` (not needed for live trading).
Kronos shadow mode requires `requirements-kronos.txt` installed and the Kronos repo cloned locally.

## Architecture

The agent runs a single main loop in `agent.py` that ticks every 10 seconds:
1. **Market hours check** — skips weekends/holidays, only trades 09:30-16:00 ET
2. **Entry scan** (every `SCAN_INTERVAL` seconds) — each strategy evaluates independently
3. **Position monitor** (every `MONITOR_INTERVAL` seconds) — checks exit conditions on open positions
4. **Risk enforcement** — daily loss limit halts trading for the day, three strikes rule (3 consecutive losses), and Bump-and-Cut risk scaling

### Core Modules

- **`agent.py`** — `OptionsAgent` orchestrates the main loop, entry scanning, position monitoring, and P&L estimation. Entrypoint. Initializes all subsystems: broker, risk, strategies, volume indicators, trend detector, wiki, and LLM strategist.
- **`broker.py`** — `IBKRBroker` wraps `ib_insync`. Handles connect/reconnect, market data (live type 1 or delayed type 3), option chains, combo orders, and single-leg orders. All IBKR interaction goes through this. Auto-falls back to delayed data if live subscription is not active (IBKR error 354/10089). Live data requires IBKR subscription (~$4.50/month for SPX).
- **`risk.py`** — `RiskManager` tracks daily P&L, enforces `MAX_DAILY_LOSS`, halts trading on breach. Persists state to `data/risk_state.json` so it survives restarts. Three Strikes Rule: halts after 3 consecutive losses in a day. Bump-and-Cut: dynamic risk scaling based on rolling P&L — bumps risk_multiplier +25% when profitable (10d P&L > 2x daily stop), cuts -50% when hitting weekly/monthly stops. Source: SMB Capital.
- **`pricing.py`** — Black-Scholes implementation for theoretical pricing and Greeks. Used by strategies to find strikes by delta and estimate P&L without live market data subscriptions.
- **`notifier.py`** — Telegram alerts (trade entered/exited, daily summary, risk breaches, heartbeat, econ calendar). Uses defensive `.get()` for all position keys with strategy-specific formatting branches.
- **`state_writer.py`** — Atomic JSON writes (temp file + rename) to `data/` directory. Dashboard reads these files; never connects to IBKR directly.
- **`config.py`** — All tunable parameters. Reads from env vars with defaults. Contains strategy-specific dataclasses (`BWBConfig`, `ZeroDTEPCSConfig`, etc.). Validates configuration at import time — fatal misconfigurations (like `max_dte_hold >= dte_min`) raise `ValueError` immediately.
- **`sizing.py`** — Dynamic position sizing. `calculate_position_size(capital, max_risk_pct, spread_width, credit_received)` replaces fixed qty. Risk per trade = capital * max_risk_pct. Qty clamped [1, 5]. Automatically applies economic calendar multiplier (0.5x on event days).
- **`econ_calendar.py`** — Hardcoded FOMC, CPI, NFP, PCE dates for 2025-2026. `is_high_impact_day()` returns True on event days. `get_sizing_multiplier()` returns 0.5 on event days, 1.0 otherwise. Integrated into sizing and daily housekeeping notifications.
- **`holidays.py`** — NYSE holiday detection. Covers all NYSE holidays (New Year's, MLK, Presidents' Day, Good Friday, Memorial Day, Juneteenth, July 4th, Labor Day, Thanksgiving, Christmas). No external dependencies.
- **`indicators.py`** — `VolumeIndicators` class: VWAP calculation, volume z-score, and volume regime analysis (quiet/normal/elevated/extreme). Used by agent to gate entries during quiet markets.
- **`trend_detector.py`** — `TrendDayDetector` using SMB Capital's 3-technique framework: market internals (TICK, A/D, volume ratio), ETF sector rotation (offense vs defense), and price action (VWAP, opening range). Produces a trend day probability score (0-100) and can block premium selling on trend days.
- **`volatility_cycle.py`** — Volatility cycle breakout scanner. Measures StdDev(close,20)/ATR(20) to detect compression (squeeze < 1.5) and expansion (> 6.0 = energy spent). Combined with volume z-score for breakout confirmation. Used to filter Wheel and Calendar entries. Source: SMB Capital — Garrett/Jeff Holden.
- **`gex.py`** — `GEXCalculator` computes dealer gamma exposure from IBKR option chain data. Produces `GEXProfile`: max gamma strike (pin magnet), gamma flip point, positive/negative gamma zones. Used by `butterfly_pin.py` to find pin targets. No external services needed.
- **`analytics.py`** — Trade autopsy + performance analysis system. Runs weekly against `trade_history.json`. Per-trade autopsy, performance by strategy/time/day, pattern detection, and "one thing to focus on" recommendation. Saves to `data/analytics/`.
- **`learnings.py`** — Adaptive learning loop. Derives rules from trade autopsy data (skip bad hours, reduce size on weak strategies). Rules are evidence-based (min 5 trades per dimension), auto-expire after 30 days. Agent reads these at startup and each scan via `should_skip_entry()`.
- **`strategist.py`** — `LLMStrategist` meta-strategy module. Calls an LLM (OpenAI-compatible API, default Nvidia NIM) to decide which strategies should be active and with what sizing. Caches decisions, enforces rate limits, falls back to rules-based routing on failure. Disabled by default (`STRATEGIST_ENABLED=false`).
- **`strategist_prompts.py`** — System prompt and context formatting for the LLM meta-strategist.
- **`wiki_reader.py`** — `WikiReader` loads and caches all wiki pages (YAML frontmatter + markdown body) on startup. Provides query methods for strategies, playbooks, concepts, and parameter extraction.
- **`wiki_tools.py`** — CLI tools for wiki maintenance: search, lint, validate, stats.
- **`wiki_ingest.py`** — Ingest pipeline for adding new knowledge sources (transcripts, papers) to the wiki.
- **`kronos_shadow.py`** — Stage 3 Kronos shadow mode (hardened). `KronosShadow` class runs Kronos-mini inference alongside the live agent, produces `ShadowDecision` objects with regime labels and overlay recommendations. Compares against structured live routing snapshots (VRP, trend, volume, risk, sizing) from `agent.py` — not a synthetic approximation. Overlay variant (conservative/balanced/aggressive) dispatched by `KRONOS_SHADOW_OVERLAY` config via `OVERLAY_DISPATCH` dict. Zero execution impact. Persists to `data/kronos_shadow.json` (snapshot with `live_snapshot` dict) and `data/kronos_shadow_history.jsonl` (append-only). Controlled by `config.KRONOS_SHADOW` (`KronosShadowConfig`). Requires Kronos repo + `requirements-kronos.txt`.
- **`test_trades.py`** — End-to-end trade test on paper account. Opens one position per strategy, waits 5 minutes, closes all.

### Strategies (`strategies/`)

Each strategy implements this public API:
- `enter() -> Optional[dict]` — Evaluate conditions and place entry order. Returns position dict or `None`.
- `should_exit(position, current_price) -> tuple[bool, str]` — Check exit conditions. Returns `(should_exit, reason_string)`.
- `exit(position) -> bool` — Place closing order.

Strategies also have a `.name` class attribute (e.g., `"BWB"`, `"ZERO_DTE_PCS"`) used to match positions to strategies.

**Daily Income Engine (60% allocation)**
- **`zero_dte_pcs.py`** — 0DTE SPX put credit spread. Entry window 09:45-10:30 ET. Sells ~8-10 delta puts with 5pt wings. Target credit $0.35-$1.50. Uses `_remaining_T()` for accurate intraday Black-Scholes pricing. Exits at 50% profit, 2x stop, long-strike breach, or 15:45 force-close. Always active in every SMB regime.

**Premium Selling (Range/Neutral)**
- **`bwb.py`** — Broken Wing Butterfly (3-leg put structure). Uses Black-Scholes to find optimal delta/width combination. 7 DTE target. Returns `None` cleanly when it can't build valid legs (common in low IV). Exits at 40% profit, 1.5x stop, DTE <= 1, or price breach.
- **`put_credit_spread.py`** — Bull put spread at 30-delta (backtest-optimized from 15d). 7 DTE target. Entry: IV rank 25-85, SMB score <= 6. Exits at 50% credit, 2x stop, DTE <= 1.
- **`jade_lizard.py`** — Short OTM put + short call spread. No upside risk if total credit > call spread width (per-share comparison). Position sizing uses put-side max loss. 7 DTE target. Entry: IV rank 30-85, SMB score <= 6. Exits at 50% credit, 1.5x stop, short-call-strike breach, DTE <= 1.

**Long Gamma (Breakout)**
- **`call_spread.py`** — Bull call spread (buy ATM call, sell call 15pts higher). Entry: SMB score >= 5, IV rank < 60. 5-10 DTE target. Exits at 75% profit, 60% debit loss stop, DTE <= 2.
- **`long_call.py`** — Long ATM call for strong breakouts. Entry: SMB score >= 7, IV rank < 45. 5-7 DTE target. Exits at 75% gain or 40% loss, DTE <= 1. DISABLED from routing (backtest-verified DANGEROUS) but kept for monitoring existing positions.

**Backtested Winners (Self-Filtering)**
- **`mean_rev_pcs.py`** — Mean-reversion put credit spread. Entry: SPX >3% below 20d high + RSI(5)<25 + IV>1.5x HV. Sells 30-delta put spread at 45 DTE. Exits at 50% profit, 3x stop, 14 DTE time stop. Very selective (~1-2 trades/year). Backtest: 89.7% WR, PF 5.86.
- **`rsi_timed_pcs.py`** — RSI-timed put credit spread. Entry: RSI(14)<30 (oversold). Sells 30-delta put spread at 45 DTE. Exits at 50% profit, 2x stop, 14 DTE time stop. Backtest: 79.5% WR, Sharpe 0.51.
- **`vrp_timed_pcs.py`** — VRP-timed put credit spread. Entry: IV-HV20 > 4 vol points. Sells 16-delta put spread at 45 DTE. Exits at 50% profit, 2x stop, 21 DTE time stop. Backtest: 83.7% WR, Sharpe 1.19.

**SMB Capital Broken Wing Butterfly**
- **`smb_bwb.py`** — Put BWB on RSI(14)>60 overbought signal. Sells 2x 25-delta puts, buys 1x higher put (+5pts) and 1x lower put (-14pts, broken wing). 45 DTE target (30-60 range). Enters for net credit. Exits at 50% max profit, 2x stop, broken wing breach, or 14 DTE time stop. Self-filtering. Backtest: 156 trades, 100% WR, Sharpe 2.856. Source: SMB Capital (Seth Freudberg).

**0DTE Directional (BB Squeeze Momentum)**
- **`bb_squeeze_live.py`** — 0DTE directional option buying on BB squeeze + TICK + ATR stop alignment. Buys OTM calls (bullish) or puts (bearish) at ~22 delta. Entry: BB inside Keltner for >= 5 bars on 5-min chart, TICK 80%+ directional, ATR stop flip confirms. Entry window 09:45-15:00 ET. Exits at 200% gain, 80% loss, ATR stop flip, or 15:45 force-close. Self-filtering — runs in VRP_FILTERED mode without VRP gate.
- **`bb_squeeze_momentum.py`** — Backtest version using daily data with momentum proxy for TICK. Not used in live trading.

**SMB Transcript Winners (Promoted from Backtest)**
- **`vix_spike_pcs.py`** — VIX spike crash insurance trade. Entry: ATM IV proxy > 40% (VIX equivalent). Sells ATM put spread (50pt wide) at 180 DTE. Exits at 50% profit or 30 DTE time stop. **NO stop loss and NO price-breach exit** — hold-to-win crash trade. Very selective (~10 trades over 13 years). Always active in every SMB regime. Backtest: 10 trades, 40% WR, +$2,275, PF 2.41, 13.6% DD.
- **`bb_credit_spread.py`** — Bollinger Band credit spread. Entry: price touches 20-period, 2-StdDev Bollinger Band. Lower BB touch = put credit spread (bullish reversion), upper BB touch = call credit spread (bearish reversion). Short strike = price ± 1*std_dev, 5pt wide, 14 DTE. Exits at 50% profit, 2x stop, 1 DTE force-close. Active in RANGE and FLAT SMB regimes.

**VRP-Filtered Uncorrelated Strategies**
- **`bb_mean_rev.py`** — Bollinger Band mean reversion PCS. Sells put credit spread when SPX touches lower BB. DTE 14, 25-delta. Backtest: Sortino 1.03, DD 10.7%, 81% WR, correlation -0.09 with PCS+CS.
- **`gamma_proxy.py`** — Long straddle when VRP < -2 (realized vol > implied, gamma is cheap). DTE 7, profit 40%, stop 30%. Uses Black-Scholes for both legs to value the straddle (not intrinsic approximation). Backtest: Sortino 6.77, 40% WR, correlation -0.02 with PCS+CS.
- **`bear_rsi_rev.py`** — Bear RSI reversal put spread. Buys put spread when RSI(14) drops from overbought (>65) to <60. DTE 14, 30-delta, profit 75%, stop 50%, time stop 3 DTE. Anti-correlated with PCS+CS (-0.41). Backtest: Sortino 0.98, PF 1.42.

**Equity Income (Wheel + Diagonal)**
- **`wheel.py`** — Wheel Strategy (Cash-Secured Puts + Covered Calls) on individual stocks. Two-phase: CSP at ~20 delta → assigned → own shares → CC above assignment price → called away → repeat. `WheelStateManager` persists per-symbol phase/premiums to `data/wheel_state.json`. Separate capital bucket from SPX strategies. Disabled by default (`WHEEL_ENABLED=false`). Source: SMB Capital.
- **`diagonal.py`** — Diagonal spread (PMCC): buy deep ITM LEAPS call + sell OTM short-term call. 25% the cost of a covered call. Monthly income from short call premiums. Disabled by default (`DIAGONAL_ENABLED=false`). Source: SMB Capital.
- **`stock_calendar.py`** — Stock calendar spread on post-earnings sideways stocks. Sell near-term ATM put, buy longer-term same-strike put. Disabled by default (`STOCK_CALENDAR_ENABLED=false`). Source: SMB Capital.

**0DTE Butterfly Pin (GEX-based)**
- **`butterfly_pin.py`** — Narrow 0DTE SPX call butterfly targeting dealer gamma pin levels (from `gex.py`). Entry 12:00-2:30pm ET, scale out 3:00-3:45pm. Risk $40-60/contract for 500-5,000% returns. Max 1 trade/week. Disabled by default (`BUTTERFLY_ENABLED=false`).

**DISABLED (kept in codebase, not routed)**
- **`condor.py`** — 0DTE iron condor. Replaced by ZERO_DTE_PCS for simpler, more focused premium selling.
- **`calendar_spread.py`** — Calendar spread. Removed from active routing due to poor forward test results.

**SMB Scorer**
- **`smb_scorer.py`** — SMB Capital 7-Checks-in-Favor scoring system (0-10 from SPX price/volume data):
  - 7-10 (BREAKOUT): ZERO_DTE_PCS + CALL_SPREAD + LONG_CALL + VIX_SPIKE_PCS (always)
  - 5-6 (MODERATE): ZERO_DTE_PCS + PUT_CREDIT_SPREAD + CALL_SPREAD + VIX_SPIKE_PCS (always)
  - 3-4 (RANGE): ZERO_DTE_PCS + PUT_CREDIT_SPREAD + JADE_LIZARD + BB_CREDIT_SPREAD + VIX_SPIKE_PCS (always)
  - 0-2 (FLAT): ZERO_DTE_PCS + BB_CREDIT_SPREAD + VIX_SPIKE_PCS (always)

### Strategy Routing Modes

`ACTIVE_STRATEGY` env var controls which strategies are active:

| Mode | Description |
|---|---|
| `BWB` | Single strategy: Broken Wing Butterfly only |
| `ZERO_DTE_PCS` | Single strategy: 0DTE Put Credit Spread only |
| `PUT_CREDIT_SPREAD` | Single strategy: Put Credit Spread only |
| `CALL_SPREAD` | Single strategy: Call Spread only |
| `BOTH` | ZERO_DTE_PCS + BWB |
| `ALL` | All 6 original active strategies |
| `SMB` | Score-driven auto-selection via SMB 7-checks framework |
| `VRP_FILTERED` | VRP-gated portfolio: PCS+CS gated by VRP>2+MA20, plus uncorrelated strategies (BB_MEAN_REV, GAMMA_PROXY, BEAR_RSI_REV, BB_SQUEEZE), plus all self-filtering strategies. Combined Sortino 4.48. |

### Position Dict Key Conventions

Each strategy produces a position dict with different keys. This matters for `notifier.py`, `agent.py._estimate_pnl()`, and `state_writer.py`:

| Strategy | Strike Keys | Value Keys |
|---|---|---|
| ZERO_DTE_PCS | `short_strike`, `long_strike` | `net_credit`, `max_loss` |
| BWB | `strike_high`, `strike_mid`, `strike_low` | `net_credit`, `max_profit` |
| CONDOR (disabled) | `long_put_strike`, `short_put_strike`, `short_call_strike`, `long_call_strike` | `net_credit` |
| CALL_SPREAD | `long_strike`, `short_strike` | `net_debit`, `max_profit` |
| LONG_CALL | `strike` | `premium` |
| PUT_CREDIT_SPREAD | `short_strike`, `long_strike` | `net_credit`, `max_loss` |
| CALENDAR_SPREAD (disabled) | `strike`, `front_exp`, `back_exp`, `right` | `net_debit` |
| JADE_LIZARD | `short_put_strike`, `short_call_strike`, `long_call_strike` | `net_credit`, `no_upside_risk` |
| BB_SQUEEZE_MOMENTUM | `strike`, `option_type`, `direction`, `atr_stop` | `entry_price`, `delta` |
| VIX_SPIKE_PCS | `short_strike`, `long_strike` | `net_credit`, `max_loss` |
| BB_CREDIT_SPREAD | `short_strike`, `long_strike`, `spread_type` | `net_credit`, `max_loss` |

All positions share: `strategy`, `expiration`, `entry_time`, `qty`, `status`, `iv`, `trade`.

### Backtest Module (`backtest/`)

Historical and forward testing, separate from the live agent:

- **`data_loader.py`** — Downloads philippdubach SPY options dataset via git LFS sparse checkout (~560 MB). Caches parquet files to `data/hist/parquet_spy/`. SPY P&L scaled by 10x (`SPX_SCALE`) to approximate SPX results.
- **`engine.py`** — `BacktestEngine` replays historical data through strategies. Uses actual bid/ask/delta from the dataset (not Black-Scholes). Computes per-trade P&L, win rate, Sharpe ratio, max drawdown, monthly returns.
- **`run_backtest.py`** — CLI entry point. Strategies: `bwb`, `condor`, `call_spread`, `long_call`, `both`, `all`.
- **`forward_test.py`** — Paper trading with live IBKR market data. `PaperBroker` wraps `IBKRBroker`, passing through data methods but intercepting order placement. Writes hypothetical trades to `data/forward_results.json`.
- **`run_*_eval.py`** — Specialized evaluation scripts for individual strategies (bb_credit, bb_squeeze, smb_bwb, vix_spike, etc.).
- **`grid_search.py`** — Parameter grid search for optimizing strategy configs.
- **`kronos_regime_data.py`** — Builds rolling OHLCV windows from SPY underlying data and derives future regime labels (realized_vol_bucket, trend_vs_chop, tail_risk) for Kronos evaluation. No torch dependency. See `research/PRD-kronos-regime-router.md`.
- **`kronos_bakeoff.py`** — CLI bakeoff runner comparing Kronos-mini/small/base on regime prediction. Resolves a local Kronos repo clone (default `~/.hermes/workspace/investigations/Kronos` or `KRONOS_REPO_PATH`), loads the native Kronos model/tokenizer/predictor, runs bounded inference, scores with balanced accuracy / recall / confusion matrix, selects a winner, writes results to `data/kronos_bakeoff.json`. Requires `requirements-kronos.txt`.
- **`kronos_router_uplift.py`** — Stage 2 uplift test: baseline HV/MA regime-adaptive router vs Kronos-mini-enhanced router. Baseline uses 5 regimes (bear/high_vol/low_vol/trend/normal) to route PCS, BWB, CALL_SPREAD. Kronos overlay applies 4 priority rules (tail_block, trend_call_spread, chop_pcs_bias, high_vol_reduce) at configurable rebalance checkpoints. Writes comparison JSON to `data/kronos_router_uplift.json`. Requires `requirements-kronos.txt`.
- **`kronos_router_sweep.py`** — Stage 2.5 overlay calibration sweep. Sweeps 18 candidate configurations: 3 overlay variants (conservative/balanced/aggressive) × 3 rebalance steps (5/10/20) × 2 trend-gating options (on/off). Conservative keeps BWB on trend; aggressive removes it (Stage 2 behavior). Trend gating requires baseline regime agreement before applying CALL_SPREAD bias. Ranks by Sharpe → drawdown → P&L, rejects pathological candidates (HHI concentration, excessive drawdown). Writes results to `data/kronos_router_sweep.json`. Requires `requirements-kronos.txt`.

### Wiki (`wiki/`)

Structured trading knowledge base. Organized by directory: `strategies/`, `playbook/`, `concepts/`, `entities/`, `meta/`, `sources/`, `analysis/`, `superpowers/`. Pages are markdown with YAML frontmatter (title, tags, sources, related, category). Loaded by `wiki_reader.py` on agent startup. Maintained via `wiki_tools.py` and `wiki_ingest.py`.

### Dashboard (`dashboard/app.py`)

Streamlit app that reads JSON files from `data/` directory (mounted read-only). Dark theme, auto-refreshes every 30 seconds. Shows open positions with payoff diagrams, cumulative P&L chart, live logs, trade history, and configuration. Runs on port 8502 (mapped from container's 8501).

### Data Flow

```
agent.py --> state_writer.py --> data/*.json <-- dashboard/app.py
                                              (read-only volume mount)
```

JSON files in `data/`: `positions.json`, `portfolio.json`, `agent_config.json`, `trade_history.json`, `risk_state.json`, `heartbeat.json`, `wheel_state.json`, `learnings.json`, `kronos_shadow.json` (latest shadow snapshot), `kronos_shadow_history.jsonl` (append-only shadow decisions).

## Key Design Decisions

- **DRY_RUN mode** — `config.py` defaults to `true`, but `.env` can set `DRY_RUN=false` for live trading. In DRY_RUN, `place_combo_order` and `place_single_order` return `"DRY_RUN"` sentinel (not `None`) so the agent tracks simulated positions instead of discarding them.
- **Market data defaults to delayed** — `config.py`, `docker-compose.yml`, and `.env` all default to `MARKET_DATA_TYPE=3` (delayed/free). Set to `1` for live data once IBKR subscription is active. Broker auto-falls back to delayed if live subscription is not active (IBKR error codes 354/10089), logging one warning per session instead of spamming.
- **Theoretical pricing** — strategies use Black-Scholes from `pricing.py` rather than live option quotes for P&L monitoring and strike selection, reducing data subscription costs.
- **Dynamic position sizing** — `sizing.py` calculates qty based on account capital and max risk per trade (default 2%). Replaces fixed `qty` in all strategies. Automatically reduces to 50% on economic event days (FOMC, CPI, NFP, PCE).
- **Economic calendar awareness** — `econ_calendar.py` hardcodes high-impact dates for 2025-2026. Agent logs event days, reduces sizing to 50%, and sends Telegram notification during daily housekeeping.
- **ZERO_DTE_PCS always active** — In SMB and VRP_FILTERED modes, the 0DTE put credit spread runs in every regime as the primary daily income engine.
- **Disabled strategies** — CONDOR and CALENDAR_SPREAD are disabled from routing but kept in the codebase. Do NOT delete their .py files.
- **Entry-day guard** — `should_exit()` checks skip DTE-based force-close on the same day the position was opened, preventing the same-day open/close bug.
- **Config validation at import** — `config.validate_config()` runs when `config.py` is imported. Ensures `max_dte_hold < dte_min` for all strategies. Agent fails fast with clear error on misconfiguration.
- **IBKR reconnect** — `ensure_connected()` skips reconnect outside market hours and near market close (>= 16:10 ET). Uses shorter retry count (3 vs 10) for mid-day reconnects. IBKR disconnects daily ~16:50 ET for maintenance.
- **EOD handling** — `_end_of_day()` detects if IBKR already disconnected and records positions as force-closed for next-day review instead of attempting exit orders.
- **Client ID 30** — reserved for this agent. Don't reuse in other IBKR apps (entryexpert uses 10 and 20).
- **Network** — must be on `entryexpert_stockalert-network` Docker network to reach ib-gateway.
- **BWB does not fallback** — when BWB can't generate a net credit (common in low IV), it returns `None` cleanly. No silent fallback to other strategies. Use `ACTIVE_STRATEGY=ALL` or `SMB` mode if you want multiple strategies.
- **Three Strikes Rule** — `RiskManager.can_enter()` halts trading after 3 consecutive losses in a day. Resets on daily_reset. Source: SMB Capital.
- **Bump-and-Cut risk scaling** — `RiskManager.check_bump_cut()` runs at daily_reset. Bumps `risk_multiplier` by 25% when 10d P&L > 2x daily stop (or 20d > 4x). Cuts by 50% when 5d P&L < -1.5x daily stop (weekly) or 20d < -2.5x (monthly). Multiplier capped [0.25, 2.0]. Applied to effective daily loss limit and available for position sizing. Cannot bump back until losses recovered.
- **VIX_SPIKE_PCS always active** — In SMB mode, the crash insurance trade runs in every regime because IV>40% self-filters. Only triggers during genuine market panics (~1-2 trades/year).
- **BB_CREDIT_SPREAD in range markets** — In SMB mode, BB credit spreads are active in RANGE (3-4) and FLAT (0-2) regimes where mean reversion thrives.
- **Volume/VWAP gating** — `VolumeConfig` controls volume z-score filtering. Entries are blocked during "quiet" volume regimes (z-score < 0.5). VWAP alignment required for directional strategies.
- **Trend day detection** — `TrendDayDetector` blocks all premium selling when trend score >= 65. Reduces position size by half when score >= 50. Optionally buys convexity on high-conviction trend days (score >= 80, disabled by default).
- **Adaptive learnings** — `learnings.py` reads autopsy data and creates time-based skip rules (e.g., "skip PCS entries before 10:00" if data shows losses). Rules expire after 30 days and regenerate from fresh data.
- **LLM strategist fallback** — When `STRATEGIST_ENABLED=true`, `LLMStrategist` calls an LLM for routing decisions but always falls back to rules-based routing (default: VRP_FILTERED) on any failure. Cached for 5 minutes, max 50 calls/day.
- **Wheel runs independently** — Wheel strategy has its own capital allocation (`WHEEL_CAPITAL`), scan interval, position tracking (`wheel_positions`), and state persistence (`wheel_state.json`). Does not interfere with SPX strategy positions.
- **Wheel assignment detection** — CSP and CC use `broker.get_stock_shares()` to check actual IBKR portfolio for share ownership after expiration, not option price heuristics. CSP assigned = 100 shares appear. CC called_away = shares disappear.
- **Wheel share verification** — `WheelCC.enter()` verifies 100 shares are held before selling a covered call. Blocks entry if shares are missing to prevent naked short calls.
- **Wheel exit pricing** — `exit()` methods receive the exit reason and current option price. Expiration events (assigned, expired_otm, called_away) skip buy-back orders since IBKR handles settlement. Profit target and stop-loss exits use the actual market price as the limit.
- **Wheel stop-loss** — CSP has a configurable stop-loss (`WHEEL_STOP_LOSS_PCT`, default 3x credit). Prevents unlimited downside on stock crashes.
- **Wheel entry time window** — Both CSP and CC entries are gated by the same time window (`WHEEL_ENTRY_TIME_START` to `WHEEL_ENTRY_TIME_END`) to avoid entering during volatile open.
- **Wheel reconciliation** — Position reconciliation includes Wheel stock symbols alongside SPX, detecting stale/orphan positions for all tracked underlyings.
- **ZERO_DTE_PCS uses actual remaining T** — `_remaining_T()` computes seconds to 16:00 ET divided by year-seconds, floored at 0.001. This gives accurate Black-Scholes values throughout the 0DTE day instead of a fixed T=1/365. Exit triggers at `long_strike` breach (approaching max loss), not `short_strike` touch (recoverable). Fallback exit limit price uses `spread_width * 0.90` instead of a hardcoded $0.10.
- **JADE_LIZARD no-upside-risk** — `no_upside_risk = total_credit >= call_spread_width` compares both in per-share dollars. Position sizing uses put-side max loss (the larger, uncapped exposure) as the risk proxy. `max_loss` key is included in the position dict. Exit triggers at `short_call_strike` breach (where losses begin), not `long_call_strike` (max loss). Scorer is checked in `should_enter()` to enforce SMB score <= 6.
- **VIX_SPIKE_PCS has NO stop loss** — Hold-to-win crash trade. Only exits at 50% profit target or 30 DTE time stop. The `price_below_long` check was removed because the backtest edge (40% WR, PF 2.41) is built on not closing at the bottom of crashes.
- **GAMMA_PROXY valuation uses Black-Scholes** — `should_exit()` prices both call and put legs via `black_scholes()` at current price and DTE, not an intrinsic + time-factor approximation.
- **CALL_SPREAD stop loss at 60% of debit** — Debit spreads can't lose more than the debit paid. Stop fires when 60% of the debit is lost (spread worth 40% of entry cost). P&L estimation matches.
- **`_estimate_pnl` handles `time_stop`** — Self-filtering strategies (45 DTE, exit at 14-21 DTE) now get a 20%-of-credit P&L estimate for `time_stop` exits instead of $0.
- **`_get_strategy` fallback covers `SMB_BWB`** — The fallback map includes `"SMB_BWB"` so open positions are monitored/exited regardless of `ACTIVE_STRATEGY` mode changes. Also added VRP_FILTERED-mode instance names for VRP_TIMED_PCS, MEAN_REV_PCS, RSI_TIMED_PCS.
- **Kronos Shadow is observation only** — `KronosShadow` runs in the main loop but NEVER alters `self.strategies`, entry gating, or order placement. Compares against structured live routing snapshots from `scan_for_entries()` (VRP/trend/volume/risk block state, sizing multipliers, active strategies). Overlay variant dispatched by `KRONOS_SHADOW_OVERLAY` config (conservative/balanced/aggressive). Fails safely (returns `ShadowDecision.from_failure()`) on any error. Daily inference cap prevents runaway costs. Lazy-loads model on first use. Disabled by default (`KRONOS_SHADOW_ENABLED=false`).

## Configuration

All config via env vars in `.env`, consumed by `config.py`. Key parameters:

| Variable | Default | Notes |
|---|---|---|
| `ACTIVE_STRATEGY` | BWB | BWB, CALL_SPREAD, LONG_CALL, PUT_CREDIT_SPREAD, JADE_LIZARD, ZERO_DTE_PCS, BOTH, ALL, SMB, or VRP_FILTERED |
| `DRY_RUN` | true | Must explicitly set false for live trading |
| `MARKET_DATA_TYPE` | 3 | 3=Delayed (free, safe default), 1=Live (requires IBKR subscription ~$4.50/mo). Broker auto-falls back to delayed if live subscription is not active. |
| `MAX_DAILY_LOSS` | 1000 | Halts all trading for the day when breached |
| `MAX_CONCURRENT` | 6 | Max open positions total |
| `ACCOUNT_CAPITAL` | 5000 | Total account capital for dynamic sizing |
| `MAX_RISK_PER_TRADE_PCT` | 0.02 | Max 2% risk per trade for dynamic sizing |
| `SCAN_INTERVAL` | 60 | Seconds between entry scans |
| `MONITOR_INTERVAL` | 30 | Seconds between position checks |
| `SMB_NARRATIVE_SCORE` | 0.5 | Override narrative check (0, 0.5, or 1) |
| `WHEEL_ENABLED` | false | Enable Wheel strategy (separate capital bucket) |
| `WHEEL_CAPITAL` | 15000 | Capital allocated to Wheel strategy |
| `WHEEL_SYMBOLS` | SOFI,HOOD,F | Comma-separated stock tickers for Wheel |
| `WHEEL_STOP_LOSS_PCT` | 3.0 | Close CSP at 3x credit received (stop-loss) |
| `BUTTERFLY_ENABLED` | false | Enable 0DTE Butterfly Pin strategy |
| `DIAGONAL_ENABLED` | false | Enable diagonal spread (PMCC) strategy |
| `STOCK_CALENDAR_ENABLED` | false | Enable stock calendar spread strategy |
| `GEX_ENABLED` | false | Enable Gamma Exposure module |
| `STRATEGIST_ENABLED` | false | Enable LLM meta-strategist |
| `VOL_ENABLED` | true | Enable volume/VWAP filtering |
| `TREND_ENABLED` | true | Enable trend day detection |
| `VOL_CYCLE_ENABLED` | true | Enable volatility cycle scanner |
| `KRONOS_SHADOW_ENABLED` | false | Enable Kronos shadow mode (Stage 3, observation only) |
| `KRONOS_SHADOW_INTERVAL` | 1200 | Shadow rebalance cadence in seconds (default 20 min) |
| `KRONOS_SHADOW_MODEL` | mini | Kronos model variant (mini/small/base) |
| `KRONOS_SHADOW_OVERLAY` | conservative | Overlay variant (conservative/balanced/aggressive) |
| `KRONOS_SHADOW_TREND_GATE` | true | Require baseline regime agreement for trend bias |

### SMB Mode

When `ACTIVE_STRATEGY=SMB`, the agent:
1. Rescores market conditions every 5 minutes using the 7-checks framework
2. Routes to appropriate strategies based on score (see SMB Scorer above)
3. ZERO_DTE_PCS is always active in every regime
4. Sends Telegram alerts when SMB score changes regime
5. Positions from previous regimes continue to be monitored even after regime change (via `_get_strategy` fallback to `_smb_*` instances)

### VRP_FILTERED Mode

When `ACTIVE_STRATEGY=VRP_FILTERED`, the agent runs a diversified portfolio:
- ZERO_DTE_PCS: always active (daily income engine, not VRP-gated)
- PCS + CS: gated by VRP > 2 and price > MA20
- Uncorrelated strategies (BB_MEAN_REV, GAMMA_PROXY, BEAR_RSI_REV, BB_SQUEEZE): self-filter via entry conditions
- All self-filtering strategies (MEAN_REV_PCS, RSI_TIMED_PCS, VRP_TIMED_PCS, SMB_BWB, VIX_SPIKE_PCS, BB_CREDIT_SPREAD)

### Strategy Mix

- **60%** — 0DTE SPX put credit spreads (ZERO_DTE_PCS) — daily income engine
- **25%** — Weekly PCS + Jade Lizard (PUT_CREDIT_SPREAD, JADE_LIZARD) — range/neutral
- **15%** — BWB + Call Spread + Long Call — directional/breakout

## Roadmap

### Phase 1: Paper Trading Validation (CURRENT)
- Running on IBKR paper account DUM065250 with delayed market data (live subscription not yet active; broker auto-falls back)
- SMB mode, backtest-optimized parameters (BWB 20d/pt40/sl1.5, PCS 30d, 3% risk/trade, mc=6)
- Goal: prove the edge over 1-3 months of real market conditions before going live

### Phase 2: Wheel Strategy — Equity Income (FUTURE — account >= $25k)
Add cash-secured puts + covered calls ("the Wheel") on individual stocks for monthly income. Only activates when account equity hits $25k. 60/40 split: $15k Wheel allocation, $10k stays on SPX engine. Forward test with $15k paper principal before live. Target: $225-450/month (1.5-3%) on Wheel capital. See `research/PRD-wheel-strategy.md` for full spec. Source: SMB Capital (Seth Freudberg).

### Phase 3: 0DTE Butterfly Pin Strategy + GEX Module (FORWARD TEST)
Asymmetric home-run play: narrow 0DTE SPX call butterflies at dealer gamma pin targets. Risk $40-60/contract for 500-5,000% returns. 52% win rate. GEX module computes dealer gamma exposure from IBKR option chain data (no paid services). Entry 12-2:30pm ET, scale out 3-3:45pm. See `research/PRD-0dte-butterfly.md` for full spec.

### Phase 4: Multi-Underlying Support (FUTURE — after paper validation)
Expand beyond SPX to cheaper underlyings for better capital efficiency on a $5k account:

**Candidates (by priority):**
1. **XSP** — Mini-SPX (1/10th size). Cash-settled, European-style. Same strategies work at 1/10th the risk. Easiest migration path.
2. **SPY** — 1/10th SPX notional, very liquid, daily 0DTE. American-style (early assignment risk on short options).
3. **QQQ** — NASDAQ exposure, liquid options, daily 0DTE. Different market dynamics, could diversify.
4. **Liquid single stocks** (AAPL, MSFT, NVDA, AMZN, TSLA) — uncorrelated to index, but requires per-stock IV/delta calibration.

**Required code changes:**
- Make strike rounding dynamic (SPX=$5, SPY/XSP=$1, stocks=$0.50-$2.50)
- Scale spread widths and credit targets per underlying
- Handle American vs European style (assignment risk)
- Add XSP as Index type in broker.py (currently only SPX→Index, everything else→Stock)
- Support running multiple underlyings simultaneously or per-strategy routing

**Two approaches to evaluate:**
- **A) Single underlying switch** — change `UNDERLYING` env var, auto-scale all parameters. Simple.
- **B) Multi-underlying portfolio** — PCS on SPY + BWB on QQQ + 0DTE on XSP. Spreads risk but complex.
