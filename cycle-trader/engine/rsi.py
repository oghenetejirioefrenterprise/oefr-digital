from __future__ import annotations
from decimal import Decimal, localcontext
from engine.context import CTX

ZERO = Decimal(0)
HUNDRED = Decimal(100)


def wilder_rsi(closes: list[Decimal], period: int = 14) -> list[Decimal | None]:
    """Wilder-smoothed RSI. Returns a list aligned to `closes`, with None for
    the first `period` entries (insufficient history).

    Runs in the engine's pinned decimal context (`engine/context.py`). Every
    division here is inherently inexact and the output feeds a *strict threshold*
    — `find_triggers`' ``rsi < RSI_TRIGGER`` at 35 — so an ambient precision
    change does not merely blur a number, it can arm an episode on the wrong
    week and start the whole strategy early. Measured on the frozen 780-week
    series: the trigger set is unchanged for prec >= 3 but flips at prec <= 2
    (EP5 moves 2022-05-16 -> 2022-05-09, EP6 2026-01-26 -> 2025-12-22), and the
    tightest real margin to the threshold is only 0.0373 RSI points
    (2012-02-13 @ 35.037), which the accumulated error stays under only from
    prec >= 5. `_rsi_from` deliberately has no pin of its own: it is private and
    reachable only from inside this block, so it inherits.
    """
    with localcontext(CTX):
        out: list[Decimal | None] = [None] * len(closes)
        if len(closes) <= period:
            return out

        gains = losses = ZERO
        for i in range(1, period + 1):
            change = closes[i] - closes[i - 1]
            if change > 0:
                gains += change
            else:
                losses += -change
        avg_gain = gains / period
        avg_loss = losses / period
        out[period] = _rsi_from(avg_gain, avg_loss)

        for i in range(period + 1, len(closes)):
            change = closes[i] - closes[i - 1]
            gain = change if change > 0 else ZERO
            loss = -change if change < 0 else ZERO
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            out[i] = _rsi_from(avg_gain, avg_loss)
        return out


def _rsi_from(avg_gain: Decimal, avg_loss: Decimal) -> Decimal:
    if avg_loss == ZERO:
        return HUNDRED if avg_gain > ZERO else ZERO
    rs = avg_gain / avg_loss
    return HUNDRED - (HUNDRED / (Decimal(1) + rs))
