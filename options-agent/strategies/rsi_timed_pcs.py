"""
strategies/rsi_timed_pcs.py — RSI-Timed Put Credit Spread
Enters when RSI(14) < 30 (oversold). Sells 30-delta put spread at 45 DTE.
50% profit, 2x stop, 14 DTE time stop.
Backtest: STRONG — Sharpe 0.51, DD 17.3%, 75% WR on test period (2020-2024).
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

log = logging.getLogger("strategy.rsi_timed_pcs")


class RSITimedPCSStrategy:
    name = "RSI_TIMED_PCS"

    # Entry parameters
    DTE_TARGET = 45
    DTE_MIN = 30
    DELTA_TARGET = 0.30
    SPREAD_WIDTH = 10       # SPX points
    RSI_PERIOD = 14
    RSI_THRESHOLD = 30.0

    # Exit parameters
    PROFIT_TARGET_PCT = 0.50
    STOP_LOSS_PCT = 2.00
    TIME_STOP_DTE = 14

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    @staticmethod
    def _calc_rsi(prices: list[float], period: int) -> Optional[float]:
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(-period, 0)]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _get_price_history(self) -> list[float]:
        try:
            contract = self.broker._get_underlying_contract()
            bars = self.broker.ib.reqHistoricalData(
                contract, endDateTime="", durationStr="30 D",
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=True,
            )
            if not bars:
                return []
            return [b.close for b in bars if b.close > 0]
        except Exception as e:
            log.warning(f"Price history fetch failed: {e}")
            return []

    def should_enter(self) -> bool:
        """Enter when RSI(14) < 30."""
        prices = self._get_price_history()
        if len(prices) < self.RSI_PERIOD + 1:
            log.info("RSI_TIMED_PCS: insufficient price history")
            return False

        rsi = self._calc_rsi(prices, self.RSI_PERIOD)
        if rsi is None:
            return False

        log.info(f"RSI_TIMED_PCS: RSI(14)={rsi:.1f} (threshold={self.RSI_THRESHOLD})")

        if rsi >= self.RSI_THRESHOLD:
            log.info(f"RSI_TIMED_PCS skip: RSI {rsi:.1f} >= {self.RSI_THRESHOLD}")
            return False

        # Trend day check
        if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'current_trend_score'):
            trend = self.agent.current_trend_score
            if trend and trend.get('is_trend_day'):
                log.info(f"RSI_TIMED_PCS skip: Trend day detected (score={trend['score']})")
                return False

        return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(dte_min=self.DTE_MIN, dte_max=self.DTE_TARGET + 5)
        if not exps:
            return None
        today = date.today()
        best = min(exps, key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - self.DTE_TARGET))
        return best

    def enter(self) -> Optional[dict]:
        if not self.should_enter():
            return None

        expiration = self.find_expiration()
        if not expiration:
            return None

        try:
            price = self.broker.get_underlying_price()
        except Exception:
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
            return None

        qty = calculate_position_size(config.ACCOUNT_CAPITAL, config.MAX_RISK_PER_TRADE_PCT,
                                      self.SPREAD_WIDTH, net_credit)

        contracts = []
        for strike in [short_strike, long_strike]:
            opt = Option(config.UNDERLYING, expiration, strike, "P", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                if opt.conId == 0:
                    return None
                contracts.append(opt)
            except Exception:
                return None

        legs = [(contracts[0].conId, 1, "SELL"), (contracts[1].conId, 1, "BUY")]
        from broker import _snap_to_tick
        limit_price = _snap_to_tick(-(net_credit - 0.05))

        trade = self.broker.place_combo_order(legs=legs, limit_price=limit_price, qty=qty,
                                              tag=f"RSI_TIMED_PCS-{expiration}")

        position = {
            "strategy": self.name, "expiration": expiration,
            "short_strike": short_strike, "long_strike": long_strike,
            "con_short": contracts[0].conId, "con_long": contracts[1].conId,
            "net_credit": net_credit, "max_loss": max_loss, "iv": iv,
            "entry_underlying": price, "entry_time": datetime.now().isoformat(),
            "qty": qty, "status": "open", "trade": trade,
        }
        log.info(f"RSI_TIMED_PCS entered: exp={expiration} sell {short_strike}P / buy {long_strike}P credit=${net_credit*100:.0f}")
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days
        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        if today != entry_date and dte <= self.TIME_STOP_DTE:
            return True, f"time_stop ({dte} DTE)"

        if current_price <= position["short_strike"]:
            return True, f"price_below_short ({current_price:.1f} <= {position['short_strike']})"

        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)
        p_short = black_scholes(current_price, position["short_strike"], T, iv, right="P")["price"]
        p_long = black_scholes(current_price, position["long_strike"], T, iv, right="P")["price"]
        pnl = position["net_credit"] - (p_short - p_long)

        if pnl >= position["net_credit"] * self.PROFIT_TARGET_PCT:
            return True, f"profit_target (${pnl*100:.0f})"
        if pnl <= -(position["net_credit"] * self.STOP_LOSS_PCT):
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
                                              qty=position["qty"], tag=f"RSI_TIMED_PCS-exit-{position['expiration']}")
        return trade is not None
