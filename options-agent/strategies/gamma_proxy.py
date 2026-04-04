"""
strategies/gamma_proxy.py — Gamma Proxy (Long Straddle when VRP < -2)
Buys ATM straddle when realized vol exceeds implied vol (gamma is cheap).
Backtest: Sortino 6.77, 40% WR, correlation -0.02 with PCS+CS.
DTE 7. Profit 40%, stop 30%.
"""

import math
import logging
import statistics
from datetime import datetime, date
from typing import Optional
from ib_insync import Option

import config
from broker import IBKRBroker, _snap_to_tick
from pricing import get_broker_iv, dte_to_years
from sizing import calculate_position_size

log = logging.getLogger("strategy.gamma_proxy")


class GammaProxyStrategy:
    name = "GAMMA_PROXY"

    DTE_TARGET = 7
    DTE_MIN = 5
    VRP_MAX = -2.0  # only enter when VRP < -2 (realized vol > implied)
    HV_WINDOW = 20
    PROFIT_TARGET_PCT = 0.40
    STOP_LOSS_PCT = 0.30

    def __init__(self, broker: IBKRBroker):
        self.broker = broker

    def _compute_vrp(self) -> Optional[float]:
        """VRP = IV - HV20. Negative means gamma is cheap."""
        try:
            # HV20
            contract = self.broker._get_underlying_contract()
            bars = self.broker.ib.reqHistoricalData(
                contract, endDateTime="", durationStr="40 D",
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=True,
            )
            if not bars or len(bars) < self.HV_WINDOW + 1:
                return None
            closes = [b.close for b in bars if b.close > 0]
            if len(closes) < self.HV_WINDOW + 1:
                return None
            log_rets = [math.log(closes[i] / closes[i-1]) for i in range(-self.HV_WINDOW, 0)]
            hv20 = statistics.stdev(log_rets) * math.sqrt(252) * 100

            # IV
            iv = get_broker_iv(self.broker) * 100

            return iv - hv20
        except Exception as e:
            log.warning(f"VRP computation failed: {e}")
            return None

    def should_enter(self) -> bool:
        """Enter when VRP < -2 (realized vol exceeds implied — gamma is cheap)."""
        vrp = self._compute_vrp()
        if vrp is None:
            return False
        log.info(f"GAMMA_PROXY: VRP={vrp:.1f} (threshold={self.VRP_MAX})")
        if vrp >= self.VRP_MAX:
            log.info(f"GAMMA_PROXY skip: VRP {vrp:.1f} >= {self.VRP_MAX}")
            return False
        log.info(f"GAMMA_PROXY SIGNAL: VRP={vrp:.1f} — gamma is cheap, buying straddle")
        return True

    def find_expiration(self) -> Optional[str]:
        exps = self.broker.get_expirations(dte_min=self.DTE_MIN, dte_max=self.DTE_TARGET + 5)
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

        # ATM strike
        atm_strike = round(price / 5) * 5

        # Get ATM call and put prices via broker quotes
        try:
            call_quote = self.broker.get_option_quote(config.UNDERLYING, expiration, atm_strike, "C")
            put_quote = self.broker.get_option_quote(config.UNDERLYING, expiration, atm_strike, "P")
            call_mid = call_quote["mid"]
            put_mid = put_quote["mid"]
        except Exception as e:
            log.warning(f"Could not get straddle quotes: {e}")
            return None

        if call_mid <= 0 or put_mid <= 0:
            log.warning(f"Invalid straddle quotes: call={call_mid} put={put_mid}")
            return None

        total_debit = call_mid + put_mid

        # Dynamic sizing: risk = total debit per contract
        qty = calculate_position_size(config.ACCOUNT_CAPITAL, config.MAX_RISK_PER_TRADE_PCT,
                                      total_debit, 0)  # debit strategy, no credit offset

        # Qualify contracts
        call_opt = Option(config.UNDERLYING, expiration, atm_strike, "C", config.EXCHANGE)
        put_opt = Option(config.UNDERLYING, expiration, atm_strike, "P", config.EXCHANGE)
        try:
            self.broker.ib.qualifyContracts(call_opt)
            self.broker.ib.qualifyContracts(put_opt)
            if call_opt.conId == 0 or put_opt.conId == 0:
                return None
        except Exception:
            return None

        # Place as two separate orders (straddle = long call + long put)
        call_limit = _snap_to_tick(call_mid + 0.05)
        put_limit = _snap_to_tick(put_mid + 0.05)

        call_trade = self.broker.place_single_order(
            call_opt.conId, "C", atm_strike, expiration, "BUY",
            qty=qty, limit_price=call_limit, tag=f"GAMMA_PROXY-call-{expiration}")
        put_trade = self.broker.place_single_order(
            put_opt.conId, "P", atm_strike, expiration, "BUY",
            qty=qty, limit_price=put_limit, tag=f"GAMMA_PROXY-put-{expiration}")

        position = {
            "strategy": self.name, "expiration": expiration,
            "strike": atm_strike,
            "con_call": call_opt.conId, "con_put": put_opt.conId,
            "call_premium": call_mid, "put_premium": put_mid,
            "net_debit": total_debit, "iv": iv,
            "entry_underlying": price, "entry_time": datetime.now().isoformat(),
            "qty": qty, "status": "open",
            "trade": call_trade,  # store one for reference
        }
        log.info(f"GAMMA_PROXY entered: exp={expiration} ATM straddle {atm_strike} debit=${total_debit*100:.0f} qty={qty}")
        return position

    def should_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        today = date.today()
        exp_date = datetime.strptime(position["expiration"], "%Y%m%d").date()
        dte = (exp_date - today).days
        entry_date = datetime.fromisoformat(position["entry_time"]).date()

        if today != entry_date and dte <= 1:
            return True, f"max_dte ({dte} DTE)"

        # Estimate current straddle value from intrinsic + rough time value
        strike = position["strike"]
        call_intrinsic = max(current_price - strike, 0)
        put_intrinsic = max(strike - current_price, 0)
        # Rough current value: intrinsic + remaining time value (decay linearly)
        time_factor = max(dte, 1) / max((exp_date - entry_date).days, 1)
        current_value = call_intrinsic + put_intrinsic + position["net_debit"] * time_factor * 0.3

        pnl_per_share = current_value - position["net_debit"]
        debit = position["net_debit"]

        if pnl_per_share >= debit * self.PROFIT_TARGET_PCT:
            return True, f"profit_target (${pnl_per_share*100:.0f})"
        if pnl_per_share <= -(debit * self.STOP_LOSS_PCT):
            return True, f"stop_loss (${pnl_per_share*100:.0f})"

        return False, ""

    def exit(self, position: dict) -> bool:
        """Close both legs of the straddle."""
        strike = position["strike"]
        expiration = position["expiration"]
        qty = position["qty"]

        try:
            # Get current prices for limit
            call_quote = self.broker.get_option_quote(config.UNDERLYING, expiration, strike, "C")
            put_quote = self.broker.get_option_quote(config.UNDERLYING, expiration, strike, "P")
            call_limit = _snap_to_tick(max(call_quote["mid"] - 0.05, 0.05))
            put_limit = _snap_to_tick(max(put_quote["mid"] - 0.05, 0.05))
        except Exception:
            call_limit = 0.05
            put_limit = 0.05

        self.broker.place_single_order(
            position["con_call"], "C", strike, expiration, "SELL",
            qty=qty, limit_price=call_limit, tag=f"GAMMA_PROXY-call-exit-{expiration}")
        self.broker.place_single_order(
            position["con_put"], "P", strike, expiration, "SELL",
            qty=qty, limit_price=put_limit, tag=f"GAMMA_PROXY-put-exit-{expiration}")

        log.info(f"GAMMA_PROXY exit orders placed for {expiration}")
        return True
