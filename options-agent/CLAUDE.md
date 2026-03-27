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
```

No tests, no linter, no build step. Python 3.12, dependencies in `requirements.txt`.

## Architecture

The agent runs a single main loop in `agent.py` that ticks every 10 seconds:
1. **Market hours check** — skips weekends, only trades 09:30-16:00 ET
2. **Entry scan** (every `SCAN_INTERVAL` seconds) — each strategy evaluates independently
3. **Position monitor** (every `MONITOR_INTERVAL` seconds) — checks exit conditions on open positions
4. **Risk enforcement** — daily loss limit halts trading for the day

### Core Modules

- **`agent.py`** — `OptionsAgent` orchestrates the main loop, entry scanning, position monitoring, and P&L estimation. Entrypoint.
- **`broker.py`** — `IBKRBroker` wraps `ib_insync`. Handles connect/reconnect, market data (delayed type 3), option chains, combo orders, and single-leg orders. All IBKR interaction goes through this.
- **`risk.py`** — `RiskManager` tracks daily P&L, enforces `MAX_DAILY_LOSS`, halts trading on breach. Persists state to `data/risk_state.json` so it survives restarts.
- **`pricing.py`** — Black-Scholes implementation for theoretical pricing and Greeks. Used by strategies to find strikes by delta and estimate P&L without live market data subscriptions.
- **`notifier.py`** — Telegram alerts (trade entered/exited, daily summary, risk breaches, heartbeat).
- **`state_writer.py`** — Atomic JSON writes (temp file + rename) to `data/` directory. Dashboard reads these files; never connects to IBKR directly.
- **`config.py`** — All tunable parameters. Reads from env vars with defaults. Contains `BWBConfig` and `CondorConfig` dataclasses.

### Strategies (`strategies/`)

Each strategy implements `enter()`, `should_exit(position, current_price)`, and `exit(position)`.

- **`bwb.py`** — Despite the name, this is a **put vertical credit spread** (sell OTM put, buy further OTM put). Uses Black-Scholes to find optimal delta/width combination. 7 DTE target. Exits at 50% profit, 2x stop, DTE <= 3, or price breach.
- **`condor.py`** — 0DTE iron condor. Entry window 09:45-10:15 ET only. Sells ~10-delta strangles with 5pt wings. Force-closes at 15:45.

### Dashboard (`dashboard/app.py`)

Streamlit app that reads JSON files from `data/` directory (mounted read-only). Dark theme, auto-refreshes every 30 seconds. Shows open positions with payoff diagrams, cumulative P&L chart, live logs, trade history, and configuration. Runs on port 8502 (mapped from container's 8501).

### Data Flow

```
agent.py → state_writer.py → data/*.json ← dashboard/app.py
                                          (read-only volume mount)
```

JSON files in `data/`: `positions.json`, `portfolio.json`, `agent_config.json`, `trade_history.json`, `risk_state.json`, `heartbeat.json`.

## Key Design Decisions

- **DRY_RUN mode** (`DRY_RUN=true` in `.env`) — logs what would happen but doesn't place orders. Default is true for safety.
- **Delayed market data** — broker switches to market data type 3 (delayed) for underlying price, avoiding live subscription requirements. Switches back to type 1 for options.
- **Theoretical pricing** — strategies use Black-Scholes from `pricing.py` rather than live option quotes for P&L monitoring and strike selection, reducing data subscription costs.
- **Client ID 20** — reserved for this agent. Don't reuse in other IBKR apps (entryexpert uses 10/11).
- **Network** — must be on `entryexpert_stockalert-network` Docker network to reach ib-gateway.

## Configuration

All config via env vars in `.env`, consumed by `config.py`. Key parameters:

| Variable | Default | Notes |
|---|---|---|
| `ACTIVE_STRATEGY` | BWB | BWB, CONDOR, or BOTH |
| `DRY_RUN` | true | Must explicitly set false for live trading |
| `MAX_DAILY_LOSS` | 500 | Halts all trading for the day when breached |
| `MAX_CONCURRENT` | 2 | Per-strategy max open positions |
| `SCAN_INTERVAL` | 60 | Seconds between entry scans |
| `MONITOR_INTERVAL` | 30 | Seconds between position checks |
