"""
broker.py — IBKR connection layer via ib_insync
Handles connect/reconnect, market data, option chains, and order placement.
"""

import logging
import time
from datetime import datetime, date
from typing import Optional, List, Tuple
from ib_insync import (
    IB, Index, Stock, Option, ComboLeg, Contract, Order,
    MarketOrder, LimitOrder, TagValue, util
)
import config

log = logging.getLogger("broker")


class IBKRBroker:
    def __init__(self):
        self.ib = IB()
        self._connected = False

    # ─── Connection ──────────────────────────────────────────────────────────

    def connect(self, retries: int = 10, delay: int = 15):
        for attempt in range(1, retries + 1):
            try:
                log.info(f"Connecting to IBKR {config.IBKR_HOST}:{config.IBKR_PORT} (attempt {attempt})")
                self.ib.connect(
                    host=config.IBKR_HOST,
                    port=config.IBKR_PORT,
                    clientId=config.IBKR_CLIENT_ID,
                    timeout=20,
                    readonly=False,
                )
                self._connected = True
                # Use delayed data globally — no live subscription needed.
                # Change to reqMarketDataType(1) if live subscriptions are added.
                self.ib.reqMarketDataType(3)
                log.info(f"Connected. Account: {self.ib.managedAccounts()}")
                return True
            except Exception as e:
                log.warning(f"Connect attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)
        raise ConnectionError("Could not connect to IBKR gateway after all retries")

    def ensure_connected(self) -> bool:
        """Reconnect if disconnected — but only during market hours."""
        if self.ib.isConnected():
            return True
        # Don't reconnect outside market hours (avoids post-close thrashing)
        now = datetime.now()
        if now.weekday() >= 5:  # weekend
            log.info("Weekend — skipping reconnect")
            return False
        time_str = now.strftime("%H:%M")
        if not ("09:20" <= time_str <= "16:15"):
            log.info(f"Outside market hours ({time_str}) — skipping reconnect")
            return False
        log.warning("IBKR disconnected — reconnecting...")
        self._connected = False
        try:
            self.connect()
            return True
        except ConnectionError:
            log.error("Reconnect failed")
            return False

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()
            self._connected = False

    # ─── Market Data ─────────────────────────────────────────────────────────

    def get_underlying_price(self, symbol: str = None) -> float:
        symbol = symbol or config.UNDERLYING
        contract = Index(symbol, "CBOE") if symbol == "SPX" else Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, "", False, False)
        self.ib.sleep(3)
        def _safe(v):
            try:
                f = float(v)
                if f != f: return 0.0
                return f
            except (TypeError, ValueError):
                return 0.0
        price = _safe(ticker.last)
        if price <= 0:
            price = _safe(ticker.close)
        if price <= 0:
            price = _safe(ticker.bid)
        if price <= 0:
            price = _safe(ticker.ask)
        if price <= 0:
            # Fallback: use historical bar
            bars = self.ib.reqHistoricalData(
                contract, endDateTime="", durationStr="1 D",
                barSizeSetting="1 day", whatToShow="TRADES", useRTH=True
            )
            if bars:
                price = _safe(bars[-1].close)
        self.ib.cancelMktData(contract)
        if price <= 0 or price != price:  # also check NaN
            raise ValueError(f"Could not get valid price for {symbol} (got {price})")
        log.info(f"Underlying {symbol} price: {price}")
        return float(price)

    def get_iv_rank(self, symbol: str = None) -> float:
        """
        Approximate IV rank using 52-week high/low of HV30.
        Returns 0-100 scale.
        """
        symbol = symbol or config.UNDERLYING
        try:
            contract = Index(symbol, "CBOE") if symbol == "SPX" else Stock(symbol, "SMART", "USD")
            self.ib.qualifyContracts(contract)
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr="1 Y",
                barSizeSetting="1 day",
                whatToShow="OPTION_IMPLIED_VOLATILITY",
                useRTH=True,
            )
            if not bars:
                return 50.0  # neutral fallback
            ivs = [b.close for b in bars if b.close > 0]
            if len(ivs) < 10:
                return 50.0
            current = ivs[-1]
            iv_min, iv_max = min(ivs), max(ivs)
            rank = ((current - iv_min) / (iv_max - iv_min)) * 100 if iv_max > iv_min else 50.0
            log.info(f"IV rank for {symbol}: {rank:.1f} (current={current:.3f})")
            return round(rank, 1)
        except Exception as e:
            log.warning(f"IV rank calculation failed: {e} — using 50")
            return 50.0

    # ─── Option Chain ─────────────────────────────────────────────────────────

    def get_expirations(self, symbol: str = None, dte_min: int = 3, dte_max: int = 21) -> List[str]:
        """Return expiration dates (YYYYMMDD) within DTE window."""
        symbol = symbol or config.UNDERLYING
        exchange = config.EXCHANGE
        contract = Index(symbol, exchange) if symbol == "SPX" else Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        chains = self.ib.reqSecDefOptParams(contract.symbol, "", contract.secType, contract.conId)
        today = date.today()
        valid = []
        for chain in chains:
            if chain.exchange not in ("CBOE", "SMART", "ISE"):
                continue
            for exp in chain.expirations:
                exp_date = datetime.strptime(exp, "%Y%m%d").date()
                dte = (exp_date - today).days
                if dte_min <= dte <= dte_max:
                    valid.append(exp)
        return sorted(set(valid))

    def get_option_strikes(
        self,
        expiration: str,
        right: str,  # "P" or "C"
        symbol: str = None,
        near_price: float = None,
        width: int = 200,
    ) -> List[float]:
        """Return available strikes near the current price."""
        symbol = symbol or config.UNDERLYING
        exchange = config.EXCHANGE
        if near_price is None:
            near_price = self.get_underlying_price(symbol)
        contract = Index(symbol, exchange) if symbol == "SPX" else Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        chains = self.ib.reqSecDefOptParams(contract.symbol, "", contract.secType, contract.conId)
        strikes = set()
        for chain in chains:
            if expiration in chain.expirations:
                strikes.update(chain.strikes)
        filtered = sorted(s for s in strikes if abs(s - near_price) <= width)
        return filtered

    def get_option_quote(self, symbol: str, expiration: str, strike: float, right: str) -> dict:
        """Get bid/ask/mid/delta/theta/iv for an option. Uses delayed data."""
        exchange = config.EXCHANGE
        opt = Option(symbol, expiration, strike, right, exchange)
        self.ib.qualifyContracts(opt)
        ticker = self.ib.reqMktData(opt, "", False, False)
        self.ib.sleep(3)
        def _safe(v):
            try:
                f = float(v)
                if f != f:  # NaN check
                    return 0.0
                return f
            except (TypeError, ValueError):
                return 0.0
        result = {
            "bid": _safe(ticker.bid),
            "ask": _safe(ticker.ask),
            "mid": (_safe(ticker.bid) + _safe(ticker.ask)) / 2 if (_safe(ticker.bid) + _safe(ticker.ask)) > 0 else 0,
            "last": _safe(ticker.last),
            "delta": ticker.modelGreeks.delta if ticker.modelGreeks else None,
            "theta": ticker.modelGreeks.theta if ticker.modelGreeks else None,
            "iv":    ticker.modelGreeks.impliedVol if ticker.modelGreeks else None,
            "strike": strike,
            "expiration": expiration,
            "right": right,
        }
        self.ib.cancelMktData(opt)
        return result

    def find_strike_by_delta(
        self, expiration: str, right: str, target_delta: float, symbol: str = None
    ) -> Optional[float]:
        """Find the strike closest to a target delta."""
        symbol = symbol or config.UNDERLYING
        price = self.get_underlying_price(symbol)
        strikes = self.get_option_strikes(expiration, right, symbol, near_price=price, width=300)
        best_strike = None
        best_diff = 999
        for strike in strikes:
            try:
                quote = self.get_option_quote(symbol, expiration, strike, right)
                delta = quote.get("delta")
                if delta is None:
                    continue
                diff = abs(abs(delta) - abs(target_delta))
                if diff < best_diff:
                    best_diff = diff
                    best_strike = strike
            except Exception:
                continue
        return best_strike

    # ─── Orders ───────────────────────────────────────────────────────────────

    def place_combo_order(
        self,
        legs: List[Tuple[int, int, str]],  # [(conId, ratio, action), ...]
        limit_price: float,
        symbol: str = None,
        order_type: str = "LMT",
        qty: int = 1,
        tif: str = "DAY",
        tag: str = "",
    ) -> Optional[object]:
        """
        Place a multi-leg combo order.
        legs = list of (conId, ratio, action) where action = "BUY" or "SELL"
        limit_price = net debit (positive) or credit (negative)
        """
        symbol = symbol or config.UNDERLYING
        exchange = config.EXCHANGE

        combo = Contract()
        combo.symbol = symbol
        combo.secType = "BAG"
        combo.currency = "USD"
        combo.exchange = exchange

        combo_legs = []
        for con_id, ratio, action in legs:
            leg = ComboLeg()
            leg.conId = con_id
            leg.ratio = ratio
            leg.action = action
            leg.exchange = exchange
            combo_legs.append(leg)
        combo.comboLegs = combo_legs

        order = LimitOrder(
            action="BUY",
            totalQuantity=qty,
            lmtPrice=round(limit_price, 2),
            tif=tif,
        )
        order.orderComboLegs = []  # let IBKR compute leg prices

        if config.DRY_RUN:
            log.info(f"[DRY RUN] Would place order: {tag} qty={qty} limit={limit_price}")
            return None

        trade = self.ib.placeOrder(combo, order)
        log.info(f"Placed order [{tag}]: orderId={trade.order.orderId} limit={limit_price}")
        self.ib.sleep(1)
        return trade

    def place_single_order(
        self,
        contract: Contract,
        action: str,
        qty: int,
        limit_price: float,
        tif: str = "DAY",
        tag: str = "",
    ):
        order = LimitOrder(action=action, totalQuantity=qty, lmtPrice=round(limit_price, 2), tif=tif)
        if config.DRY_RUN:
            log.info(f"[DRY RUN] Would place {action} order: {tag} qty={qty} limit={limit_price}")
            return None
        trade = self.ib.placeOrder(contract, order)
        log.info(f"Placed {action} order [{tag}]: orderId={trade.order.orderId}")
        self.ib.sleep(1)
        return trade

    def cancel_order(self, trade):
        if trade and self.ib.isConnected():
            self.ib.cancelOrder(trade.order)
            log.info(f"Cancelled order {trade.order.orderId}")

    # ─── Positions / P&L ─────────────────────────────────────────────────────

    def get_positions(self) -> List[dict]:
        positions = self.ib.positions()
        result = []
        for p in positions:
            result.append({
                "symbol": p.contract.symbol,
                "secType": p.contract.secType,
                "conId": p.contract.conId,
                "strike": getattr(p.contract, "strike", None),
                "right": getattr(p.contract, "right", None),
                "expiration": getattr(p.contract, "lastTradeDateOrContractMonth", None),
                "qty": p.position,
                "avg_cost": p.avgCost,
            })
        return result

    def get_pnl(self) -> dict:
        account_values = self.ib.accountValues()
        pnl = {"daily_pnl": 0.0, "unrealized_pnl": 0.0, "realized_pnl": 0.0}
        for av in account_values:
            if av.tag == "DailyPnL":
                pnl["daily_pnl"] = float(av.value)
            elif av.tag == "UnrealizedPnL":
                pnl["unrealized_pnl"] = float(av.value)
            elif av.tag == "RealizedPnL":
                pnl["realized_pnl"] = float(av.value)
        return pnl

    def qualify(self, contract: Contract) -> Contract:
        self.ib.qualifyContracts(contract)
        return contract
