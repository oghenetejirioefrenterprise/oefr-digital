from decimal import Decimal
from engine.bars import to_weeks, monday_of
from engine.types import Bar


def d(date, o, h, l, c):
    return Bar(date, Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def test_monday_of_anchors_to_iso_monday():
    # 2015-01-26 is a Monday; 2015-02-01 is the Sunday that ends that week
    assert monday_of("2015-01-26") == "2015-01-26"
    assert monday_of("2015-02-01") == "2015-01-26"
    assert monday_of("2015-01-05") == "2015-01-05"
    assert monday_of("2015-01-11") == "2015-01-05"


def test_monday_of_crosses_year_and_leap_boundaries():
    """Pin the Sunday-label -> Monday-label conversion where it has actually bitten.

    The reference datasets label weeks by Sunday close, this codebase by ISO
    Monday. Every one of these cases is a Sunday resolving back to a Monday in
    a different month, and two of them in a different *year*. An implementation
    reaching for ``isocalendar()``/``fromisocalendar()`` or ``strftime("%W")``
    regresses here while the in-month 2015 cases above stay green.
    """
    # 2021-01-03 is the Sunday of ISO 2020-W53 -> its Monday is in the prior year.
    assert monday_of("2021-01-03") == "2020-12-28"
    # 2015-01-01 is a Thursday; its ISO week opened in the prior year.
    assert monday_of("2015-01-01") == "2014-12-29"
    # 2020-03-01 is a Sunday; walking back six days crosses the 29 Feb leap day.
    assert monday_of("2020-03-01") == "2020-02-24"


def test_week_high_is_max_of_daily_highs_low_is_min_of_daily_lows():
    bars = [
        d("2015-01-26", 285, 300, 280, 295),
        d("2015-01-27", 295, 309.90, 290, 300),
        d("2015-02-01", 300, 305, 275, 280),
    ]
    weeks = to_weeks(bars)
    assert len(weeks) == 1
    assert weeks[0].monday == "2015-01-26"
    assert weeks[0].high == Decimal("309.90")
    assert weeks[0].low == Decimal("275")
    assert weeks[0].close == Decimal("280")  # close of the LAST day in the week


def test_weeks_are_ordered_and_split_on_monday_boundary():
    # Supplied newest-first, so the returned ordering is genuinely exercised
    # rather than inherited from the input.
    bars = [d("2015-01-26", 1, 9, 1, 5),     # Monday -> new week
            d("2015-01-25", 1, 2, 0.5, 1)]   # Sunday -> belongs to 2015-01-19
    weeks = to_weeks(bars)
    assert [w.monday for w in weeks] == ["2015-01-19", "2015-01-26"]


def test_week_close_is_the_chronologically_last_day_not_the_last_supplied():
    """Defends the ``sorted()`` in ``to_weeks``.

    ``close = group[-1].close`` only means "last *day* of the week" because the
    bars were sorted on the way into the bucket. Fed newest-first, an unsorted
    implementation would return Monday's 295 instead of Friday's 280 — and every
    other assertion in this file would still pass, because high/low are
    order-independent and the other fixtures are already in date order.
    """
    bars = [
        d("2015-01-30", 300, 305, 275, 280),   # Friday: the true weekly close
        d("2015-01-28", 295, 309.90, 290, 999),
        d("2015-01-26", 285, 300, 280, 295),   # Monday: first day, supplied last
    ]
    weeks = to_weeks(bars)
    assert len(weeks) == 1
    assert weeks[0].close == Decimal("280")
    # high/low are order-independent, and stay correct either way
    assert weeks[0].high == Decimal("309.90")
    assert weeks[0].low == Decimal("275")
