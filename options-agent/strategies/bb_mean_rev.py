"""
strategies/bb_mean_rev.py — Bollinger Band Mean Reversion PCS
Sells put credit spread when SPX touches lower Bollinger Band (oversold bounce).
Backtest: Sortino 1.03, DD 10.7%, 81% WR, correlation -0.09 with PCS+CS.
DTE 14. 25-delta. Profit 50%, stop 2x.
"""

import logging
import statistics
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from broker import IBKRBroker, _snap_to_tick
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.bb_mean_rev")


class BBMeanRevStrategy:
    name = "BB_MEAN_REV"

    DTE_TARGET = 14
    DTE_MIN = 10
    DELTA_TARGET = 0.25
    SPREAD_WIDTH = 10  # SPX points
    BB_PERIOD = 20
    PROFIT_TARGET_PCT = 0.50
    STOP_LOSS_PCT = 2.00
    MAX_DTE_HOLD = 1

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    def _get_bb_lower(self) -> Optional[float]:
        """Get lower Bollinger Band (20-period, 2 std dev)."""
        try:
            contract = self.broker._get_underlying_contract()
            bars = self.broker.ib.reqHistoricalData(
                contract, endDateTime="", durationStr="40 D",
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=True,
            )
            if not bars or len(bars) < self.BB_PERIOD:
                return None
            closes = [b.close for b in bars if b.close > 0]
            if len(closes) < self.BB_PERIOD:
                return None
            recent = closes[-self.BB_PERIOD:]
            mean = statistics.mean(recent)
            std = statistics.stdev(recent)
            return mean - 2 * std
        except Exception as e:
            log.warning(f"BB calculation failed: {e}")
            return None

    def should_enter(self) -> bool:
        """Enter when price is at or below lower Bollinger Band."""
        try:
            price = self.broker.get_underlying_price()
            bb_lower = self._get_bb_lower()
            if bb_lower is None:
                return False
            log.info(f"BB_MEAN_REV: price={price:.1f} BB_lower={bb_lower:.1f}")
            if price > bb_lower:
                log.info(f"BB_MEAN_REV skip: price {price:.1f} > BB lower {bb_lower:.1f}")
                return False
            log.info(f"BB_MEAN_REV SIGNAL: price {price:.1f} <= BB lower {bb_lower:.1f} — oversold")

            # Trend day check
            if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'current_trend_score'):
                trend = self.agent.current_trend_score
                if trend and trend.get('is_trend_day'):
                    log.info(f"BB_MEAN_REV skip: Trend day detected (score={trend['score']})")
                    return False

            return True
        except Exception as e:
            log.warning(f"BB_MEAN_REV entry check failed: {e}")
            return False

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(dte_min=self.DTE_MIN, dte_max=self.DTE_TARGET + 7)
        if not exps:
            return None
        today = date.today()
        return min(exps, key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - self.DTE_TARGET))

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
        limit_price = _snap_to_tick(-(net_credit - 0.05))
        trade = self.broker.place_combo_order(legs=legs, limit_price=limit_price, qty=qty,
                                              tag=f"BB_MEAN_REV-{expiration}")

        position = {
            "strategy": self.name, "expiration": expiration,
            "short_strike": short_strike, "long_strike": long_strike,
            "con_short": contracts[0].conId, "con_long": contracts[1].conId,
            "net_credit": net_credit, "max_loss": max_loss, "iv": iv,
            "entry_underlying": price, "entry_time": datetime.now().isoformat(),
            "qty": qty, "status": "open", "trade": trade,
        }
        log.info(f"BB_MEAN_REV entered: exp={expiration} sell {short_strike}P / buy {long_strike}P credit=${net_credit*100:.0f}")
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days
        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        if today != entry_date and dte <= self.MAX_DTE_HOLD:
            return True, f"max_dte ({dte} DTE)"
        if current_price <= position["short_strike"]:
            return True, f"price_breach ({current_price:.1f} <= {position['short_strike']})"

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
            limit_price = _snap_to_tick(p_short - p_long + 0.10)
        except Exception:
            limit_price = 0.10
        trade = self.broker.place_combo_order(legs=legs, limit_price=limit_price,
                                              qty=position["qty"], tag=f"BB_MEAN_REV-exit-{position['expiration']}")
        return trade is not None
