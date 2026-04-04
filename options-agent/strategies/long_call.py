"""
strategies/long_call.py — Long Call Strategy
Buys an ATM call when SMB score >= 7 and IV rank < 45.
High conviction breakout play — buy gamma when the setup is strong and vol is cheap.
Exit: double (100% gain) or lose 50% of premium. DTE <= 1 force-close.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import LONG_CALL
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.long_call")


class LongCallStrategy:
    name = "LONG_CALL"

    def __init__(self, broker: IBKRBroker, scorer=None):
        self.broker = broker
        self.scorer = scorer  # SMBScorer instance (optional)

    def should_enter(self) -> bool:
        """Require high SMB score AND low IV (cheap gamma)."""
        try:
            iv_rank = self.broker.get_iv_rank()
            log.info(f"LONG_CALL entry check: IV_rank={iv_rank:.1f} max={LONG_CALL.max_iv_rank}")
            if iv_rank > LONG_CALL.max_iv_rank:
                log.info(f"LONG_CALL skip: IV rank {iv_rank:.1f} > max {LONG_CALL.max_iv_rank} (premium too expensive)")
                return False
        except Exception as e:
            log.warning(f"LONG_CALL IV check failed: {e} — allowing entry")

        if self.scorer is not None:
            last = self.scorer.last()
            if last and last["score"] < LONG_CALL.min_smb_score:
                log.info(f"LONG_CALL skip: SMB score {last['score']} < min {LONG_CALL.min_smb_score}")
                return False

        return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(
            dte_min=LONG_CALL.dte_min,
            dte_max=LONG_CALL.dte_target + 3,
        )
        if not exps:
            log.warning("No expirations found in DTE window")
            return None
        today = date.today()
        best = min(
            exps,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - LONG_CALL.dte_target),
        )
        dte = (datetime.strptime(best, "%Y%m%d").date() - today).days
        log.info(f"Selected expiration {best} ({dte} DTE)")
        return best

    def build_legs(self, expiration: str) -> Optional[dict]:
        """
        Single-leg long call at ~0.50 delta (ATM).
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

        log.info(f"LONG_CALL build: underlying={price:.2f} IV={iv*100:.1f}% DTE={dte}")

        # Strike at target delta (~ATM)
        strike = get_strike_from_delta(self.broker, price, T, iv, LONG_CALL.delta_target, "C")
        strike = round(strike / 5) * 5  # round to nearest 5

        # Price via Black-Scholes
        premium = black_scholes(price, strike, T, iv, right="C")["price"]

        if premium <= 0:
            log.warning(f"Invalid premium: {premium}")
            return None

        # Dynamic position sizing (for long call: spread_width=premium, credit=0)
        qty = calculate_position_size(
            capital=config.ACCOUNT_CAPITAL,
            max_risk_pct=config.MAX_RISK_PER_TRADE_PCT,
            spread_width=premium,
            credit_received=0,
        )

        log.info(
            f"LONG_CALL: buy {strike}C | premium=${premium*100:.0f} | qty={qty}"
        )

        # Qualify contract
        opt = Option(config.UNDERLYING, expiration, strike, "C", config.EXCHANGE)
        try:
            self.broker.ib.qualifyContracts(opt)
        except Exception as e:
            log.error(f"Could not qualify {strike}C: {e}")
            return None

        return {
            "expiration": expiration,
            "strike": strike,
            "con_id": opt.conId,
            "premium": premium,
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

        # Single-leg: buy call(s)
        qty = legs_info["qty"]
        limit_price = legs_info["premium"] + 0.10  # slight slippage allowance

        trade = self.broker.place_single_order(
            con_id=legs_info["con_id"],
            right="C",
            strike=legs_info["strike"],
            expiration=legs_info["expiration"],
            action="BUY",
            qty=qty,
            limit_price=limit_price,
            tag=f"LONG_CALL-{legs_info['expiration']}",
        )

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "strike": legs_info["strike"],
            "con_id": legs_info["con_id"],
            "premium": legs_info["premium"],
            "iv": legs_info["iv"],
            "dte": legs_info["dte"],
            "entry_underlying": legs_info["underlying_price"],
            "entry_time": datetime.now().isoformat(),
            "qty": qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"LONG_CALL entered: exp={expiration} "
            f"buy {legs_info['strike']}C @ ${legs_info['premium']*100:.0f} qty={qty}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days

        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        # DTE force-close (not on entry day)
        if today != entry_date and dte <= LONG_CALL.max_dte_hold:
            return True, f"max_dte_hold ({dte} DTE)"

        # Theoretical current value
        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)
        current_value = black_scholes(current_price, position["strike"], T, iv, right="C")["price"]
        pnl = current_value - position["premium"]

        log.info(f"LONG_CALL monitor: pnl=${pnl*100:.0f} price={current_price:.1f} dte={dte}")

        # Profit target: 100% (double the premium)
        target = position["premium"] * LONG_CALL.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f} >= ${target*100:.0f})"

        # Stop loss: lose 50% of premium
        stop = position["premium"] * LONG_CALL.stop_loss_pct
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f} <= -${stop*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        try:
            exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
            dte = (exp_date - date.today()).days
            T = dte_to_years(max(dte, 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()
            current_value = black_scholes(price, position["strike"], T, iv, right="C")["price"]
            limit_price = max(current_value - 0.10, 0.01)
        except Exception:
            limit_price = 0.05

        trade = self.broker.place_single_order(
            con_id=position["con_id"],
            right="C",
            strike=position["strike"],
            expiration=position["expiration"],
            action="SELL",
            qty=position["qty"],
            limit_price=limit_price,
            tag=f"LONG_CALL-exit-{position['expiration']}",
        )
        log.info(f"LONG_CALL exit order placed for {position['expiration']}")
        return trade is not None
