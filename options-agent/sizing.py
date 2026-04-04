"""
sizing.py — Dynamic Position Sizing
Replaces fixed qty with risk-based sizing.
Risk per trade = capital * max_risk_pct.
Max loss per contract = (spread_width - credit) * 100.
qty = floor(risk_per_trade / max_loss_per_contract), clamped [1, 5].
"""

import math
import logging

from econ_calendar import get_sizing_multiplier

log = logging.getLogger("sizing")


def calculate_position_size(
    capital: float,
    max_risk_pct: float,
    spread_width: float,
    credit_received: float,
    volume_sizing_multiplier: float = 1.0,
    trend_sizing_multiplier: float = 1.0,
) -> int:
    """
    Calculate number of contracts based on risk budget.
    Automatically reduces sizing on high-impact economic event days (FOMC, CPI, NFP, PCE).
    Applies volume-based and trend-based sizing adjustments when provided.

    Args:
        capital: Account capital in dollars (e.g. 5000)
        max_risk_pct: Max risk per trade as decimal (e.g. 0.02 = 2%)
        spread_width: Width of spread in points (e.g. 10 for a 10pt spread)
        credit_received: Credit received per share (e.g. 0.50 for $50 credit)
            For debit strategies, pass 0 and use net_debit as spread_width.
        volume_sizing_multiplier: Volume-based sizing adjustment (0.5-1.5, default 1.0)
        trend_sizing_multiplier: Trend day sizing adjustment (0.5-1.0, default 1.0)

    Returns:
        Number of contracts to trade (min 1, max 5)
    """
    # Apply economic calendar multiplier (0.5 on event days, 1.0 otherwise)
    econ_mult = get_sizing_multiplier()
    risk_per_trade = capital * max_risk_pct * econ_mult
    max_loss_per_contract = (spread_width - credit_received) * 100  # SPX multiplier

    if max_loss_per_contract <= 0:
        log.warning(
            f"Max loss per contract <= 0 (width={spread_width}, credit={credit_received}) — using qty=1"
        )
        return 1

    # Apply volume-based sizing multiplier (clamped to 0.5-1.5)
    vol_mult = max(0.5, min(volume_sizing_multiplier, 1.5))
    risk_per_trade *= vol_mult

    # Apply trend day sizing multiplier (clamped to 0.5-1.0)
    trend_mult = max(0.5, min(trend_sizing_multiplier, 1.0))
    risk_per_trade *= trend_mult

    qty = math.floor(risk_per_trade / max_loss_per_contract)
    qty = max(1, min(qty, 5))  # floor 1, cap 5

    notes = []
    if econ_mult < 1.0:
        notes.append(f"econ_mult={econ_mult}")
    if vol_mult != 1.0:
        notes.append(f"vol_mult={vol_mult:.2f}")
    if trend_mult != 1.0:
        notes.append(f"trend_mult={trend_mult:.2f}")
    note_str = f" [{', '.join(notes)}]" if notes else ""
    log.info(
        f"Position size: capital=${capital:.0f} risk={max_risk_pct*100:.1f}% "
        f"risk_budget=${risk_per_trade:.0f} max_loss/contract=${max_loss_per_contract:.0f} → qty={qty}{note_str}"
    )
    return qty
