# Week 1 Bugfix Design — Options Agent

**Date:** 2026-03-27
**Status:** Approved
**Approach:** A (fix in place)
**Goal:** Fix all 5 critical bugs from Week 1 forward test, resume paper trading

---

## Context

The options agent ran a 2-day forward test (Mar 26-27, 2026). It produced 0 successful BWB trades, 5 scratch/losing put vertical trades, and exposed 5 critical bugs. The agent targets 10% monthly returns on SPX options using a Broken Wing Butterfly strategy at 7 DTE.

---

## Bug #1: BWB Strategy Rewrite

### Problem
`strategies/bwb.py` is a put vertical spread mislabeled as BWB. Fixed wing widths (5/10/15pt) cannot generate net credit when IV is ~22%. The `min_iv_rank=20` filter passes but the structure physically cannot produce credit in low-IV regimes. Result: 0 BWB trades in 2 days.

### Fix
Rewrite `bwb.py` to a real 3-leg Broken Wing Butterfly.

**Structure:** Long 1x higher put / Short 2x middle puts / Long 1x lower put (broken wing)

**Strike selection — hybrid delta-based with floor:**
- Short strikes (middle): target ~25-delta puts, found via Black-Scholes from `pricing.py`
- Long high put (upper wing): ATM or nearest 5pt strike above short, creating the wide upper wing
- Long low put (broken wing): target ~8-10 delta, minimum 10pt below short strikes
- Search multiple delta/width combinations, pick the one with best risk/reward that produces net credit

**Credit requirement:** Net credit >= `min_net_credit` (default $0.10/share) at entry or skip the day.

**Fallback:** If no configuration produces credit, try tighter upper wing (ATM - 5pts instead of ATM). If still no credit, log and skip. No silent fallback to a different strategy type.

**Config changes to `BWBConfig` in `config.py`:**
- Remove: `wing_width_near`, `wing_width_far`
- Add: `short_delta_target: float = 0.25` (absolute value, target delta for short strikes)
- Add: `wing_delta_target: float = 0.08` (target delta for broken wing long put)
- Add: `min_wing_width: int = 10` (minimum points between short and broken wing)
- Add: `min_net_credit: float = 0.10` (minimum credit per share to enter)
- Keep: `dte_target: 7`, `dte_min: 5` (already 5 in current code), `profit_target_pct: 0.50`, `stop_loss_pct: 2.00`
- Change: `max_dte_hold: 1` (was 3)

**Combo order:** Build a 3-leg combo order with ratios 1/2/1:
```python
legs = [
    (con_high, 1, "BUY"),   # long 1x upper put
    (con_mid,  2, "SELL"),   # short 2x middle puts
    (con_low,  1, "BUY"),   # long 1x broken wing put
]
```
`place_combo_order()` already supports the `ratio` field in the tuple format.

**Position dict keys (used by notifier, dashboard, state_writer):**

All values in per-share/per-point terms unless noted. The `$100 * qty` multiplier is applied at display/P&L estimation time only.

- `strategy`: `"BWB"`
- `strike_high`: upper long put strike (float)
- `strike_mid`: short put strike x2 (float)
- `strike_low`: broken wing long put strike (float)
- `con_high`: conId for upper long put
- `con_mid`: conId for short puts
- `con_low`: conId for broken wing put
- `net_credit`: net credit per share (float, e.g. 0.50 = $50/contract)
- `max_profit`: `(strike_high - strike_mid) + net_credit` (per-share; upper wing width + credit)
- `qty`: number of spreads (int)
- `expiration`: YYYYMMDD string
- `iv`: implied volatility at entry (float, decimal)
- `dte`: days to expiry at entry (int)
- `entry_time`: ISO 8601 datetime string
- `entry_underlying`: SPX price at entry (float)
- `status`: `"open"` or `"closed"`

**Exit logic for 3-leg BWB in `should_exit()`:**
- Price below `strike_low` (broken wing): max loss reached, exit immediately
- Price below `strike_mid` (short strikes): high risk zone, exit
- DTE <= `max_dte_hold` (and not entry day): force-close
- Theoretical P&L >= `profit_target_pct * max_profit`: take profit
- Theoretical P&L <= `-stop_loss_pct * net_credit`: stop loss
- P&L calculation: use Black-Scholes to price all 3 legs at current underlying price, compute net value vs entry credit

**Expiration search:** `get_expirations(dte_min=BWB.dte_min, dte_max=BWB.dte_target + 3)` — derived from config, not hardcoded.

**Files changed:** `config.py`, `strategies/bwb.py`

---

## Bug #2: Notifier KeyError

### Problem
`notifier.py:trade_entered()` checks `strat == "BWB"` and accesses `position['strike_high']`, `position['strike_mid']`, `position['strike_low']` — keys that the old put-vertical `bwb.py` did not produce. Every entry threw `KeyError: 'strike_high'`.

### Fix
After Bug #1 rewrite, the real BWB will produce `strike_high`, `strike_mid`, `strike_low` keys. Update `notifier.py:trade_entered()` to display the 3-leg structure:

```
BWB Entered
Exp: 20260402
Long: 5600P | Short: 5580Px2 | Wing: 5560P
Net Credit: $150
Max Profit: $2,150
```

Use `.get()` with fallback `"?"` for all strike keys to prevent future KeyErrors.

Also update `trade_exited()` to display the 3-leg structure in exit notifications (useful for debugging during paper trading). Update the BWB label text from "PUT VERTICAL Entered" to "BWB Entered".

**Files changed:** `notifier.py`

---

## Bug #3: Same-Day Exit

### Problem
Positions entered at 7 DTE exited immediately with reason `max_dte_hold (7 DTE)`. The logs show the exit triggered on the same scan cycle as entry.

### Fix

**Config:**
- `dte_target: 7` (unchanged)
- `dte_min: 5` (already 5 in current code, unchanged — allows 5-10 DTE entries)
- `max_dte_hold: 1` (change from 3 to 1 — force-close only at 1 DTE)

**Edge case — DTE=0 (agent was down and wakes up on expiration day):** The `dte <= 1` check catches DTE=0, so the position will be force-closed. The entry-day guard does not interfere since it's not the entry day. This is correct behavior.

**Code guard in `bwb.py:should_exit()`:**
Add an entry-day safety check. If `entry_time` is today, skip the `max_dte_hold` check entirely. A position should never be force-closed due to DTE on the day it was opened.

```python
# Never force-close on entry day
entry_date = datetime.fromisoformat(position["entry_time"]).date()
if today != entry_date and dte <= BWB.max_dte_hold:
    return True, f"max_dte_hold ({dte} DTE)"
```

**Expiration search range:** `get_expirations(dte_min=5, dte_max=10)` — target 7, accept 5-10.

**Files changed:** `config.py`, `strategies/bwb.py`

---

## Bug #4: Delayed Market Data

### Problem
`broker.py:get_underlying_price()` switches to delayed data (type 3) then back to live (type 1). But `get_option_quote()` switches to delayed and never switches back. This leaves the broker permanently in delayed mode, causing 10,000+ warning 10167 messages.

### Fix
The agent doesn't have live market data subscriptions. Stop fighting it.

- Set `reqMarketDataType(3)` once at connection time in `broker.py:connect()`
- Remove all `reqMarketDataType` toggling from `get_underlying_price()` and `get_option_quote()`
- The agent already uses Black-Scholes theoretical pricing for strike selection and P&L monitoring, so delayed underlying price is sufficient
- Add a comment noting that switching to `reqMarketDataType(1)` at connect time is the only change needed if live subscriptions are added later

**Files changed:** `broker.py`

---

## Bug #5: Overnight Connection Thrashing

### Problem
After market close (~16:00 ET), IBKR drops the connection. The agent's main loop continues ticking every 10 seconds, calling `ensure_connected()` which enters a 10-retry x 15-second delay reconnect loop. This thrashes for minutes, fills logs with errors, and wastes resources.

### Fix — market-hours-aware scheduling in `agent.py`:

**Timezone handling:**
The Docker container is already configured with `TZ=America/New_York` in `docker-compose.yml`, so `datetime.now()` returns ET. All time comparisons in the codebase rely on this. Add a startup assertion in `agent.py` to verify the timezone is ET and log a warning if not. This is a known constraint — the agent must run in ET.

**End of day (16:15 ET):**
1. Force-close any remaining open positions
2. Send daily P&L summary via notifier
3. Call `broker.disconnect()`
4. Write final heartbeat with `mode: "sleeping"`
5. Enter sleep mode

**Sleep mode:**
- Sleep in 60-second chunks until 09:20 ET next trading day
- Skip Saturday and Sunday entirely (calculate next Monday)
- Continue writing heartbeat every 60s so dashboard shows agent is alive but sleeping
- Dashboard can show "SLEEPING" status based on heartbeat metadata

**Known limitation:** US market holidays (Good Friday, Memorial Day, etc.) are not handled. The agent will wake up, connect, and sit idle on holidays. This is harmless (no setups will be found) but wastes a connection. Holiday handling is deferred to future work.

**Morning reconnect (09:20 ET):**
1. Call `broker.connect()`
2. Run `daily_housekeeping()` (reset risk state)
3. Resume normal 10-second main loop

**`daily_housekeeping()` timing fix:**
Current code triggers only when `now.strftime("%H:%M") == "09:30"` (exact string match), which can be missed with a 10-second loop. Change to `>=` comparison with a `last_housekeeping_date` flag — run once per day on first tick after 09:20.

**`ensure_connected()` improvement:**
- Add market hours check: if current time is outside 09:20-16:15 ET on a weekday, don't attempt reconnection. Log `"Outside market hours — skipping reconnect"` and return False.
- This prevents the reconnect storm even if the sleep scheduling has a timing edge case.

**Heartbeat metadata:**
- Update `state_writer.write_heartbeat()` to accept an optional `mode` parameter: `"trading"`, `"sleeping"`, `"disconnected"`
- Dashboard reads `mode` field from `heartbeat.json` to show appropriate status badge

**Files changed:** `agent.py`, `broker.py`, `state_writer.py`, `dashboard/app.py`

---

## Files Changed Summary

| File | Changes |
|------|---------|
| `config.py` | BWBConfig: remove fixed widths, add delta targets + min_net_credit, change max_dte_hold=1 |
| `strategies/bwb.py` | Full rewrite: real 3-leg BWB, hybrid delta-based strike selection, 3-leg exit logic, entry-day exit guard |
| `notifier.py` | Fix trade_entered() and trade_exited() to use correct BWB keys with .get() fallbacks, fix label text |
| `broker.py` | Set delayed data once at connect, remove toggling, add market-hours check to ensure_connected() |
| `agent.py` | Add overnight disconnect at 16:15, sleep-until-morning logic, morning reconnect at 09:20, fix daily_housekeeping timing, add TZ assertion |
| `state_writer.py` | Update write_heartbeat() to accept optional mode parameter |
| `dashboard/app.py` | Read heartbeat mode field, show SLEEPING status badge |

---

## Long-Term Improvements (Future Work)

These are documented for future implementation after the agent proves stable in paper trading:

### Approach B: Strategy Base Class + Scheduler
- Extract `BaseStrategy` ABC with `enter()`, `should_exit()`, `exit()` interface and shared DTE/P&L logic
- `Scheduler` class to own connection lifecycle (connect, disconnect, sleep, reconnect)
- Benefit: cleaner separation, easier to add new strategies (e.g., calendar spreads, jade lizards)
- When: after 2+ weeks of stable paper trading and before adding a 3rd strategy

### Approach C: Event-Driven State Machine
- Rebuild `agent.py` around states: `CONNECTING -> PRE_MARKET -> SCANNING -> MONITORING -> POST_MARKET -> SLEEPING`
- Each state has explicit entry/exit actions and allowed transitions
- Benefit: eliminates timing edge cases, makes behavior fully deterministic
- When: if the agent grows beyond 3 strategies or needs to handle multiple underlyings

### Live Market Data
- Switch `reqMarketDataType(1)` at connect time when subscriptions are available
- Replace Black-Scholes P&L estimates with real greeks from `ticker.modelGreeks`
- Benefit: more accurate entry/exit decisions, especially near expiration
- When: after confirming the strategy is profitable on delayed data

### Position Reconciliation
- On every reconnect, query `broker.get_positions()` and reconcile with in-memory `open_positions`
- Handle orphaned positions (agent restarted mid-trade) by matching on expiration + strikes
- Benefit: prevents phantom positions and missed exits after container restarts
- When: before going live (DRY_RUN=false)

### Multi-Account / Multi-Instance
- Client ID management for running BWB + Condor on separate agent instances
- Shared risk state via Redis or file locks
- Benefit: independent scaling of strategies
- When: only if running BOTH strategies simultaneously causes contention

---

## Success Criteria

1. BWB strategy generates net credit entries in IV rank 20-85 range
2. Zero KeyErrors in notifier on trade entry/exit
3. No same-day forced exits due to DTE
4. Clean logs — no market data type warnings
5. Agent cleanly disconnects at 16:15 ET, reconnects at 09:20 ET, no connection thrashing
6. Ready for 2-week paper trading extension with 10+ clean trades
