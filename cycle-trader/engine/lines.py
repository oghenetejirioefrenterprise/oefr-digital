from __future__ import annotations
from decimal import Decimal
from engine.types import OnChain


def lines_for(oc: OnChain) -> tuple[Decimal, Decimal, Decimal]:
    """Return (T1 realized, T2 midpoint, T3 balanced) for a given day.

    SPEC §3. Weights are 1:2:4 across T1:T2:T3 and live in engine/orders.py.
    """
    return (oc.realized, oc.midpoint, oc.balanced)
