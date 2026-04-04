"""
strategies/call_spread.py — Bull Call Spread Strategy
Buys a call near ATM and sells a call 10pts higher.
Used when SMB score is 5-6 (moderate breakout setup) and IV rank < 60.
DTE target: 5-10 days.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import CALL_SPREAD
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.call_spread")


class CallSpreadStrategy:
    name = "CALL_SPREAD"

    def __init__(self, broker: IBKRBroker, scorer=None):
        self.broker = broker
        self.scorer = scorer  # SMBScorer instance (optional; checked before entry)

    def should_enter(self) -> bool:
        """Check IV rank and SMB score filters."""
        try:
            iv_rank = self.broker.get_iv_rank()
            log.info(f"CALL_SPREAD entry check: IV_rank={iv_rank:.1f} max={CALL_SPREAD.max_iv_rank}")
            if iv_rank > CALL_SPREAD.max_iv_rank:
                log.info(f"CALL_SPREAD skip: IV rank {iv_rank:.1f} > max {CALL_SPREAD.max_iv_rank} (don't buy expensive premium)")
                return False
        except Exception as e:
            log.warning(f"CALL_SPREAD IV check failed: {e} — allowing entry")

        if self.scorer is not None:
            last = self.scorer.last()
            if last and last["score"] < CALL_SPREAD.min_smb_score:
                log.info(f"CALL_SPREAD skip: SMB score {last['score']} < min {CALL_SPREAD.min_smb_score}")
                return False

        # Trend day check
        if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'current_trend_score'):
            trend = self.agent.current_trend_score
            if trend and trend.get('is_trend_day'):
                log.info(f"CALL_SPREAD skip: Trend day detected (score={trend['score']})")
                return False

        return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(
            dte_min=CALL_SPREAD.dte_min,
            dte_max=CALL_SPREAD.dte_target + 5,
        )
        if not exps:
            log.warning("No expirations found in DTE window")
            return None
        today = date.today()
        best = min(
            exps,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - CALL_SPREAD.dte_target),
        )
        dte = (datetime.strptime(best, "%Y%m%d").date() - today).days
        log.info(f"Selected expiration {best} ({dte} DTE)")
        return best

    def build_legs(self, expiration: str) -> Optional[dict]:
        """
        Bull call spread:
          Buy call at ~0.45 delta (near ATM)
          Sell call spread_width pts higher
        """
        try:
            price = self.broker.get_underlying_price()
        except Exception as e:
            log.warning(f"Could not get underlying price: {e}")
            return None
        if price is None or price <= 0 or price != price:
            log.warning(f"Invalid underlying price: {price}")
            return None

        today = date.today()
        exp_date = datetime.strptime(expiration, "%Y%m%d").date()
        dte = (exp_date - today).days
        T = dte_to_years(dte)
        iv = get_broker_iv(self.broker)

        log.info(f"CALL_SPREAD build: underlying={price:.2f} IV={iv*100:.1f}% DTE={dte}")

        # Long call: target delta ~0.45 (near ATM)
        long_strike = get_strike_from_delta(self.broker, price, T, iv, CALL_SPREAD.delta_target, "C")
        short_strike = long_strike + CALL_SPREAD.spread_width
        # Round to nearest 5
        long_strike = round(long_strike / 5) * 5
        short_strike = long_strike + CALL_SPREAD.spread_width

        # Price both legs via Black-Scholes
        c_long = black_scholes(price, long_strike, T, iv, right="C")["price"]
        c_short = black_scholes(price, short_strike, T, iv, right="C")["price"]

        net_debit = c_long - c_short  # what we pay
        max_profit = CALL_SPREAD.spread_width - net_debit

        if net_debit <= 0:
            log.warning(f"Net debit is non-positive: {net_debit:.4f} — skipping")
            return None

        if max_profit <= 0:
            log.warning(f"Max profit <= 0 for this spread (debit too wide) — skipping")
            return None

        # Dynamic position sizing (for debit spread: spread_width=debit, credit=0)
        qty = calculate_position_size(
            capital=config.ACCOUNT_CAPITAL,
            max_risk_pct=config.MAX_RISK_PER_TRADE_PCT,
            spread_width=net_debit,
            credit_received=0,
        )

        log.info(
            f"CALL_SPREAD: buy {long_strike}C / sell {short_strike}C | "
            f"debit=${net_debit*100:.0f} | max_profit=${max_profit*100:.0f} | qty={qty}"
        )

        # Qualify contracts
        contracts = []
        for strike in [long_strike, short_strike]:
            opt = Option(config.UNDERLYING, expiration, strike, "C", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                contracts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}C: {e}")
                return None

        return {
            "expiration": expiration,
            "long_strike": long_strike,
            "short_strike": short_strike,
            "con_long": contracts[0].conId,
            "con_short": contracts[1].conId,
            "net_debit": net_debit,
            "max_profit": max_profit,
            "iv": iv,
            "dte": dte,
            "underlying_price": price,
            "qty": qty,
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

        # Buy long call, sell short call
        legs = [
            (legs_info["con_long"],  1, "BUY"),
            (legs_info["con_short"], 1, "SELL"),
        ]

        # Debit spread: limit price = debit we're willing to pay (positive)
        limit_price = legs_info["net_debit"] + 0.05  # slight slippage

        qty = legs_info["qty"]
        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=qty,
            tag=f"CALL_SPREAD-{expiration}",
        )

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "long_strike": legs_info["long_strike"],
            "short_strike": legs_info["short_strike"],
            "con_long": legs_info["con_long"],
            "con_short": legs_info["con_short"],
            "net_debit": legs_info["net_debit"],
            "max_profit": legs_info["max_profit"],
            "iv": legs_info["iv"],
            "dte": legs_info["dte"],
            "entry_underlying": legs_info["underlying_price"],
            "entry_time": datetime.now().isoformat(),
            "qty": qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"CALL_SPREAD entered: exp={expiration} "
            f"buy {legs_info['long_strike']}C / sell {legs_info['short_strike']}C "
            f"debit=${legs_info['net_debit']*100:.0f} qty={qty}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days

        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        # DTE force-close (not on entry day)
        if today != entry_date and dte <= CALL_SPREAD.max_dte_hold:
            return True, f"max_dte_hold ({dte} DTE)"

        # Theoretical P&L
        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)

        c_long = black_scholes(current_price, position["long_strike"], T, iv, right="C")["price"]
        c_short = black_scholes(current_price, position["short_strike"], T, iv, right="C")["price"]

        current_value = c_long - c_short  # current spread value
        pnl = current_value - position["net_debit"]  # profit (positive) or loss (negative)

        log.info(f"CALL_SPREAD monitor: pnl=${pnl*100:.0f} price={current_price:.1f} dte={dte}")

        # Profit target: 50% of max profit
        target = position["max_profit"] * CALL_SPREAD.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f} >= ${target*100:.0f})"

        # Stop loss: 2x debit paid
        stop = position["net_debit"] * CALL_SPREAD.stop_loss_pct
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f} <= -${stop*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse: sell long call, buy back short call
        legs = [
            (position["con_long"],  1, "SELL"),
            (position["con_short"], 1, "BUY"),
        ]

        try:
            exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
            dte = (exp_date - date.today()).days
            T = dte_to_years(max(dte, 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()
            c_long = black_scholes(price, position["long_strike"], T, iv, right="C")["price"]
            c_short = black_scholes(price, position["short_strike"], T, iv, right="C")["price"]
            close_credit = c_long - c_short  # sell back at current value
            limit_price = max(close_credit - 0.10, 0.01)
        except Exception:
            limit_price = 0.05

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=position["qty"],
            tag=f"CALL_SPREAD-exit-{position['expiration']}",
        )
        log.info(f"CALL_SPREAD exit order placed for {position['expiration']}")
        return trade is not None
