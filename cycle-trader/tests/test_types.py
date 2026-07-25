from decimal import Decimal
import pytest
from engine.types import Bar, DesiredOrder, OrderPurpose, OrderSide, OrderKind


def test_bar_is_immutable_and_decimal():
    b = Bar(date="2015-01-26", open=Decimal("290"), high=Decimal("309.90"),
            low=Decimal("285"), close=Decimal("300"))
    assert b.high == Decimal("309.90")
    with pytest.raises(Exception):
        b.high = Decimal("1")


def test_bar_from_json_row_converts_to_decimal():
    row = {"date": "2020-03-16", "o": 5360.33, "h": 5365.42,
           "l": 4442.12, "c": 5028.97, "src": "binance"}
    b = Bar.from_json(row)
    assert b.open == Decimal("5360.33")
    assert isinstance(b.low, Decimal)


def test_desired_order_identity_is_purpose():
    o = DesiredOrder(purpose=OrderPurpose.T1, side=OrderSide.BUY,
                     kind=OrderKind.LIMIT, price=Decimal("52848"),
                     units=Decimal("1"))
    assert o.purpose is OrderPurpose.T1
    assert o.side is OrderSide.BUY
