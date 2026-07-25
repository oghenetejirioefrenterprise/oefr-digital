"""`compute()` — the single public entry point M2 calls once a day.

What this file is trying to pin down, beyond "it returns something plausible":

1. **Determinism and no lookahead.** Same inputs, same output; truncating the
   inputs at `asof` changes nothing. Those two properties are what make the
   gates evidence about live-money code rather than about a backtest.
2. **The four date boundaries that decide which orders exist**, none of which
   the module signatures enforce and each of which is a real fault on real
   data: the trigger week must be *settled* before it arms anything; the
   accumulation lines may not rest inside the trigger week; the BoS week must be
   *settled* before the ladder and the breakout can be priced; the mirror signal
   must post-date arming.
3. **The reference exits, end to end through `compute`.** EP2's and EP4's mirror
   exits reproduce to the cent and to the day. EP5's does not, and that
   divergence is asserted rather than avoided — it is SPEC §14 OQ-7(b), an owner
   decision under §9, and pinning it here means a silent change of reading fails.
4. **That refusal propagates.** `desired_orders` raises rather than emitting a
   smaller set, because under a desired-state reconciler a short set reads at the
   venue as "cancel everything, including the stop". `compute` must not catch it.
5. **The input contract with M2** (§11 below). `compute` takes three things M2
   reconstructs independently — a trade history (`held_units`), an order book
   (`filled_purposes`) and a clock (`asof`) — and any two of them can disagree
   with the third while every individual value looks reasonable. Each such
   disagreement is refused, because the resulting order sets are not merely
   wrong, they are wrong in the expensive direction: a 21-unit breakout, or a
   market sell of the whole position off a dead feed.

**The daily-run model these boundaries assume, stated once.** The cron runs after
the UTC daily close (CLAUDE.md), so `compute(asof=D)` sees D's completed bar and
the orders it returns are what rests **during D+1**. Every boundary below falls
out of that one convention, and it is what makes the settled-week readings agree
with §11's recorded fill dates instead of beating them by a week.
"""
from __future__ import annotations

from datetime import date as _date, timedelta
from decimal import Decimal

import pytest

from engine.bars import monday_of, week_end
from engine.engine import compute
from engine.fills import sell_limit_fill
from engine.lifecycle import chain_episodes, find_triggers
from engine.types import (Bar, EpisodeState, EpisodeStatus, OrderKind,
                          OrderPurpose, OrderSide)

ONE = Decimal(1)
TRANCHES = {OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3}
RUNGS = {OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
         OrderPurpose.LADDER_0786}

# --- coherent ledgers -----------------------------------------------------
# `filled_purposes` and `held_units` must be able to describe the same account,
# and `compute` refuses when they cannot. Every positioned test below therefore
# names a real ledger rather than reaching for `held_units=1` with nothing
# filled — which is not a shortcut but the exact contradiction the guard exists
# to catch, and which on the buy side silently selects the 21-unit branch.
#
#: What happened in all four activated episodes: accumulation filled 3/3
#: (§14 OQ-3), so 7 units held.
ACCUMULATED = frozenset(TRANCHES)
ACCUMULATED_UNITS = Decimal(7)
#: ...and after Exit 1 sold half.
ARMED = ACCUMULATED | {OrderPurpose.EXIT1}
ARMED_UNITS = Decimal("3.5")
#: EP6's live path instead: no tranche filled, so the position comes from the
#: ladder. A filled 0.5 rung on the rolled 21-unit pool is 3 units (§14 OQ-3).
RUNG_FILLED = frozenset({OrderPurpose.LADDER_050})
RUNG_UNITS = Decimal(3)


def _day_before(iso: str) -> str:
    return (_date.fromisoformat(iso) - timedelta(days=1)).isoformat()


def _plus(iso: str, days: int) -> str:
    return (_date.fromisoformat(iso) + timedelta(days=days)).isoformat()


def _purposes(result):
    return {o.purpose for o in result.orders}


def _by_purpose(result):
    return {o.purpose: o for o in result.orders}


# --------------------------------------------------------------------------
# 1. the two properties that make the gates mean anything
# --------------------------------------------------------------------------

@pytest.mark.parametrize("asof,filled,held", [
    ("2026-07-19", frozenset({OrderPurpose.T1}), ONE),      # WATCHING
    ("2023-03-01", ACCUMULATED, ACCUMULATED_UNITS),         # CONFIRMED
    ("2024-12-01", ARMED, ARMED_UNITS),                     # DISTRIBUTING
])
def test_compute_is_deterministic(bars, onchain, asof, filled, held):
    """Same inputs, same outputs — always. One date per status, because the
    three branches reach different code."""
    a = compute(bars, onchain, EpisodeState(), asof=asof,
                filled_purposes=filled, held_units=held)
    b = compute(bars, onchain, EpisodeState(), asof=asof,
                filled_purposes=filled, held_units=held)
    assert a == b


@pytest.mark.parametrize("asof", ["2026-05-01", "2023-03-01", "2015-02-05",
                                  "2020-12-31"])
def test_compute_never_looks_past_asof(bars, onchain, asof):
    """Truncating the input at `asof` must not change the result.

    Four dates rather than one, so the property is exercised in every status the
    engine can be in — WATCHING, CONFIRMED and DISTRIBUTING each reach different
    code, and a lookahead in the mirror scan (which walks bars *after* the
    signal) would be invisible from a WATCHING date alone.
    """
    truncated = [b for b in bars if b.date <= asof]
    oc = {d: v for d, v in onchain.items() if d <= asof}
    full = compute(bars, onchain, EpisodeState(), asof=asof)
    part = compute(truncated, oc, EpisodeState(), asof=asof)
    assert full.state == part.state
    assert full.orders == part.orders


# --------------------------------------------------------------------------
# 2. the live episode (G5) and the post-BoS reconstruction
# --------------------------------------------------------------------------

def test_compute_on_ep6_is_watching_with_three_accumulation_orders(bars, onchain):
    result = compute(bars, onchain, EpisodeState(), asof="2026-07-19")
    assert result.state.status is EpisodeStatus.WATCHING
    assert result.state.operative_lh == Decimal("82850")
    assert _purposes(result) == TRANCHES
    assert OrderPurpose.STOP not in _purposes(result)
    # Buy-limits, weighted 1:2:4, priced at the day's on-chain lines (SPEC §3).
    orders = _by_purpose(result)
    assert all(o.side is OrderSide.BUY and o.kind is OrderKind.LIMIT
               for o in result.orders)
    assert [orders[p].units for p in (OrderPurpose.T1, OrderPurpose.T2,
                                      OrderPurpose.T3)] == [ONE, Decimal(2),
                                                            Decimal(4)]
    oc = onchain["2026-07-19"]
    assert orders[OrderPurpose.T1].price == oc.realized
    assert orders[OrderPurpose.T2].price == oc.midpoint
    assert orders[OrderPurpose.T3].price == oc.balanced
    # T3 (balanced) sits UNDER T2 (midpoint) under T1 (realized) — the deeper
    # the line, the bigger the tranche, which is what 1:2:4 is for. §14 OQ-3's
    # "BTC sits far above T1 (~52.9k)" is this number.
    assert orders[OrderPurpose.T3].price < orders[OrderPurpose.T2].price \
        < orders[OrderPurpose.T1].price
    assert Decimal("52000") < oc.realized < Decimal("53000")


def test_compute_reconstructs_ep5_confirmed_after_its_bos(bars, onchain):
    """The killer regression for stateless reconstruction: at a post-BoS date
    the broken LH is invalidated (§4.5 — the BoS killed it), so any
    implementation that derives the BoS from 'today's operative LH' flips back
    to WATCHING here."""
    r = compute(bars, onchain, EpisodeState(), asof="2023-03-01")
    assert r.state.status is EpisodeStatus.CONFIRMED
    assert r.state.el_star == Decimal("15476")
    assert monday_of(r.state.bos_date) == "2023-02-13"
    assert r.state.operative_lh == Decimal("25211.32")   # the broken LH, kept


def test_the_state_carries_both_anchors_and_they_are_not_the_same_object(
        bars, onchain):
    """§13.3 v1.2.1: `scope_start` is D — the structural anchor — while
    `prior_ath` is §6.1's exit anchor. EP4 is the episode that proves they are
    different objects: D is the June-2019 13,970 week, the exit anchor is the
    Dec-2017 19,798.68. An engine that merged them still gets EL* right and
    Exit 1 wrong.
    """
    ep4 = compute(bars, onchain, EpisodeState(), asof="2020-08-03").state
    assert ep4.trigger_date == "2020-03-09"
    assert ep4.scope_start == "2019-06-24"
    assert ep4.prior_ath == Decimal("19798.68")
    assert ep4.el_star == Decimal("3782.13")

    ep5 = compute(bars, onchain, EpisodeState(), asof="2023-03-01").state
    assert ep5.scope_start == "2021-11-08"
    assert ep5.prior_ath == Decimal("69000")
    # The confirmation date of the LH that was actually broken — carried so the
    # journal can say WHICH structure activated the episode, not just when.
    assert ep5.lh_confirmed_at is not None
    assert ep5.lh_confirmed_at < ep5.bos_date


def test_the_watching_running_low_is_the_live_episode_low(bars, onchain):
    """PRD §8 / §13.3: EP6's low from D is 57,800.19, and it is a *running*
    anchor pre-BoS — the value the §6.1 level drifts down with."""
    r = compute(bars, onchain, EpisodeState(), asof="2026-07-19")
    assert r.state.scope_start == "2025-10-06"
    assert r.state.running_low == Decimal("57800.19")
    assert r.state.el_star is None, "nothing freezes before the BoS"


def test_a_filled_tranche_is_not_re_rested(bars, onchain):
    """§3 through `compute`: `filled_purposes` removes that buy-limit and only
    that one. M1 always passes the empty set; M2 feeds it from trade history."""
    r = compute(bars, onchain, EpisodeState(), asof="2026-07-19",
                filled_purposes=frozenset({OrderPurpose.T1, OrderPurpose.T3}),
                held_units=Decimal(5))          # 1 + 4 units, the two that filled
    assert _purposes(r) == {OrderPurpose.T2}


def test_operative_lh_after_a_bos_is_not_todays_answer(bars, onchain):
    """`operative_lh(asof)` does NOT return None after a BoS — it falls back to
    an older, higher candidate. On EP2 that is 453.92 from 2015-01-27 onward.

    So the state's `operative_lh` must come from `first_bos`'s *broken*
    candidate, not from re-asking today. Both readings survive a `== 305`
    assertion on the BoS day itself; only the day after separates them.
    """
    from engine.structure import operative_lh
    scoped = compute(bars, onchain, EpisodeState(), asof="2015-01-27")
    assert scoped.state.operative_lh == Decimal("305.00")

    weeks_now = [w for w in _weeks_of(bars, "2015-01-27")]
    episodes = chain_episodes(
        weeks_now, [b for b in bars if b.date <= "2015-01-27"],
        find_triggers(weeks_now, _rsi_of(weeks_now)), data_end="2015-01-27")
    today = operative_lh(list(episodes[-1].candidates), asof="2015-01-27")
    assert today is not None and today.price == Decimal("453.92"), \
        "the stale-structure fallback this test exists to exclude"


def _weeks_of(bars, asof):
    from engine.bars import to_weeks
    return [w for w in to_weeks([b for b in bars if b.date <= asof])
            if week_end(w.monday) <= asof]


def _rsi_of(weeks):
    from engine.rsi import wilder_rsi
    return wilder_rsi([w.close for w in weeks])


# --------------------------------------------------------------------------
# 3. boundary one — the trigger week must be settled
# --------------------------------------------------------------------------

def test_every_reference_episode_is_first_detected_on_its_label_date(
        bars, onchain, cy1):
    """The reference labels each episode by the trigger week's **Sunday close**,
    and that is exactly the first `asof` at which `compute` may know about it.

    A week's RSI is not knowable until its Sunday close, so arming on a partial
    week is a lookahead. This asserts both halves: detected on the label date,
    NOT detected the day before. Six episodes, no literals — the labels come out
    of the reference file (§13.10: labels are Sunday-anchored, engine dates are
    ISO Mondays).
    """
    for row in cy1["episodes"]:
        label = row["episode"].split("-", 1)[1]
        trigger = monday_of(label)
        on = compute(bars, onchain, EpisodeState(), asof=label)
        assert on.state.trigger_date == trigger, row["episode"]
        before = compute(bars, onchain, EpisodeState(), asof=_day_before(label))
        assert before.state.trigger_date != trigger, (
            f"{row['episode']} armed a week early off an unsettled weekly RSI")


@pytest.mark.parametrize("asof,expected_trigger", [
    # A phantom trigger: the partial week of 2025-11-17 dips under RSI 35 for two
    # days and recovers by its Sunday close. No such episode exists in the
    # record. Reading partial weeks arms one and rests three buy-limits on it.
    ("2025-11-21", "2022-05-16"),
    ("2025-11-22", "2022-05-16"),
    # A trigger that arms a week early and then MOVES: the LUNA week
    # 2022-05-09 prints RSI < 35 midweek, recovers by Sunday, and the real EP5
    # trigger lands on 2022-05-16. §11 and §13.3 both record 2022-05-16.
    ("2022-05-12", "2020-03-09"),
    ("2022-05-14", "2020-03-09"),
])
def test_an_unsettled_weekly_rsi_never_arms_an_episode(bars, onchain, asof,
                                                       expected_trigger):
    r = compute(bars, onchain, EpisodeState(), asof=asof)
    assert r.state.trigger_date == expected_trigger


def test_accumulation_cannot_rest_inside_the_trigger_week(bars, onchain, cy1):
    """§11's accumulation fills start the Monday AFTER the trigger week —
    EP3 wk 2018-11-19 fills 2018-11-26, EP4 wk 2020-03-09 fills 2020-03-16.

    `compute(asof=D)` returns what rests during D+1, so "the earliest day a
    tranche can rest" is `first detection date + 1`. Asserting it against the
    reference's own recorded fill date is what makes this a fact rather than a
    restatement of the implementation.
    """
    ref = {e["episode"]: e for e in cy1["episodes"]}
    for label, first_fill in (("EP3-2018-11-25", "2018-11-26"),
                              ("EP4-2020-03-15", "2020-03-16")):
        detected = label.split("-", 1)[1]
        assert ref[label]["accumulation"][0]["date"] == first_fill
        assert _plus(detected, 1) == first_fill
        armed = compute(bars, onchain, EpisodeState(), asof=detected)
        assert _purposes(armed) == TRANCHES
        # ...and the run one day earlier, inside the trigger week, arms nothing
        # for this episode.
        earlier = compute(bars, onchain, EpisodeState(),
                          asof=_day_before(detected))
        assert earlier.state.trigger_date != monday_of(detected)


# --------------------------------------------------------------------------
# 4. boundary two — the BoS week must be settled before the ladder is priced
# --------------------------------------------------------------------------

def test_the_ladder_and_breakout_wait_for_the_bos_week_to_close(bars, onchain):
    """SPEC §5 prices the ladder off the **BoS-week high** and fires the breakout
    "after the BoS week". `desired_orders` has no date input and rests the
    breakout the moment the status is CONFIRMED, so that "after" is delegated
    entirely to `compute`.

    Under OQ-3 the breakout carries 21 units, not 14, so a run inside the still
    open BoS week would buy the entire book at that week's running top. G1's BoS
    week is 2015-01-26..2015-02-01 and §13.3 records the 0.5 rung gap-filling
    **2015-02-02** — the first day the order can rest under this reading.
    """
    bos_week = ("2015-01-26", "2015-01-27", "2015-01-30", "2015-01-31")
    for asof in bos_week:
        r = compute(bars, onchain, EpisodeState(), asof=asof,
                    filled_purposes=ACCUMULATED, held_units=ACCUMULATED_UNITS)
        assert r.state.status is EpisodeStatus.CONFIRMED
        assert not (_purposes(r) & (RUNGS | {OrderPurpose.BREAKOUT})), asof
        # The stop is priced off EL*, which froze at the BoS — so it CAN rest,
        # and must: suppressing it would leave the position naked for a week.
        assert OrderPurpose.STOP in _purposes(r), asof

    settled = compute(bars, onchain, EpisodeState(), asof="2015-02-01")
    assert RUNGS | {OrderPurpose.BREAKOUT} <= _purposes(settled)
    rungs = _by_purpose(settled)
    # §13.3's ladder, to the cent: 231.15 / 212.25 / 186.10 (186.105 exact).
    assert rungs[OrderPurpose.LADDER_050].price == Decimal("231.15")
    assert rungs[OrderPurpose.LADDER_062].price == Decimal("212.25")
    assert rungs[OrderPurpose.LADDER_0786].price == Decimal("186.105")
    # ...off the SETTLED week high, which is also the breakout level.
    assert settled.state.bos_week_high == Decimal("309.90")
    assert rungs[OrderPurpose.BREAKOUT].price == Decimal("309.90")
    assert rungs[OrderPurpose.BREAKOUT].kind is OrderKind.STOP_MARKET


def test_the_bos_week_high_is_frozen_from_the_close_onward(bars, onchain):
    """Once the BoS week has settled the level never moves again — the ladder
    and the breakout would otherwise reprice for the life of the episode.

    Both historical BoS days happen to print their own week's high (the break
    day is the strongest of its week in EP2 and EP5 alike), so the *running*
    half of this property cannot be observed on real data; it is exercised in
    `test_the_bos_week_high_is_running_while_the_week_is_open` instead.
    """
    for later in ("2015-02-01", "2015-02-09", "2016-01-04", "2017-05-01"):
        got = compute(bars, onchain, EpisodeState(), asof=later)
        assert got.state.bos_week_high == Decimal("309.90"), later


def test_ep5_ladder_prices_off_its_own_settled_bos_week_high(bars, onchain):
    """G3's 25,250, the second BoS-week high SPEC §5 names."""
    r = compute(bars, onchain, EpisodeState(), asof="2023-03-01")
    assert r.state.bos_week_high == Decimal("25250")
    assert _by_purpose(r)[OrderPurpose.BREAKOUT].price == Decimal("25250")


def test_the_oq3_roll_is_wired_through_compute(bars, onchain):
    """§14 OQ-3 leg 1: accumulation that never filled joins the ladder pool.

    Historically all four episodes filled 3/3, so the only way to see this
    through `compute` is to tell it what filled. Unfilled -> 21-unit pool at
    2:4:8 (3/6/12); all three filled -> the base 14 (2/4/8).
    """
    nothing_filled = compute(bars, onchain, EpisodeState(), asof="2015-02-01")
    units = {p: o.units for p, o in _by_purpose(nothing_filled).items()}
    assert [units[p] for p in (OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
                               OrderPurpose.LADDER_0786)] == [Decimal(3),
                                                              Decimal(6),
                                                              Decimal(12)]
    assert units[OrderPurpose.BREAKOUT] == Decimal(21)

    all_filled = compute(bars, onchain, EpisodeState(), asof="2015-02-01",
                         filled_purposes=ACCUMULATED,
                         held_units=ACCUMULATED_UNITS)
    units = {p: o.units for p, o in _by_purpose(all_filled).items()}
    assert [units[p] for p in (OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
                               OrderPurpose.LADDER_0786)] == [Decimal(2),
                                                              Decimal(4),
                                                              Decimal(8)]
    assert units[OrderPurpose.BREAKOUT] == Decimal(14)


# --------------------------------------------------------------------------
# 5. boundary three — the mirror signal must post-date arming
# --------------------------------------------------------------------------

def test_compute_ep5_distributing_after_exit1_with_no_unarmed_mirror(bars,
                                                                     onchain):
    """2024-12-01: Exit 1 printed 2024-11-11, so EP5 is DISTRIBUTING — but the
    Aug-2024 break of the May-2024 swing PRE-dates arming and must not have
    produced a mirror signal (SPEC §6.2: arming precedes the signal).

    With `held_units == 0` the order list is empty either way, so the position
    is held open here: the absence of a MIRROR order is only evidence when a
    MIRROR order was possible.
    """
    r = compute(bars, onchain, EpisodeState(), asof="2024-12-01",
                filled_purposes=ARMED, held_units=ARMED_UNITS)
    assert r.state.status is EpisodeStatus.DISTRIBUTING
    assert r.state.exit1_done is True
    assert _purposes(r) == {OrderPurpose.STOP}


def test_nothing_sell_side_rests_while_the_engine_holds_nothing(bars, onchain):
    """`held_units == 0` -> no stop, no Exit 1, no mirror. M1 has no fill
    tracking, so this is the default and it is the safe one: a sell order for
    BTC the account does not hold is rejected by the venue."""
    for asof in ("2023-03-01", "2024-12-01", "2025-06-01"):
        r = compute(bars, onchain, EpisodeState(), asof=asof)
        assert not (_purposes(r) & {OrderPurpose.STOP, OrderPurpose.EXIT1,
                                    OrderPurpose.MIRROR}), asof


def test_exit1_rests_at_the_1272_extension_until_it_prints(bars, onchain):
    """§6.1 through `compute`: EL* + 1.272 x (prior ATH - EL*), and §11's EP2
    Exit 1 of 1,437.88 on 2017-05-02."""
    before = compute(bars, onchain, EpisodeState(), asof="2017-05-01",
                     filled_purposes=ACCUMULATED, held_units=ACCUMULATED_UNITS)
    assert before.state.status is EpisodeStatus.CONFIRMED
    exit1 = _by_purpose(before)[OrderPurpose.EXIT1]
    assert exit1.side is OrderSide.SELL and exit1.kind is OrderKind.LIMIT
    assert exit1.units == ACCUMULATED_UNITS / 2    # half the position
    assert exit1.price.quantize(Decimal("0.01")) == Decimal("1437.88")
    after = compute(bars, onchain, EpisodeState(), asof="2017-05-02",
                    filled_purposes=ARMED, held_units=ARMED_UNITS)
    assert after.state.status is EpisodeStatus.DISTRIBUTING
    assert OrderPurpose.EXIT1 not in _purposes(after)


# --------------------------------------------------------------------------
# 6. the mirror exit, end to end — and the OQ-7(b) divergence
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", ["EP2-2014-09-28", "EP4-2020-03-15"])
def test_compute_reproduces_the_reference_mirror_exit(bars, onchain, cy1,
                                                      label):
    """The resting MIRROR limit `compute` publishes on day D-1 fills on the
    reference's own exit date at the reference's own price.

    EP2 (2,405.00 on 2017-07-20) and EP4 (55,892.00 on 2021-04-28) are the two
    the entry point can see: `compute` reports the LATEST episode, so EP3 —
    which is still open when EP4 triggers — is shadowed. That is §14 OQ-1's
    concurrent-episode case showing up as a product limitation, noted in
    `engine/engine.py`. EP3's exit is the same day and price as EP4's anyway.
    """
    ref = {e["episode"]: e for e in cy1["episodes"]}[label]["exit_mirror"]
    bar = {b.date: b for b in bars}[ref["date"]]
    r = compute(bars, onchain, EpisodeState(), asof=_day_before(ref["date"]),
                filled_purposes=ARMED, held_units=ARMED_UNITS)
    assert r.state.status is EpisodeStatus.DISTRIBUTING
    mirror = _by_purpose(r)[OrderPurpose.MIRROR]
    assert mirror.side is OrderSide.SELL and mirror.kind is OrderKind.LIMIT
    assert sell_limit_fill(bar, mirror.price) == ref["px"]


def test_ep5_mirror_does_not_reproduce_and_that_is_oq7b(bars, onchain, cy1):
    """SPEC §14 OQ-7(b), asserted so it cannot be "fixed" without a §9 amendment.

    `find_swing_lows` implements reading (a) — confirmation against the swing
    week's own high. Reading (b), confirmation against the decline's top, is what
    reproduces all four reference exits. EP5 is the episode that separates them:
    (a) breaks wk 2024-12-30's low on 2025-01-09 and exits **2025-01-15 @
    98,804.845**, six weeks early and 5.2% high against the reference's
    2025-03-02 @ 93,923.26.

    Changing the reading is an owner decision under §9, not an implementation
    fix. Until it is made, this is the engine's behaviour and it is pinned to
    the number, so a silent flip fails here rather than shipping.
    """
    ref = {e["episode"]: e for e in cy1["episodes"]}["EP5-2022-05-22"]["exit_mirror"]
    assert (ref["date"], ref["px"]) == ("2025-03-02", Decimal("93923.26"))

    day = "2025-01-15"
    r = compute(bars, onchain, EpisodeState(), asof=_day_before(day),
                filled_purposes=ARMED, held_units=ARMED_UNITS)
    mirror = _by_purpose(r)[OrderPurpose.MIRROR]
    bar = {b.date: b for b in bars}[day]
    assert sell_limit_fill(bar, mirror.price) == Decimal("98804.845")
    assert day < ref["date"], "reading (a) exits early, not late"


def test_the_mirror_falls_back_to_market_eight_weeks_after_the_signal(bars,
                                                                      onchain):
    """§6.2: no 50% bounce within 8 weeks of the signal -> sell at market.

    EP2's signal is 2017-07-10. Measured in **calendar** days from the signal,
    not in bars: a data gap must not postpone a deadline. Day 56 is still the
    limit; day 57 is the market order, and it REPLACES the limit rather than
    joining it (both resting would sell the remainder twice).
    """
    signal = "2017-07-10"
    still_limit = compute(bars, onchain, EpisodeState(),
                          asof=_plus(signal, 56), filled_purposes=ARMED,
                          held_units=ARMED_UNITS)
    assert _by_purpose(still_limit)[OrderPurpose.MIRROR].kind is OrderKind.LIMIT

    fallback = compute(bars, onchain, EpisodeState(),
                       asof=_plus(signal, 57), filled_purposes=ARMED,
                       held_units=ARMED_UNITS)
    mirror = _by_purpose(fallback)[OrderPurpose.MIRROR]
    assert mirror.kind is OrderKind.MARKET
    assert mirror.price is None
    assert len([o for o in fallback.orders
                if o.purpose is OrderPurpose.MIRROR]) == 1


@pytest.mark.parametrize("asof", ["2025-06-15", "2025-12-15", "2026-01-31"])
def test_the_first_armed_mirror_signal_wins_and_later_structure_is_inert(
        bars, onchain, asof):
    """§13.9: "the position exits at the FIRST armed mirror signal. Later
    signals are recorded but inert."

    EP5's first armed signal is 2025-01-09 (reading (a); see OQ-7(b) above), so
    §6.2's 8-week deadline expired 2025-03-07 and the desired order has been the
    market fallback ever since. That is only true if the signal never moved.

    This is the assertion that separates the day-walk from the sketch the M1
    plan carried, which scans swings newest-first and takes the first one it can
    find a break for. That sketch re-signals continuously as new structure forms
    — 2025-04-06, then 2025-12-15, then 2026-01-20 on this very data — and each
    re-signal resets the deadline, so the fallback never fires and the resting
    sell is repriced off a *later* top. On EP2 and EP4 the two readings happen
    to agree, so nothing else in this file would notice.
    """
    r = compute(bars, onchain, EpisodeState(), asof=asof,
                filled_purposes=ARMED, held_units=ARMED_UNITS)
    assert r.state.status is EpisodeStatus.DISTRIBUTING
    assert r.state.trigger_date == "2022-05-16"
    mirror = _by_purpose(r)[OrderPurpose.MIRROR]
    assert mirror.kind is OrderKind.MARKET, \
        "the mirror re-signalled off later structure and reset the deadline"


# --------------------------------------------------------------------------
# 7. refusal must propagate
# --------------------------------------------------------------------------

def test_a_missing_on_chain_row_raises_rather_than_cancelling_the_book(bars,
                                                                       onchain):
    """The daily run is a reconciler: a shorter desired set is an instruction to
    CANCEL. `desired_orders` raises instead of dropping a tranche, and that is
    only protective if `compute` lets the exception out.

    The realistic trigger is the balanced-price feed going stale — CLAUDE.md's
    one fragile dependency — and the reference series already shows it: the bars
    run to 2026-07-20 while the on-chain series ends 2026-07-19.
    """
    assert max(onchain) == "2026-07-19" < bars[-1].date
    with pytest.raises(ValueError, match="accumulation line"):
        compute(bars, onchain, EpisodeState(), asof="2026-07-20")

    holed = {d: v for d, v in onchain.items() if d != "2026-07-19"}
    with pytest.raises(ValueError, match="accumulation line"):
        compute(bars, holed, EpisodeState(), asof="2026-07-19")


def test_a_non_positive_accumulation_line_raises(bars, onchain):
    """The other refusal path in `_watching`, reached through `compute`: a
    corrupt on-chain row rather than a missing one."""
    from engine.types import OnChain
    corrupt = dict(onchain)
    corrupt["2026-07-19"] = OnChain(date="2026-07-19", realized=Decimal(0),
                                    balanced=Decimal("38850"))
    with pytest.raises(ValueError, match="must be positive"):
        compute(bars, corrupt, EpisodeState(), asof="2026-07-19")


# --------------------------------------------------------------------------
# 8. the ends of the lifecycle
# --------------------------------------------------------------------------

def test_before_the_first_trigger_the_engine_is_idle_and_rests_nothing(bars,
                                                                       onchain):
    r = compute(bars, onchain, EpisodeState(), asof="2011-10-01")
    assert r.state.status is EpisodeStatus.IDLE
    assert r.state == EpisodeState()
    assert r.orders == ()


def test_an_empty_window_returns_the_prior_state_untouched(bars, onchain):
    """No bars at or before `asof` is not "IDLE", it is "no information". The
    caller's persisted state is returned unchanged and nothing is cancelled."""
    prior = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal(10))
    r = compute(bars, onchain, prior, asof="2009-01-01")
    assert r.state is prior
    assert r.orders == ()
    assert compute([], onchain, prior, asof="2020-01-01").state is prior


def test_closed_and_expired_are_unreachable_in_m1(bars, onchain, cy1):
    """Stated as a test so the gap is visible rather than folklore.

    CLOSED needs fill tracking (M2, from venue trade history). EXPIRED is never
    a *current* state: §1 bounds an episode's expiry by the next episode's
    trigger, and the moment that trigger prints the next episode is the one
    `compute` reports — so EP1 reads WATCHING throughout its own life and then
    disappears. Sampled across the whole series, monthly.
    """
    seen = set()
    for year in range(2011, 2027):
        for month in range(1, 13):
            asof = f"{year}-{month:02d}-15"
            if asof < bars[0].date or asof > "2026-07-19":
                continue
            seen.add(compute(bars, onchain, EpisodeState(), asof=asof).state.status)
    assert EpisodeStatus.CLOSED not in seen
    assert EpisodeStatus.EXPIRED not in seen
    assert {EpisodeStatus.WATCHING, EpisodeStatus.CONFIRMED,
            EpisodeStatus.DISTRIBUTING} <= seen
    # EP1 is EXPIRED in the record but never reports as such while it is live.
    assert {e["episode"] for e in cy1["episodes"] if e["status"] == "expired"} \
        == {"EP1-2011-11-27"}
    assert compute(bars, onchain, EpisodeState(),
                   asof="2013-06-15").state.trigger_date == "2011-11-21"


# --------------------------------------------------------------------------
# 9. the stop — synthetic, because no historical episode ever touched EL*
# --------------------------------------------------------------------------

#: EP6's live anchors (SPEC §13.3, PRD §8): D = the 126,199.63 ATH week, running
#: low 57,800.19, operative LH 82,850. The synthetic continues the real series
#: rather than inventing one, so the trigger, D, the LH scan and EL* are all the
#: engine's own output on real data and only the future is fabricated.
EP6_EL = Decimal("57800.19")
EP6_LH = Decimal("82850")


def _extend(bars, rows):
    """Append synthetic daily bars from 2026-07-21 (the day after the data end).

    `rows` is a list of (high, low) pairs; open and close are placed inside the
    range so the weekly close series stays smooth — a sharp weekly close would
    drag RSI-14 under 35 and arm a *new* episode, which would silently change
    which episode `compute` is reporting on.
    """
    out = list(bars)
    day = _date.fromisoformat("2026-07-21")
    for high, low in rows:
        mid = (high + low) / 2
        out.append(Bar(date=day.isoformat(), open=mid, high=high, low=low,
                       close=mid))
        day += timedelta(days=1)
    return out


def _ramp_through_the_lh(pad: int = 0, extra: int = 0):
    """Sessions climbing from the last real close through 82,850.

    `pad` prepends flat sessions, which shifts where in the week the break
    lands — the two BoS days in the record both print their own week's high, so
    a mid-week break has to be constructed to be observed at all. `extra`
    continues the climb past the break, which is what makes the BoS week's high
    keep rising after the BoS day.
    """
    rows = [(Decimal("65900"), Decimal("64900"))] * pad
    price = Decimal("65300")
    while price < Decimal("84000"):
        rows.append((price + Decimal("600"), price - Decimal("400")))
        price += Decimal("1500")
    for _ in range(extra):
        rows.append((price + Decimal("600"), price - Decimal("400")))
        price += Decimal("1500")
    return rows


def _bos_of(bars, onchain, rows, filled=frozenset(), held=Decimal(0)):
    extended = _extend(bars, rows)
    return extended, compute(extended, onchain, EpisodeState(),
                             asof=extended[-1].date, filled_purposes=filled,
                             held_units=held)


def test_a_synthetic_break_of_the_live_lh_confirms_ep6(bars, onchain):
    """The premise of the stop tests: the fabricated future activates EP6 on a
    break of 82,850, with EL* frozen at the real running low."""
    _extended, r = _bos_of(bars, onchain, _ramp_through_the_lh(),
                           filled=RUNG_FILLED, held=RUNG_UNITS)
    assert r.state.status is EpisodeStatus.CONFIRMED
    assert r.state.trigger_date == "2026-01-26"
    assert r.state.operative_lh == EP6_LH
    assert r.state.el_star == EP6_EL
    stop = _by_purpose(r)[OrderPurpose.STOP]
    assert stop.price == EP6_EL
    assert stop.kind is OrderKind.STOP_MARKET
    # Sized from what is HELD, never from the capital plan (orders.py).
    assert stop.units == RUNG_UNITS


def test_the_bos_week_high_is_running_while_the_week_is_open(bars, onchain):
    """Never the settled value — that would be a lookahead — and never lower
    than what has actually printed.

    The padded ramp breaks 82,850 early in a week and keeps climbing, so the
    week's eventual high is well above the break day's. A run inside that week
    must report the running value and must not price a ladder off it.
    """
    rows = _ramp_through_the_lh(pad=2, extra=3)
    extended = _extend(bars, rows)
    bos = compute(extended, onchain, EpisodeState(),
                  asof=extended[-1].date).state.bos_date
    assert week_end(monday_of(bos)) > extended[-1].date, \
        "the break must land inside a week that is still open"

    seen = []
    for bar in [b for b in extended if b.date >= bos]:
        r = compute(extended, onchain, EpisodeState(), asof=bar.date)
        assert r.state.bos_date == bos
        assert not (_purposes(r) & (RUNGS | {OrderPurpose.BREAKOUT}))
        seen.append(r.state.bos_week_high)
    assert seen == sorted(seen), "a weekly high cannot fall"
    assert seen[0] < seen[-1], "the running high never moved: no lookahead check"
    assert seen[-1] == max(b.high for b in extended if b.date >= bos)


def test_a_post_bos_new_low_stops_the_episode_without_moving_the_anchor(
        bars, onchain):
    """§6.3 as narrowed by §13.1: a touch of the frozen EL*, from the BoS onward.

    A stopped episode is over — nothing rests, and the reconciler clears the
    book. The wick is a single session so the weekly close barely moves and no
    new episode arms behind it.

    The wick prints 57,000, BELOW EL*. That is what separates the frozen anchor
    from a still-running minimum: §13.1 freezes `episode_low` at the BoS, so
    `running_low` must still read 57,800.19 and the stop must still be priced
    there. An engine that kept the minimum running would report 57,000 and
    would have priced the stop under the level it just breached.
    """
    rows = _ramp_through_the_lh()
    rows += [(Decimal("83000"), Decimal("82000"))] * 6      # settle the BoS week
    rows += [(Decimal("82500"), Decimal("57000"))]          # the breach
    # The stop executed, so the ledger says so: bought a rung, sold it on the
    # STOP, holding nothing. `held_units > 0` here is a venue divergence and is
    # refused instead — see the test below.
    extended, r = _bos_of(bars, onchain, rows,
                          filled=RUNG_FILLED | {OrderPurpose.STOP})
    assert r.state.status is EpisodeStatus.STOPPED
    assert r.orders == ()
    assert r.state.el_star == EP6_EL
    assert r.state.running_low == EP6_EL
    assert min(b.low for b in extended if b.date > r.state.bos_date) < EP6_EL

    # One session earlier the episode is alive and the stop is resting.
    alive = compute(extended[:-1], onchain, EpisodeState(),
                    asof=extended[-2].date, filled_purposes=RUNG_FILLED,
                    held_units=RUNG_UNITS)
    assert alive.state.status is EpisodeStatus.CONFIRMED
    assert OrderPurpose.STOP in _purposes(alive)


def test_a_touch_of_el_star_to_the_cent_stops_the_episode(bars, onchain):
    """"Touch", not "breach": the low equals EL* exactly."""
    rows = _ramp_through_the_lh()
    rows += [(Decimal("83000"), Decimal("82000"))] * 6
    rows += [(Decimal("82500"), EP6_EL)]
    _extended, r = _bos_of(bars, onchain, rows,
                           filled=RUNG_FILLED | {OrderPurpose.STOP})
    assert r.state.status is EpisodeStatus.STOPPED


def test_the_bos_day_itself_cannot_stop_the_episode(bars, onchain):
    """EL* is the running low *through the BoS day inclusive*, so on that day
    `low <= EL*` is true by construction whenever the BoS day printed the low.
    A non-strict scan therefore stops every such episode the instant it
    activates. The BoS bar here breaks 82,850 and prints the episode low in the
    same session.
    """
    rows = _ramp_through_the_lh()[:-1]
    rows += [(Decimal("83500"), Decimal("50000"))]      # break and crash, one bar
    extended, r = _bos_of(bars, onchain, rows)
    assert r.state.status is EpisodeStatus.CONFIRMED
    assert r.state.el_star == Decimal("50000")
    assert r.state.bos_date == extended[-1].date


# --------------------------------------------------------------------------
# 10. one chain, two callers
# --------------------------------------------------------------------------

def test_compute_and_the_gate_fixture_derive_the_same_episode_chain(
        bars, onchain, episode_scope):
    """`chain_episodes` is engine code that both `compute` and the gate suite
    call. Before Task 14 the chain existed only in `tests/gates/conftest.py`,
    so "the gates pass" certified test-local orchestration rather than shipped
    code, and a mutation of the rule could pass the gates while `compute` did
    something else.
    """
    asof = "2026-07-19"
    weeks = _weeks_of(bars, asof)
    visible = [b for b in bars if b.date <= asof]
    episodes = chain_episodes(weeks, visible, find_triggers(weeks, _rsi_of(weeks)),
                              data_end=asof)
    assert [ep.trigger for ep in episodes] == episode_scope["triggers"]
    for ep in episodes:
        d_week, bos, broken = episode_scope["scopes"][ep.trigger]
        assert (ep.d_week, ep.bos_date) == (d_week, bos)
        assert (ep.broken_lh.price if ep.broken_lh else None) == broken
    # ...and the state `compute` publishes is the last link of that chain.
    live = compute(bars, onchain, EpisodeState(), asof=asof).state
    assert live.trigger_date == episodes[-1].trigger
    assert live.scope_start == episodes[-1].d_week


def test_an_episode_cannot_activate_after_its_successor_triggers(bars):
    """§1: an episode "expires if no valid BoS ever prints (bounded by the next
    episode's trigger)".

    **The frozen data never exercises this bound**, which is why it is tested
    with a fabricated successor rather than left to the gates: EP1 is the only
    expired episode and it expires with zero LH candidates (the §13.3 trigger-
    anchor guard — itself resting on §14 OQ-6's suspect 2011 wick), so removing
    the bound entirely changes nothing on real history. A mutation of
    `end=era_end` to `end=data_end` survives the whole suite without this.

    EP2 really did break 305.00 on 2015-01-26. Insert a successor trigger one
    week earlier and that break belongs to the successor's era, so EP2 must
    report no activation at all.
    """
    asof = "2016-01-04"
    weeks = _weeks_of(bars, asof)
    visible = [b for b in bars if b.date <= asof]
    real = find_triggers(weeks, _rsi_of(weeks))
    assert real[:2] == ["2011-11-21", "2014-09-22"]

    unbounded = chain_episodes(weeks, visible, real, data_end=asof)
    assert unbounded[1].bos_date == "2015-01-26"

    fabricated = real[:2] + ["2015-01-19"] + real[2:]
    bounded = chain_episodes(weeks, visible, fabricated, data_end=asof)
    assert bounded[1].trigger == "2014-09-22"
    assert bounded[1].bos_date is None, \
        "EP2 activated on a break that belongs to its successor's era"
    assert bounded[1].broken_lh is None
    # ...and the successor's window still starts where EP2's activation would
    # have: it did not activate, so the chain carries the older window forward.
    assert bounded[2].window_start == bounded[1].window_start


def test_the_mirror_ordering_boundaries_are_unexercised_by_this_data(bars, cy1):
    """Three `<=`/`<` boundaries in `_mirror_lines` that the record cannot pin.

    Mutation testing found all three surviving, and rather than leave that as a
    silent hole or invent a synthetic for a reading that §14 OQ-7(b) is likely
    to replace outright, the premise is asserted: on every activated episode,
    between arming and the first signal,

      1. no swing confirms and is broken on the SAME day (§6.2: confirmation
         strictly precedes the break) — note the event class does occur
         elsewhere in every era, 16 times in EP2's, so this is a fact about the
         window, not about the data being too smooth;
      2. the arming day is itself never a signal day (§6.2: arming precedes the
         signal);
      3. the signal day's own high is never the lifetime argmax that prices the
         fill.

    If a data refresh makes any of them live, this fails and the corresponding
    boundary stops being a free choice.
    """
    from engine.bars import to_weeks
    from engine.structure import find_swing_lows

    episodes = {e["episode"]: e for e in cy1["episodes"] if e["status"] == "bos"}
    assert len(episodes) == 4
    armings = {row["episode"]: row["exit_ext_1272"]["date"]
               for row in episodes.values()}
    for label, armed in armings.items():
        # The BoS is the era start; take it from the engine's own chain.
        weeks = _weeks_of(bars, armed)
        visible = [b for b in bars if b.date <= armed]
        chain = chain_episodes(weeks, visible, find_triggers(weeks, _rsi_of(weeks)),
                               data_end=armed)
        bos = next(ep.bos_date for ep in chain
                   if ep.trigger == monday_of(label.split("-", 1)[1]))
        era = [b for b in bars if b.date >= bos]
        swings = find_swing_lows(to_weeks(era), era)

        signal = None
        for bar in era:
            if bar.date <= armed:
                continue
            confirmed = [s for s in swings if s.confirmed_at < bar.date]
            if confirmed and bar.low < max(confirmed,
                                           key=lambda s: s.week_monday).low:
                signal = bar
                break
        assert signal is not None, label

        # 1 — same-day confirm-and-break, inside the window that decides
        assert not [s for s in swings for b in era
                    if b.date == s.confirmed_at and b.low < s.low
                    and armed < b.date <= signal.date], label
        # ...but the event class is real, elsewhere in the same era.
        assert [s for s in swings for b in era
                if b.date == s.confirmed_at and b.low < s.low], label
        # 2 — the arming day is not itself a signal
        arming_bar = next(b for b in era if b.date == armed)
        earlier = [s for s in swings if s.confirmed_at < armed]
        assert not (earlier and arming_bar.low < max(
            earlier, key=lambda s: s.week_monday).low), label
        # 3 — the signal day's high is not the top the fill is priced from
        assert signal.high != max(b.high for b in era
                                  if b.date <= signal.date), label


def test_each_episodes_window_starts_at_the_previous_activation(bars,
                                                                episode_scope):
    """SPEC §13.3's chaining rule, and the two places it is load-bearing:
    EP4's D is the June-2019 week (13,970), not the Dec-2017 ATH — its exit
    anchor. Bounding D at the era end instead leaks the next bull run in.
    """
    episodes = {ep.trigger: ep for ep in episode_scope["episodes"]}
    assert episodes["2020-03-09"].d_week == "2019-06-24"
    assert episodes["2020-03-09"].window_start == episodes["2018-11-19"].bos_date
    assert episodes["2022-05-16"].window_start == episodes["2020-03-09"].bos_date
    assert episodes["2011-11-21"].window_start == "2011-08-15"   # data start


# --------------------------------------------------------------------------
# 11. the input contract with M2
# --------------------------------------------------------------------------
#
# `held_units`, `filled_purposes` and `asof` are three independent
# reconstructions of the same account and the same day. M2 wires them from
# different places — trade history, order book, cron — so they can lag
# independently, and each individual value looks perfectly reasonable while the
# combination does not. All three combinations below produce order sets that are
# wrong in the expensive direction, which is why they are refused rather than
# clamped: under a desired-state reconciler a silently-wrong set is worse than a
# refused run, and a refused run cancels nothing.

def test_every_order_purpose_is_classified_by_side():
    """`BUY_PURPOSES | SELL_PURPOSES` must cover `OrderPurpose` exactly.

    The coherence guard asks "did anything buy-side fill?", so a purpose missing
    from both sets would be invisible to it and a purpose in both would make the
    question meaningless. Adding an `OrderPurpose` without classifying it fails
    here rather than quietly widening the hole the guard exists to close.
    """
    from engine.orders import BUY_PURPOSES, SELL_PURPOSES
    assert BUY_PURPOSES | SELL_PURPOSES == set(OrderPurpose)
    assert not (BUY_PURPOSES & SELL_PURPOSES)


def test_holding_units_with_nothing_filled_is_refused(bars, onchain):
    """The contradiction that costs the most, and the reason the *defaults* are
    not the conservative choice they look like on the buy side.

    `filled_purposes=frozenset()` selects §14 OQ-3's roll: the whole unfilled
    accumulation pool joins the ladder, so the rungs go 3 / 6 / 12 instead of
    2 / 4 / 8 and the breakout carries the entire 21-unit book instead of 14.
    SPEC §14 OQ-3 records accumulation filling 3/3 in every activated episode,
    so that is the branch that has never once happened. Combine it with
    `held_units=7` and the engine rests a 21-unit ladder and a 7-unit stop in
    the same tuple, from inputs that cannot both be true.
    """
    with pytest.raises(ValueError, match="incoherent ledger"):
        compute(bars, onchain, EpisodeState(), asof="2015-02-01",
                held_units=ACCUMULATED_UNITS)

    # The two branches this is protecting, measured rather than asserted in
    # prose — this is what the refused run would have emitted.
    aggressive = _by_purpose(compute(bars, onchain, EpisodeState(),
                                     asof="2015-02-01"))
    conservative = _by_purpose(compute(bars, onchain, EpisodeState(),
                                       asof="2015-02-01",
                                       filled_purposes=ACCUMULATED,
                                       held_units=ACCUMULATED_UNITS))
    assert aggressive[OrderPurpose.BREAKOUT].units == Decimal(21)
    assert conservative[OrderPurpose.BREAKOUT].units == Decimal(14)
    assert aggressive[OrderPurpose.LADDER_050].units == Decimal(3)
    assert conservative[OrderPurpose.LADDER_050].units == Decimal(2)


def test_buying_and_then_holding_nothing_is_refused(bars, onchain):
    """The converse: fills on record, no position, and nothing sold to explain
    where it went."""
    with pytest.raises(ValueError, match="incoherent ledger"):
        compute(bars, onchain, EpisodeState(), asof="2015-02-01",
                filled_purposes=ACCUMULATED, held_units=Decimal(0))
    # A sell-side fill is exactly what makes it coherent again.
    ok = compute(bars, onchain, EpisodeState(), asof="2017-06-01",
                 filled_purposes=ARMED | {OrderPurpose.MIRROR},
                 held_units=Decimal(0))
    assert ok.state.status is EpisodeStatus.DISTRIBUTING


@pytest.mark.parametrize("filled,held", [
    (frozenset(), Decimal(0)),                       # flat, nothing done
    (ACCUMULATED, ACCUMULATED_UNITS),                # accumulation 3/3
    (ARMED, ARMED_UNITS),                            # ...half sold at Exit 1
    (RUNG_FILLED, RUNG_UNITS),                       # EP6's ladder-only path
])
def test_the_coherent_ledgers_are_accepted(bars, onchain, filled, held):
    """The guard must not be so strict that it refuses the real shapes."""
    r = compute(bars, onchain, EpisodeState(), asof="2023-03-01",
                filled_purposes=filled, held_units=held)
    assert r.state.status is EpisodeStatus.CONFIRMED


def test_a_stale_price_feed_is_refused_instead_of_market_selling(bars, onchain):
    """`asof` is a clock; `bars` is a price feed. Two decisions read the clock
    alone — the BoS-week release and §6.2's 8-week deadline — so a feed that
    stops updating while the cron keeps firing walks the engine forward on
    imagined time rather than freezing it.

    The measured consequence, and the reason this is engine-side: with EP5
    positioned, bars truncated at 2025-01-20 and `asof="2025-03-20"`, the mirror
    flips to a MARKET order with `price=None` — the engine market-sells the
    whole remaining position because the prices stopped arriving — and stays
    there for every later `asof`.
    """
    stale = [b for b in bars if b.date <= "2025-01-20"]
    with pytest.raises(ValueError, match="stale price feed"):
        compute(stale, onchain, EpisodeState(), asof="2025-03-20",
                filled_purposes=ARMED, held_units=ARMED_UNITS)

    # ...and it is not only the mirror: a full CONFIRMED set, breakout included,
    # would otherwise be published off bars ten months old.
    with pytest.raises(ValueError, match="stale price feed"):
        compute([b for b in bars if b.date <= "2015-02-01"], onchain,
                EpisodeState(), asof="2015-12-01")


def test_one_day_of_publisher_lag_is_tolerated(bars, onchain):
    """The run fires after the UTC close of `asof`, so that day's candle should
    exist — but a publisher that has not yet closed it must not halt an
    otherwise healthy system. One day is the whole allowance; two is a broken
    feed.
    """
    lagging = [b for b in bars if b.date <= "2023-02-28"]
    ok = compute(lagging, onchain, EpisodeState(), asof="2023-03-01",
                 filled_purposes=ACCUMULATED, held_units=ACCUMULATED_UNITS)
    assert ok.state.status is EpisodeStatus.CONFIRMED
    with pytest.raises(ValueError, match="stale price feed"):
        compute(lagging, onchain, EpisodeState(), asof="2023-03-02",
                filled_purposes=ACCUMULATED, held_units=ACCUMULATED_UNITS)


def test_an_empty_window_is_not_a_stale_feed(bars, onchain):
    """No bar at all is "no information", not "stale": there is nothing to be
    stale, so the prior state is returned and nothing is cancelled."""
    prior = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal(10))
    assert compute(bars, onchain, prior, asof="2009-01-01").state is prior


def test_stopped_while_still_holding_units_is_refused(bars, onchain):
    """A stopped episode rests nothing, and `()` means "cancel everything" to
    the reconciler — correct only if the stop actually executed.

    If it did not (venue outage, a gap straight through the level, a rejected
    size), the account is still long while the engine believes it is flat, and a
    silent `()` disarms that position permanently: the status never leaves
    STOPPED, so no stop and no exit is ever re-rested for the episode again.
    """
    rows = _ramp_through_the_lh()
    rows += [(Decimal("83000"), Decimal("82000"))] * 6
    rows += [(Decimal("82500"), Decimal("57000"))]
    with pytest.raises(ValueError, match="STOPPED but held_units"):
        _bos_of(bars, onchain, rows, filled=RUNG_FILLED, held=RUNG_UNITS)
    # Recording the STOP fill — which is what makes held_units 0 — clears it.
    _extended, r = _bos_of(bars, onchain, rows,
                           filled=RUNG_FILLED | {OrderPurpose.STOP})
    assert r.state.status is EpisodeStatus.STOPPED
    assert r.orders == ()
