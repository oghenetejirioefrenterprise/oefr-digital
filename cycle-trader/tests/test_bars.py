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
    bars = [d("2015-01-25", 1, 2, 0.5, 1),   # Sunday -> belongs to 2015-01-19
            d("2015-01-26", 1, 9, 1, 5)]     # Monday -> new week
    weeks = to_weeks(bars)
    assert [w.monday for w in weeks] == ["2015-01-19", "2015-01-26"]
