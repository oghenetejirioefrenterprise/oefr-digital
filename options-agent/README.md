# Options Agent

Fully autonomous SPX options trading agent. Connects to your existing ib-gateway, scans for setups, places trades, monitors positions, and exits automatically. Zero human intervention required during market hours.

## Architecture

```
agent.py          — Main loop (market hours, scan, monitor, risk)
broker.py         — IBKR connection (ib_insync), quotes, orders
risk.py           — Daily loss limits, position sizing, halt logic
notifier.py       — Telegram alerts for every trade + daily summary
config.py         — All tunable parameters
strategies/
  bwb.py          — Broken Wing Butterfly (9 DTE, put side, 50% profit target)
  condor.py       — 0DTE Iron Condor (10-delta, 9:45-10:15 entry window)
```

## Quick Start

### 1. Approve IBKR 2FA
When ib-gateway restarts, approve the push on IBKR Mobile.

### 2. Start in DRY RUN mode first
```bash
cd ~/apps/options-agent
# DRY_RUN=true is default in .env
docker compose up -d
docker logs -f options-agent
```

### 3. Verify you see in logs:
```
Options Agent starting
Strategy: BWB | DRY_RUN: True
Connected. Account: ['U...']
```

### 4. Go live when ready
```bash
# Edit .env
DRY_RUN=false

docker compose up -d --force-recreate
```

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| ACTIVE_STRATEGY | BWB | BWB, CONDOR, or BOTH |
| UNDERLYING | SPX | SPX or SPY |
| MAX_CONCURRENT | 2 | Max open positions |
| MAX_DAILY_LOSS | 500 | Hard stop trading for the day ($) |
| MAX_POSITION_RISK | 2500 | Max risk per trade ($) |
| DRY_RUN | true | false to place live orders |

## BWB Strategy (Default)

- Entry: 9 DTE, put BWB below market
- Strikes: ATM long / -20pt short x2 / -30pt long (broken wing)
- Net credit at entry required (rejects debit structures)
- IV rank filter: 20-85
- Exit: 50% profit target OR 2x stop OR DTE ≤ 7

## 0DTE Condor Strategy

- Entry: 9:45-10:15 AM ET only
- Strikes: ~10-delta calls and puts
- Width: 5 pts each side
- Exit: 50% profit, 2x stop, or 15:45 force-close

## Telegram Alerts

You'll get notified on every:
- Trade entered (strikes, credit, max risk)
- Trade exited (reason, P&L)
- Daily summary (total P&L, wins/losses)
- Risk breach (trading halted)
- Agent heartbeat (daily at market open)

## IBKR Requirements

- ib-gateway must have READ_ONLY_API=no (already set in entryexpert/.env)
- Client ID 20-21 reserved for this agent (don't reuse in other apps)
- Market data subscriptions: SPX index data + options data required

## Commands

```bash
# Start
docker compose up -d

# Logs
docker logs -f options-agent

# Stop
docker compose down

# Rebuild after code changes
docker compose up -d --build
```
