"""
strategies/zero_dte_pcs.py — 0DTE SPX Put Credit Spread (Daily Income Engine)
Sells ~8-10 delta OTM puts with 5-10pt protection wings.
Entry window: 09:45-10:30 ET on 0DTE expiry (SPX Mon/Wed/Fri).
Target credit: $0.50-$1.50 per spread.
Exit: 50% profit, 2x stop, or 15:45 force-close.
60% allocation — runs in every SMB regime.
"""

import logging
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from config import ZERO_DTE_PCS
from broker import IBKRBroker
from pricing import black_scholes, get_broker_iv, get_strike_from_delta, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.zero_dte_pcs")


class ZeroDTEPCSStrategy:
    name = "ZERO_DTE_PCS"

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    def is_entry_window(self) -> bool:
        now = datetime.now().strftime("%H:%M")
        return ZERO_DTE_PCS.entry_time_start <= now <= ZERO_DTE_PCS.entry_time_end

    def is_force_close_time(self) -> bool:
        now = datetime.now().strftime("%H:%M")
        return now >= ZERO_DTE_PCS.force_close_time

    def find_0dte_expiration(self) -> Optional[str]:
        """Find today's expiration — SPX has Mon/Wed/Fri 0DTE."""
        today = date.today()
        today_str = today.strftime("%Y%m%d")
        exps = self.broker.get_expirations(dte_min=0, dte_max=1)
        if today_str in exps:
            return today_str
        log.info(f"No 0DTE expiry today ({today_str}) — SPX 0DTE available Mon/Wed/Fri")
        return None

    def build_legs(self, expiration: str) -> Optional[dict]:
        try:
            price = self.broker.get_underlying_price()
        except Exception as e:
            log.warning(f"Could not get underlying price: {e}")
            return None
        if price is None or price <= 0 or price != price:
            log.warning(f"Invalid underlying price: {price} — skipping entry")
            return None

        iv = get_broker_iv(self.broker)
        T = dte_to_years(1)  # 0DTE → use 1 day minimum

        log.info(f"0DTE PCS: underlying={price:.2f} IV={iv*100:.1f}%")

        # Find short put at ~8-10 delta
        short_put_strike = get_strike_from_delta(
            self.broker, price, T, iv, -ZERO_DTE_PCS.delta_target, "P"
        )
        short_put_strike = round(short_put_strike / 5) * 5

        # Long put: protection wing below
        long_put_strike = short_put_strike - ZERO_DTE_PCS.spread_width

        log.info(f"0DTE PCS strikes: sell {short_put_strike}P / buy {long_put_strike}P")

        # Theoretical prices via Black-Scholes
        p_short = black_scholes(price, short_put_strike, T, iv, right="P")["price"]
        p_long = black_scholes(price, long_put_strike, T, iv, right="P")["price"]

        net_credit = p_short - p_long
        max_loss = ZERO_DTE_PCS.spread_width - net_credit

        log.info(f"0DTE PCS credit: ${net_credit*100:.0f} | max_loss: ${max_loss*100:.0f}")

        # Validate credit range ($0.50-$1.50 per spread in dollar terms, i.e. 0.005-0.015 per share for SPX)
        credit_dollars = net_credit * 100
        if credit_dollars < ZERO_DTE_PCS.min_credit:
            log.warning(f"Credit too low: ${credit_dollars:.0f} < ${ZERO_DTE_PCS.min_credit:.0f} min — skipping")
            return None
        if credit_dollars > ZERO_DTE_PCS.max_credit:
            log.warning(f"Credit too high: ${credit_dollars:.0f} > ${ZERO_DTE_PCS.max_credit:.0f} max — may indicate bad strikes")
            return None

        if max_loss <= 0:
            log.warning(f"Max loss <= 0 — invalid structure")
            return None

        # Dynamic position sizing
        qty = calculate_position_size(
            capital=config.ACCOUNT_CAPITAL,
            max_risk_pct=config.MAX_RISK_PER_TRADE_PCT,
            spread_width=ZERO_DTE_PCS.spread_width,
            credit_received=net_credit,
        )

        log.info(
            f"0DTE PCS: sell {short_put_strike}P / buy {long_put_strike}P | "
            f"credit=${net_credit*100:.0f} | max_loss=${max_loss*100:.0f} | qty={qty}"
        )

        # Qualify contracts
        contracts = []
        for strike in [short_put_strike, long_put_strike]:
            opt = Option(config.UNDERLYING, expiration, strike, "P", config.EXCHANGE)
            try:
                self.broker.ib.qualifyContracts(opt)
                if opt.conId == 0:
                    log.error(f"qualifyContracts returned conId=0 for {strike}P — contract not found")
                    return None
                contracts.append(opt)
            except Exception as e:
                log.error(f"Could not qualify {strike}P: {e}")
                return None

        return {
            "expiration": expiration,
            "short_strike": short_put_strike,
            "long_strike": long_put_strike,
            "con_short": contracts[0].conId,
            "con_long": contracts[1].conId,
            "net_credit": net_credit,
            "max_loss": max_loss,
            "iv": iv,
            "underlying_price": price,
            "qty": qty,
        }

    def enter(self) -> Optional[dict]:
        if not self.is_entry_window():
            log.info(f"Not in entry window ({ZERO_DTE_PCS.entry_time_start}-{ZERO_DTE_PCS.entry_time_end})")
            return None

        # Trend day check
        if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'current_trend_score'):
            trend = self.agent.current_trend_score
            if trend and trend.get('is_trend_day'):
                log.info(f"ZERO_DTE_PCS skip: Trend day detected (score={trend['score']})")
                return None

        expiration = self.find_0dte_expiration()
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

        # Credit spread: negative limit = credit to us
        limit_price = -(legs_info["net_credit"] - 0.05)

        qty = legs_info["qty"]
        trade = self.broker.place_combo_order(
            legs=legs,
            limit_price=limit_price,
            qty=qty,
            tag=f"ZERO_DTE_PCS-{expiration}",
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
            "entry_underlying": legs_info["underlying_price"],
            "entry_time": datetime.now().isoformat(),
            "qty": qty,
            "status": "open",
            "trade": trade,
        }

        log.info(
            f"ZERO_DTE_PCS entered: exp={expiration} "
            f"sell {legs_info['short_strike']}P / buy {legs_info['long_strike']}P "
            f"credit=${legs_info['net_credit']*100:.0f} qty={qty}"
        )
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        # 15:45 force-close
        if self.is_force_close_time():
            return True, "force_close_time"

        # Price breached short strike
        if current_price <= position["short_strike"]:
            return True, f"price_below_short ({current_price:.1f} <= {position['short_strike']})"

        # Theoretical P&L
        iv = position.get("iv", 0.20)
        T = dte_to_years(1)

        p_short = black_scholes(current_price, position["short_strike"], T, iv, right="P")["price"]
        p_long = black_scholes(current_price, position["long_strike"], T, iv, right="P")["price"]

        current_cost = p_short - p_long  # cost to close
        pnl = position["net_credit"] - current_cost  # positive = profit

        log.info(f"ZERO_DTE_PCS monitor: pnl=${pnl*100:.0f} price={current_price:.1f}")

        # Profit target: 50% of credit
        target = position["net_credit"] * ZERO_DTE_PCS.profit_target_pct
        if pnl >= target:
            return True, f"profit_target (${pnl*100:.0f})"

        # Stop loss: 2x credit
        stop = position["net_credit"] * ZERO_DTE_PCS.stop_loss_mult
        if pnl <= -stop:
            return True, f"stop_loss (${pnl*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        # Reverse: buy back short put, sell long put
        legs = [
            (position["con_short"], 1, "BUY"),
            (position["con_long"],  1, "SELL"),
        ]

        try:
            iv = position.get("iv", 0.20)
            T = dte_to_years(1)
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
            tag=f"ZERO_DTE_PCS-exit-{position['expiration']}",
        )
        log.info(f"ZERO_DTE_PCS exit order placed")
        return trade is not None
