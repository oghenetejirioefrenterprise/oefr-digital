from decimal import Decimal, localcontext

import pytest

from engine.context import CTX
from engine.levels import LADDER_UNITS
from engine.orders import ACC_UNITS, desired_orders, roll_unfilled
from engine.types import (DesiredOrder, EpisodeState, EpisodeStatus, OrderKind,
                          OrderPurpose, OrderSide)


def test_watching_state_rests_three_accumulation_limit_buys():
    state = EpisodeState(status=EpisodeStatus.WATCHING, trigger_date="2026-02-02")
    lines = {"t1": Decimal("52848"), "t2": Decimal("45849"), "t3": Decimal("38851")}
    orders = desired_orders(state, lines, filled_purposes=set(),
                            held_units=Decimal(0))
    assert {o.purpose for o in orders} == {OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3}
    assert all(o.side is OrderSide.BUY and o.kind is OrderKind.LIMIT for o in orders)
    units = {o.purpose: o.units for o in orders}
    assert units[OrderPurpose.T1] == Decimal(1)
    assert units[OrderPurpose.T2] == Decimal(2)
    assert units[OrderPurpose.T3] == Decimal(4)


def test_filled_tranches_are_not_re_rested():
    state = EpisodeState(status=EpisodeStatus.WATCHING, trigger_date="2022-05-23")
    lines = {"t1": Decimal("23188"), "t2": Decimal("21437"), "t3": Decimal("19685")}
    orders = desired_orders(state, lines, filled_purposes={OrderPurpose.T1},
                            held_units=Decimal(1))
    assert OrderPurpose.T1 not in {o.purpose for o in orders}


def test_confirmed_state_rests_ladder_stop_breakout_and_exit1():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), bos_date="2015-01-28",
                         prior_ath=Decimal("1163.00"))
    orders = desired_orders(state, lines={},
                            filled_purposes={OrderPurpose.T1, OrderPurpose.T2,
                                             OrderPurpose.T3},
                            held_units=Decimal(7))
    purposes = {o.purpose for o in orders}
    assert {OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
            OrderPurpose.LADDER_0786, OrderPurpose.STOP,
            OrderPurpose.BREAKOUT, OrderPurpose.EXIT1} <= purposes
    stop = next(o for o in orders if o.purpose is OrderPurpose.STOP)
    assert stop.side is OrderSide.SELL and stop.kind is OrderKind.STOP_MARKET
    assert stop.price == Decimal("152.40")
    assert stop.units == Decimal(7)          # held units, NOT total_units
    ex1 = next(o for o in orders if o.purpose is OrderPurpose.EXIT1)
    assert ex1.side is OrderSide.SELL and ex1.kind is OrderKind.LIMIT
    assert abs(ex1.price - Decimal("1437.88")) < Decimal("0.01")   # G1's Exit 1
    assert ex1.units == Decimal("3.5")       # half the held units
    brk = next(o for o in orders if o.purpose is OrderPurpose.BREAKOUT)
    assert brk.kind is OrderKind.STOP_MARKET and brk.price == Decimal("309.90")


def test_no_stop_and_no_exit1_while_nothing_is_held():
    """A sell for units the account doesn't hold is an invalid order."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), bos_date="2026-09-01",
                         prior_ath=Decimal("126200"))
    orders = desired_orders(state, lines={}, filled_purposes=set(),
                            held_units=Decimal(0))
    purposes = {o.purpose for o in orders}
    assert OrderPurpose.STOP not in purposes
    assert OrderPurpose.EXIT1 not in purposes


def test_watching_state_has_no_stop_order():
    """SPEC §13.1: the stop only exists from the BoS onward."""
    state = EpisodeState(status=EpisodeStatus.WATCHING, running_low=Decimal("57800"))
    orders = desired_orders(state, {"t1": Decimal("1"), "t2": Decimal("1"),
                                    "t3": Decimal("1")}, filled_purposes=set(),
                            held_units=Decimal(3))
    assert OrderPurpose.STOP not in {o.purpose for o in orders}


def test_closed_state_rests_nothing():
    for status in (EpisodeStatus.CLOSED, EpisodeStatus.STOPPED, EpisodeStatus.EXPIRED):
        assert desired_orders(EpisodeState(status=status), {}, set(),
                              held_units=Decimal(21)) == ()


def test_oq3_roll_sends_unfilled_accumulation_to_the_ladder_in_2_4_8():
    """Owner 2026-07-24. All 7 accumulation units unfilled -> ladder pool
    becomes 14 + 7 = 21 units, still split 2:4:8."""
    pool = roll_unfilled(acc_unfilled_units=Decimal(7), ladder_units=Decimal(14))
    assert sum(pool.values()) == Decimal(21)
    assert pool["0.5"] == Decimal(21) * Decimal(2) / Decimal(14)
    assert pool["0.62"] == Decimal(21) * Decimal(4) / Decimal(14)
    assert pool["0.786"] == Decimal(21) * Decimal(8) / Decimal(14)


def test_oq3_roll_with_nothing_unfilled_leaves_the_ladder_untouched():
    pool = roll_unfilled(acc_unfilled_units=Decimal(0), ladder_units=Decimal(14))
    assert pool["0.5"] == Decimal(2)
    assert pool["0.62"] == Decimal(4)
    assert pool["0.786"] == Decimal(8)


# --- additions beyond the brief -------------------------------------------
#
# This module is the only place where a computed number becomes an instruction
# to spend money, so the tests below are weighted towards the ways a *plausible*
# desired set is nonetheless an unsafe one.


# --- the inverted-leg guard (the hazard this task exists to close) ---------

def test_inverted_bos_leg_refuses_instead_of_emitting_self_executing_buys():
    """bos_week_high <= el_star puts every ladder level ABOVE the BoS high.

    engine.levels.ladder_levels is deliberately unguarded arithmetic:
    ladder_levels(100000, 90000) returns 95,000 / 96,200 / 97,860 without
    complaint. At M5 those are resting BUY-LIMITS, and a buy-limit above market
    fills immediately at market. The ordering is guaranteed by correct upstream
    state and the gates catch a violation on historical data, but a bad live
    print in 2027 reaches this function first.
    """
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("100000"),
                         bos_week_high=Decimal("90000"), prior_ath=Decimal("126200"))
    with pytest.raises(ValueError, match="inverted"):
        desired_orders(state, {}, set(), held_units=Decimal(7))


def test_degenerate_zero_length_leg_is_also_refused():
    """A zero leg collapses all three rungs onto the BoS high AND onto the
    stop. Equality is not a harmless boundary here, so the guard is strict."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("82850"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    with pytest.raises(ValueError, match="inverted"):
        desired_orders(state, {}, set(), held_units=Decimal(7))


def test_a_healthy_leg_by_one_tick_is_accepted():
    """The guard rejects only the inversion, not tight legs."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("82850"),
                         bos_week_high=Decimal("82850.01"), prior_ath=Decimal("126200"))
    orders = desired_orders(state, {}, set(), held_units=Decimal(0))
    assert OrderPurpose.LADDER_050 in {o.purpose for o in orders}


def test_every_ladder_level_sits_below_the_breakout_price():
    """The property the guard protects, asserted on the emitted set."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    orders = desired_orders(state, {}, set(), held_units=Decimal(0))
    brk = next(o for o in orders if o.purpose is OrderPurpose.BREAKOUT)
    rungs = [o for o in orders if o.purpose in (OrderPurpose.LADDER_050,
                                                OrderPurpose.LADDER_062,
                                                OrderPurpose.LADDER_0786)]
    assert len(rungs) == 3
    assert all(o.price < brk.price for o in rungs)
    assert all(o.price > state.el_star for o in rungs)


def test_exit1_anchor_at_or_below_el_star_is_refused():
    """Same hazard, sell side: a 1.272 extension priced at or under EL* is a
    sell-limit below market, which fills instantly at max(level, open)."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("57800"))
    with pytest.raises(ValueError, match="exit anchor"):
        desired_orders(state, {}, set(), held_units=Decimal(7))


def test_confirmed_without_anchors_refuses_rather_than_dropping_the_stop():
    """An empty/partial desired set means CANCEL to the reconciler. Silently
    omitting the stop would disarm the only protection CY-1 has."""
    for bad in (EpisodeState(status=EpisodeStatus.CONFIRMED,
                             bos_week_high=Decimal("309.90")),
                EpisodeState(status=EpisodeStatus.CONFIRMED,
                             el_star=Decimal("152.40"))):
        with pytest.raises(ValueError, match="el_star|bos_week_high"):
            desired_orders(bad, {}, set(), held_units=Decimal(7))


def test_confirmed_without_prior_ath_refuses_once_units_are_held():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"))
    with pytest.raises(ValueError, match="prior_ath"):
        desired_orders(state, {}, set(), held_units=Decimal(7))


def test_confirmed_without_prior_ath_is_fine_while_nothing_is_held():
    """Exit 1 is not wanted at all with a flat account, so its anchor is not
    yet required — the ladder and breakout still rest."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"))
    orders = desired_orders(state, {}, set(), held_units=Decimal(0))
    assert OrderPurpose.BREAKOUT in {o.purpose for o in orders}


def test_unknown_status_refuses_instead_of_resting_nothing():
    """A future EpisodeStatus falling through to `return ()` would read as
    'cancel everything' at the venue. Refuse instead."""
    with pytest.raises(ValueError, match="unhandled"):
        desired_orders(EpisodeState(status="teleporting"), {}, set(),
                       held_units=Decimal(0))


def test_negative_held_units_is_refused():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), prior_ath=Decimal("1163.00"))
    with pytest.raises(ValueError, match="held_units"):
        desired_orders(state, {}, set(), held_units=Decimal(-1))


def test_total_units_must_exceed_the_accumulation_pool():
    """total_units - 7 is the ladder pool; <= 7 makes it zero or negative."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), prior_ath=Decimal("1163.00"))
    with pytest.raises(ValueError, match="total_units"):
        desired_orders(state, {}, set(), held_units=Decimal(0),
                       total_units=Decimal(7))


# --- WATCHING -------------------------------------------------------------

def test_watching_refuses_when_an_unfilled_tranche_has_no_line():
    """A missing line is a dead data feed, not 'no order wanted'. Emitting the
    other two would have the reconciler cancel the third."""
    state = EpisodeState(status=EpisodeStatus.WATCHING)
    with pytest.raises(ValueError, match="t3"):
        desired_orders(state, {"t1": Decimal("52848"), "t2": Decimal("45849")},
                       set(), held_units=Decimal(0))


def test_watching_does_not_need_the_line_of_an_already_filled_tranche():
    state = EpisodeState(status=EpisodeStatus.WATCHING)
    orders = desired_orders(state, {"t1": Decimal("52848"), "t2": Decimal("45849")},
                            {OrderPurpose.T3}, held_units=Decimal(4))
    assert {o.purpose for o in orders} == {OrderPurpose.T1, OrderPurpose.T2}


def test_watching_refuses_a_non_positive_line_value():
    """A zero realized price means the CoinMetrics derivation divided badly."""
    state = EpisodeState(status=EpisodeStatus.WATCHING)
    with pytest.raises(ValueError, match="t1"):
        desired_orders(state, {"t1": Decimal(0), "t2": Decimal("45849"),
                               "t3": Decimal("38851")}, set(), held_units=Decimal(0))


def test_watching_rests_no_exits_and_no_breakout():
    state = EpisodeState(status=EpisodeStatus.WATCHING, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    orders = desired_orders(state, {"t1": Decimal("52848"), "t2": Decimal("45849"),
                                    "t3": Decimal("38851")}, set(),
                            held_units=Decimal(7))
    assert {o.purpose for o in orders} == {OrderPurpose.T1, OrderPurpose.T2,
                                           OrderPurpose.T3}


def test_watching_prices_the_tranches_at_that_days_line_values():
    state = EpisodeState(status=EpisodeStatus.WATCHING)
    lines = {"t1": Decimal("52848"), "t2": Decimal("45849"), "t3": Decimal("38851")}
    prices = {o.purpose: o.price
              for o in desired_orders(state, lines, set(), held_units=Decimal(0))}
    assert prices[OrderPurpose.T1] == Decimal("52848")
    assert prices[OrderPurpose.T2] == Decimal("45849")
    assert prices[OrderPurpose.T3] == Decimal("38851")


def test_idle_rests_nothing():
    assert desired_orders(EpisodeState(status=EpisodeStatus.IDLE), {}, set(),
                          held_units=Decimal(0)) == ()


# --- CONFIRMED ------------------------------------------------------------

def test_confirmed_never_re_rests_accumulation_tranches():
    """SPEC §13.6: lines die at the BoS, inclusive. Their capital rolls; the
    orders do not survive."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), prior_ath=Decimal("1163.00"))
    orders = desired_orders(state, {"t1": Decimal("100"), "t2": Decimal("90"),
                                    "t3": Decimal("80")}, set(), held_units=Decimal(0))
    assert not ({OrderPurpose.T1, OrderPurpose.T2,
                 OrderPurpose.T3} & {o.purpose for o in orders})


def test_confirmed_ladder_prices_match_gate_g1():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), prior_ath=Decimal("1163.00"))
    prices = {o.purpose: o.price
              for o in desired_orders(state, {}, set(), held_units=Decimal(0))}
    assert prices[OrderPurpose.LADDER_050] == Decimal("231.150")
    assert prices[OrderPurpose.LADDER_062] == Decimal("212.250")
    assert abs(prices[OrderPurpose.LADDER_0786] - Decimal("186.10")) < Decimal("0.01")


def test_ladder_units_are_joined_to_levels_by_key_not_by_position():
    """LADDER_UNITS.keys() == LADDER.keys() is asserted upstream, but their
    ORDER is not. A zip would be silently wrong the day either dict is
    reordered: the deepest rung must carry the largest size."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), prior_ath=Decimal("1163.00"))
    rungs = {o.purpose: o for o in desired_orders(state, {},
                                                  {OrderPurpose.T1, OrderPurpose.T2,
                                                   OrderPurpose.T3},
                                                  held_units=Decimal(7))}
    deep, mid, shallow = (rungs[OrderPurpose.LADDER_0786],
                          rungs[OrderPurpose.LADDER_062],
                          rungs[OrderPurpose.LADDER_050])
    assert deep.price < mid.price < shallow.price
    assert deep.units > mid.units > shallow.units
    assert (shallow.units, mid.units, deep.units) == (Decimal(2), Decimal(4), Decimal(8))


def test_confirmed_rolls_unfilled_accumulation_into_the_ladder():
    """OQ-3 leg 1. Nothing accumulated -> the ladder carries all 21 units."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    units = {o.purpose: o.units
             for o in desired_orders(state, {}, set(), held_units=Decimal(0))}
    assert units[OrderPurpose.LADDER_050] == Decimal(3)
    assert units[OrderPurpose.LADDER_062] == Decimal(6)
    assert units[OrderPurpose.LADDER_0786] == Decimal(12)
    assert units[OrderPurpose.BREAKOUT] == Decimal(21)


def test_partially_filled_accumulation_rolls_only_the_unfilled_units():
    """T1 filled (1 unit) -> 6 roll, ladder pool 20."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    units = {o.purpose: o.units
             for o in desired_orders(state, {}, {OrderPurpose.T1},
                                     held_units=Decimal(1))}
    # The expectation is computed in CTX too: 20*2/14 is a repeating expansion,
    # so evaluating it at the ambient prec 28 would disagree in the 29th digit.
    with localcontext(CTX):
        assert units[OrderPurpose.LADDER_050] == Decimal(20) * Decimal(2) / Decimal(14)
        assert units[OrderPurpose.LADDER_062] == Decimal(20) * Decimal(4) / Decimal(14)
        assert units[OrderPurpose.LADDER_0786] == Decimal(20) * Decimal(8) / Decimal(14)
    assert units[OrderPurpose.BREAKOUT] == Decimal(20)


def test_breakout_carries_exactly_the_still_unfilled_ladder_units():
    """OQ-3 leg 2: ladder rungs that go unfilled join the breakout."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), prior_ath=Decimal("1163.00"))
    orders = desired_orders(state, {}, {OrderPurpose.T1, OrderPurpose.T2,
                                        OrderPurpose.T3, OrderPurpose.LADDER_050},
                            held_units=Decimal(9))
    units = {o.purpose: o.units for o in orders}
    assert OrderPurpose.LADDER_050 not in units      # already filled
    assert units[OrderPurpose.BREAKOUT] == Decimal(12) == units[OrderPurpose.LADDER_062] \
        + units[OrderPurpose.LADDER_0786]


def test_no_breakout_rests_once_every_ladder_rung_has_filled():
    """Nothing left to chase; a zero-size stop-market would be rejected."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), prior_ath=Decimal("1163.00"))
    orders = desired_orders(state, {},
                            {OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3,
                             OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
                             OrderPurpose.LADDER_0786}, held_units=Decimal(21))
    assert OrderPurpose.BREAKOUT not in {o.purpose for o in orders}


def test_exit1_is_sized_from_holdings_not_from_the_capital_plan():
    """7 units held out of a 21-unit plan -> 3.5, never 10.5."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("15476"),
                         bos_week_high=Decimal("25250"), prior_ath=Decimal("69000"))
    ex1 = next(o for o in desired_orders(state, {}, set(), held_units=Decimal(7))
               if o.purpose is OrderPurpose.EXIT1)
    assert ex1.units == Decimal("3.5")
    assert abs(ex1.price - Decimal("83558.53")) < Decimal("0.01")   # G3's Exit 1


def test_exit1_is_not_re_rested_once_it_has_printed():
    """Re-resting after the take-profit filled sells half the remainder again."""
    base = dict(status=EpisodeStatus.CONFIRMED, el_star=Decimal("15476"),
                bos_week_high=Decimal("25250"), prior_ath=Decimal("69000"))
    done = desired_orders(EpisodeState(**base, exit1_done=True), {}, set(),
                          held_units=Decimal(7))
    assert OrderPurpose.EXIT1 not in {o.purpose for o in done}
    via_fills = desired_orders(EpisodeState(**base), {}, {OrderPurpose.EXIT1},
                               held_units=Decimal(7))
    assert OrderPurpose.EXIT1 not in {o.purpose for o in via_fills}
    # ... and the stop still rests over the remainder.
    assert OrderPurpose.STOP in {o.purpose for o in done}


def test_confirmed_stop_is_a_sell_stop_at_el_star_for_everything_held():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("15476"),
                         bos_week_high=Decimal("25250"), prior_ath=Decimal("69000"))
    stop = next(o for o in desired_orders(state, {}, set(), held_units=Decimal("6.25"))
                if o.purpose is OrderPurpose.STOP)
    assert stop.units == Decimal("6.25")
    assert stop.price == Decimal("15476")


# --- DISTRIBUTING ---------------------------------------------------------

def test_distributing_without_a_signal_rests_only_the_stop():
    """SPEC §6.2: the mirror target does not exist before a signal."""
    state = EpisodeState(status=EpisodeStatus.DISTRIBUTING, el_star=Decimal("15476"),
                         bos_week_high=Decimal("25250"), prior_ath=Decimal("69000"),
                         exit1_done=True)
    orders = desired_orders(state, {}, set(), held_units=Decimal("3.5"))
    assert [o.purpose for o in orders] == [OrderPurpose.STOP]
    assert orders[0].units == Decimal("3.5")


def test_distributing_with_a_signal_rests_the_mirror_limit_and_the_stop():
    state = EpisodeState(status=EpisodeStatus.DISTRIBUTING, el_star=Decimal("15476"),
                         exit1_done=True)
    orders = desired_orders(state, {"mirror": Decimal("114100")}, set(),
                            held_units=Decimal("3.5"))
    mirror = next(o for o in orders if o.purpose is OrderPurpose.MIRROR)
    assert mirror.side is OrderSide.SELL and mirror.kind is OrderKind.LIMIT
    assert mirror.price == Decimal("114100") and mirror.units == Decimal("3.5")
    assert OrderPurpose.STOP in {o.purpose for o in orders}


def test_distributing_fallback_replaces_the_mirror_limit_rather_than_joining_it():
    """Both resting would sell the remainder twice."""
    state = EpisodeState(status=EpisodeStatus.DISTRIBUTING, el_star=Decimal("15476"),
                         exit1_done=True)
    orders = desired_orders(state, {"mirror": Decimal("114100"),
                                    "mirror_fallback": Decimal(1)}, set(),
                            held_units=Decimal("3.5"))
    mirrors = [o for o in orders if o.purpose is OrderPurpose.MIRROR]
    assert len(mirrors) == 1
    assert mirrors[0].kind is OrderKind.MARKET and mirrors[0].price is None
    assert mirrors[0].units == Decimal("3.5")


def test_distributing_treats_a_falsy_fallback_flag_as_not_fired():
    state = EpisodeState(status=EpisodeStatus.DISTRIBUTING, el_star=Decimal("15476"),
                         exit1_done=True)
    orders = desired_orders(state, {"mirror": Decimal("114100"),
                                    "mirror_fallback": Decimal(0)}, set(),
                            held_units=Decimal("3.5"))
    mirror = next(o for o in orders if o.purpose is OrderPurpose.MIRROR)
    assert mirror.kind is OrderKind.LIMIT


def test_distributing_with_nothing_held_rests_nothing():
    state = EpisodeState(status=EpisodeStatus.DISTRIBUTING, el_star=Decimal("15476"),
                         exit1_done=True)
    assert desired_orders(state, {"mirror": Decimal("114100")}, set(),
                          held_units=Decimal(0)) == ()


def test_distributing_without_el_star_refuses():
    state = EpisodeState(status=EpisodeStatus.DISTRIBUTING, exit1_done=True)
    with pytest.raises(ValueError, match="el_star"):
        desired_orders(state, {}, set(), held_units=Decimal("3.5"))


def test_distributing_rests_no_ladder_and_no_second_exit1():
    state = EpisodeState(status=EpisodeStatus.DISTRIBUTING, el_star=Decimal("15476"),
                         bos_week_high=Decimal("25250"), prior_ath=Decimal("69000"),
                         exit1_done=True)
    purposes = {o.purpose for o in desired_orders(state, {"mirror": Decimal("114100")},
                                                  set(), held_units=Decimal("3.5"))}
    assert purposes == {OrderPurpose.STOP, OrderPurpose.MIRROR}


# --- roll_unfilled --------------------------------------------------------

def test_roll_conserves_the_pool_exactly_for_every_reachable_split():
    """Capital must not evaporate into rounding. The eight reachable pools are
    14 + {0..7}; only 14 and 21 divide 2:4:8 exactly, so the other six exercise
    a genuinely inexact division."""
    for acc in range(8):
        pool = roll_unfilled(Decimal(acc), Decimal(14))
        assert sum(pool.values()) == Decimal(14) + Decimal(acc), acc


def test_roll_preserves_the_2_4_8_ratio_under_an_inexact_split():
    """Each rung is derived from the pool, not scaled off its neighbour, so the
    ratio holds to the context's precision rather than to the last digit:
    `2.142...143 * 4` double-rounds one ulp away from `15 * 8 / 14`."""
    pool = roll_unfilled(Decimal(1), Decimal(14))
    with localcontext(CTX):
        assert pool["0.62"] == pool["0.5"] * 2
        assert abs(pool["0.786"] - pool["0.5"] * 4) < Decimal("1e-32")


def test_roll_keys_are_the_ladder_keys():
    assert set(roll_unfilled(Decimal(0), Decimal(14))) == set(LADDER_UNITS)


def test_roll_rejects_a_negative_or_empty_ladder_pool():
    with pytest.raises(ValueError):
        roll_unfilled(Decimal(0), Decimal(0))
    with pytest.raises(ValueError):
        roll_unfilled(Decimal(-1), Decimal(14))


def test_roll_is_unaffected_by_a_hostile_ambient_decimal_context():
    """The division is inexact, so an ambient prec change would move the sizes
    of every rolled ladder rung. engine.context.CTX pins it."""
    baseline = roll_unfilled(Decimal(1), Decimal(14))
    with localcontext() as ctx:
        ctx.prec = 4
        assert roll_unfilled(Decimal(1), Decimal(14)) == baseline


# --- cross-cutting invariants ---------------------------------------------

def test_no_order_is_ever_emitted_with_non_positive_size():
    states = [
        (EpisodeState(status=EpisodeStatus.WATCHING),
         {"t1": Decimal("52848"), "t2": Decimal("45849"), "t3": Decimal("38851")},
         set(), Decimal(0)),
        (EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                      bos_week_high=Decimal("82850"), prior_ath=Decimal("126200")),
         {}, set(), Decimal(7)),
        (EpisodeState(status=EpisodeStatus.DISTRIBUTING, el_star=Decimal("57800"),
                      exit1_done=True),
         {"mirror": Decimal("114100")}, set(), Decimal("3.5")),
    ]
    for state, lines, filled, held in states:
        for o in desired_orders(state, lines, filled, held_units=held):
            assert o.units > 0, (state.status, o)


def test_every_emitted_order_is_a_desired_order_with_a_coherent_shape():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    for o in desired_orders(state, {}, set(), held_units=Decimal(7)):
        assert isinstance(o, DesiredOrder)
        assert isinstance(o.price, Decimal)      # only MARKET may price None
        assert (o.side is OrderSide.BUY) is (o.purpose in (
            OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3,
            OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
            OrderPurpose.LADDER_0786, OrderPurpose.BREAKOUT))


def test_purposes_within_one_desired_set_are_unique():
    """The reconciler diffs by purpose; a duplicate would place two orders."""
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    orders = desired_orders(state, {}, set(), held_units=Decimal(7))
    assert len({o.purpose for o in orders}) == len(orders)


def test_the_desired_set_is_a_pure_function_of_its_arguments():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), prior_ath=Decimal("126200"))
    first = desired_orders(state, {}, set(), held_units=Decimal(7))
    second = desired_orders(state, {}, set(), held_units=Decimal(7))
    assert first == second
    assert isinstance(first, tuple)


def test_accumulation_weights_are_the_frozen_1_2_4():
    assert [ACC_UNITS[p] for p in (OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3)] \
        == [Decimal(1), Decimal(2), Decimal(4)]
    assert sum(ACC_UNITS.values()) + sum(LADDER_UNITS.values()) == Decimal(21)
