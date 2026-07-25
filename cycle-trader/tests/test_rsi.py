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


# Wilder's own worked example from "New Concepts in Technical Trading Systems"
# (1978) — the 33-close series reproduced in the standard published RSI table.
CANONICAL_CLOSES = [
    "44.34", "44.09", "44.15", "43.61", "44.33", "44.83", "45.10", "45.42",
    "45.84", "46.08", "45.89", "46.03", "45.61", "46.28", "46.28", "46.00",
    "46.03", "46.41", "46.22", "45.64", "46.21", "46.25", "45.71", "46.45",
    "45.78", "45.35", "44.03", "44.18", "44.22", "44.57", "43.42", "42.66",
    "43.13",
]


def test_matches_wilders_canonical_worked_example():
    """Pins the smoothing arithmetic against Wilder's published RSI table.

    This is the ONLY test standing between this function and an undetected EMA
    substitution. The other five check structure — alignment, bounds, monotonic
    extremes — and a review found that four of five plausible corruptions slip
    past all of them: EMA alpha=2/15 instead of Wilder's 1/14 (balanced series
    ends ~46.4), a plain SMA of gains/losses (ends exactly 50.0), a seed over 13
    changes instead of 14, and a seed divided by period+1 (which scales both
    averages equally, leaving RS untouched). Every one of those lands inside the
    ten-point-wide 45-55 window that test_balanced_series_lands_near_50 allows.

    Exact published values leave no such room. Asserted to 2dp because the
    published table is quoted to 2dp; the implementation carries full Decimal
    precision underneath.
    """
    out = wilder_rsi([Decimal(x) for x in CANONICAL_CLOSES], period=14)
    two_dp = Decimal("0.01")
    assert out[14].quantize(two_dp) == Decimal("70.46")  # first real value
    assert out[15].quantize(two_dp) == Decimal("66.25")
    assert out[16].quantize(two_dp) == Decimal("66.48")
    assert out[-1].quantize(two_dp) == Decimal("37.79")


def test_seed_window_covers_exactly_period_changes():
    """Pins the seed window at 14 changes, which the canonical test cannot.

    Wilder's published series has closes[13] == closes[14] == 46.28, so its
    14th change is exactly zero and a seed built from only 13 changes drops a
    term worth nothing — every canonical value survives that corruption intact.
    Verified by mutation: `range(1, period)` leaves the whole rest of this file
    green.

    So this series puts all the weight on the boundary change. Thirteen rises of
    +1 followed by a single -13: a correct 14-change seed sees gains == losses
    == 13, giving RS == 1 and exactly 50. A 13-change seed never sees the drop,
    so avg_loss is 0 and it returns 100. 50 vs 100 — no rounding tolerance
    needed.
    """
    closes = [Decimal(100)]
    for _ in range(13):
        closes.append(closes[-1] + Decimal(1))
    closes.append(closes[-1] - Decimal(13))
    assert len(closes) == 15
    assert wilder_rsi(closes, period=14)[14] == Decimal(50)
