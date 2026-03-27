"""
agent.py — Main Trading Agent Loop
Orchestrates: market hours check → entry scan → position monitor → exit → risk management
Runs indefinitely. Designed to be left alone.
"""

import logging
import os
import sys
import time
import signal
from datetime import datetime, date
from typing import List, Optional

import config
import state_writer
from broker import IBKRBroker
from risk import RiskManager
from notifier import Notifier
from strategies.bwb import BWBStrategy
from strategies.condor import CondorStrategy

# ─── Logging setup ──────────────────────────────────────────────────────────
os.makedirs(config.LOG_DIR, exist_ok=True)
os.makedirs(config.DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.LOG_DIR, "agent.log")),
    ],
)
log = logging.getLogger("agent")

# Verify timezone is ET — all market-hours logic depends on this
_tz_check = datetime.now().astimezone().tzname()
if _tz_check not in ("EST", "EDT"):
    log.warning(f"System timezone is {_tz_check}, not ET — market hours logic may be wrong. Set TZ=America/New_York")


class OptionsAgent:
    def __init__(self):
        self.broker = IBKRBroker()
        self.notifier = Notifier()
        self.risk = RiskManager(notifier=self.notifier)
        self.open_positions: List[dict] = []
        self.running = True
        self.last_scan_time = None
        self.last_monitor_time = None
        self.last_heartbeat_date = None
        self.start_time = datetime.now()
        self.last_portfolio_write = None

        # Strategy instances
        self.strategies = []
        if config.ACTIVE_STRATEGY in ("BWB", "BOTH"):
            self.strategies.append(BWBStrategy(self.broker))
        if config.ACTIVE_STRATEGY in ("CONDOR", "BOTH"):
            self.strategies.append(CondorStrategy(self.broker))

        # Graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        log.info("Shutdown signal received — exiting cleanly")
        self.running = False

    # ─── Market Hours ────────────────────────────────────────────────────────

    def is_market_open(self) -> bool:
        now = datetime.now()
        # Skip weekends
        if now.weekday() >= 5:
            return False
        time_str = now.strftime("%H:%M")
        return config.MARKET_OPEN_TIME <= time_str <= config.MARKET_CLOSE_TIME

    def is_market_closing_soon(self) -> bool:
        """True if within 30 minutes of close."""
        now = datetime.now().strftime("%H:%M")
        return now >= "15:30"

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

    # ─── Entry Logic ─────────────────────────────────────────────────────────

    def scan_for_entries(self):
        """Try to enter new positions if conditions are met."""
        can_enter, reason = self.risk.can_enter(len(self.open_positions))
        if not can_enter:
            log.info(f"No entry: {reason}")
            return

        if self.is_market_closing_soon():
            log.info("Market closing soon — no new entries")
            return

        for strategy in self.strategies:
            # Don't double-enter same strategy (max 1 concurrent per strategy)
            existing = [p for p in self.open_positions if p["strategy"] == strategy.name]
            if len(existing) >= 1:
                log.info(f"{strategy.name} already has {len(existing)} open position(s) — skipping")
                continue

            log.info(f"Scanning for {strategy.name} entry...")
            try:
                self.broker.ensure_connected()
                position = strategy.enter()
                if position:
                    self.open_positions.append(position)
                    state_writer.write_positions(self.open_positions)
                    self.notifier.trade_entered(position)
                    log.info(f"{strategy.name} position opened: {position['expiration']}")
            except Exception as e:
                log.error(f"Entry error for {strategy.name}: {e}", exc_info=True)
                self.notifier.error(f"{strategy.name} entry failed: {e}")

    # ─── Monitor + Exit ──────────────────────────────────────────────────────

    def monitor_positions(self):
        """Check all open positions for exit conditions."""
        if not self.open_positions:
            return

        try:
            self.broker.ensure_connected()
            current_price = self.broker.get_underlying_price()
        except Exception as e:
            log.error(f"Could not get underlying price: {e}")
            return

        to_close = []
        for position in self.open_positions:
            if position.get("status") != "open":
                continue

            strategy = self._get_strategy(position["strategy"])
            if not strategy:
                continue

            try:
                should_exit, reason = strategy.should_exit(position, current_price)
                if should_exit:
                    log.info(f"Closing {position['strategy']} — reason: {reason}")
                    to_close.append((position, strategy, reason))
            except Exception as e:
                log.error(f"Monitor error for {position['strategy']}: {e}", exc_info=True)

        for position, strategy, reason in to_close:
            try:
                success = strategy.exit(position)
                if success or config.DRY_RUN:
                    position["status"] = "closed"
                    position["exit_reason"] = reason
                    position["exit_time"] = datetime.now().isoformat()
                    # Estimate P&L — must happen after exit_reason is set
                    pnl = self._estimate_pnl(position, reason)
                    position["realized_pnl"] = pnl
                    self.open_positions.remove(position)
                    self.risk.record_exit(position, pnl)
                    state_writer.append_closed_trade(position, pnl, reason)
                    state_writer.write_positions(self.open_positions)
                    self.notifier.trade_exited(position, reason, pnl)
                    log.info(f"Position closed: reason={reason} pnl=${pnl:.2f}")
            except Exception as e:
                log.error(f"Exit error: {e}", exc_info=True)
                self.notifier.error(f"Exit failed for {position['strategy']}: {e}")

        # Always sync positions after monitor cycle
        try:
            state_writer.write_positions(self.open_positions)
        except Exception as e:
            log.warning(f"state_writer positions sync failed: {e}")

    def _estimate_pnl(self, position: dict, reason: str = "") -> float:
        """
        Estimate P&L based on exit reason.
        In DRY_RUN these are approximations; in live mode actual fills are in the trade object.
        """
        try:
            net_credit = float(position.get("net_credit") or 0)
            max_profit = float(position.get("max_profit") or net_credit)
            multiplier = 100  # SPX options = $100/point

            if "profit_target" in reason:
                # Closed at 50% of max profit
                return round(max_profit * 0.50 * multiplier * position.get("qty", 1), 2)
            elif "stop_loss" in reason:
                # Closed at 2x credit loss
                return round(-(net_credit * 2.0) * multiplier * position.get("qty", 1), 2)
            elif "force_close" in reason or "market_closed" in reason:
                # Closed at end of day — assume small profit (80% of credit)
                return round(net_credit * 0.80 * multiplier * position.get("qty", 1), 2)
            elif "price_below" in reason or "price_above" in reason:
                # Breached a strike — take moderate loss
                return round(-(net_credit * 1.5) * multiplier * position.get("qty", 1), 2)
            elif "max_dte" in reason:
                # Time exit — roughly 60% of credit
                return round(net_credit * 0.60 * multiplier * position.get("qty", 1), 2)
            else:
                return 0.0
        except Exception:
            return 0.0

    def _get_strategy(self, name: str):
        for s in self.strategies:
            if s.name == name:
                return s
        return None

    # ─── Daily Housekeeping ───────────────────────────────────────────────────

    def daily_housekeeping(self):
        today = date.today().isoformat()
        if self.last_heartbeat_date == today:
            return
        self.last_heartbeat_date = today
        self.risk.daily_reset()
        self.notifier.heartbeat(
            f"Strategies: {config.ACTIVE_STRATEGY} | "
            f"DRY_RUN: {config.DRY_RUN} | "
            f"Max positions: {config.MAX_CONCURRENT_POSITIONS}"
        )
        log.info("Daily housekeeping complete")

    # ─── Main Loop ───────────────────────────────────────────────────────────

    def run(self):
        log.info("=" * 60)
        log.info(f"Options Agent starting")
        log.info(f"Strategy: {config.ACTIVE_STRATEGY} | DRY_RUN: {config.DRY_RUN}")
        log.info(f"Underlying: {config.UNDERLYING} | Max positions: {config.MAX_CONCURRENT_POSITIONS}")
        log.info("=" * 60)

        # Write initial config to dashboard data dir
        try:
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
            state_writer.write_positions([])
            state_writer.write_portfolio(daily_pnl=0.0)
            state_writer.write_heartbeat()
        except Exception as e:
            log.warning(f"Initial state_writer call failed: {e}")

        # If outside trading hours, skip initial connect and go straight to sleep
        if not self._is_trading_hours():
            log.info("Starting outside trading hours — entering sleep mode")
            state_writer.write_heartbeat(mode="sleeping")
            self._sleep_until_morning()
            if not self.running:
                return

        # Connect to IBKR
        try:
            self.broker.connect()
        except Exception as e:
            log.error(f"Fatal: could not connect to IBKR: {e}")
            self.notifier.error(f"Agent failed to start: {e}")
            sys.exit(1)

        self.notifier.send(
            f"🚀 <b>Options Agent Started</b>\n"
            f"Strategy: {config.ACTIVE_STRATEGY}\n"
            f"Underlying: {config.UNDERLYING}\n"
            f"DRY RUN: {config.DRY_RUN}"
        )

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

        # Shutdown
        log.info("Agent shutting down...")
        if self.open_positions:
            log.warning(f"{len(self.open_positions)} positions still open at shutdown")
            self.notifier.send(f"⚠️ Agent shutting down with {len(self.open_positions)} open positions")

        # Send daily summary
        self.notifier.daily_summary(
            self.risk.daily_realized_pnl,
            self.risk.trades_count,
            self.risk.wins_today,
            self.risk.losses_today,
        )
        self.broker.disconnect()
        log.info("Agent stopped.")


if __name__ == "__main__":
    agent = OptionsAgent()
    agent.run()
