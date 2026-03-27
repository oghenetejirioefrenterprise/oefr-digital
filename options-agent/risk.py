"""
risk.py — Risk manager
Tracks daily P&L, enforces max loss limits, position sizing, and trading halts.
"""

import logging
import json
import os
from datetime import datetime, date
from typing import List

import config

log = logging.getLogger("risk")

STATE_FILE = os.path.join(config.DATA_DIR, "risk_state.json")


class RiskManager:
    def __init__(self, notifier=None):
        self.notifier = notifier
        self.trading_halted = False
        self.halt_reason = ""
        self.daily_realized_pnl = 0.0
        self.trades_today: List[dict] = []
        self.state_date = date.today().isoformat()
        self._load_state()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE) as f:
                    state = json.load(f)
                if state.get("date") == date.today().isoformat():
                    self.daily_realized_pnl = state.get("daily_pnl", 0.0)
                    self.trades_today = state.get("trades", [])
                    self.trading_halted = state.get("halted", False)
                    self.halt_reason = state.get("halt_reason", "")
                    log.info(f"Loaded risk state: pnl={self.daily_realized_pnl:.2f} halted={self.trading_halted}")
            except Exception as e:
                log.warning(f"Could not load risk state: {e}")

    def _save_state(self):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        state = {
            "date": date.today().isoformat(),
            "daily_pnl": self.daily_realized_pnl,
            "trades": self.trades_today,
            "halted": self.trading_halted,
            "halt_reason": self.halt_reason,
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def can_enter(self, open_positions: int) -> tuple[bool, str]:
        """Returns (can_enter, reason)."""
        if self.trading_halted:
            return False, f"trading_halted: {self.halt_reason}"
        if open_positions >= config.MAX_CONCURRENT_POSITIONS:
            return False, f"max_concurrent_positions ({open_positions}/{config.MAX_CONCURRENT_POSITIONS})"
        if self.daily_realized_pnl <= -config.MAX_DAILY_LOSS_USD:
            self._halt(f"daily_loss_limit breached (${self.daily_realized_pnl:.2f})")
            return False, self.halt_reason
        return True, "ok"

    def record_exit(self, position: dict, pnl: float):
        """Record a closed trade."""
        now = datetime.now().isoformat()
        record = {
            "strategy": position["strategy"],
            "expiration": position.get("expiration", ""),
            "pnl": pnl,
            "time": now,
            "win": pnl > 0,
        }
        self.trades_today.append(record)
        self.daily_realized_pnl += pnl
        log.info(f"Trade recorded: pnl={pnl:.2f} daily_total={self.daily_realized_pnl:.2f}")

        # Write full position to trade_history.json (for dashboard — includes strikes)
        self._append_trade_history(position, pnl, now)

        # Check daily loss limit after recording
        if self.daily_realized_pnl <= -config.MAX_DAILY_LOSS_USD:
            self._halt(f"daily_loss_limit breached after trade (${self.daily_realized_pnl:.2f})")

        self._save_state()

    def _append_trade_history(self, position: dict, pnl: float, exit_time: str):
        """Append full trade record (with strikes) to trade_history.json for the dashboard."""
        history_file = os.path.join(config.DATA_DIR, "trade_history.json")
        try:
            if os.path.exists(history_file):
                with open(history_file) as f:
                    history = json.load(f)
            else:
                history = []

            record = {
                "strategy":       position.get("strategy", ""),
                "expiration":     position.get("expiration", ""),
                "entry_time":     position.get("entry_time", ""),
                "exit_time":      exit_time,
                "realized_pnl":   pnl,
                "win":            pnl > 0,
                "exit_reason":    position.get("exit_reason", ""),
                # BWB strikes
                "strike_high":    position.get("strike_high"),
                "strike_mid":     position.get("strike_mid"),
                "strike_low":     position.get("strike_low"),
                # Condor strikes
                "long_put_strike":   position.get("long_put_strike"),
                "short_put_strike":  position.get("short_put_strike"),
                "short_call_strike": position.get("short_call_strike"),
                "long_call_strike":  position.get("long_call_strike"),
                "net_credit":     position.get("net_credit", 0),
                "qty":            position.get("qty", 1),
            }
            history.insert(0, record)
            # Keep last 500 trades
            history = history[:500]
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            log.warning(f"Could not write trade_history.json: {e}")

    def _halt(self, reason: str):
        self.trading_halted = True
        self.halt_reason = reason
        log.warning(f"TRADING HALTED: {reason}")
        if self.notifier:
            self.notifier.risk_breach(reason)
        self._save_state()

    def daily_reset(self):
        """Call at market open each day to reset daily counters."""
        today = date.today().isoformat()
        if self.state_date != today:
            log.info("New trading day — resetting risk state")
            self.daily_realized_pnl = 0.0
            self.trades_today = []
            self.trading_halted = False
            self.halt_reason = ""
            self.state_date = today
            self._save_state()

    @property
    def wins_today(self) -> int:
        return sum(1 for t in self.trades_today if t.get("win"))

    @property
    def losses_today(self) -> int:
        return sum(1 for t in self.trades_today if not t.get("win"))

    @property
    def trades_count(self) -> int:
        return len(self.trades_today)
