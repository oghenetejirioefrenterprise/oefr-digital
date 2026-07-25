import dataclasses
from decimal import Decimal, Inexact, ROUND_FLOOR, localcontext

import pytest

from engine.context import CTX
from engine.lines import lines_for

from engine.types import (
    Bar,
    DesiredOrder,
    EngineResult,
    EpisodeState,
    EpisodeStatus,
    OnChain,
    OrderKind,
    OrderPurpose,
    OrderSide,
    Week,
)


# --------------------------------------------------------------------------
# Bar
# --------------------------------------------------------------------------


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
    assert b.date == "2020-03-16"
    assert b.open == Decimal("5360.33")
    assert isinstance(b.low, Decimal)


def test_bar_from_json_strips_time_component():
    row = {"date": "2020-03-16T00:00:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5}
    assert Bar.from_json(row).date == "2020-03-16"


def test_bar_coerces_raw_floats_to_exact_decimal():
    """Q-1: hand-built Bars must not silently retain floats.

    Later tasks hand-build Bar fixtures. A stored float compares False
    against the Decimal the engine produces, and does so silently.
    """
    b = Bar(date="2020-03-16", open=290.0, high=5365.42, low=4442.12, close=5028.97)
    assert isinstance(b.open, Decimal)
    assert b.open == Decimal("290")
    assert b.high == Decimal("5365.42")
    assert b.close == Decimal("5028.97")


def test_bar_coerces_ints_and_strings():
    b = Bar(date="2020-03-16", open=290, high="309.90", low=285, close=300)
    assert b.open == Decimal("290")
    assert b.high == Decimal("309.90")
    assert isinstance(b.close, Decimal)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"),
                                 Decimal("NaN"), Decimal("Infinity")])
def test_non_finite_prices_are_rejected(bad):
    """Q-2: NaN compares False under == but raises under < and min()."""
    with pytest.raises(ValueError, match="finite"):
        Bar(date="2020-03-16", open=bad, high=Decimal("1"),
            low=Decimal("1"), close=Decimal("1"))


@pytest.mark.parametrize("bad", ["16/03/2020", "16/03/2020extra", "2020-3-6",
                                 "not-a-date", "", "20200316"])
def test_non_iso_dates_are_rejected(bad):
    """Q-3: [:10] truncates rather than parses, producing a dict key that
    never matches and a day that silently has no accumulation line."""
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        Bar(date=bad, open=Decimal("1"), high=Decimal("1"),
            low=Decimal("1"), close=Decimal("1"))


def test_bar_from_json_rejects_non_iso_date():
    row = {"date": "16/03/2020extra", "o": 1, "h": 1, "l": 1, "c": 1}
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        Bar.from_json(row)


# --------------------------------------------------------------------------
# Week
# --------------------------------------------------------------------------


def test_week_coerces_floats_and_is_frozen():
    w = Week(monday="2020-03-16", high=6000.0, low=4442.12, close=5028.97)
    assert w.monday == "2020-03-16"
    assert w.high == Decimal("6000")
    assert w.low == Decimal("4442.12")
    with pytest.raises(dataclasses.FrozenInstanceError):
        w.close = Decimal("1")


def test_week_rejects_non_iso_monday():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        Week(monday="03/16/2020", high=Decimal("1"), low=Decimal("1"),
             close=Decimal("1"))


# --------------------------------------------------------------------------
# OnChain
# --------------------------------------------------------------------------


def test_onchain_midpoint_is_exact_decimal_average():
    oc = OnChain(date="2026-07-23", realized=Decimal("20000"),
                 balanced=Decimal("14702"))
    assert oc.midpoint == Decimal("17351")
    assert isinstance(oc.midpoint, Decimal)


def test_onchain_midpoint_after_float_coercion():
    """The midpoint is the only computed logic in the module; it must stay
    exact even when the JSON boundary handed us floats."""
    oc = OnChain(date="2026-07-23", realized=52848.35, balanced=38845.65)
    assert oc.midpoint == Decimal("45847")


def test_onchain_is_frozen():
    oc = OnChain(date="2026-07-23", realized=Decimal("1"), balanced=Decimal("1"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        oc.realized = Decimal("2")


# --------------------------------------------------------------------------
# DesiredOrder  (Q-4: replaces the tautological identity test)
# --------------------------------------------------------------------------


def test_desired_order_coerces_price_and_units_and_is_frozen():
    o = DesiredOrder(purpose=OrderPurpose.T1, side=OrderSide.BUY,
                     kind=OrderKind.LIMIT, price=52848.35, units=1)
    assert o.price == Decimal("52848.35")
    assert isinstance(o.units, Decimal)
    with pytest.raises(dataclasses.FrozenInstanceError):
        o.price = Decimal("1")


def test_desired_order_allows_null_price_for_market_orders():
    """Breakouts and the stop are market orders; price stays optional and
    must not be coerced into Decimal('None')."""
    o = DesiredOrder(purpose=OrderPurpose.BREAKOUT, side=OrderSide.BUY,
                     kind=OrderKind.MARKET, price=None, units=Decimal("1"))
    assert o.price is None


def test_purpose_is_the_reconciler_dedupe_key():
    """The desired-state reconciler keys resting orders by purpose, so a
    purpose must be hashable and must collapse two orders onto one slot."""
    a = DesiredOrder(purpose=OrderPurpose.T1, side=OrderSide.BUY,
                     kind=OrderKind.LIMIT, price=Decimal("52848"),
                     units=Decimal("1"))
    b = DesiredOrder(purpose=OrderPurpose.T1, side=OrderSide.BUY,
                     kind=OrderKind.LIMIT, price=Decimal("51000"),
                     units=Decimal("1"))
    c = DesiredOrder(purpose=OrderPurpose.T2, side=OrderSide.BUY,
                     kind=OrderKind.LIMIT, price=Decimal("48000"),
                     units=Decimal("1"))
    book = {o.purpose: o for o in (a, b, c)}
    assert len(book) == 2
    assert book[OrderPurpose.T1] is b
    assert book[OrderPurpose.T2] is c


def test_order_enum_wire_values_are_stable():
    """These strings are persisted and compared against exchange-side
    state; renaming a value silently orphans resting orders."""
    assert [p.value for p in OrderPurpose] == [
        "T1", "T2", "T3", "LADDER_050", "LADDER_062", "LADDER_0786",
        "BREAKOUT", "EXIT1", "MIRROR", "STOP",
    ]
    assert [s.value for s in OrderSide] == ["buy", "sell"]
    assert [k.value for k in OrderKind] == ["limit", "stop_market", "market"]


# --------------------------------------------------------------------------
# EpisodeState / EngineResult / EpisodeStatus
# --------------------------------------------------------------------------


def test_episode_status_wire_values_are_stable():
    assert [s.value for s in EpisodeStatus] == [
        "idle", "watching", "confirmed", "distributing",
        "closed", "expired", "stopped",
    ]


def test_episode_state_defaults_to_idle_and_empty():
    s = EpisodeState()
    assert s.status is EpisodeStatus.IDLE
    assert s.trigger_date is None
    assert s.prior_ath is None
    assert s.operative_lh is None
    assert s.exit1_done is False


def test_episode_state_is_frozen():
    """Task 14 treats state as an immutable value carried across runs; a
    refactor dropping frozen=True would break at maximum cost."""
    s = EpisodeState()
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.status = EpisodeStatus.CLOSED


def test_episode_state_replace_returns_new_state_and_coerces():
    s = EpisodeState(status=EpisodeStatus.WATCHING, trigger_date="2026-01-05")
    t = dataclasses.replace(s, status=EpisodeStatus.CONFIRMED,
                            operative_lh=52848.35)
    assert s.status is EpisodeStatus.WATCHING
    assert s.operative_lh is None
    assert t.status is EpisodeStatus.CONFIRMED
    assert t.trigger_date == "2026-01-05"
    assert t.operative_lh == Decimal("52848.35")
    assert isinstance(t.operative_lh, Decimal)


def test_episode_state_rejects_non_iso_dates():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        EpisodeState(trigger_date="05/01/2026")


def test_engine_result_holds_state_and_orders_and_is_frozen():
    o = DesiredOrder(purpose=OrderPurpose.T1, side=OrderSide.BUY,
                     kind=OrderKind.LIMIT, price=Decimal("52848"),
                     units=Decimal("1"))
    r = EngineResult(state=EpisodeState(), orders=(o,))
    assert r.state.status is EpisodeStatus.IDLE
    assert r.orders == (o,)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.orders = ()


def test_midpoint_is_independent_of_the_ambient_decimal_context():
    """`OnChain.midpoint` is the T2 accumulation line -- a **fill price**, handed
    straight to the buy-limit primitive by `lines_for`, not a display value. Its
    division is inexact, so an ambient precision change moves a price the
    strategy actually trades at: on EP3's real fill day (2018-11-26) the midpoint
    is 4502.886081702271637464274772, and it deviates by 3e-7 at prec 10, 0.006
    at prec 6 and 0.114 at prec 4 -- ambient-dependent over a wider window than
    any other computation in the engine.

    This module was wrongly cleared in `engine/context.py`'s audit as
    construction-only until 2026-07-25; `_dec` is indeed context-free, but
    `midpoint` computes. engine/context.py pins it; this test fails if that pin
    is removed.

    Inputs carry 28 significant digits deliberately -- that is what the real
    CoinMetrics-derived series looks like, because `data/loaders.py` derives
    realized price by an unpinned division at the ambient default. The quotient
    therefore needs 28 digits, far more than the hostile precision below, so
    precision is genuinely observable; round two-decimal inputs would pass
    unpinned. (It terminates at 28 rather than saturating `CTX.prec`, so the
    exact value is asserted directly and holds for any pin >= 29.)
    """
    oc = OnChain(date="2018-11-26",
                 realized=Decimal("5138.427551844371825042817368"),
                 balanced=Decimal("3867.344611560171449885732176"))
    expected = oc.midpoint
    assert expected == Decimal("4502.886081702271637464274772")
    assert len(expected.as_tuple().digits) == 28 <= CTX.prec

    with localcontext() as ctx:
        ctx.prec = 4
        ctx.rounding = ROUND_FLOOR
        ctx.traps[Inexact] = True
        assert oc.midpoint == expected
        # lines_for must carry the pinned value through, not recompute it
        assert lines_for(oc)[1] == expected
