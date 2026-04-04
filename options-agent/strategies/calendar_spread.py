"""
strategies/calendar_spread.py — Calendar Spread (Time Spread)
Sells near-term ATM option, buys longer-term ATM option at same strike.
Profits from theta differential — near-term decays faster than back month.
Best in moderate IV environments (25-70 IV rank).
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import CALENDAR_SPREAD
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years

log = logging.getLogger("strategy.calendar_spread")

MAX_POSITION_CAPITAL = 5000


class CalendarSpreadStrategy:
    name = "CALENDAR_SPREAD"

    def __init__(self, broker: IBKRBroker, scorer=None):
        self.broker = broker
        self.scorer = scorer

    def should_enter(self) -> bool:
        """Check IV rank is in the sweet spot for calendars."""
        try:
            iv_rank = self.broker.get_iv_rank()
            log.info(f"CALENDAR_SPREAD entry check: IV_rank={iv_rank:.1f}")
            if iv_rank < CALENDAR_SPREAD.min_iv_rank:
                log.info(f"CALENDAR_SPREAD skip: IV rank {iv_rank:.1f} < min {CALENDAR_SPREAD.min_iv_rank}")
                return False
            if iv_rank > CALENDAR_SPREAD.max_iv_rank:
                log.info(f"CALENDAR_SPREAD skip: IV rank {iv_rank:.1f} > max {CALENDAR_SPREAD.max_iv_rank} (vol crush risk)")
                return False
        except Exception as e:
            log.warning(f"CALENDAR_SPREAD IV check failed: {e} — allowing entry")

        return True

    def find_expirations(self) -> Optional[tuple]:
        """Find front and back month expirations."""
        # Front month
        front_exps = self.broker.get_expirations(
            dte_min=CALENDAR_SPREAD.front_dte_min,
            dte_max=CALENDAR_SPREAD.front_dte_target + 5,
        )
        if not front_exps:
            log.warning("No front month expirations found")
            return None

        # Back month
        back_exps = self.broker.get_expirations(
            dte_min=CALENDAR_SPREAD.back_dte_min,
            dte_max=CALENDAR_SPREAD.back_dte_target + 10,
        )
        if not back_exps:
            log.warning("No back month expirations found")
            return None

        today = date.today()

        # Best front expiration (closest to target DTE)
        front = min(
            front_exps,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - CALENDAR_SPREAD.front_dte_target),
        )
        front_dte = (datetime.strptime(front, "%Y%m%d").date() - today).days

        # Best back expiration (closest to target DTE, must be after front)
        valid_back = [
            e for e in back_exps
            if datetime.strptime(e, "%Y%m%d").date() > datetime.strptime(front, "%Y%m%d").date()
        ]
        if not valid_back:
            log.warning("No valid back month expiration after front month")
            return None

        back = min(
            valid_back,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - CALENDAR_SPREAD.back_dte_target),
        )
        back_dte = (datetime.strptime(back, "%Y%m%d").date() - today).days

        log.info(f"Calendar expirations: front={front} ({front_dte} DTE) back={back} ({back_dte} DTE)")
        return front, back

    def build_legs(self, front_exp: str, back_exp: str) -> Optional[dict]:
        """
        Calendar spread:
          Sell front-month ATM option
          Buy back-month ATM option (same strike)
        Net debit = back premium - front premium (back costs more)
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
        front_date = datetime.strptime(front_exp, "%Y%m%d").date()
        back_date = datetime.strptime(back_exp, "%Y%m%d").date()
        front_dte = (front_date - today).days
        back_dte = (back_date - today).days

        T_front = dte_to_years(front_dte)
        T_back = dte_to_years(back_dte)
        iv = get_broker_iv(self.broker)

        right = CALENDAR_SPREAD.right

        log.info(f"CALENDAR_SPREAD build: underlying={price:.2f} IV={iv*100:.1f}% front={front_dte}DTE back={back_dte}DTE")

        # ATM strike (nearest to current price)
        strike = round(price / 5) * 5

        # Price both legs
        front_price = black_scholes(price, strike, T_front, iv, right=right)["price"]
        back_price = black_scholes(price, strike, T_back, iv, right=right)["price"]

        net_debit = back_price - front_price  # what we pay (back is more expensive)

        if net_debit <= 0:
            log.warning(f"Net debit non-positive: {net_debit:.4f} — invalid calendar")
            return None

        # Theoretical max profit is hard to pin exactly for calendars;
        # approximate as front premium (what we collect) minus theta erosion
        # In practice, profit comes from front decaying faster than back
        max_profit_approx = front_price * 0.60  # conservative estimate

        # Calculate qty based on max capital
        debit_per_spread = net_debit * 100
        if debit_per_spread > 0:
            max_qty = int(MAX_POSITION_CAPITAL / debit_per_spread)
            qty = max(1, min(max_qty, CALENDAR_SPREAD.qty))
        else:
            qty = CALENDAR_SPREAD.qty

        log.info(
            f"CALENDAR_SPREAD: sell {front_exp} {strike}{right} / buy {back_exp} {strike}{right} | "
            f"debit=${net_debit*100:.0f} | front=${front_price*100:.0f} back=${back_price*100:.0f} | "
            f"qty={qty}"
        )

        # Qualify contracts
        front_opt = Option(config.UNDERLYING, front_exp, strike, right, config.EXCHANGE)
        back_opt = Option(config.UNDERLYING, back_exp, strike, right, config.EXCHANGE)
        try:
            self.broker.ib.qualifyContracts(front_opt)
            if front_opt.conId == 0:
                log.error(f"qualifyContracts returned conId=0 for front {front_exp} {strike}{right} — contract not found")
                return None
            self.broker.ib.qualifyContracts(back_opt)
            if back_opt.conId == 0:
                log.error(f"qualifyContracts returned conId=0 for back {back_exp} {strike}{right} — contract not found")
                return None
        except Exception as e:
            log.error(f"Could not qualify calendar contracts: {e}")
            return None

        return {
            "front_exp": front_exp,
            "back_exp": back_exp,
            "strike": strike,
            "right": right,
            "con_front": front_opt.conId,
            "con_back": back_opt.conId,
            "net_debit": net_debit,
            "front_premium": front_price,
            "back_premium": back_price,
            "max_profit_approx": max_profit_approx,
            "iv": iv,
            "front_dte": (datetime.strptime(front_exp, "%Y%m%d").date() - today).days,
            "back_dte": (datetime.strptime(back_exp, "%Y%m%d").date() - today).days,
            "underlying_price": price,
            "qty": qty,
        }

    def enter(self) -> Optional[dict]:
        if not self.should_enter():
            return None

        expirations = self.find_expirations()
        if not expirations:
            return None

        front_exp, back_exp = expirations
        legs_info = self.build_legs(front_exp, back_exp)
        if not legs_info:
            return None

        # Calendar: sell front, buy back (same strike)
        legs = [
            (legs_info["con_front"], 1, "SELL"),
            (legs_info["con_back"],  1, "BUY"),
        ]

        # Debit spread: limit = debit we're willing to pay
        limit_price = legs_info["net_debit"] + 0.10

        qty = legs_info["qty"]
        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=qty,
            tag=f"CALENDAR-{front_exp}-{back_exp}",
        )

        position = {
            "strategy": self.name,
            "expiration": legs_info["front_exp"],  # use front for main expiration tracking
            "front_exp": legs_info["front_exp"],
            "back_exp": legs_info["back_exp"],
            "strike": legs_info["strike"],
            "right": legs_info["right"],
            "con_front": legs_info["con_front"],
            "con_back": legs_info["con_back"],
            "net_debit": legs_info["net_debit"],
            "front_premium": legs_info["front_premium"],
            "back_premium": legs_info["back_premium"],
            "iv": legs_info["iv"],
            "front_dte": legs_info["front_dte"],
            "back_dte": legs_info["back_dte"],
            "entry_underlying": legs_info["underlying_price"],
            "entry_time": datetime.now().isoformat(),
            "qty": qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"CALENDAR_SPREAD entered: front={front_exp} back={back_exp} "
            f"strike={legs_info['strike']}{legs_info['right']} "
            f"debit=${legs_info['net_debit']*100:.0f} qty={qty}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        front_date = datetime.strptime(position["front_exp"], "%Y%m%d").date()
        back_date = datetime.strptime(position["back_exp"], "%Y%m%d").date()
        front_dte = (front_date - today).days
        back_dte = (back_date - today).days

        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        # Front month approaching expiration — close to avoid assignment risk
        if today != entry_date and front_dte <= CALENDAR_SPREAD.min_front_dte_hold:
            return True, f"front_dte_hold ({front_dte} DTE on front month)"

        # Theoretical P&L: current value of calendar = back price - front price
        T_front = dte_to_years(max(front_dte, 1))
        T_back = dte_to_years(max(back_dte, 1))
        iv = position.get("iv", 0.20)
        right = position.get("right", "P")

        front_val = black_scholes(current_price, position["strike"], T_front, iv, right=right)["price"]
        back_val = black_scholes(current_price, position["strike"], T_back, iv, right=right)["price"]

        current_value = back_val - front_val  # current spread value
        pnl = current_value - position["net_debit"]  # profit/loss

        log.info(
            f"CALENDAR_SPREAD monitor: pnl=${pnl*100:.0f} price={current_price:.1f} "
            f"front_dte={front_dte} back_dte={back_dte}"
        )

        # Profit target: 25% of debit paid
        target = position["net_debit"] * CALENDAR_SPREAD.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f} >= ${target*100:.0f})"

        # Stop loss: 100% of debit (max loss = debit paid)
        stop = position["net_debit"] * CALENDAR_SPREAD.stop_loss_pct
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f} <= -${stop*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse: buy back front, sell back
        legs = [
            (position["con_front"], 1, "BUY"),
            (position["con_back"],  1, "SELL"),
        ]

        try:
            today = date.today()
            front_dte = (datetime.strptime(position["front_exp"], "%Y%m%d").date() - today).days
            back_dte = (datetime.strptime(position["back_exp"], "%Y%m%d").date() - today).days
            T_front = dte_to_years(max(front_dte, 1))
            T_back = dte_to_years(max(back_dte, 1))
            iv = position.get("iv", 0.20)
            right = position.get("right", "P")
            price = self.broker.get_underlying_price()

            front_val = black_scholes(price, position["strike"], T_front, iv, right=right)["price"]
            back_val = black_scholes(price, position["strike"], T_back, iv, right=right)["price"]
            # Closing: buy front (costs money), sell back (get money)
            # Net = back_val - front_val (should be credit if calendar has value)
            close_credit = back_val - front_val
            limit_price = -(max(close_credit - 0.10, 0.01))  # negative = credit to us
        except Exception:
            limit_price = 0.05

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=position["qty"],
            tag=f"CALENDAR-exit-{position['front_exp']}",
        )
        log.info(f"CALENDAR_SPREAD exit order placed for front={position['front_exp']}")
        return trade is not None
