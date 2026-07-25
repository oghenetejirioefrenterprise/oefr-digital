from decimal import Decimal
from engine.rsi import wilder_rsi


def test_first_period_values_are_none():
    closes = [Decimal(x) for x in range(1, 20)]
    out = wilder_rsi(closes, period=14)
    assert len(out) == len(closes)
    assert all(v is None for v in out[:14])
    assert out[14] is not None


def test_monotonic_rise_gives_rsi_100():
    closes = [Decimal(x) for x in range(1, 30)]
    out = wilder_rsi(closes, period=14)
    assert out[-1] == Decimal(100)


def test_monotonic_fall_gives_rsi_0():
    closes = [Decimal(30 - x) for x in range(0, 29)]
    out = wilder_rsi(closes, period=14)
    assert out[-1] == Decimal(0)


def test_rsi_stays_within_0_and_100():
    closes = [Decimal(100)]
    for i in range(40):
        closes.append(closes[-1] + (Decimal(3) if i % 3 else Decimal(-2)))
    assert all(v is None or Decimal(0) <= v <= Decimal(100) for v in wilder_rsi(closes))


def test_balanced_series_lands_near_50():
    """Alternating +1/-1 gives ~48.4, not exactly 50 — Wilder's seed period is
    a simple average, so the first window skews the smoothing slightly."""
    closes = [Decimal(100)]
    for i in range(40):
        closes.append(closes[-1] + (Decimal(1) if i % 2 == 0 else Decimal(-1)))
    assert Decimal(45) < wilder_rsi(closes)[-1] < Decimal(55)


def test_flat_series_returns_zero_not_fifty():
    """Edge case pinned deliberately: with no gains AND no losses this
    implementation returns 0 (conventionally RSI is undefined here). Harmless
    for CY-1 — weekly BTC closes are never flat — but pinned so a future
    refactor cannot change it silently."""
    assert wilder_rsi([Decimal(100)] * 30)[-1] == Decimal(0)
