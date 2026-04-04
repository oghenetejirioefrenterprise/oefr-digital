"""
strategies/jade_lizard.py — Jade Lizard Strategy
Short OTM put + short call spread (sell call, buy further OTM call).
If total credit > call spread width, there is NO upside risk.
Premium collection from both sides of the market.
Best in elevated IV environments (IV rank >= 30).
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import JADE_LIZARD
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.jade_lizard")


class JadeLizardStrategy:
    name = "JADE_LIZARD"

    def __init__(self, broker: IBKRBroker, scorer=None):
        self.broker = broker
        self.scorer = scorer

    def should_enter(self) -> bool:
        """Check IV rank is elevated enough for good premium."""
        try:
            iv_rank = self.broker.get_iv_rank()
            log.info(f"JADE_LIZARD entry check: IV_rank={iv_rank:.1f}")
            if iv_rank < JADE_LIZARD.min_iv_rank:
                log.info(f"JADE_LIZARD skip: IV rank {iv_rank:.1f} < min {JADE_LIZARD.min_iv_rank} (not enough premium)")
                return False
            if iv_rank > JADE_LIZARD.max_iv_rank:
                log.info(f"JADE_LIZARD skip: IV rank {iv_rank:.1f} > max {JADE_LIZARD.max_iv_rank}")
                return False
        except Exception as e:
            log.warning(f"JADE_LIZARD IV check failed: {e} — allowing entry")

        return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(
            dte_min=JADE_LIZARD.dte_min,
            dte_max=JADE_LIZARD.dte_target + 5,
        )
        if not exps:
            log.warning("No expirations found in DTE window")
            return None
        today = date.today()
        best = min(
            exps,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - JADE_LIZARD.dte_target),
        )
        dte = (datetime.strptime(best, "%Y%m%d").date() - today).days
        log.info(f"Selected expiration {best} ({dte} DTE)")
        return best

    def build_legs(self, expiration: str) -> Optional[dict]:
        """
        Jade Lizard = 3 legs:
          1. Sell OTM put at ~20-delta
          2. Sell OTM call at ~15-delta
          3. Buy OTM call at (short call + spread_width) for protection

        Key: total credit > call spread width → NO upside risk
        Downside risk = short put strike - total credit
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

        log.info(f"JADE_LIZARD build: underlying={price:.2f} IV={iv*100:.1f}% DTE={dte}")

        # Find put strike at ~20-delta
        short_put_strike = get_strike_from_delta(
            self.broker, price, T, iv, -JADE_LIZARD.put_delta_target, "P"
        )
        short_put_strike = round(short_put_strike / 5) * 5

        # Find call strike at ~15-delta
        short_call_strike = get_strike_from_delta(
            self.broker, price, T, iv, JADE_LIZARD.call_delta_target, "C"
        )
        short_call_strike = round(short_call_strike / 5) * 5

        # Long call = short call + spread width (protection)
        long_call_strike = short_call_strike + JADE_LIZARD.call_spread_width

        # Price all 3 legs via Black-Scholes
        p_put = black_scholes(price, short_put_strike, T, iv, right="P")["price"]
        p_short_call = black_scholes(price, short_call_strike, T, iv, right="C")["price"]
        p_long_call = black_scholes(price, long_call_strike, T, iv, right="C")["price"]

        # Total credit = put premium + call spread credit
        put_credit = p_put
        call_spread_credit = p_short_call - p_long_call
        total_credit = put_credit + call_spread_credit

        if total_credit <= 0.10:
            log.warning(f"Total credit too low: ${total_credit*100:.0f} — skipping")
            return None

        # Check if total credit > call spread width (no upside risk)
        call_spread_width_pts = JADE_LIZARD.call_spread_width
        no_upside_risk = total_credit >= call_spread_width_pts
        if no_upside_risk:
            log.info(f"JADE_LIZARD: no upside risk! credit ${total_credit*100:.0f} >= spread width ${call_spread_width_pts*100:.0f}")

        # Max loss on downside = short put strike - total credit (per share)
        # (only on the put side, since call side is capped)
        max_loss_down = short_put_strike - total_credit  # theoretical
        # Practical max loss with the put spread structure
        downside_risk = max(0, call_spread_width_pts - total_credit) if not no_upside_risk else 0
        put_risk = short_put_strike - total_credit  # naked put risk (we accept this)

        # Dynamic position sizing
        # Risk: call side capped at call_spread_width, put side is naked.
        # Use call spread width as the spread_width for sizing (defined risk side).
        qty = calculate_position_size(
            capital=config.ACCOUNT_CAPITAL,
            max_risk_pct=config.MAX_RISK_PER_TRADE_PCT,
            spread_width=JADE_LIZARD.call_spread_width,
            credit_received=total_credit,
        )

        log.info(
            f"JADE_LIZARD: sell {short_put_strike}P + sell {short_call_strike}C / buy {long_call_strike}C | "
            f"total credit=${total_credit*100:.0f} (put=${put_credit*100:.0f} call_spread=${call_spread_credit*100:.0f}) | "
            f"no_upside_risk={no_upside_risk} | qty={qty}"
        )

        # Qualify all contracts
        contracts = []
        for strike, right in [
            (short_put_strike, "P"),
            (short_call_strike, "C"),
            (long_call_strike, "C"),
        ]:
            opt = Option(config.UNDERLYING, expiration, strike, right, config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                if opt.conId == 0:
                    log.error(f"qualifyContracts returned conId=0 for {strike}{right} — contract not found")
                    return None
                contracts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}{right}: {e}")
                return None

        return {
            "expiration": expiration,
            "short_put_strike": short_put_strike,
            "short_call_strike": short_call_strike,
            "long_call_strike": long_call_strike,
            "con_short_put": contracts[0].conId,
            "con_short_call": contracts[1].conId,
            "con_long_call": contracts[2].conId,
            "put_credit": put_credit,
            "call_spread_credit": call_spread_credit,
            "net_credit": total_credit,
            "no_upside_risk": no_upside_risk,
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

        # 3-leg Jade Lizard: sell put, sell call, buy further OTM call
        legs = [
            (legs_info["con_short_put"],  1, "SELL"),
            (legs_info["con_short_call"], 1, "SELL"),
            (legs_info["con_long_call"],  1, "BUY"),
        ]

        # Credit: limit price negative = credit to us
        limit_price = -(legs_info["net_credit"] - 0.05)

        qty = legs_info["qty"]
        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=qty,
            tag=f"JADE_LIZARD-{expiration}",
        )

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "short_put_strike": legs_info["short_put_strike"],
            "short_call_strike": legs_info["short_call_strike"],
            "long_call_strike": legs_info["long_call_strike"],
            "con_short_put": legs_info["con_short_put"],
            "con_short_call": legs_info["con_short_call"],
            "con_long_call": legs_info["con_long_call"],
            "put_credit": legs_info["put_credit"],
            "call_spread_credit": legs_info["call_spread_credit"],
            "net_credit": legs_info["net_credit"],
            "no_upside_risk": legs_info["no_upside_risk"],
            "iv": legs_info["iv"],
            "dte": legs_info["dte"],
            "entry_underlying": legs_info["underlying_price"],
            "entry_time": datetime.now().isoformat(),
            "qty": qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"JADE_LIZARD entered: exp={expiration} "
            f"sell {legs_info['short_put_strike']}P + "
            f"sell {legs_info['short_call_strike']}C / buy {legs_info['long_call_strike']}C "
            f"credit=${legs_info['net_credit']*100:.0f} qty={qty}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days

        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        # DTE force-close (not on entry day)
        if today != entry_date and dte <= JADE_LIZARD.max_dte_hold:
            return True, f"max_dte_hold ({dte} DTE)"

        # Price below short put = put side in trouble
        if current_price <= position["short_put_strike"]:
            return True, f"price_below_short_put ({current_price:.1f} <= {position['short_put_strike']})"

        # Price above short call = call side tested (but capped by long call)
        if current_price >= position["long_call_strike"]:
            return True, f"price_above_long_call ({current_price:.1f} >= {position['long_call_strike']})"

        # Theoretical P&L
        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)

        p_put = black_scholes(current_price, position["short_put_strike"], T, iv, right="P")["price"]
        p_sc = black_scholes(current_price, position["short_call_strike"], T, iv, right="C")["price"]
        p_lc = black_scholes(current_price, position["long_call_strike"], T, iv, right="C")["price"]

        # Cost to close all 3 legs
        current_cost = p_put + (p_sc - p_lc)
        pnl = position["net_credit"] - current_cost  # positive = profit

        log.info(f"JADE_LIZARD monitor: pnl=${pnl*100:.0f} price={current_price:.1f} dte={dte}")

        # Profit target: 50% of total credit
        target = position["net_credit"] * JADE_LIZARD.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f} >= ${target*100:.0f})"

        # Stop loss: 1.5x total credit
        stop = position["net_credit"] * JADE_LIZARD.stop_loss_pct
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f} <= -${stop*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse: buy back put, buy back short call, sell long call
        legs = [
            (position["con_short_put"],  1, "BUY"),
            (position["con_short_call"], 1, "BUY"),
            (position["con_long_call"],  1, "SELL"),
        ]

        try:
            exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
            dte = (exp_date - date.today()).days
            T = dte_to_years(max(dte, 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()

            p_put = black_scholes(price, position["short_put_strike"], T, iv, right="P")["price"]
            p_sc = black_scholes(price, position["short_call_strike"], T, iv, right="C")["price"]
            p_lc = black_scholes(price, position["long_call_strike"], T, iv, right="C")["price"]

            close_debit = p_put + (p_sc - p_lc)
            limit_price = close_debit + 0.10
        except Exception:
            limit_price = 0.10

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=position["qty"],
            tag=f"JADE_LIZARD-exit-{position['expiration']}",
        )
        log.info(f"JADE_LIZARD exit order placed for {position['expiration']}")
        return trade is not None
