# BTC Cycle Phase Monitor

Tracks Bitcoin's macro market cycle position and sends Telegram + email alerts on phase transitions and weekly Monday updates.

## Phase Definitions

| Phase | Condition | Action |
|-------|-----------|--------|
| 🟢 **ACCUMULATE** | BTC < 200W SMA | DCA aggressively. Max allocation. |
| 🟡 **HOLD** | BTC > SMA, pre-halving or early cycle | Hold spot. Minimal trading. |
| 🚀 **RIDE** | Post-halving bull run (halving → Q4 of year+1) | Hold spot. Add on dips >20%. |
| 🔴 **DISTRIBUTE** | Q4 year-after-halving OR Pi Cycle crossed OR MVRV ≥ 5 | Scale out 25%/month. Take profits. |
| ⚙️ **GRIND** | Post-distribution bear market | Run active trading. Leverage on dips. |

**Current context (as of March 2026):**
- Last halving: April 19, 2024 (703 days ago)
- Distribution window: Q4 2025 (Oct–Dec 2025) — now passed
- Current phase: **GRIND** — bear market / active trading mode
- Next halving: ~March 2028

## Indicators Used

### 1. 200-Week SMA
- **Source:** Kraken OHLC API (weekly candles, ~429 weeks available)
- **Signal:** BTC below 200W SMA = deep accumulation zone
- **Current:** BTC +18.6% above 200W SMA (~$59,431)

### 2. Pi Cycle Top Indicator
- **Calculation:** 111-day MA vs 350-day MA × 2
- **Signal:** Cross = cycle top (DISTRIBUTE)
- **Source:** Computed from Binance.US daily candles (400 days)
- **Current:** 59.3% gap — no cross signal

### 3. MVRV Ratio
- **Source:** CoinMetrics community API (free, no key)
- **Signal:** MVRV < 0.5 = undervalued, MVRV ≥ 5.0 = overheated
- **Current:** ~1.25 (fair value)
- **Graceful fallback:** If CoinMetrics API is unavailable, analysis continues without it

### 4. Halving Cycle Calendar
- Hardcoded halving dates: 2012, 2016, 2020, 2024
- RIDE phase: halving → Q4 of following year
- DISTRIBUTE window: Q4 of year after halving

## Data Sources (All Free, No Auth)

| Data | Source | Endpoint |
|------|--------|----------|
| Weekly candles | Kraken | `GET /0/public/OHLC?pair=XBTUSD&interval=10080` |
| Weekly fallback | Binance.US | `GET /api/v3/klines?symbol=BTCUSD&interval=1w` |
| Daily candles | Binance.US | `GET /api/v3/klines?symbol=BTCUSD&interval=1d&limit=400` |
| Daily fallback | Kraken | `GET /0/public/OHLC?pair=XBTUSD&interval=1440` |
| MVRV | CoinMetrics | `GET /v4/timeseries/asset-metrics?assets=btc&metrics=CapMVRVCur` |

## Notification Triggers

1. **Phase transition** — Fires immediately when phase changes
2. **Weekly Monday update** — Fires every Monday (if not already sent that day)

### Delivery Channels
- **Telegram:** All Things Crypto group (`-1003766961821`) — message printed to stdout, OpenClaw delivers it
- **Email:** POSTs to email-webhook app at `http://localhost:3500/api/webhook/e7c94802-443d-4d57-a6c9-ed475955c2cc`

## File Structure

```
cycle/
├── cycle_monitor.py     # Main monitoring script
├── cycle_state.json     # Current phase state (auto-created)
├── cycle_history.json   # All phase checks log (auto-created)
└── README.md            # This file
```

## Running

```bash
cd ~/apps/auto-research-trader/cycle
python3 cycle_monitor.py
```

No dependencies beyond the standard `requests` library (pre-installed in the OEFR venv).

## Cron Setup (Recommended)

Run every 6 hours via OpenClaw cron:

```
0 */6 * * *  cd ~/apps/auto-research-trader/cycle && python3 cycle_monitor.py >> /tmp/cycle_monitor.log 2>&1
```

Or use the OpenClaw scheduler. The script is idempotent — safe to run as often as needed.

## State Files

### cycle_state.json
```json
{
  "phase": "GRIND",
  "btc_price": 70491.0,
  "sma_200w": 59431.41,
  "distance_pct": 18.6,
  "mvrv": 1.2517,
  "pi_cycle": { "status": "normal", "gap_pct": 59.27 },
  "last_halving": "2024-04-19",
  "days_since_halving": 703,
  "last_update": "2026-03-24T03:16:11+00:00"
}
```

### cycle_history.json
Append-only log of every monitor run with phase, indicators, and whether a notification was sent.

## Alert Thresholds

| Alert | Condition |
|-------|-----------|
| ACCUMULATE zone | BTC < 200W SMA |
| Pi Cycle warning | 111MA within 2% of 350MA×2 |
| MVRV overheated | MVRV ≥ 5.0 |
| MVRV undervalued | MVRV ≤ 0.5 |
| DISTRIBUTE window | Q4 of year after halving |
