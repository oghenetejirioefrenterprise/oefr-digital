from decimal import Decimal
from engine.fills import buy_limit_fill, buy_stop_fill, sell_limit_fill, sell_stop_fill
from engine.types import Bar


def bar(o, h, l, c="0"):
    return Bar("2020-01-01", Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def test_buy_limit_no_touch_returns_none():
    assert buy_limit_fill(bar(100, 110, 95), Decimal("90")) is None


def test_buy_limit_touch_fills_at_level():
    assert buy_limit_fill(bar(100, 110, 85), Decimal("90")) == Decimal("90")


def test_buy_limit_gap_open_below_level_fills_at_open():
    """SPEC §3: if the day opens below the line, fill at the open."""
    assert buy_limit_fill(bar(80, 95, 70), Decimal("90")) == Decimal("80")


def test_buy_stop_fills_at_level_on_break_up():
    assert buy_stop_fill(bar(300, 310, 295), Decimal("309.90")) == Decimal("309.90")


def test_buy_stop_gap_open_above_level_fills_at_open():
    """Cannot buy below the breakout price when the day opens above it."""
    assert buy_stop_fill(bar(320, 330, 315), Decimal("309.90")) == Decimal("320")


def test_buy_stop_no_touch_returns_none():
    assert buy_stop_fill(bar(300, 305, 295), Decimal("309.90")) is None


def test_sell_limit_fills_at_level_on_rally():
    assert sell_limit_fill(bar(80000, 84000, 79000), Decimal("83558.53")) == Decimal("83558.53")


def test_sell_limit_gap_open_above_level_fills_at_open():
    assert sell_limit_fill(bar(85000, 86000, 84000), Decimal("83558.53")) == Decimal("85000")


def test_sell_stop_fills_at_level_on_breakdown():
    assert sell_stop_fill(bar(16000, 16500, 15000), Decimal("15476")) == Decimal("15476")


def test_sell_stop_gap_open_below_level_fills_at_open():
    assert sell_stop_fill(bar(15000, 15200, 14000), Decimal("15476")) == Decimal("15000")


def test_verified_ep4_gap_day_reproduces_all_three_tranches():
    """2020-03-16: open 5360.33, lines 5566.46 / 5135.22 / 4703.98."""
    b = bar("5360.33", "5365.42", "4442.12")
    assert buy_limit_fill(b, Decimal("5566.46")) == Decimal("5360.33")
    assert buy_limit_fill(b, Decimal("5135.22")) == Decimal("5135.22")
    assert buy_limit_fill(b, Decimal("4703.98")) == Decimal("4703.98")
