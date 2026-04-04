"""
strategies/put_credit_spread.py — Put Credit Spread (Bull Put Spread)
Sells an OTM put and buys a further OTM put for protection.
High-probability income strategy (~85% win rate at 15-delta).
Best in neutral-to-bullish markets. Entry: IV rank >= 25, SMB score <= 6.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import PUT_CREDIT_SPREAD
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.put_credit_spread")


class PutCreditSpreadStrategy:
    name = "PUT_CREDIT_SPREAD"

    def __init__(self, broker: IBKRBroker, scorer=None, agent=None):
        self.broker = broker
        self.scorer = scorer
        self.agent = agent

    def should_enter(self) -> bool:
        """Check IV rank, SMB score, and VWAP filters."""
        try:
            iv_rank = self.broker.get_iv_rank()
            log.info(f"PUT_CREDIT_SPREAD entry check: IV_rank={iv_rank:.1f}")
            if iv_rank < PUT_CREDIT_SPREAD.min_iv_rank:
                log.info(f"PUT_CREDIT_SPREAD skip: IV rank {iv_rank:.1f} < min {PUT_CREDIT_SPREAD.min_iv_rank} (not enough premium)")
                return False
            if iv_rank > PUT_CREDIT_SPREAD.max_iv_rank:
                log.info(f"PUT_CREDIT_SPREAD skip: IV rank {iv_rank:.1f} > max {PUT_CREDIT_SPREAD.max_iv_rank} (tail risk)")
                return False
        except Exception as e:
            log.warning(f"PUT_CREDIT_SPREAD IV check failed: {e} — allowing entry")

        if self.scorer is not None:
            last = self.scorer.last()
            if last and last["score"] > PUT_CREDIT_SPREAD.max_smb_score:
                log.info(f"PUT_CREDIT_SPREAD skip: SMB score {last['score']} > max {PUT_CREDIT_SPREAD.max_smb_score} (breakout — wrong side for selling puts)")
                return False

        # Trend day check
        if self.agent and hasattr(self.agent, 'current_trend_score'):
            trend = self.agent.current_trend_score
            if trend and trend.get('is_trend_day'):
                log.info(f"PUT_CREDIT_SPREAD skip: Trend day detected (score={trend['score']})")
                return False

        # VWAP filter: price should be >= VWAP for put credit spreads (buyers in control)
        # Soft filter — if data unavailable, allow entry with warning
        if self.agent is not None and getattr(self.agent, 'current_vwap_data', None):
            vwap_data = self.agent.current_vwap_data
            regime = getattr(self.agent, 'current_volume_regime', None)
            price_vs_vwap = vwap_data.get("price_vs_vwap", "at")
            vwap = vwap_data.get("vwap", 0)
            current_price = vwap_data.get("current_price", 0)

            log.info(f"PUT_CREDIT_SPREAD VWAP check: price={current_price:.1f} vwap={vwap:.1f} position={price_vs_vwap} regime={regime}")

            if price_vs_vwap == "below" and regime != "capitulation":
                log.info(f"PUT_CREDIT_SPREAD skip: Price below VWAP ({current_price:.1f} < {vwap:.1f}) — sellers in control")
                return False
        elif self.agent is not None:
            log.warning("PUT_CREDIT_SPREAD: VWAP data unavailable — allowing entry without VWAP filter")

        return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(
            dte_min=PUT_CREDIT_SPREAD.dte_min,
            dte_max=PUT_CREDIT_SPREAD.dte_target + 5,
        )
        if not exps:
            log.warning("No expirations found in DTE window")
            return None
        today = date.today()
        best = min(
            exps,
            key=lambda e: abs((datetime.strptime(e, "%Y%m%d").date() - today).days - PUT_CREDIT_SPREAD.dte_target),
        )
        dte = (datetime.strptime(best, "%Y%m%d").date() - today).days
        log.info(f"Selected expiration {best} ({dte} DTE)")
        return best

    def build_legs(self, expiration: str) -> Optional[dict]:
        """
        Bull put spread (put credit spread):
          Sell put at ~15-delta (OTM)
          Buy put spread_width pts lower (further OTM, protection)
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

        log.info(f"PUT_CREDIT_SPREAD build: underlying={price:.2f} IV={iv*100:.1f}% DTE={dte}")

        # Short put: target delta ~-0.15 (OTM put)
        short_strike = get_strike_from_delta(
            self.broker, price, T, iv, -PUT_CREDIT_SPREAD.delta_target, "P"
        )
        long_strike = short_strike - PUT_CREDIT_SPREAD.spread_width
        # Round to nearest 5
        short_strike = round(short_strike / 5) * 5
        long_strike = short_strike - PUT_CREDIT_SPREAD.spread_width

        # Price both legs via Black-Scholes
        p_short = black_scholes(price, short_strike, T, iv, right="P")["price"]
        p_long = black_scholes(price, long_strike, T, iv, right="P")["price"]

        net_credit = p_short - p_long  # credit received
        max_loss = PUT_CREDIT_SPREAD.spread_width - net_credit  # max risk per share

        if net_credit <= 0.05:
            log.warning(f"Net credit too low: ${net_credit*100:.0f} — skipping")
            return None

        if max_loss <= 0:
            log.warning(f"Max loss <= 0 — invalid structure")
            return None

        # Dynamic position sizing
        qty = calculate_position_size(
            capital=config.ACCOUNT_CAPITAL,
            max_risk_pct=config.MAX_RISK_PER_TRADE_PCT,
            spread_width=PUT_CREDIT_SPREAD.spread_width,
            credit_received=net_credit,
        )

        log.info(
            f"PUT_CREDIT_SPREAD: sell {short_strike}P / buy {long_strike}P | "
            f"credit=${net_credit*100:.0f} | max_loss=${max_loss*100:.0f} | qty={qty}"
        )

        # Qualify contracts
        contracts = []
        for strike in [short_strike, long_strike]:
            opt = Option(config.UNDERLYING, expiration, strike, "P", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                contracts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}P: {e}")
                return None

        return {
            "expiration": expiration,
            "short_strike": short_strike,
            "long_strike": long_strike,
            "con_short": contracts[0].conId,
            "con_long": contracts[1].conId,
            "net_credit": net_credit,
            "max_loss": max_loss,
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

        # Sell short put, buy long put
        legs = [
            (legs_info["con_short"], 1, "SELL"),
            (legs_info["con_long"],  1, "BUY"),
        ]

        # Credit spread: limit price = credit we want (negative = credit to us)
        limit_price = -(legs_info["net_credit"] - 0.05)

        qty = legs_info["qty"]
        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=qty,
            tag=f"PUT_CREDIT_SPREAD-{expiration}",
        )

        position = {
            "strategy": self.name,
            "expiration": expiration,
            "short_strike": legs_info["short_strike"],
            "long_strike": legs_info["long_strike"],
            "con_short": legs_info["con_short"],
            "con_long": legs_info["con_long"],
            "net_credit": legs_info["net_credit"],
            "max_loss": legs_info["max_loss"],
            "iv": legs_info["iv"],
            "dte": legs_info["dte"],
            "entry_underlying": legs_info["underlying_price"],
            "entry_time": datetime.now().isoformat(),
            "qty": qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"PUT_CREDIT_SPREAD entered: exp={expiration} "
            f"sell {legs_info['short_strike']}P / buy {legs_info['long_strike']}P "
            f"credit=${legs_info['net_credit']*100:.0f} qty={qty}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days

        # Entry-day guard: NEVER force-close on the day we entered (prevents same-day open/close bug)
        entry_date = datetime.fromisoformat(position["entry_time"]).date()
        is_entry_day = (today == entry_date)

        # DTE force-close (NEVER on entry day)
        if not is_entry_day and dte <= PUT_CREDIT_SPREAD.max_dte_hold:
            log.info(f"PUT_CREDIT_SPREAD exit: DTE threshold reached ({dte} DTE <= {PUT_CREDIT_SPREAD.max_dte_hold})")
            return True, f"max_dte_hold ({dte} DTE)"

        # On entry day, skip DTE-based exit
        if is_entry_day and dte <= PUT_CREDIT_SPREAD.max_dte_hold:
            log.debug(f"PUT_CREDIT_SPREAD: Entry-day guard active, skipping DTE exit check ({dte} DTE)")

        # Price below short strike = tested, high risk
        if current_price <= position["short_strike"]:
            return True, f"price_below_short ({current_price:.1f} <= {position['short_strike']})"

        # Theoretical P&L
        T = dte_to_years(max(dte, 1))
        iv = position.get("iv", 0.20)

        p_short = black_scholes(current_price, position["short_strike"], T, iv, right="P")["price"]
        p_long = black_scholes(current_price, position["long_strike"], T, iv, right="P")["price"]

        # Current cost to close = buy back short, sell long
        current_cost = p_short - p_long
        pnl = position["net_credit"] - current_cost  # positive = profit

        log.info(f"PUT_CREDIT_SPREAD monitor: pnl=${pnl*100:.0f} price={current_price:.1f} dte={dte}")

        # Profit target: 50% of credit received
        target = position["net_credit"] * PUT_CREDIT_SPREAD.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f} >= ${target*100:.0f})"

        # Stop loss: 1.5x credit received
        stop = position["net_credit"] * PUT_CREDIT_SPREAD.stop_loss_pct
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f} <= -${stop*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse: buy back short put, sell long put
        legs = [
            (position["con_short"], 1, "BUY"),
            (position["con_long"],  1, "SELL"),
        ]

        try:
            exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
            dte = (exp_date - date.today()).days
            T = dte_to_years(max(dte, 1))
            iv = position.get("iv", 0.20)
            price = self.broker.get_underlying_price()
            p_short = black_scholes(price, position["short_strike"], T, iv, right="P")["price"]
            p_long = black_scholes(price, position["long_strike"], T, iv, right="P")["price"]
            close_debit = p_short - p_long
            limit_price = close_debit + 0.10
        except Exception:
            limit_price = 0.10

        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=position["qty"],
            tag=f"PUT_CREDIT_SPREAD-exit-{position['expiration']}",
        )
        log.info(f"PUT_CREDIT_SPREAD exit order placed for {position['expiration']}")
        return trade is not None
