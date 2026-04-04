"""
strategies/vrp_timed_pcs.py — VRP-Timed Put Credit Spread
Enters when Volatility Risk Premium (IV - HV20) > 4 vol points.
Sells 16-delta put spread at 45 DTE. 50% profit, 2x stop, 21 DTE time stop.
Backtest: STRONG — Sharpe 1.19, DD 4.1%, 87% WR on test period (2020-2024).
"""

import math
import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.vrp_timed_pcs")


class VRPTimedPCSStrategy:
    name = "VRP_TIMED_PCS"

    # Entry parameters (from backtest)
    DTE_TARGET = 45
    DTE_MIN = 30
    DELTA_TARGET = 0.16
    SPREAD_WIDTH = 10       # SPX points
    VRP_THRESHOLD = 4.0     # vol points (IV - HV20)
    HV_WINDOW = 20

    # Exit parameters
    PROFIT_TARGET_PCT = 0.50
    STOP_LOSS_PCT = 2.00
    TIME_STOP_DTE = 21

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    def _get_hv20(self) -> Optional[float]:
        """Calculate 20-day historical volatility from IBKR daily bars."""
        try:
            contract = self.broker._get_underlying_contract()
            bars = self.broker.ib.reqHistoricalData(
                contract, endDateTime="", durationStr="40 D",
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=True,
            )
            if not bars or len(bars) < self.HV_WINDOW + 1:
                return None
            closes = [b.close for b in bars if b.close > 0]
            if len(closes) < self.HV_WINDOW + 1:
                return None
            log_rets = [math.log(closes[i] / closes[i-1])
                        for i in range(-self.HV_WINDOW, 0)]
            import statistics
            hv = statistics.stdev(log_rets) * math.sqrt(252) * 100
            return hv
        except Exception as e:
            log.warning(f"HV20 calculation failed: {e}")
            return None

    def _get_iv_proxy(self) -> Optional[float]:
        """Get current IV from IBKR as percentage (e.g., 23.0 for 23%)."""
        try:
            iv = get_broker_iv(self.broker)
            return iv * 100  # convert to percentage
        except Exception:
            return None

    def should_enter(self) -> bool:
        """Check VRP filter: IV - HV20 > 4 vol points."""
        hv20 = self._get_hv20()
        iv = self._get_iv_proxy()
        if hv20 is None or iv is None:
            log.info(f"VRP_TIMED_PCS: cannot compute VRP (hv20={hv20}, iv={iv})")
            return False

        vrp = iv - hv20
        log.info(f"VRP_TIMED_PCS: IV={iv:.1f}% HV20={hv20:.1f}% VRP={vrp:.1f} (threshold={self.VRP_THRESHOLD})")

        if vrp < self.VRP_THRESHOLD:
            log.info(f"VRP_TIMED_PCS skip: VRP {vrp:.1f} < {self.VRP_THRESHOLD} threshold")
            return False

        # Trend day check
        if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'current_trend_score'):
            trend = self.agent.current_trend_score
            if trend and trend.get('is_trend_day'):
                log.info(f"VRP_TIMED_PCS skip: Trend day detected (score={trend['score']})")
                return False

        return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(dte_min=self.DTE_MIN, dte_max=self.DTE_TARGET + 5)
        if not exps:
            return None
        today = date.today()
        best = min(exps, key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - self.DTE_TARGET))
        dte = (datetime.strptime(best, "%Y%m%d").date() - today).days
        log.info(f"VRP_TIMED_PCS expiration: {best} ({dte} DTE)")
        return best

    def enter(self) -> Optional[dict]:
        if not self.should_enter():
            return None

        expiration = self.find_expiration()
        if not expiration:
            return None

        try:
            price = self.broker.get_underlying_price()
        except Exception as e:
            log.warning(f"Could not get price: {e}")
            return None

        exp_date = datetime.strptime(expiration, "%Y%m%d").date()
        dte = (exp_date - date.today()).days
        T = dte_to_years(dte)
        iv = get_broker_iv(self.broker)

        short_strike = get_strike_from_delta(self.broker, price, T, iv, -self.DELTA_TARGET, "P")
        short_strike = round(short_strike / 5) * 5
        long_strike = short_strike - self.SPREAD_WIDTH

        p_short = black_scholes(price, short_strike, T, iv, right="P")["price"]
        p_long = black_scholes(price, long_strike, T, iv, right="P")["price"]
        net_credit = p_short - p_long
        max_loss = self.SPREAD_WIDTH - net_credit

        if net_credit <= 0.05 or max_loss <= 0:
            log.warning(f"VRP_TIMED_PCS: invalid spread (credit={net_credit:.4f}, max_loss={max_loss:.4f})")
            return None

        qty = calculate_position_size(
            config.ACCOUNT_CAPITAL, config.MAX_RISK_PER_TRADE_PCT,
            self.SPREAD_WIDTH, net_credit,
        )

        # Qualify contracts
        contracts = []
        for strike in [short_strike, long_strike]:
            opt = Option(config.UNDERLYING, expiration, strike, "P", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                if opt.conId == 0:
                    return None
                contracts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}P: {e}")
                return None

        legs = [(contracts[0].conId, 1, "SELL"), (contracts[1].conId, 1, "BUY")]
        from broker import _snap_to_tick
        limit_price = _snap_to_tick(-(net_credit - 0.05))

        trade = self.broker.place_combo_order(legs=legs, limit_price=limit_price, qty=qty,
                                              tag=f"VRP_TIMED_PCS-{expiration}")

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "short_strike": short_strike,
            "long_strike": long_strike,
            "con_short": contracts[0].conId,
            "con_long": contracts[1].conId,
            "net_credit": net_credit,
            "max_loss": max_loss,
            "iv": iv,
            "entry_underlying": price,
            "entry_time": datetime.now().isoformat(),
            "qty": qty,
            "status": "open",
            "trade": trade,
        }
        log.info(f"VRP_TIMED_PCS entered: exp={expiration} sell {short_strike}P / buy {long_strike}P credit=${net_credit*100:.0f} qty={qty}")
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days
        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        # Time stop at 21 DTE (not on entry day)
        if today != entry_date and dte <= self.TIME_STOP_DTE:
            return True, f"time_stop ({dte} DTE)"

        if current_price <= position["short_strike"]:
            return True, f"price_below_short ({current_price:.1f} <= {position['short_strike']})"

        # Theoretical P&L
        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)
        p_short = black_scholes(current_price, position["short_strike"], T, iv, right="P")["price"]
        p_long = black_scholes(current_price, position["long_strike"], T, iv, right="P")["price"]
        current_cost = p_short - p_long
        pnl = position["net_credit"] - current_cost

        target = position["net_credit"] * self.PROFIT_TARGET_PCT
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f})"

        stop = position["net_credit"] * self.STOP_LOSS_PCT
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        legs = [(position["con_short"], 1, "BUY"), (position["con_long"], 1, "SELL")]
        try:
            exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
            dte = (exp_date - date.today()).days
            T = dte_to_years(max(dte, 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()
            p_short = black_scholes(price, position["short_strike"], T, iv, right="P")["price"]
            p_long = black_scholes(price, position["long_strike"], T, iv, right="P")["price"]
            from broker import _snap_to_tick
            limit_price = _snap_to_tick(p_short - p_long + 0.10)
        except Exception:
            limit_price = 0.10

        trade = self.broker.place_combo_order(legs=legs, limit_price=limit_price,
                                              qty=position["qty"], tag=f"VRP_TIMED_PCS-exit-{position['expiration']}")
        return trade is not None
