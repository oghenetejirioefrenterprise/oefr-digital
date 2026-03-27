"""
strategies/condor.py — 0DTE Iron Condor Strategy
Uses Black-Scholes theoretical pricing (no live data subscription needed).
Enter between 9:45-10:15 ET on 0DTE expiry.
Sell OTM call spread + OTM put spread at ~10-delta.
Exit at 50% profit, 2x stop, or 15:45 force-close.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import CONDOR
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years

log = logging.getLogger("strategy.condor")


class CondorStrategy:
    name = "CONDOR"

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    def is_entry_window(self) -> bool:
        now = datetime.now().strftime("%H:%M")
        return CONDOR.entry_time_start <= now <= CONDOR.entry_time_end

    def is_force_close_time(self) -> bool:
        now = datetime.now().strftime("%H:%M")
        return now >= CONDOR.force_close_time

    def find_0dte_expiration(self) -> Optional[str]:
        today = date.today()
        today_str = today.strftime("%Y%m%d")
        exps = self.broker.get_expirations(dte_min=0, dte_max=1)
        if today_str in exps:
            return today_str
        log.info(f"No 0DTE expiry today ({today_str})")
        return None

    def build_legs(self, expiration: str) -> Optional[dict]:
        try:
            price = self.broker.get_underlying_price()
        except Exception as e:
            log.warning(f"Could not get underlying price: {e}")
            return None
        if price is None or price <= 0 or price != price:  # last check catches NaN
            log.warning(f"Invalid underlying price: {price} — skipping entry")
            return None

        iv = get_broker_iv(self.broker)
        T = dte_to_years(1)  # 0DTE → use 1 day minimum

        log.info(f"0DTE condor: underlying={price:.2f} IV={iv*100:.1f}%")

        # Find strikes at target delta
        short_put_strike = get_strike_from_delta(
            self.broker, price, T, iv, -CONDOR.delta_target, "P"
        )
        long_put_strike = short_put_strike - CONDOR.spread_width

        short_call_strike = get_strike_from_delta(
            self.broker, price, T, iv, CONDOR.delta_target, "C"
        )
        long_call_strike = short_call_strike + CONDOR.spread_width

        log.info(
            f"Condor strikes: put {long_put_strike}/{short_put_strike} | "
            f"call {short_call_strike}/{long_call_strike}"
        )

        # Theoretical prices
        p_lp = black_scholes(price, long_put_strike, T, iv, right="P")["price"]
        p_sp = black_scholes(price, short_put_strike, T, iv, right="P")["price"]
        p_sc = black_scholes(price, short_call_strike, T, iv, right="C")["price"]
        p_lc = black_scholes(price, long_call_strike, T, iv, right="C")["price"]

        net_credit = (p_sp + p_sc) - (p_lp + p_lc)
        log.info(f"Condor net credit: ${net_credit*100:.0f}")

        if net_credit < 0.10:
            log.warning(f"Net credit too low: ${net_credit*100:.0f}")
            return None

        # Qualify contracts
        opts = []
        for strike, right in [
            (long_put_strike, "P"),
            (short_put_strike, "P"),
            (short_call_strike, "C"),
            (long_call_strike, "C"),
        ]:
            opt = Option(config.UNDERLYING, expiration, strike, right, config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                opts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}{right}: {e}")
                return None

        return {
            "expiration": expiration,
            "long_put_strike": long_put_strike,
            "short_put_strike": short_put_strike,
            "short_call_strike": short_call_strike,
            "long_call_strike": long_call_strike,
            "con_lp": opts[0].conId,
            "con_sp": opts[1].conId,
            "con_sc": opts[2].conId,
            "con_lc": opts[3].conId,
            "net_credit": net_credit,
            "iv": iv,
        }

    def enter(self) -> Optional[dict]:
        if not self.is_entry_window():
            log.info(f"Not in entry window ({CONDOR.entry_time_start}-{CONDOR.entry_time_end})")
            return None

        expiration = self.find_0dte_expiration()
        if not expiration:
            return None

        legs_info = self.build_legs(expiration)
        if not legs_info:
            return None

        legs = [
            (legs_info["con_lp"], 1, "BUY"),
            (legs_info["con_sp"], 1, "SELL"),
            (legs_info["con_sc"], 1, "SELL"),
            (legs_info["con_lc"], 1, "BUY"),
        ]

        limit_price = legs_info["net_credit"] - 0.05  # positive = credit we want to receive

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=CONDOR.qty,
            tag=f"CONDOR-0DTE-{expiration}",
        )

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "long_put_strike": legs_info["long_put_strike"],
            "short_put_strike": legs_info["short_put_strike"],
            "short_call_strike": legs_info["short_call_strike"],
            "long_call_strike": legs_info["long_call_strike"],
            "con_lp": legs_info["con_lp"],
            "con_sp": legs_info["con_sp"],
            "con_sc": legs_info["con_sc"],
            "con_lc": legs_info["con_lc"],
            "net_credit": legs_info["net_credit"],
            "iv": legs_info["iv"],
            "entry_time": datetime.now().isoformat(),
            "qty": CONDOR.qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"CONDOR entered: exp={expiration} "
            f"put={legs_info['long_put_strike']}/{legs_info['short_put_strike']} "
            f"call={legs_info['short_call_strike']}/{legs_info['long_call_strike']} "
            f"credit=${legs_info['net_credit']*100:.0f}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        if self.is_force_close_time():
            return True, "force_close_time"

        # Price breached short strikes
        if current_price >= position["short_call_strike"]:
            return True, f"price_above_short_call ({current_price:.1f} >= {position['short_call_strike']})"
        if current_price <= position["short_put_strike"]:
            return True, f"price_below_short_put ({current_price:.1f} <= {position['short_put_strike']})"

        # Theoretical P&L
        iv = position.get("iv", 0.20)
        T = dte_to_years(1)

        p_lp = black_scholes(current_price, position["long_put_strike"], T, iv, right="P")["price"]
        p_sp = black_scholes(current_price, position["short_put_strike"], T, iv, right="P")["price"]
        p_sc = black_scholes(current_price, position["short_call_strike"], T, iv, right="C")["price"]
        p_lc = black_scholes(current_price, position["long_call_strike"], T, iv, right="C")["price"]

        current_cost = (p_lp + p_lc) - (p_sp + p_sc)
        pnl = position["net_credit"] - current_cost

        log.info(f"CONDOR monitor: pnl=${pnl*100:.0f} price={current_price:.1f}")

        if pnl >= position["net_credit"] * CONDOR.profit_target_pct:
            return True, f"profit_target (${pnl*100:.0f})"

        stop = position["net_credit"] * CONDOR.stop_loss_mult
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        legs = [
            (position["con_lp"], 1, "SELL"),
            (position["con_sp"], 1, "BUY"),
            (position["con_sc"], 1, "BUY"),
            (position["con_lc"], 1, "SELL"),
        ]

        try:
            iv = position.get("iv", 0.20)
            T = dte_to_years(1)
            price = self.broker.get_underlying_price()
            p_lp = black_scholes(price, position["long_put_strike"], T, iv, right="P")["price"]
            p_sp = black_scholes(price, position["short_put_strike"], T, iv, right="P")["price"]
            p_sc = black_scholes(price, position["short_call_strike"], T, iv, right="C")["price"]
            p_lc = black_scholes(price, position["long_call_strike"], T, iv, right="C")["price"]
            close_debit = (p_lp + p_lc) - (p_sp + p_sc)
            limit_price = close_debit + 0.10
        except Exception:
            limit_price = 0.10

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=position["qty"],
            tag=f"CONDOR-exit-{position['expiration']}",
        )
        log.info(f"CONDOR exit order placed")
        return trade is not None
