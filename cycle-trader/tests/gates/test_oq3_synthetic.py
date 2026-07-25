"""Synthetic coverage for the OQ-3 roll: accumulation unfilled at BoS ->
ladder -> breakout. No historical episode exercises this path.

SPEC §14 OQ-3 (owner-resolved 2026-07-25) has two legs:

    leg 1  unfilled ACCUMULATION capital joins the LADDER pool, re-split 2:4:8
    leg 2  unfilled LADDER rungs join the BREAKOUT

Leg 2 is well covered: all four BoS episodes left rungs unfilled and the
breakout swept them (EP2 8u, EP3 14u, EP4 14u, EP5 12u). **Leg 1 has zero
historical coverage** — accumulation filled 3/3 in every one of them, so the
roll never had anything to carry. `test_history_never_exercised_leg_1` asserts
that from the reference JSON rather than asserting it in a comment, because it
is the premise the rest of this file rests on.

That also means there is no reference answer to diff against. `cy1_lifecycle.json`
rolls unfilled accumulation straight to the BREAKOUT — its own `spec` string
flags the deviation — and OQ-3 overrides it. The two agree on all recorded
history precisely because the roll was always empty. So on leg 1 this file is
not reproducing a frozen result the way G1-G5 do; it is pinning the resolution
itself. Everything here is a rule reading, and the rule is §14 OQ-3 plus the
frozen 2:4:8.

EP6 is on track to be the first episode to take it: no tranche has filled, spot
is ~11% above T1, and a break of 82,850 without a revisit to the accumulation
lines rolls the entire 7-unit accumulation pool — a third of the book — down a
path nothing has tested. The EP6-grounded tests below use the live anchors
(EL* 57,800.19, prior ATH 126,199.63, operative LH 82,850) so the synthetic
stays tied to the real episode rather than drifting into invented numbers; the
brief's own rounded values (57,800 / 126,200) are checked against them.
"""
from decimal import Decimal, localcontext

from engine.context import CTX
from engine.levels import ladder_levels
from engine.lifecycle import freeze_el, prior_cycle_ath
from engine.orders import ACC_UNITS, TOTAL_UNITS, desired_orders, roll_unfilled
from engine.structure import operative_lh
from engine.types import (EpisodeState, EpisodeStatus, OrderKind, OrderPurpose,
                          OrderSide)

ASOF = "2026-07-22"
#: EP6's D week — the 126,199.63 ATH week, which is `freeze_el`'s scope_start.
EP6_D_WEEK = "2025-10-06"
#: The synthetic BoS: a break of the live operative LH, dated after the data end.
BOS_HIGH = Decimal("82850")
BOS_DATE = "2026-09-01"

TRANCHES = (OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3)
RUNGS = (OrderPurpose.LADDER_050, OrderPurpose.LADDER_062, OrderPurpose.LADDER_0786)


def _state(el_star=Decimal("57800"), prior_ath=Decimal("126200")) -> EpisodeState:
    return EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=el_star,
                        bos_week_high=BOS_HIGH, bos_date=BOS_DATE,
                        prior_ath=prior_ath)


def _by_purpose(orders):
    return {o.purpose: o for o in orders}


# --- the premise: leg 1 is untested by history ----------------------------

def test_history_never_exercised_leg_1(cy1):
    """Every BoS episode filled accumulation 3/3, so the roll was always empty.

    This is the justification for the whole file. If a data refresh ever gives
    leg 1 real coverage, this test fails and the synthetic stops being the only
    evidence — which is the outcome worth being told about, loudly.
    """
    activated = [e for e in cy1["episodes"] if e["status"] == "bos"]
    assert len(activated) == 4, "EP2-EP5 are the activated episodes"
    for ep in activated:
        acc = ep["accumulation"]
        assert len(acc) == 3
        assert all(a["filled"] for a in acc), \
            f"{ep['episode']} would give leg 1 historical coverage"
        # ...and leg 2 was exercised every time, which is why it needs no
        # synthetic: some rung always went unfilled and the breakout took it.
        assert any(not r["filled"] for r in ep["reserve"]), ep["episode"]
        assert Decimal(ep["breakout"]["units"]) == sum(
            Decimal(r["w"]) for r in ep["reserve"] if not r["filled"])

    # The reference implements the pre-OQ-3 reading (accumulation -> breakout).
    # Recorded here so the disagreement is visible rather than folklore: it is
    # unobservable on this data only because the roll was always empty.
    assert "unfilled joins breakout [FLAGGED]" in cy1["spec"]


# --- leg 1, verbatim from the task brief ----------------------------------

def test_all_accumulation_unfilled_rolls_the_whole_pool_to_the_ladder():
    """EP6's likely path: BoS with zero tranches filled, held_units 0."""
    state = _state()
    orders = desired_orders(state, lines={}, filled_purposes=set(),
                            held_units=Decimal(0))
    ladder = [o for o in orders if o.purpose.name.startswith("LADDER")]
    assert sum(o.units for o in ladder) == Decimal(21), \
        "7 unfilled accumulation units must join the 14 ladder units"
    ratios = sorted(o.units for o in ladder)
    assert ratios[1] / ratios[0] == Decimal(2)
    assert ratios[2] / ratios[0] == Decimal(4)
    # The absolute sizes, not just the ratios: 2:4:8 of a 21-unit pool. Stated
    # as literals rather than read back off LADDER_UNITS so that re-weighting
    # the frozen constants cannot make this test agree with itself.
    units = {o.purpose: o.units for o in ladder}
    assert units[OrderPurpose.LADDER_050] == Decimal(3)
    assert units[OrderPurpose.LADDER_062] == Decimal(6)
    assert units[OrderPurpose.LADDER_0786] == Decimal(12)


def test_partial_accumulation_fill_rolls_only_the_remainder():
    state = _state()
    orders = desired_orders(state, lines={},
                            filled_purposes={OrderPurpose.T1, OrderPurpose.T2},
                            held_units=Decimal(3))
    ladder = [o for o in orders if o.purpose.name.startswith("LADDER")]
    assert sum(o.units for o in ladder) == Decimal(18)  # 14 + T3's 4 units


def test_unfilled_ladder_units_join_the_breakout():
    pool = roll_unfilled(Decimal(7), Decimal(14))
    assert sum(pool.values()) == Decimal(21)
    state = _state()
    orders = desired_orders(state, lines={},
                            filled_purposes={OrderPurpose.LADDER_050},
                            held_units=Decimal(3))   # the filled 0.5 rung
    brk = next(o for o in orders if o.purpose is OrderPurpose.BREAKOUT)
    ladder = [o for o in orders if o.purpose.name.startswith("LADDER")]
    assert brk.units == sum(o.units for o in ladder)
    assert brk.price == Decimal("82850")


# --- conservation across every reachable leg-1 split -----------------------

def test_the_roll_conserves_the_book_on_all_eight_fill_subsets():
    """Filled accumulation + resting ladder == 21, for all 2^3 subsets.

    Only the empty subset (leg 1's full roll) and the full subset (history) are
    named elsewhere; the six intermediate splits are reachable and equally
    untested, and they are the ones where the pool is an inexact 34-digit
    expansion. Conservation is the invariant that says the roll neither creates
    capital (double-spending the quote balance) nor drops it on the floor.
    """
    subsets = [set(), {OrderPurpose.T1}, {OrderPurpose.T2}, {OrderPurpose.T3},
               {OrderPurpose.T1, OrderPurpose.T2},
               {OrderPurpose.T1, OrderPurpose.T3},
               {OrderPurpose.T2, OrderPurpose.T3}, set(TRANCHES)]
    assert len({frozenset(s) for s in subsets}) == 8
    for filled in subsets:
        with localcontext(CTX):
            spent = sum((ACC_UNITS[p] for p in filled), Decimal(0))
        orders = desired_orders(_state(), lines={}, filled_purposes=filled,
                                held_units=spent or Decimal(0))
        rungs = [o for o in orders if o.purpose in RUNGS]
        assert len(rungs) == 3, filled
        with localcontext(CTX):
            resting = sum((o.units for o in rungs), Decimal(0))
        assert spent + resting == TOTAL_UNITS, filled
        # Leg 2 hands the same total to the breakout while every rung is unfilled.
        assert _by_purpose(orders)[OrderPurpose.BREAKOUT].units == resting, filled


def test_the_roll_resizes_the_ladder_without_repricing_it():
    """Leg 1 moves capital, never levels.

    The rungs are §5 retracements of the BoS leg; they do not know how much
    accumulation filled. A roll that also nudged the prices would put the whole
    rolled pool at levels no gate has ever checked, and G1's 231.15 / 212.25 /
    186.10 would still pass because that episode filled 3/3.
    """
    full_roll = _by_purpose(desired_orders(_state(), {}, set(), Decimal(0)))
    no_roll = _by_purpose(desired_orders(_state(), {}, set(TRANCHES), Decimal(7)))
    for purpose in RUNGS:
        assert full_roll[purpose].price == no_roll[purpose].price
        assert full_roll[purpose].units > no_roll[purpose].units
    assert {p: o.units for p, o in no_roll.items() if p in RUNGS} == \
        {OrderPurpose.LADDER_050: Decimal(2), OrderPurpose.LADDER_062: Decimal(4),
         OrderPurpose.LADDER_0786: Decimal(8)}


# --- grounded in the live EP6 episode --------------------------------------

def test_the_synthetic_anchors_are_ep6s_real_anchors(bars, weeks, episode_scope):
    """The premise, from real data: EP6's live LH/EL*/ATH are what this file uses.

    The brief's 57,800 / 126,200 are roundings of 57,800.19 / 126,199.63. Pinned
    here so a data refresh that moves EP6's low surfaces as a failure in this
    file rather than as a synthetic that quietly stops describing the episode.
    """
    trigger = "2026-01-26"
    assert trigger in episode_scope["triggers"]
    d_week, bos, broken = episode_scope["scopes"][trigger]
    assert (d_week, bos, broken) == (EP6_D_WEEK, None, None), \
        "EP6 must still be unactivated for this synthetic to be hypothetical"

    from engine.structure import find_lh_candidates
    cands = find_lh_candidates(weeks, bars, scope_start=d_week,
                               trigger_monday=trigger)
    assert operative_lh(cands, asof=ASOF).price == BOS_HIGH

    el_star = freeze_el(bars, EP6_D_WEEK, ASOF)
    ath, ath_week = prior_cycle_ath(weeks, trigger)
    assert (el_star, ath, ath_week) == (Decimal("57800.19"), Decimal("126199.63"),
                                        EP6_D_WEEK)
    assert abs(el_star - Decimal("57800")) < Decimal("1")
    assert abs(ath - Decimal("126200")) < Decimal("1")
    # No tranche can have filled: the shallowest line is far under the low.
    assert min(b.low for b in bars if b.date >= trigger) == el_star


def test_ep6s_full_roll_prices_every_rung_between_the_stop_and_the_breakout(
        bars, weeks):
    """The order set the live episode would produce on a BoS with no fills.

    Built from engine-derived anchors, not from the rounded literals, so this is
    the set that would actually rest. `EL* < 0.786 < 0.62 < 0.5 < BoS high` is
    what makes the rungs buy-limits *under* market with the stop beneath all of
    them; any inversion is the module's self-executing-buy failure.
    """
    el_star = freeze_el(bars, EP6_D_WEEK, ASOF)
    ath, _ = prior_cycle_ath(weeks, "2026-01-26")
    orders = _by_purpose(desired_orders(_state(el_star, ath), {}, set(), Decimal(0)))

    deep, mid, shallow = (orders[OrderPurpose.LADDER_0786],
                          orders[OrderPurpose.LADDER_062],
                          orders[OrderPurpose.LADDER_050])
    assert el_star < deep.price < mid.price < shallow.price < BOS_HIGH
    # Bigger size the deeper it goes — the 2:4:8 shape, checked on prices rather
    # than on the dict keys, so a rung/level mis-join shows up here.
    assert deep.units > mid.units > shallow.units
    assert (shallow.units, mid.units, deep.units) == (Decimal(3), Decimal(6),
                                                      Decimal(12))
    assert [o.side for o in (deep, mid, shallow)] == [OrderSide.BUY] * 3
    assert [o.kind for o in (deep, mid, shallow)] == [OrderKind.LIMIT] * 3
    # The engine's levels, independently: the roll must not have touched them.
    assert {o.price for o in (deep, mid, shallow)} == \
        set(ladder_levels(el_star, BOS_HIGH).values())
    # Nothing sell-side yet: no units are held on BoS day under the full roll,
    # so no stop rests either. This is the one moment CY-1 is unprotected, and
    # it is unprotected because there is nothing to protect.
    assert set(orders) == set(RUNGS) | {OrderPurpose.BREAKOUT}


def test_the_full_roll_deploys_at_a_better_average_price_than_the_breakout(bars):
    """Why leg 1 favours the ladder, in numbers, and why leg 2 is the worse arm.

    Both legs deploy the same 21 units; only the price differs. If every rung
    fills, the book averages 65,372.39 — 7,572.20 above EL*. If none does, leg 2
    takes all 21 units at the BoS-week high, 25,049.81 above EL*, so the same
    position sits **231% further from the stop** and risks 3.31x as much.

    Price ratio and risk ratio are different numbers and the second is the one
    an owner acts on. 82,850 / 65,372.39 = 1.27 says the breakout pays 27% more
    per coin; it says nothing about exposure, because the stop is not at zero.
    Measured to the stop — the only distance that can actually be lost — the
    ratio is 3.31. The first review of this file quoted 1.27 as the risk figure
    and asserted the bound against it, which advertised a tight assertion that
    was 2.6x loose. Both bounds below are therefore two-sided and pinned to
    ~0.3%: a one-sided `> 1.27` passes on almost any arithmetic.

    Asserting the average also pins the size-to-level join: swap the 3-unit and
    12-unit rungs and the 2:4:8 ratios still look right, but the average entry
    moves the wrong way.
    """
    el_star = freeze_el(bars, EP6_D_WEEK, ASOF)
    orders = _by_purpose(desired_orders(_state(el_star), {}, set(), Decimal(0)))
    rungs = [orders[p] for p in RUNGS]
    with localcontext(CTX):
        notional = sum((o.price * o.units for o in rungs), Decimal(0))
        avg = notional / TOTAL_UNITS
        # Risk = price distance to the stop x size. EL* is where the position is
        # closed (§6.3), so it is the floor of the loss, not zero.
        ladder_risk = notional - el_star * TOTAL_UNITS
        breakout_risk = (BOS_HIGH - el_star) * TOTAL_UNITS
        risk_ratio = breakout_risk / ladder_risk
        price_ratio = BOS_HIGH / avg
    assert Decimal("65372") < avg < Decimal("65373")
    # The average sits below the midpoint of the rung range, because the deep
    # rung carries 12 of the 21 units. A size/level swap breaks this, not the
    # bare "inside the range" check.
    assert min(o.price for o in rungs) < avg < max(o.price for o in rungs)
    with localcontext(CTX):
        midpoint = (min(o.price for o in rungs) + max(o.price for o in rungs)) / 2
    assert avg < midpoint
    # Leg 2 is strictly the more expensive way to end up with the same 21 units.
    assert orders[OrderPurpose.BREAKOUT].price == BOS_HIGH
    assert avg < BOS_HIGH
    assert ladder_risk < breakout_risk
    assert Decimal("3.30") < risk_ratio < Decimal("3.32")
    # ...and the two ratios are kept side by side so neither can be quoted as
    # the other again. 1.27 is real, but it answers a different question.
    assert Decimal("1.26") < price_ratio < Decimal("1.27")
    assert risk_ratio > price_ratio * Decimal("2.6")


def test_the_roll_puts_exactly_half_as_much_again_behind_the_same_stop(bars):
    """Leg 1's cost, stated as the owner would feel it.

    The roll does not move a single rung price, so the extra exposure is purely
    the extra size: 21 units where a 3/3-filled episode would have laddered 14,
    at identical levels against an identical stop. That is **+50%**, exactly —
    not "a third more", which is the share of the book the roll moves (7 of 21),
    a different quantity that the first review of this file conflated with it.
    Exact rather than approximate because 21/14 scales every term of the risk
    sum by the same 1.5.
    """
    el_star = freeze_el(bars, EP6_D_WEEK, ASOF)
    state = _state(el_star)

    def ladder_risk(filled, held):
        rungs = [o for o in desired_orders(state, {}, set(filled), held)
                 if o.purpose in RUNGS]
        with localcontext(CTX):
            units = sum((o.units for o in rungs), Decimal(0))
            return sum((o.price * o.units for o in rungs),
                       Decimal(0)) - el_star * units, units

    rolled, rolled_units = ladder_risk(set(), Decimal(0))          # leg 1 fires
    base, base_units = ladder_risk(TRANCHES, Decimal(7))           # history's path
    assert (rolled_units, base_units) == (Decimal(21), Decimal(14))
    with localcontext(CTX):
        assert rolled / base == Decimal("1.5")
    assert rolled > base
    # The 7 rolled units are a third of the book and a half again of the ladder.
    with localcontext(CTX):
        assert (rolled_units - base_units) / TOTAL_UNITS == Decimal(1) / Decimal(3)


def test_the_rolled_episode_reconciles_idempotently_from_bos_to_full_deployment(
        bars, weeks):
    """The whole untested path, run as the daily reconciler would run it.

    Day N and day N+1 with identical inputs must produce identical sets — a
    growing set means the reconciler places duplicates, and the branch that made
    that a real bug (a re-rested BREAKOUT triggering on placement) is exactly the
    branch a fully rolled episode takes.
    """
    el_star = freeze_el(bars, EP6_D_WEEK, ASOF)
    ath, _ = prior_cycle_ath(weeks, "2026-01-26")
    state = _state(el_star, ath)

    def run(filled, held):
        first = desired_orders(state, {}, set(filled), held)
        assert first == desired_orders(state, {}, set(filled), held)
        return _by_purpose(first)

    # BoS day: nothing filled, nothing held. Whole pool resting on the ladder.
    day1 = run(set(), Decimal(0))
    assert set(day1) == set(RUNGS) | {OrderPurpose.BREAKOUT}

    # The 0.5 rung fills for 3 units. The stop and Exit 1 arm; the breakout
    # shrinks to the 18 units still unfilled.
    day2 = run({OrderPurpose.LADDER_050}, Decimal(3))
    assert OrderPurpose.LADDER_050 not in day2
    assert day2[OrderPurpose.BREAKOUT].units == Decimal(18)
    assert day2[OrderPurpose.STOP].units == Decimal(3)
    assert day2[OrderPurpose.STOP].price == el_star
    assert day2[OrderPurpose.EXIT1].units == Decimal(3) / Decimal(2)

    # The breakout sweeps the remaining 18. Buy side closes; sell side covers
    # all 21 units the roll bought.
    day3 = run({OrderPurpose.LADDER_050, OrderPurpose.BREAKOUT}, TOTAL_UNITS)
    assert set(day3) == {OrderPurpose.STOP, OrderPurpose.EXIT1}
    assert day3[OrderPurpose.STOP].units == TOTAL_UNITS
    assert day3[OrderPurpose.EXIT1].units == TOTAL_UNITS / Decimal(2)
    assert not [o for o in day3.values() if o.side is OrderSide.BUY]
    # The sell side never exceeds what was bought — a stop for units the account
    # does not hold is rejected by the venue and aborts the run.
    assert day3[OrderPurpose.STOP].units <= TOTAL_UNITS
