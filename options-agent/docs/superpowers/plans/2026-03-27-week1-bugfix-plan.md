# Week 1 Bugfix Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 5 critical bugs from the Week 1 forward test so the options agent can resume paper trading with a real Broken Wing Butterfly strategy.

**Architecture:** Fix in place — modify 7 existing files, no new files or abstractions. Each task targets one bug and produces a working commit.

**Tech Stack:** Python 3.12, ib_insync, Streamlit, Black-Scholes pricing

**Spec:** `docs/superpowers/specs/2026-03-27-week1-bugfix-design.md`

---

## Chunk 1: Config + BWB Strategy Rewrite (Bugs #1, #3)

### Task 1: Update BWBConfig in config.py

**Files:**
- Modify: `config.py:23-39`

- [ ] **Step 1: Update BWBConfig dataclass**

Replace the BWBConfig class with delta-based parameters:

```python
@dataclass
class BWBConfig:
    dte_target: int       = 7       # days to expiry at entry
    dte_min: int          = 5       # don't enter if DTE < this
    qty: int              = 1       # number of spreads
    # Strike selection (delta-based, hybrid with floor)
    short_delta_target: float = 0.25   # target delta for short (middle) strikes (absolute)
    min_wing_width: int       = 10     # minimum pts between short and broken wing
    min_net_credit: float     = 0.10   # minimum credit per share to enter
    # Exit rules
    profit_target_pct: float  = 0.50   # close at 50% of max profit
    stop_loss_pct: float      = 2.00   # close at 2x premium received
    max_dte_hold: int         = 1      # force-close if DTE drops to this
    # Entry filters
    min_iv_rank: float    = 20.0    # don't enter if IV rank < 20
    max_iv_rank: float    = 85.0    # don't enter if IV rank > 85
```

This removes `wing_width_near`, `wing_width_far` (fixed offsets that couldn't produce credit in low IV), and `wing_delta_target` (unused — wing strike is found by searching widths from `min_wing_width` upward, optimizing for R/R). Adds `short_delta_target`, `min_wing_width`, `min_net_credit`. Changes `max_dte_hold` from 3 to 1.

- [ ] **Step 2: Verify config loads**

Run: `cd /home/oghenetejiri/apps/options-agent && python -c "from config import BWB; print(f'short_delta={BWB.short_delta_target} min_wing={BWB.min_wing_width} min_credit={BWB.min_net_credit} max_dte_hold={BWB.max_dte_hold}')"`

Expected: `short_delta=0.25 min_wing=10 min_credit=0.1 max_dte_hold=1`

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "fix(config): replace fixed BWB wing widths with delta-based params, set max_dte_hold=1"
```

---

### Task 2: Rewrite BWB strategy as real 3-leg Broken Wing Butterfly

**Files:**
- Modify: `strategies/bwb.py` (full rewrite)

- [ ] **Step 1: Rewrite bwb.py**

Replace the entire file with the real BWB implementation:

```python
"""
strategies/bwb.py — Broken Wing Butterfly (3-leg put structure)
Long 1x upper put / Short 2x middle puts / Long 1x lower put (broken wing).
Hybrid delta-based strike selection with minimum wing width floor.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import BWB
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years

log = logging.getLogger("strategy.bwb")


class BWBStrategy:
    name = "BWB"

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    def should_enter(self) -> bool:
        """Check IV rank filter before entering."""
        try:
            iv_rank = self.broker.get_iv_rank()
            log.info(f"BWB entry check: IV_rank={iv_rank:.1f} (min={BWB.min_iv_rank} max={BWB.max_iv_rank})")
            if iv_rank < BWB.min_iv_rank:
                log.info(f"BWB skip: IV rank {iv_rank:.1f} < min {BWB.min_iv_rank}")
                return False
            if iv_rank > BWB.max_iv_rank:
                log.info(f"BWB skip: IV rank {iv_rank:.1f} > max {BWB.max_iv_rank}")
                return False
            return True
        except Exception as e:
            log.warning(f"BWB should_enter IV check failed: {e} — allowing entry")
            return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(
            dte_min=BWB.dte_min,
            dte_max=BWB.dte_target + 3,
        )
        if not exps:
            log.warning("No expirations found in DTE window")
            return None
        today = date.today()
        best = min(
            exps,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - BWB.dte_target),
        )
        dte = (datetime.strptime(best, "%Y%m%d").date() - today).days
        log.info(f"Selected expiration {best} ({dte} DTE)")
        return best

    def build_legs(self, expiration: str) -> Optional[dict]:
        """
        Build a real Broken Wing Butterfly:
        Long 1x upper put (near ATM) / Short 2x middle puts / Long 1x lower put (broken wing).
        Uses hybrid delta-based selection with minimum wing width floor.
        """
        try:
            price = self.broker.get_underlying_price()
        except Exception as e:
            log.warning(f"Could not get underlying price: {e}")
            return None
        if price is None or price <= 0:
            return None

        today = date.today()
        exp_date = datetime.strptime(expiration, "%Y%m%d").date()
        dte = (exp_date - today).days
        T = dte_to_years(dte)
        iv = get_broker_iv(self.broker)

        log.info(f"BWB build: underlying={price:.2f} IV={iv*100:.1f}% DTE={dte}")

        # Find short (middle) strike at target delta
        short_delta = -BWB.short_delta_target  # negative for puts
        strike_mid = get_strike_from_delta(self.broker, price, T, iv, short_delta, "P")

        best = None

        # Try multiple upper wing widths and wing deltas
        for upper_offset in [0, 5, 10, 15, 20]:
            strike_high = strike_mid + upper_offset
            # Round to nearest 5
            strike_high = round(strike_high / 5) * 5

            # Don't go above ATM + 5
            if strike_high > price + 5:
                continue

            for wing_width in range(BWB.min_wing_width, 35, 5):
                strike_low = strike_mid - wing_width
                strike_low = round(strike_low / 5) * 5

                # Price all 3 legs via Black-Scholes
                p_high = black_scholes(price, strike_high, T, iv, right="P")["price"]
                p_mid = black_scholes(price, strike_mid, T, iv, right="P")["price"]
                p_low = black_scholes(price, strike_low, T, iv, right="P")["price"]

                # BWB net credit = sell 2x mid - buy 1x high - buy 1x low
                net_credit = 2 * p_mid - p_high - p_low

                if net_credit < BWB.min_net_credit:
                    continue

                upper_wing = strike_high - strike_mid
                max_profit = upper_wing + net_credit  # per-share

                # Risk/reward ratio
                max_loss_down = wing_width - upper_wing - net_credit  # loss if below strike_low
                if max_loss_down <= 0:
                    max_loss_down = 0.01  # avoid division by zero
                rr_ratio = max_profit / max_loss_down

                candidate = {
                    "strike_high": strike_high,
                    "strike_mid": strike_mid,
                    "strike_low": strike_low,
                    "net_credit": net_credit,
                    "max_profit": max_profit,
                    "upper_wing": upper_wing,
                    "lower_wing": wing_width,
                    "rr_ratio": rr_ratio,
                }

                if best is None or rr_ratio > best["rr_ratio"]:
                    best = candidate

        if not best:
            log.warning(
                f"No valid BWB configuration found "
                f"(IV={iv*100:.1f}%, mid_strike={strike_mid}, price={price:.0f})"
            )
            return None

        log.info(
            f"Best BWB: {best['strike_high']}P / {best['strike_mid']}Px2 / {best['strike_low']}P "
            f"| credit=${best['net_credit']*100:.0f} | max_profit=${best['max_profit']*100:.0f} "
            f"| upper={best['upper_wing']}pts lower={best['lower_wing']}pts | R/R={best['rr_ratio']:.2f}"
        )

        # Qualify all 3 contracts
        contracts = []
        for strike in [best["strike_high"], best["strike_mid"], best["strike_low"]]:
            opt = Option(config.UNDERLYING, expiration, strike, "P", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                contracts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}P: {e}")
                return None

        return {
            "expiration": expiration,
            "strike_high": best["strike_high"],
            "strike_mid": best["strike_mid"],
            "strike_low": best["strike_low"],
            "con_high": contracts[0].conId,
            "con_mid": contracts[1].conId,
            "con_low": contracts[2].conId,
            "net_credit": best["net_credit"],
            "max_profit": best["max_profit"],
            "upper_wing": best["upper_wing"],
            "lower_wing": best["lower_wing"],
            "iv": iv,
            "dte": dte,
            "underlying_price": price,
        }

    def enter(self) -> Optional[dict]:
        if not self.should_enter():
            return None

        expiration = self.find_expiration()
        if not expiration:
            return None

        legs_info = self.build_legs(expiration)
        if not legs_info:
            return None

        # 3-leg BWB combo: buy 1x high, sell 2x mid, buy 1x low
        legs = [
            (legs_info["con_high"], 1, "BUY"),
            (legs_info["con_mid"],  2, "SELL"),
            (legs_info["con_low"],  1, "BUY"),
        ]

        # Limit price: net credit we want (negative = credit to us)
        limit_price = -(legs_info["net_credit"] - 0.05)

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=BWB.qty,
            tag=f"BWB-{expiration}",
        )

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "strike_high": legs_info["strike_high"],
            "strike_mid": legs_info["strike_mid"],
            "strike_low": legs_info["strike_low"],
            "con_high": legs_info["con_high"],
            "con_mid": legs_info["con_mid"],
            "con_low": legs_info["con_low"],
            "net_credit": legs_info["net_credit"],
            "max_profit": legs_info["max_profit"],
            "iv": legs_info["iv"],
            "dte": legs_info["dte"],
            "entry_underlying": legs_info["underlying_price"],
            "entry_time": datetime.now().isoformat(),
            "qty": BWB.qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"BWB entered: exp={expiration} "
            f"{legs_info['strike_high']}P / {legs_info['strike_mid']}Px2 / {legs_info['strike_low']}P "
            f"credit=${legs_info['net_credit']*100:.0f}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days

        # Entry-day guard: never force-close on the day we entered
        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        # DTE force-close (not on entry day)
        if today != entry_date and dte <= BWB.max_dte_hold:
            return True, f"max_dte_hold ({dte} DTE)"

        # Price below broken wing = at or near max loss
        if current_price <= position["strike_low"]:
            return True, f"price_below_wing ({current_price:.1f} <= {position['strike_low']})"

        # Price below short strikes = high risk zone
        if current_price <= position["strike_mid"]:
            return True, f"price_below_short ({current_price:.1f} <= {position['strike_mid']})"

        # Theoretical P&L via Black-Scholes on all 3 legs
        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)

        p_high = black_scholes(current_price, position["strike_high"], T, iv, right="P")["price"]
        p_mid = black_scholes(current_price, position["strike_mid"], T, iv, right="P")["price"]
        p_low = black_scholes(current_price, position["strike_low"], T, iv, right="P")["price"]

        # Current value of the BWB (cost to close)
        current_value = p_high + p_low - 2 * p_mid
        # P&L = credit received - cost to close (positive = profit)
        pnl = position["net_credit"] - current_value

        log.info(f"BWB monitor: pnl=${pnl*100:.0f} price={current_price:.1f} dte={dte}")

        # Profit target: 50% of max profit
        target = position.get("max_profit", position["net_credit"]) * BWB.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f} >= ${target*100:.0f})"

        # Stop loss: 2x credit received
        stop = position["net_credit"] * BWB.stop_loss_pct
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f} <= -${stop*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse the entry: sell high, buy 2x mid, sell low
        legs = [
            (position["con_high"], 1, "SELL"),
            (position["con_mid"],  2, "BUY"),
            (position["con_low"],  1, "SELL"),
        ]

        try:
            T = dte_to_years(max(position.get("dte", 5), 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()
            p_h = black_scholes(price, position["strike_high"], T, iv, right="P")["price"]
            p_m = black_scholes(price, position["strike_mid"], T, iv, right="P")["price"]
            p_l = black_scholes(price, position["strike_low"], T, iv, right="P")["price"]
            close_debit = p_h + p_l - 2 * p_m
            limit_price = close_debit + 0.10
        except Exception:
            limit_price = 0.10

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=position["qty"],
            tag=f"BWB-exit-{position['expiration']}",
        )
        log.info(f"BWB exit order placed for {position['expiration']}")
        return trade is not None
```

- [ ] **Step 2: Verify imports work**

Run: `cd /home/oghenetejiri/apps/options-agent && python -c "from strategies.bwb import BWBStrategy; print('BWBStrategy loaded OK')"`

Expected: `BWBStrategy loaded OK`

- [ ] **Step 3: Commit**

```bash
git add strategies/bwb.py
git commit -m "fix(bwb): rewrite as real 3-leg BWB with delta-based strike selection

Replaces the mislabeled put vertical with a real Broken Wing Butterfly:
- Long 1x upper put / Short 2x middle puts / Long 1x lower put
- Hybrid delta-based strike selection adapts to IV regime
- Entry-day guard prevents same-day DTE exit (Bug #3)
- Position dict now uses strike_high/strike_mid/strike_low keys"
```

---

## Chunk 2: Notifier Fix (Bug #2)

### Task 3: Fix notifier to use correct BWB position keys

**Files:**
- Modify: `notifier.py:35-68`

- [ ] **Step 1: Update trade_entered() BWB branch**

In `notifier.py`, replace lines 39-48 (the `if strat == "BWB":` block):

```python
        if strat == "BWB":
            strike_h = position.get("strike_high", "?")
            strike_m = position.get("strike_mid", "?")
            strike_l = position.get("strike_low", "?")
            max_prof = position.get("max_profit", 0)
            msg = (
                f"\U0001f7e2 <b>BWB Entered</b>\n"
                f"Exp: {exp}\n"
                f"Long: {strike_h}P | Short: {strike_m}Px2 | Wing: {strike_l}P\n"
                f"Net Credit: ${credit*100:.0f}\n"
                f"Max Profit: ${max_prof*100:.0f}"
            )
```

- [ ] **Step 2: Update trade_exited() to show BWB strikes**

Replace the `trade_exited` method (lines 59-68):

```python
    def trade_exited(self, position: dict, reason: str, pnl: float):
        strat = position.get("strategy", "?")
        emoji = "\u2705" if pnl > 0 else "\U0001f534"
        strikes = ""
        if strat == "BWB":
            strikes = (
                f"Strikes: {position.get('strike_high', '?')}/"
                f"{position.get('strike_mid', '?')}x2/"
                f"{position.get('strike_low', '?')}\n"
            )
        elif strat == "CONDOR":
            strikes = (
                f"Put: {position.get('long_put_strike', '?')}/{position.get('short_put_strike', '?')} "
                f"Call: {position.get('short_call_strike', '?')}/{position.get('long_call_strike', '?')}\n"
            )
        msg = (
            f"{emoji} <b>{strat} Closed</b>\n"
            f"{strikes}"
            f"Reason: {reason}\n"
            f"P&L: ${pnl:+.2f}\n"
            f"Exp: {position.get('expiration', '')}"
        )
        self.send(msg)
```

- [ ] **Step 3: Verify notifier imports**

Run: `cd /home/oghenetejiri/apps/options-agent && python -c "from notifier import Notifier; print('Notifier loaded OK')"`

Expected: `Notifier loaded OK`

- [ ] **Step 4: Commit**

```bash
git add notifier.py
git commit -m "fix(notifier): use correct BWB strike keys, add strikes to exit notification"
```

---

## Chunk 3: Broker Market Data Fix (Bug #4)

### Task 4: Set delayed market data once at connect, remove toggling

**Files:**
- Modify: `broker.py:26-44,59-94,171-200`

- [ ] **Step 1: Add reqMarketDataType(3) to connect()**

In `broker.py`, after line 37 (`self._connected = True`), add:

```python
                # Use delayed data globally — no live subscription needed.
                # Change to reqMarketDataType(1) if live subscriptions are added.
                self.ib.reqMarketDataType(3)
```

- [ ] **Step 2: Remove toggling from get_underlying_price()**

In `broker.py:get_underlying_price()`, remove these two lines:
- Line 64: `self.ib.reqMarketDataType(3)  # 3 = DELAYED`
- Line 90: `self.ib.reqMarketDataType(1)  # switch back to live for options`

- [ ] **Step 3: Remove toggling from get_option_quote()**

In `broker.py:get_option_quote()`, remove this line:
- Line 176: `self.ib.reqMarketDataType(3)  # 3 = DELAYED`

- [ ] **Step 4: Verify broker imports**

Run: `cd /home/oghenetejiri/apps/options-agent && python -c "from broker import IBKRBroker; print('IBKRBroker loaded OK')"`

Expected: `IBKRBroker loaded OK`

- [ ] **Step 5: Update ensure_connected() with market hours guard**

In `broker.py`, also replace the `ensure_connected` method (lines 46-50). This must be in the same commit as the market data fix because `ensure_connected()` will return `False` outside market hours, and the agent.py main loop (Task 7) needs the corresponding market-hours guards.

```python
    def ensure_connected(self) -> bool:
        """Reconnect if disconnected — but only during market hours."""
        if self.ib.isConnected():
            return True
        # Don't reconnect outside market hours (avoids post-close thrashing)
        now = datetime.now()
        if now.weekday() >= 5:  # weekend
            log.info("Weekend — skipping reconnect")
            return False
        time_str = now.strftime("%H:%M")
        if not ("09:20" <= time_str <= "16:15"):
            log.info(f"Outside market hours ({time_str}) — skipping reconnect")
            return False
        log.warning("IBKR disconnected — reconnecting...")
        self._connected = False
        try:
            self.connect()
            return True
        except ConnectionError:
            log.error("Reconnect failed")
            return False
```

- [ ] **Step 6: Commit**

**IMPORTANT:** Task 6 (agent.py main loop rewrite) MUST be applied immediately after this commit. Between this commit and Task 6, `ensure_connected()` returns `False` outside market hours but the agent loop doesn't yet have market-hours guards. Apply both in the same deployment window.

```bash
git add broker.py
git commit -m "fix(broker): set delayed data once at connect, add market-hours guard to ensure_connected"
```

---

### Task 5: Update state_writer.write_heartbeat() to accept mode parameter

**Files:**
- Modify: `state_writer.py:158-160`

- [ ] **Step 1: Add mode parameter to write_heartbeat()**

Replace the `write_heartbeat` function:

```python
def write_heartbeat(mode: str = "trading") -> None:
    """Write a heartbeat timestamp + mode. Called from the main loop to signal liveness."""
    _atomic_write(HEARTBEAT_FILE, {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
    })
```

- [ ] **Step 2: Commit**

```bash
git add state_writer.py
git commit -m "fix(state_writer): add mode param to write_heartbeat (trading/sleeping/disconnected)"
```

---

### Task 6: Add overnight disconnect/reconnect scheduling to agent.py

**Files:**
- Modify: `agent.py` (main loop rewrite)

- [ ] **Step 1: Add TZ assertion and helper methods**

At the top of `agent.py`, after the logging setup (after line 35), add:

```python
# Verify timezone is ET — all market-hours logic depends on this
_tz_check = datetime.now().astimezone().tzname()
if _tz_check not in ("EST", "EDT"):
    log.warning(f"System timezone is {_tz_check}, not ET — market hours logic may be wrong. Set TZ=America/New_York")
```

- [ ] **Step 2: Add _is_trading_hours() and _next_trading_morning() to OptionsAgent**

Add these methods to the OptionsAgent class (after `is_market_closing_soon`):

```python
    def _is_trading_hours(self) -> bool:
        """True if within the agent's active window (09:20 - 16:15 ET, weekdays)."""
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        time_str = now.strftime("%H:%M")
        return "09:20" <= time_str <= "16:15"

    def _is_eod(self) -> bool:
        """True if past 16:15 ET — time to disconnect."""
        now = datetime.now()
        return now.strftime("%H:%M") >= "16:15"

    def _sleep_until_morning(self):
        """Sleep in 60-second chunks until 09:20 ET next trading day."""
        log.info("Entering sleep mode until next trading day")
        while self.running:
            now = datetime.now()
            # Wake up at 09:20 on weekdays
            if now.weekday() < 5 and now.strftime("%H:%M") >= "09:20":
                if now.strftime("%H:%M") < "16:15":
                    log.info("Morning — waking up")
                    break
            try:
                state_writer.write_heartbeat(mode="sleeping")
            except Exception:
                pass
            time.sleep(60)

    def _end_of_day(self):
        """Clean shutdown at end of trading day."""
        log.info("End of day — shutting down for the night")

        # Force-close any remaining positions
        if self.open_positions:
            log.warning(f"EOD: force-closing {len(self.open_positions)} open positions")
            for pos in list(self.open_positions):
                strategy = self._get_strategy(pos["strategy"])
                if strategy:
                    try:
                        strategy.exit(pos)
                    except Exception as e:
                        log.error(f"EOD exit failed: {e}")
                pos["status"] = "closed"
                pos["exit_reason"] = "eod_force_close"
                pos["exit_time"] = datetime.now().isoformat()
                pnl = self._estimate_pnl(pos, "force_close")
                pos["realized_pnl"] = pnl
                self.risk.record_exit(pos, pnl)
                state_writer.append_closed_trade(pos, pnl, "eod_force_close")
                self.notifier.trade_exited(pos, "eod_force_close", pnl)
            self.open_positions.clear()
            state_writer.write_positions([])

        # Daily summary
        self.notifier.daily_summary(
            self.risk.daily_realized_pnl,
            self.risk.trades_count,
            self.risk.wins_today,
            self.risk.losses_today,
        )

        # Disconnect
        self.broker.disconnect()
        state_writer.write_heartbeat(mode="sleeping")
        log.info("Disconnected from IBKR — entering sleep mode")
```

- [ ] **Step 3: Rewrite the main loop in run()**

Replace the `while self.running:` loop (lines 264-344) with:

```python
        while self.running:
            try:
                now = datetime.now()

                # ── End of day: disconnect and sleep ──
                if self._is_eod():
                    self._end_of_day()
                    self._sleep_until_morning()
                    if not self.running:
                        break
                    # Morning: reconnect
                    try:
                        self.broker.connect()
                        log.info("Morning reconnect successful")
                    except Exception as e:
                        log.error(f"Morning reconnect failed: {e}")
                        self.notifier.error(f"Morning reconnect failed: {e}")
                        time.sleep(60)
                        continue
                    self.daily_housekeeping()
                    continue

                # ── Pre-market: wait for open ──
                if not self._is_trading_hours():
                    try:
                        state_writer.write_heartbeat(mode="sleeping")
                    except Exception:
                        pass
                    time.sleep(60)
                    continue

                # ── Daily housekeeping (once per day, first tick after 09:20) ──
                today_str = date.today().isoformat()
                if self.last_heartbeat_date != today_str:
                    self.daily_housekeeping()

                # ── Trading hours: scan + monitor ──
                if self.is_market_open():
                    # Entry scan every SCAN_INTERVAL_SECS
                    if (
                        self.last_scan_time is None
                        or (now - self.last_scan_time).seconds >= config.SCAN_INTERVAL_SECS
                    ):
                        self.scan_for_entries()
                        self.last_scan_time = now

                    # Monitor open positions every MONITOR_INTERVAL_SECS
                    if (
                        self.last_monitor_time is None
                        or (now - self.last_monitor_time).seconds >= config.MONITOR_INTERVAL_SECS
                    ):
                        self.monitor_positions()
                        self.last_monitor_time = now

                # Write portfolio data every 5 minutes
                if (
                    self.last_portfolio_write is None
                    or (now - self.last_portfolio_write).seconds >= 300
                ):
                    try:
                        spx_price = None
                        if self.broker.ib.isConnected():
                            try:
                                spx_price = self.broker.get_underlying_price()
                            except Exception:
                                pass
                        state_writer.write_portfolio(
                            spx_price=spx_price,
                            daily_pnl=self.risk.daily_realized_pnl,
                            realized=self.risk.daily_realized_pnl,
                        )
                        state_writer.write_config(
                            strategy=config.ACTIVE_STRATEGY,
                            underlying=config.UNDERLYING,
                            dry_run=config.DRY_RUN,
                            max_positions=config.MAX_CONCURRENT_POSITIONS,
                            max_daily_loss=config.MAX_DAILY_LOSS_USD,
                            max_position_risk=config.MAX_POSITION_RISK_USD,
                            scan_interval=config.SCAN_INTERVAL_SECS,
                            start_time=self.start_time,
                        )
                        self.last_portfolio_write = now
                    except Exception as e:
                        log.warning(f"Portfolio state write failed: {e}")

                # Write heartbeat every main loop tick
                try:
                    state_writer.write_heartbeat(mode="trading")
                except Exception:
                    pass

                time.sleep(10)  # main loop tick

            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error(f"Main loop error: {e}", exc_info=True)
                self.notifier.error(f"Main loop error: {e}")
                time.sleep(30)
```

- [ ] **Step 4: Verify agent loads**

Run: `cd /home/oghenetejiri/apps/options-agent && python -c "from agent import OptionsAgent; print('OptionsAgent loaded OK')"`

Expected: `OptionsAgent loaded OK` (or a TZ warning followed by OK)

- [ ] **Step 5: Commit**

```bash
git add agent.py
git commit -m "fix(agent): add overnight disconnect/reconnect, fix daily_housekeeping timing

- Disconnect at 16:15 ET, sleep until 09:20 ET next trading day
- Skip weekends in sleep loop
- Market-hours guard prevents reconnect thrashing
- daily_housekeeping uses date flag instead of exact time match
- TZ assertion at startup warns if not running in ET"
```

---

### Task 7: Update dashboard to show SLEEPING status

**Files:**
- Modify: `dashboard/app.py:593-613,730-748`

- [ ] **Step 1: Update heartbeat liveness check to handle sleeping mode**

In `dashboard/app.py`, replace the agent liveness section (lines 593-613):

```python
agent_alive   = False
agent_sleeping = False
last_alive_ts = None

hb_ts = heartbeat.get("timestamp")
hb_mode = heartbeat.get("mode", "trading")
if hb_ts:
    try:
        hb_dt = datetime.fromisoformat(hb_ts)
        age   = (datetime.now() - hb_dt).total_seconds()
        if age < 120:
            agent_alive = True
            agent_sleeping = (hb_mode == "sleeping")
        last_alive_ts = hb_dt
    except Exception:
        pass

if not last_alive_ts and log_lines:
    try:
        last_alive_ts = datetime.strptime(log_lines[-1][:19], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_alive_ts).total_seconds() < 300:
            agent_alive = True
    except Exception:
        pass
```

- [ ] **Step 2: Update agent status card to show SLEEPING**

In `dashboard/app.py`, replace the status determination block (lines 732-739):

```python
if trading_halted:
    s_cls, s_val = "red", "HALTED"
elif not agent_alive:
    s_cls, s_val = "red", "OFFLINE"
elif agent_sleeping:
    s_cls, s_val = "blue", "SLEEPING"
elif dry_run:
    s_cls, s_val = "yellow", "DRY RUN"
else:
    s_cls, s_val = "green", "ONLINE"
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "fix(dashboard): show SLEEPING status when agent is in overnight sleep mode"
```

---

## Chunk 5: Verification

### Task 8: End-to-end import verification and Docker build

- [ ] **Step 1: Verify all modules import cleanly**

Run: `cd /home/oghenetejiri/apps/options-agent && python -c "
from config import BWB, CONDOR
from broker import IBKRBroker
from strategies.bwb import BWBStrategy
from strategies.condor import CondorStrategy
from notifier import Notifier
from risk import RiskManager
from agent import OptionsAgent
import state_writer
print('All imports OK')
print(f'BWB config: short_delta={BWB.short_delta_target} min_wing={BWB.min_wing_width} min_credit={BWB.min_net_credit} max_dte_hold={BWB.max_dte_hold}')
"`

Expected: All imports OK + correct config values

- [ ] **Step 2: Docker build test**

Run: `cd /home/oghenetejiri/apps/options-agent && docker compose build --no-cache`

Expected: Both `options-agent` and `options-dashboard` images build successfully

- [ ] **Step 3: Commit plan doc**

```bash
git add docs/superpowers/plans/2026-03-27-week1-bugfix-plan.md
git commit -m "docs: add Week 1 bugfix implementation plan"
```
