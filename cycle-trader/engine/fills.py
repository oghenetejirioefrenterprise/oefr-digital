"""The four direction-aware fill primitives — SPEC §13.2.

Buy-limit  : touch = low  <= level, fill = min(level, open)
Buy-stop   : touch = high >= level, fill = max(level, open)
Sell-limit : touch = high >= level, fill = max(level, open)
Sell-stop  : touch = low  <= level, fill = min(level, open)
"""
from __future__ import annotations
from decimal import Decimal
from engine.types import Bar


def buy_limit_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.low > level:
        return None
    return min(level, bar.open)


def buy_stop_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.high < level:
        return None
    return max(level, bar.open)


def sell_limit_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.high < level:
        return None
    return max(level, bar.open)


def sell_stop_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.low > level:
        return None
    return min(level, bar.open)
