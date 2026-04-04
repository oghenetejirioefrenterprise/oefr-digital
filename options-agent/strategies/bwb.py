"""
strategies/bwb.py — Broken Wing Butterfly (3-leg put structure)
Long 1x upper put / Short 2x middle puts / Long 1x lower put (broken wing).
Hybrid delta-based strike selection with minimum wing width floor.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import BWB
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.bwb")


class BWBStrategy:
    name = "BWB"

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    def should_enter(self) -> bool:
        """Check IV rank filter before entering."""
        try:
            iv_rank = self.broker.get_iv_rank()
            log.info(f"BWB entry check: IV_rank={iv_rank:.1f} (min={BWB.min_iv_rank} max={BWB.max_iv_rank})")
            if iv_rank < BWB.min_iv_rank:
                log.info(f"BWB skip: IV rank {iv_rank:.1f} < min {BWB.min_iv_rank}")
                return False
            if iv_rank > BWB.max_iv_rank:
                log.info(f"BWB skip: IV rank {iv_rank:.1f} > max {BWB.max_iv_rank}")
                return False
            return True
        except Exception as e:
            log.warning(f"BWB should_enter IV check failed: {e} — allowing entry")
            return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(
            dte_min=BWB.dte_min,
            dte_max=BWB.dte_target + 3,
        )
        if not exps:
            log.warning("No expirations found in DTE window")
            return None
        today = date.today()
        best = min(
            exps,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - BWB.dte_target),
        )
        dte = (datetime.strptime(best, "%Y%m%d").date() - today).days
        log.info(f"Selected expiration {best} ({dte} DTE)")
        return best

    def build_legs(self, expiration: str) -> Optional[dict]:
        """
        Build a real Broken Wing Butterfly:
        Long 1x upper put (near ATM) / Short 2x middle puts / Long 1x lower put (broken wing).
        Uses hybrid delta-based selection with minimum wing width floor.
        """
        try:
            price = self.broker.get_underlying_price()
        except Exception as e:
            log.warning(f"Could not get underlying price: {e}")
            return None
        if price is None or price <= 0:
            return None

        today = date.today()
        exp_date = datetime.strptime(expiration, "%Y%m%d").date()
        dte = (exp_date - today).days
        T = dte_to_years(dte)
        iv = get_broker_iv(self.broker)

        log.info(f"BWB build: underlying={price:.2f} IV={iv*100:.1f}% DTE={dte}")

        # Find short (middle) strike at target delta
        short_delta = -BWB.short_delta_target  # negative for puts
        strike_mid = get_strike_from_delta(self.broker, price, T, iv, short_delta, "P")

        best = None

        # Try multiple upper wing widths and wing deltas
        for upper_offset in [0, 5, 10, 15, 20]:
            strike_high = strike_mid + upper_offset
            # Round to nearest 5
            strike_high = round(strike_high / 5) * 5

            # Don't go above ATM + 5
            if strike_high > price + 5:
                continue

            for wing_width in range(BWB.min_wing_width, 35, 5):
                strike_low = strike_mid - wing_width
                strike_low = round(strike_low / 5) * 5

                # Price all 3 legs via Black-Scholes
                p_high = black_scholes(price, strike_high, T, iv, right="P")["price"]
                p_mid = black_scholes(price, strike_mid, T, iv, right="P")["price"]
                p_low = black_scholes(price, strike_low, T, iv, right="P")["price"]

                # BWB net credit = sell 2x mid - buy 1x high - buy 1x low
                net_credit = 2 * p_mid - p_high - p_low

                if net_credit < BWB.min_net_credit:
                    continue

                upper_wing = strike_high - strike_mid
                max_profit = upper_wing + net_credit  # per-share

                # Risk/reward ratio
                max_loss_down = wing_width - upper_wing - net_credit  # loss if below strike_low
                if max_loss_down <= 0:
                    max_loss_down = 0.01  # avoid division by zero
                rr_ratio = max_profit / max_loss_down

                candidate = {
                    "strike_high": strike_high,
                    "strike_mid": strike_mid,
                    "strike_low": strike_low,
                    "net_credit": net_credit,
                    "max_profit": max_profit,
                    "upper_wing": upper_wing,
                    "lower_wing": wing_width,
                    "rr_ratio": rr_ratio,
                }

                if best is None or rr_ratio > best["rr_ratio"]:
                    best = candidate

        if not best:
            log.warning(
                f"BWB SKIPPED: No valid configuration found "
                f"(IV={iv*100:.1f}%, mid_strike={strike_mid}, price={price:.0f}). "
                f"In low IV environments, BWB often cannot generate net credits. "
                f"Consider using PUT_CREDIT_SPREAD strategy directly instead."
            )
            # NOTE: BWB does NOT auto-fallback to PUT_CREDIT_SPREAD.
            # If you want both strategies, set ACTIVE_STRATEGY=ALL or use SMB mode.
            return None

        log.info(
            f"Best BWB: {best['strike_high']}P / {best['strike_mid']}Px2 / {best['strike_low']}P "
            f"| credit=${best['net_credit']*100:.0f} | max_profit=${best['max_profit']*100:.0f} "
            f"| upper={best['upper_wing']}pts lower={best['lower_wing']}pts | R/R={best['rr_ratio']:.2f}"
        )

        # Qualify all 3 contracts
        contracts = []
        for strike in [best["strike_high"], best["strike_mid"], best["strike_low"]]:
            opt = Option(config.UNDERLYING, expiration, strike, "P", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                contracts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}P: {e}")
                return None

        return {
            "expiration": expiration,
            "strike_high": best["strike_high"],
            "strike_mid": best["strike_mid"],
            "strike_low": best["strike_low"],
            "con_high": contracts[0].conId,
            "con_mid": contracts[1].conId,
            "con_low": contracts[2].conId,
            "net_credit": best["net_credit"],
            "max_profit": best["max_profit"],
            "upper_wing": best["upper_wing"],
            "lower_wing": best["lower_wing"],
            "iv": iv,
            "dte": dte,
            "underlying_price": price,
        }

    def enter(self) -> Optional[dict]:
        if not self.should_enter():
            log.info("BWB: Entry conditions not met (IV rank filter)")
            return None

        expiration = self.find_expiration()
        if not expiration:
            log.info("BWB: No suitable expiration found")
            return None

        legs_info = self.build_legs(expiration)
        if not legs_info:
            # build_legs already logs the specific reason (e.g., no valid credit config)
            # BWB does NOT fallback to other strategies - returns None cleanly
            log.info("BWB: No valid leg configuration found - no entry")
            return None

        # 3-leg BWB combo: buy 1x high, sell 2x mid, buy 1x low
        legs = [
            (legs_info["con_high"], 1, "BUY"),
            (legs_info["con_mid"],  2, "SELL"),
            (legs_info["con_low"],  1, "BUY"),
        ]

        # Dynamic position sizing (BWB: spread_width = lower_wing, credit = net_credit)
        qty = calculate_position_size(
            capital=config.ACCOUNT_CAPITAL,
            max_risk_pct=config.MAX_RISK_PER_TRADE_PCT,
            spread_width=legs_info["lower_wing"],
            credit_received=legs_info["net_credit"],
        )

        # Limit price: net credit we want (negative = credit to us)
        limit_price = -(legs_info["net_credit"] - 0.05)

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=qty,
            tag=f"BWB-{expiration}",
        )

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "strike_high": legs_info["strike_high"],
            "strike_mid": legs_info["strike_mid"],
            "strike_low": legs_info["strike_low"],
            "con_high": legs_info["con_high"],
            "con_mid": legs_info["con_mid"],
            "con_low": legs_info["con_low"],
            "net_credit": legs_info["net_credit"],
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
            f"BWB entered: exp={expiration} "
            f"{legs_info['strike_high']}P / {legs_info['strike_mid']}Px2 / {legs_info['strike_low']}P "
            f"credit=${legs_info['net_credit']*100:.0f}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days

        # Entry-day guard: never force-close on the day we entered
        entry_date = datetime.fromisoformat(position["entry_time"]).date()
        is_entry_day = (today == entry_date)

        # DTE force-close (NEVER on entry day - prevents same-day open/close bug)
        if not is_entry_day and dte <= BWB.max_dte_hold:
            log.info(f"BWB exit: DTE threshold reached ({dte} DTE <= {BWB.max_dte_hold})")
            return True, f"max_dte_hold ({dte} DTE)"

        # On entry day, skip DTE-based exit
        if is_entry_day and dte <= BWB.max_dte_hold:
            log.debug(f"BWB: Entry-day guard active, skipping DTE exit check ({dte} DTE)")

        # Price below broken wing = at or near max loss
        if current_price <= position["strike_low"]:
            return True, f"price_below_wing ({current_price:.1f} <= {position['strike_low']})"

        # Price below short strikes = high risk zone
        if current_price <= position["strike_mid"]:
            return True, f"price_below_short ({current_price:.1f} <= {position['strike_mid']})"

        # Theoretical P&L via Black-Scholes on all 3 legs
        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)

        p_high = black_scholes(current_price, position["strike_high"], T, iv, right="P")["price"]
        p_mid = black_scholes(current_price, position["strike_mid"], T, iv, right="P")["price"]
        p_low = black_scholes(current_price, position["strike_low"], T, iv, right="P")["price"]

        # Current value of the BWB (cost to close)
        current_value = p_high + p_low - 2 * p_mid
        # P&L = credit received - cost to close (positive = profit)
        pnl = position["net_credit"] - current_value

        log.info(f"BWB monitor: pnl=${pnl*100:.0f} price={current_price:.1f} dte={dte}")

        # Profit target: 50% of max profit
        target = position.get("max_profit", position["net_credit"]) * BWB.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f} >= ${target*100:.0f})"

        # Stop loss: 2x credit received
        stop = position["net_credit"] * BWB.stop_loss_pct
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f} <= -${stop*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse the entry: sell high, buy 2x mid, sell low
        legs = [
            (position["con_high"], 1, "SELL"),
            (position["con_mid"],  2, "BUY"),
            (position["con_low"],  1, "SELL"),
        ]

        try:
            exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
            current_dte = (exp_date - date.today()).days
            T = dte_to_years(max(current_dte, 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()
            p_h = black_scholes(price, position["strike_high"], T, iv, right="P")["price"]
            p_m = black_scholes(price, position["strike_mid"], T, iv, right="P")["price"]
            p_l = black_scholes(price, position["strike_low"], T, iv, right="P")["price"]
            close_debit = p_h + p_l - 2 * p_m
            limit_price = close_debit + 0.10
        except Exception:
            limit_price = 0.10

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=position["qty"],
            tag=f"BWB-exit-{position['expiration']}",
        )
        log.info(f"BWB exit order placed for {position['expiration']}")
        return trade is not None
