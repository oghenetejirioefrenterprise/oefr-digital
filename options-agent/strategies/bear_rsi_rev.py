"""
strategies/bear_rsi_rev.py — Bear RSI Reversal Put Spread
Buys put spread when RSI(14) drops from overbought (>65) to <60.
Captures bearish reversals. Anti-correlated with PCS+CS (-0.41).
Backtest: Sortino 0.98, DD 15.8%, 40% WR, PF 1.42 on test (2020-2024).
DTE 14. 30-delta. Profit 75%, stop 50%, time stop 3 DTE.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from broker import IBKRBroker, _snap_to_tick
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.bear_rsi_rev")


class BearRSIRevStrategy:
    name = "BEAR_RSI_REV"

    DTE_TARGET = 14
    DTE_MIN = 10
    DELTA_TARGET = 0.30
    SPREAD_WIDTH = 10  # SPX points
    RSI_PERIOD = 14
    RSI_PREV_MIN = 65.0    # previous RSI must have been above this
    RSI_TRIGGER = 60.0     # current RSI must drop below this
    PROFIT_TARGET_PCT = 0.75
    STOP_LOSS_PCT = 0.50
    TIME_STOP_DTE = 3

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    @staticmethod
    def _calc_rsi(closes: list[float], period: int) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i-1] for i in range(-period, 0)]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def should_enter(self) -> bool:
        """Enter when today's RSI(14) < 60 AND yesterday's RSI(14) was > 65.
        Compares daily RSI values, not scan-to-scan."""
        try:
            contract = self.broker._get_underlying_contract()
            bars = self.broker.ib.reqHistoricalData(
                contract, endDateTime="", durationStr="30 D",
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=True,
            )
            if not bars or len(bars) < self.RSI_PERIOD + 2:
                return False
            closes = [b.close for b in bars if b.close > 0]
            if len(closes) < self.RSI_PERIOD + 2:
                return False

            # Today's RSI (all closes)
            current_rsi = self._calc_rsi(closes, self.RSI_PERIOD)
            # Yesterday's RSI (exclude last close)
            prev_rsi = self._calc_rsi(closes[:-1], self.RSI_PERIOD)

            if current_rsi is None or prev_rsi is None:
                return False

            log.info(f"BEAR_RSI_REV: RSI(14) today={current_rsi:.1f} yesterday={prev_rsi:.1f}")

            if prev_rsi > self.RSI_PREV_MIN and current_rsi < self.RSI_TRIGGER:
                log.info(f"BEAR_RSI_REV SIGNAL: RSI dropped from {prev_rsi:.1f} to {current_rsi:.1f} — bearish reversal")

                # Trend day check
                if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'current_trend_score'):
                    trend = self.agent.current_trend_score
                    if trend and trend.get('is_trend_day'):
                        log.info(f"BEAR_RSI_REV skip: Trend day detected (score={trend['score']})")
                        return False

                return True

            log.info(f"BEAR_RSI_REV skip: no reversal signal")
            return False
        except Exception as e:
            log.warning(f"BEAR_RSI_REV entry check failed: {e}")
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

        # Buy 30-delta put (long leg)
        long_strike = get_strike_from_delta(self.broker, price, T, iv, -self.DELTA_TARGET, "P")
        long_strike = round(long_strike / 5) * 5
        short_strike = long_strike - self.SPREAD_WIDTH

        p_long = black_scholes(price, long_strike, T, iv, right="P")["price"]
        p_short = black_scholes(price, short_strike, T, iv, right="P")["price"]
        net_debit = p_long - p_short
        max_profit = self.SPREAD_WIDTH - net_debit

        if net_debit <= 0.05 or max_profit <= 0:
            return None

        qty = calculate_position_size(config.ACCOUNT_CAPITAL, config.MAX_RISK_PER_TRADE_PCT,
                                      net_debit, 0)  # debit strategy

        contracts = []
        for strike in [long_strike, short_strike]:
            opt = Option(config.UNDERLYING, expiration, strike, "P", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                if opt.conId == 0:
                    return None
                contracts.append(opt)
            except Exception:
                return None

        # Bear put spread: buy higher put, sell lower put
        legs = [(contracts[0].conId, 1, "BUY"), (contracts[1].conId, 1, "SELL")]
        limit_price = _snap_to_tick(net_debit + 0.05)
        trade = self.broker.place_combo_order(legs=legs, limit_price=limit_price, qty=qty,
                                              tag=f"BEAR_RSI_REV-{expiration}")

        position = {
            "strategy": self.name, "expiration": expiration,
            "long_strike": long_strike, "short_strike": short_strike,
            "con_long": contracts[0].conId, "con_short": contracts[1].conId,
            "net_debit": net_debit, "max_profit": max_profit, "iv": iv,
            "entry_underlying": price, "entry_time": datetime.now().isoformat(),
            "qty": qty, "status": "open", "trade": trade,
        }
        log.info(f"BEAR_RSI_REV entered: exp={expiration} buy {long_strike}P / sell {short_strike}P debit=${net_debit*100:.0f}")
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days
        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        if today != entry_date and dte <= self.TIME_STOP_DTE:
            return True, f"time_stop ({dte} DTE)"

        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)
        p_long = black_scholes(current_price, position["long_strike"], T, iv, right="P")["price"]
        p_short = black_scholes(current_price, position["short_strike"], T, iv, right="P")["price"]
        current_value = p_long - p_short
        pnl = current_value - position["net_debit"]

        if pnl >= position["net_debit"] * self.PROFIT_TARGET_PCT:
            return True, f"profit_target (${pnl*100:.0f})"
        if pnl <= -(position["net_debit"] * self.STOP_LOSS_PCT):
            return True, f"stop_loss (${pnl*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse: sell long put, buy short put
        legs = [(position["con_long"], 1, "SELL"), (position["con_short"], 1, "BUY")]
        try:
            exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
            dte = (exp_date - date.today()).days
            T = dte_to_years(max(dte, 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()
            p_long = black_scholes(price, position["long_strike"], T, iv, right="P")["price"]
            p_short = black_scholes(price, position["short_strike"], T, iv, right="P")["price"]
            limit_price = _snap_to_tick(max(p_long - p_short - 0.10, 0.05))
        except Exception:
            limit_price = 0.05
        trade = self.broker.place_combo_order(legs=legs, limit_price=limit_price,
                                              qty=position["qty"], tag=f"BEAR_RSI_REV-exit-{position['expiration']}")
        return trade is not None
