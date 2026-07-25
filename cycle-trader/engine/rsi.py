from __future__ import annotations
from decimal import Decimal

ZERO = Decimal(0)
HUNDRED = Decimal(100)


def wilder_rsi(closes: list[Decimal], period: int = 14) -> list[Decimal | None]:
    """Wilder-smoothed RSI. Returns a list aligned to `closes`, with None for
    the first `period` entries (insufficient history)."""
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
