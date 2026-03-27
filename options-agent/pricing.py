"""
pricing.py — Theoretical option pricing via Black-Scholes.
Uses IV from IBKR + historical vol as fallback. No live data subscription needed.
"""

import math
from datetime import datetime, date
from typing import Optional, Tuple

from ib_insync import IB, Index, Stock, Option

import config
from broker import IBKRBroker

log = __import__("logging").getLogger("pricing")


def _norm_cdf(x: float) -> float:
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes(
    S: float,       # underlying price
    K: float,       # strike
    T: float,       # time to expiry in years
    sigma: float,   # IV (decimal, e.g. 0.15 for 15%)
    r: float = 0.05,
    right: str = "P",
) -> dict:
    """
    Compute Black-Scholes price + Greeks for an option.
    Returns dict with price, delta, gamma, theta, vega.
    """
    if T <= 0.001:
        T = 0.001

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if right == "C":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        delta = _norm_cdf(d1)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = _norm_cdf(d1) - 1

    gamma = _norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * _norm_pdf(d1) * math.sqrt(T) / 100  # per 1% vol

    if right == "C":
        theta = (
            -S * _norm_pdf(d1) * sigma / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * _norm_cdf(d2)
        ) / 365
    else:
        theta = (
            -S * _norm_pdf(d1) * sigma / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T) * _norm_cdf(-d2)
        ) / 365

    return {
        "price": max(price, 0),
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "iv": sigma,
        "strike": K,
        "right": right,
    }


def get_strike_from_delta(
    broker: IBKRBroker,
    S: float,
    T: float,
    sigma: float,
    target_delta: float,
    right: str = "P",
) -> float:
    """
    Find the strike whose BS delta is closest to target_delta.
    target_delta is negative for puts (e.g. -0.10 for 10-delta put).
    """
    best_strike = S
    best_diff = 999

    # Search in a wide range
    for k_mult in range(-30, 30):
        K = S + k_mult * 5  # 5-pt increments for SPX
        greeks = black_scholes(S, K, T, sigma, right=right)
        d = greeks["delta"]
        diff = abs(d - target_delta)
        if diff < best_diff:
            best_diff = diff
            best_strike = K

    return round(best_strike / 5) * 5  # round to nearest 5


def get_broker_iv(broker: IBKRBroker, symbol: str = None) -> float:
    """
    Get current IV from IBKR. Uses historical data endpoint (no live subscription).
    Falls back to HV30 if IV unavailable.
    """
    symbol = symbol or config.UNDERLYING
    try:
        contract = Index(symbol, "CBOE") if symbol == "SPX" else Stock(symbol, "SMART", "USD")
        broker.ib.qualifyContracts(contract)
        bars = broker.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="30 D",
            barSizeSetting="1 day",
            whatToShow="OPTION_IMPLIED_VOLATILITY",
            useRTH=True,
        )
        if bars:
            ivs = [b.close for b in bars if b.close and b.close > 0]
            if ivs:
                avg = sum(ivs[-5:]) / min(len(ivs), 5)  # last 5 days
                log.info(f"IV from IBKR: {avg:.4f} ({avg*100:.1f}%)")
                return avg
    except Exception as e:
        log.warning(f"IV fetch failed: {e}")

    # Fallback: use HV30
    try:
        bars = broker.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="60 D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
        )
        if bars and len(bars) > 5:
            returns = [math.log(bars[i].close / bars[i-1].close)
                       for i in range(1, len(bars)) if bars[i].close > 0 and bars[i-1].close > 0]
            if returns:
                import statistics
                hv = statistics.stdev(returns[-30:]) * math.sqrt(252)
                log.info(f"HV30 fallback: {hv:.4f} ({hv*100:.1f}%)")
                return hv
    except Exception as e:
        log.warning(f"HV30 calculation failed: {e}")

    log.warning("Using default IV: 0.20")
    return 0.20


def dte_to_years(dte: int) -> float:
    return dte / 365.0
