"""EP2-EP5 structural regression against `cy1_lifecycle.json` — the reference
implementation (CLAUDE.md: "the reference implementation and the thing to
reproduce"; SPEC §11's own table is a transcription OF it).

WHY THIS FILE READS THE REFERENCE INSTEAD OF A HAND-TYPED TABLE
---------------------------------------------------------------
Mutation testing kills changes to *code*. It is structurally blind to a wrong
expected *constant*: a mis-transcribed number makes a test green against the
wrong target and no mutant can reveal it. This build has already produced five
wrong transcribed numbers (four in SPEC prose, one in an engine docstring), and
in every case the computed value was right and the copied one was wrong.

So every expected value below is read from the `cy1` fixture at run time. The
only literals in this file are in `test_the_reference_file_is_what_this_suite_
expects`, and they are asserted **against** the file — a typo there fails loudly
instead of silently re-aiming a test.

Two cautions on the reference file, both observed rather than assumed:

* **Numeric fields only.** Its `entry_rule` string still reads "gates: R15 unique
  passer", an overclaim SPEC §13.3a has since retired (R_e = 15 is the upper edge
  of a band, not a unique passer). Prose in that file is stale; the numbers are
  not.
* **`cash_flow`'s money fields are JSON integers** and `data/loaders.py` sets
  `parse_float=Decimal` but not `parse_int`, so they arrive as `int`. Nothing
  here does money arithmetic on them; anything that starts to must add
  `parse_int=Decimal` first.

WHAT IS ASSERTED, AND WHAT IS DELIBERATELY NOT
-----------------------------------------------
Asserted: fill dates, fill prices, accumulation line values, EL*, the prior-cycle
ATH, the 1.272 level, and both exits' dates and prices — SPEC §14's "assert
structural facts" list, all of which reconcile exactly. Since 2026-07-25 the
**buy side** as well: `bos_week_high`, the three ladder rungs (levels, weights
and the three fills that happened), and the breakout's level, size and fill day.
Fourteen of the twenty-one units are spent there and none of it was pinned; see
that section's own header for what the omission was hiding.

NOT asserted: pnl percentages. §11's figures disagree with the reference by
+0.5 to +1.1 points each (§14 OQ-4, explicitly non-blocking; owner 2026-07-24:
"the cumulative return is not really relevant"). That divergence is pinned as a
divergence in `test_pnl_is_not_asserted_because_spec_and_the_reference_disagree`,
so reconciling OQ-4 reports itself here rather than being absorbed.

THE MIRROR EXIT IS NOT DRIVEN BY `engine/`, AND IT SEPARATES TWO READINGS
-------------------------------------------------------------------------
§6.2's break detection and walk-forward fill have no engine implementation (see
`tests/gates/test_mirror_gate.py`'s module docstring) — only `find_swing_lows`
and `levels.mirror_target` exist. The harness below is therefore test-local, and
is cross-checked against `find_swing_lows` in
`test_the_local_swing_scan_reproduces_the_engine_under_reading_a` so that the
only thing it varies is the one predicate under test.

**New evidence for `find_swing_lows`' obligation 2.** Its docstring records two
readings of §6.2's "confirmed by a subsequent higher high" — (a) higher than the
swing week's own high, which the engine implements, and (b) higher than the
decline's argmax top, the strict §4.3 mirror — and states that G4 cannot separate
them. **EP2-EP5 do.** Under (b) all four reference mirror exits reproduce
exactly; under (a) EP5 exits 2025-01-15 @ 98,804.845 instead of 2025-03-02 @
93,923.26. That is a 6-week, 5.2% difference in a live exit, so the engine as it
stands cannot reproduce EP5's Exit 2. Both outcomes are pinned below rather than
one of them being quietly chosen — the decision is the owner's (§9).
"""
from datetime import date, timedelta
from decimal import Decimal, localcontext

import pytest

from engine.bars import monday_of, to_weeks
from engine.context import CTX
from engine.engine import compute
from engine.fills import buy_limit_fill, buy_stop_fill, sell_limit_fill
from engine.levels import LADDER_UNITS, extension_1272, mirror_target
from engine.lifecycle import freeze_el, prior_cycle_ath
from engine.lines import lines_for
from engine.structure import R_DOWN_DEFAULT, find_swing_lows
from engine.types import (EpisodeState, EpisodeStatus, OrderKind,
                          OrderPurpose, OrderSide)

#: The four episodes that activated. EP1 expired and EP6 is still watching, so
#: neither has a fill; `test_the_unactivated_episodes_have_no_fills` asserts that
#: rather than this list quietly omitting them.
ACTIVATED = ("EP2-2014-09-28", "EP3-2018-11-25", "EP4-2020-03-15",
             "EP5-2022-05-22")

#: §6.2's confirmation reference price, the two readings of `find_swing_lows`'
#: obligation 2. (a) is what the engine implements.
CONFIRM_WEEK_HIGH = "a"
CONFIRM_DECLINE_TOP = "b"

#: The reference's reserve rows, in its own order, joined to the engine's ladder
#: BY NAME. `levels.LADDER` and this dict are two dicts with matching keys and no
#: guaranteed shared ordering, so zipping them would be silently wrong the day
#: either is reordered — the same argument `orders.LADDER_PURPOSE` makes.
RESERVE = {"F_0.5": ("0.5", OrderPurpose.LADDER_050),
           "F_0.62": ("0.62", OrderPurpose.LADDER_062),
           "F_0.786": ("0.786", OrderPurpose.LADDER_0786)}

#: Accumulation filled 3/3 in every activated episode (§14 OQ-3) — 7 units.
ACCUMULATED = frozenset({OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3})
ACCUMULATED_UNITS = Decimal(7)

#: Half a cent. The reference records prices to 2dp and this suite compares the
#: engine's exact arithmetic against them, so the tolerance is exactly the
#: rounding the reference applied — see
#: `test_the_2dp_record_is_ambiguous_only_at_an_exact_half_cent`, which shows
#: that a plain `quantize` cannot be used and why the tolerance hides nothing.
HALF_CENT = Decimal("0.005")


def _2dp(value: Decimal) -> Decimal:
    """The reference records prices to 2dp; the engine returns exact arithmetic
    (`engine/levels.py`: "the 2dp is presentational, not normative")."""
    return value.quantize(Decimal("0.01"))


def _week_end(monday: str) -> str:
    y, m, d = (int(x) for x in monday.split("-"))
    return (date(y, m, d) + timedelta(days=6)).isoformat()


def _day_before(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return (date(y, m, d) - timedelta(days=1)).isoformat()


def _first_actionable_day(trigger_monday: str) -> str:
    """The Monday AFTER the trigger week.

    `find_triggers` returns a week LABEL, and that week's RSI is not knowable
    until its Sunday close — treating the Monday as tradeable is a one-week
    lookahead (CLAUDE.md rule 5, `engine/lifecycle.py`). Load-bearing on real
    data, not a formality: see
    `test_accumulation_may_not_start_inside_the_trigger_week`.
    """
    y, m, d = (int(x) for x in trigger_monday.split("-"))
    return (date(y, m, d) + timedelta(days=7)).isoformat()


# --------------------------------------------------------------------------
# harnesses
# --------------------------------------------------------------------------

def _accumulation_fills(bars, onchain, first_day, bos):
    """Walk-forward accumulation (SPEC §3, §13.6).

    Each tranche fills on the first day in [first_day, BoS-day inclusive] whose
    low touches **that day's** line value. The lines move daily, so the level a
    fill is tested against is the level of the day it is tested on.

    Missing on-chain data raises rather than skipping the day: a skipped day is a
    silently missed fill, and the four windows are fully covered (asserted in
    `test_the_accumulation_windows_have_complete_on_chain_coverage`).
    """
    out = []
    for tranche in range(3):
        hit = None
        for bar in bars:
            if bar.date < first_day or bar.date > bos:
                continue
            line = lines_for(onchain[bar.date])[tranche]
            fill = buy_limit_fill(bar, line)
            if fill is not None:
                hit = (bar.date, fill, line)
                break
        out.append(hit)
    return out


def _exit1_fill(bars, level, bos):
    """§6.1: the resting sell-limit at the 1.272 extension, from the BoS onward.

    The BoS-day boundary is INERT on all four episodes (every Exit 1 is years
    later), so this gate does not pin whether the level rests on the BoS day
    itself or the day after. Stated rather than implied.
    """
    for bar in bars:
        if bar.date < bos:
            continue
        fill = sell_limit_fill(bar, level)
        if fill is not None:
            return bar.date, fill
    return None, None


class _FirstHigherHigh:
    """"First bar after `t` whose high exceeds `x`", answered without rescanning.

    The naive `next(b for b in bars if b.date > t and b.high > x)` is what
    `find_swing_lows` runs, and on a 4,200-bar episode lifetime with ~500
    candidates it costs ~2M comparisons per scan — 26s across this file. This is
    the same query answered off a next-greater-element staircase: from the first
    bar after `t`, hop to the next strictly higher high until one clears `x`.
    Every bar skipped by a hop has a high at or below the one hopped from, so it
    could not have cleared `x` either.

    It is an optimisation of the harness, never of the engine, and
    `test_the_local_swing_scan_reproduces_the_engine_under_reading_a` compares
    the result to `find_swing_lows` element for element — so a wrong answer here
    fails as a mismatch rather than passing as a different rule.
    """

    def __init__(self, bars):
        self.dates = [b.date for b in bars]
        self.highs = [b.high for b in bars]
        self.nge = [None] * len(bars)
        stack = []
        for i in range(len(bars) - 1, -1, -1):
            while stack and self.highs[stack[-1]] <= self.highs[i]:
                stack.pop()
            self.nge[i] = stack[-1] if stack else None
            stack.append(i)

    def after(self, t, x):
        from bisect import bisect_right
        i = bisect_right(self.dates, t)
        if i >= len(self.dates):
            return None
        while i is not None and self.highs[i] <= x:
            i = self.nge[i]
        return None if i is None else self.dates[i]


def _swing_lows(weeks, bars, confirm, r_down=R_DOWN_DEFAULT):
    """`find_swing_lows` with §6.2's confirmation reference price parametrised.

    Verified identical to the engine under `CONFIRM_WEEK_HIGH` — that check is a
    test, not a comment, so this cannot drift into a second implementation of the
    detector while claiming to isolate one predicate. That includes the pinned
    Decimal context on the one inexact expression: at ambient precision the
    decline percentages differ from the engine's in the 29th digit, which the
    equality check catches (and which is exactly the class of drift
    `engine/context.py` exists to stop).
    """
    index = _FirstHigherHigh(bars)
    out = []
    running_top = None
    for i, cand in enumerate(weeks):
        if i == 0:
            running_top = cand
            continue
        top = running_top
        if cand.high > running_top.high:
            running_top = cand
        if top.high <= 0:
            continue
        with localcontext(CTX):
            decline = (top.high - cand.low) / top.high * Decimal(100)
        if decline < r_down:
            continue
        reference_price = cand.high if confirm == CONFIRM_WEEK_HIGH else top.high
        confirmed_at = index.after(_week_end(cand.monday), reference_price)
        if confirmed_at is not None:
            out.append((cand.monday, cand.low, confirmed_at, decline,
                        top.monday, top.high))
    return out


#: `_swing_lows` is deterministic in (scope start, confirmation reading) and the
#: `bars` fixture is session-scoped and frozen, so the scans are memoised across
#: the three tests that need them. Keyed on the scope start rather than on the
#: bar list, which is safe only because every call in this file passes the same
#: full history — stated so a future caller slicing `bars` differently notices.
_SWING_SCANS: dict[tuple[str, str, Decimal], list] = {}


def _lifetime_swings(bars, scope_start, confirm, r_down=R_DOWN_DEFAULT):
    key = (scope_start, confirm, r_down)
    if key not in _SWING_SCANS:
        window = [b for b in bars if b.date >= scope_start]
        _SWING_SCANS[key] = _swing_lows(to_weeks(window), window, confirm, r_down)
    return _SWING_SCANS[key]


def _mirror_exit(bars, scope_start, armed_from, confirm, top_from_swing=False,
                 r_down=R_DOWN_DEFAULT):
    """§6.2 end to end, over the position lifetime.

    Scope = [BoS, data end] (§6.2: "only structure formed during the episode's
    uptrend"). Arming = the Exit 1 print. Signal = the first day after arming
    whose low trades below the most recent swing confirmed **strictly before**
    that day. Fill = walk-forward `(top_high + low_so_far) / 2`, `low_so_far`
    updated before that day's high is tested, break day excluded.

    `top_from_swing` substitutes the swing's own decline top for the lifetime
    argmax — the trap `find_swing_lows` names ("`top_high` IS NOT the mirror
    fill's `top_high`"). It breaks every episode; see the test.
    """
    window = [b for b in bars if b.date >= scope_start]
    swings = _lifetime_swings(bars, scope_start, confirm, r_down)

    signal = broken = None
    for bar in window:
        if bar.date <= armed_from:
            continue
        confirmed = [s for s in swings if s[2] < bar.date]
        if not confirmed:
            continue
        latest = max(confirmed, key=lambda s: s[0])
        if bar.low < latest[1]:
            signal, broken = bar, latest
            break
    if signal is None:
        return None

    top = broken[5] if top_from_swing else max(
        b.high for b in window if b.date <= signal.date)
    low_so_far = signal.low
    for bar in window:
        if bar.date <= signal.date:
            continue
        low_so_far = min(low_so_far, bar.low)
        fill = sell_limit_fill(bar, mirror_target(top, low_so_far))
        if fill is not None:
            return {"signal": signal.date, "swing_week": broken[0], "top": top,
                    "date": bar.date, "price": fill}
    return None


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def reference(cy1):
    return {e["episode"]: e for e in cy1["episodes"]}


@pytest.fixture(scope="module")
def scope(bars, weeks, cy1, episode_scope):
    """Reference episode label -> the ENGINE's derived facts for it.

    The trigger is derived from the label itself (`monday_of` on the reference's
    Sunday-anchored date, §13.10) rather than pasted, so a label that the engine
    does not detect as a trigger fails here instead of being looked past.
    """
    out = {}
    for row in cy1["episodes"]:
        label = row["episode"]
        trigger = monday_of(label.split("-", 1)[1])
        assert trigger in episode_scope["triggers"], (
            f"engine found no trigger at {trigger} for reference episode "
            f"{label}; triggers are {episode_scope['triggers']}")
        d_week, bos, _broken = episode_scope["scopes"][trigger]
        out[label] = {
            "trigger": trigger,
            "d_week": d_week,
            "bos": bos,
            "first_day": _first_actionable_day(trigger),
            "el_star": freeze_el(bars, d_week, bos) if bos else None,
            "prior_ath": prior_cycle_ath(weeks, trigger)[0],
        }
    return out


# --------------------------------------------------------------------------
# the transcription guard
# --------------------------------------------------------------------------

def test_the_reference_file_is_what_this_suite_expects(cy1, reference):
    """The ONLY literals in this file, and they are checked against the file.

    Everything else reads `cy1` at run time, so this is where a data refresh or a
    swapped reference file has to report itself. It is also the one place a
    transcription error can occur, and here an error FAILS rather than re-aiming
    a downstream assertion at the wrong target.
    """
    assert cy1["data_end"] == "2026-07-20"
    assert [e["episode"] for e in cy1["episodes"]] == [
        "EP1-2011-11-27", "EP2-2014-09-28", "EP3-2018-11-25",
        "EP4-2020-03-15", "EP5-2022-05-22", "EP6-2026-02-01",
    ]
    assert [e["episode"] for e in cy1["episodes"] if e["status"] == "bos"] == \
        list(ACTIVATED)
    assert reference["EP1-2011-11-27"]["status"] == "expired"
    assert reference["EP6-2026-02-01"]["status"] == "watching"

    # The four structural rows, in the reference's own units.
    expected = {
        "EP2-2014-09-28": {
            "acc": [("2014-10-04", "346.70"), ("2014-10-04", "335.69"),
                    ("2014-10-04", "324.68")],
            "el": "152.40", "ath": "1163.00",
            "exit1": ("2017-05-02", "1437.88"),
            "exit2": ("2017-07-20", "2405.00"),
        },
        "EP3-2018-11-25": {
            "acc": [("2018-11-26", "4088.69"), ("2018-11-26", "4088.69"),
                    ("2018-11-26", "4088.69")],
            "el": "3156.26", "ath": "19798.68",
            "exit1": ("2020-12-25", "24325.42"),
            "exit2": ("2021-04-28", "55892.00"),
        },
        "EP4-2020-03-15": {
            "acc": [("2020-03-16", "5360.33"), ("2020-03-16", "5135.22"),
                    ("2020-03-16", "4703.98")],
            "el": "3782.13", "ath": "19798.68",
            "exit1": ("2020-12-19", "24155.18"),
            "exit2": ("2021-04-28", "55892.00"),
        },
        "EP5-2022-05-22": {
            "acc": [("2022-06-13", "23188.45"), ("2022-06-14", "21260.53"),
                    ("2022-06-18", "19078.10")],
            "el": "15476.00", "ath": "69000.00",
            "exit1": ("2024-11-11", "83558.53"),
            "exit2": ("2025-03-02", "93923.26"),
        },
    }
    for label, exp in expected.items():
        ref = reference[label]
        assert [(a["date"], a["px"]) for a in ref["accumulation"]] == \
            [(d, Decimal(p)) for d, p in exp["acc"]]
        assert ref["anchors"]["episode_low"] == Decimal(exp["el"])
        assert ref["anchors"]["prior_ath"] == Decimal(exp["ath"])
        assert (ref["exit_ext_1272"]["date"],
                ref["exit_ext_1272"]["px"]) == (exp["exit1"][0],
                                                Decimal(exp["exit1"][1]))
        assert (ref["exit_mirror"]["date"],
                ref["exit_mirror"]["px"]) == (exp["exit2"][0],
                                              Decimal(exp["exit2"][1]))
        # §13.9: every one of these is a 50% bounce fill, never the 8-week
        # market fallback. If a rule change flips one to "fallback" the exit
        # price becomes a market print and this table stops meaning what it says.
        assert ref["exit_mirror"]["mode"] == "fill_50"

    # --- the BUY side, same treatment ------------------------------------
    # Every buy-side assertion in this file reads these fields at run time, so
    # this is where a data refresh has to report itself for them too. The rungs
    # are listed in the reference's F_0.5 / F_0.62 / F_0.786 order as
    # (level, fill date or None, fill price or None); the breakout as
    # (date, price, units).
    expected_buy = {
        "EP2-2014-09-28": {
            "leg_high": "309.90",
            "reserve": [("231.15", "2015-02-02", "226.93"),
                        ("212.25", "2015-02-05", "212.25"),
                        ("186.10", None, None)],
            "breakout": ("2015-07-12", "309.90", "8"),
        },
        "EP3-2018-11-25": {
            "leg_high": "5275.01",
            "reserve": [("4215.64", None, None), ("3961.39", None, None),
                        ("3609.67", None, None)],
            "breakout": ("2019-04-08", "5275.01", "14"),
        },
        "EP4-2020-03-15": {
            "leg_high": "12123.46",
            "reserve": [("7952.80", None, None), ("6951.84", None, None),
                        ("5567.17", None, None)],
            "breakout": ("2020-08-17", "12123.46", "14"),
        },
        "EP5-2022-05-22": {
            "leg_high": "25250.00",
            "reserve": [("20363.00", "2023-03-09", "20363.00"),
                        ("19190.12", None, None), ("17567.64", None, None)],
            "breakout": ("2023-03-14", "25250.00", "12"),
        },
    }
    for label, exp in expected_buy.items():
        ref = reference[label]
        assert ref["anchors"]["leg_high"] == Decimal(exp["leg_high"])
        assert [r["name"] for r in ref["reserve"]] == list(RESERVE)
        for row, (lvl, fill_date, px) in zip(ref["reserve"], exp["reserve"]):
            assert row["lvl"] == Decimal(lvl)
            assert row["filled"] is (fill_date is not None)
            assert row.get("date") == fill_date
            assert row.get("px") == (None if px is None else Decimal(px))
        assert (ref["breakout"]["date"], ref["breakout"]["px"],
                ref["breakout"]["units"]) == (exp["breakout"][0],
                                              Decimal(exp["breakout"][1]),
                                              Decimal(exp["breakout"][2]))


# --------------------------------------------------------------------------
# anchors
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", ACTIVATED)
def test_anchors_reproduce(label, scope, reference):
    """EL* and the prior-cycle ATH, engine vs reference.

    They are asserted TOGETHER because EP4 is the episode that proves they are
    different objects: its exit anchor is the Dec-2017 19,798.68 while its
    structural anchor D is the June-2019 13,970 week (§13.3). An engine that
    conflated them still gets EL* right and Exit 1 wrong.
    """
    ref, got = reference[label], scope[label]
    assert got["el_star"] == ref["anchors"]["episode_low"]
    assert got["prior_ath"] == ref["anchors"]["prior_ath"]
    # EP3 and EP4 share one prior ATH while holding different EL* — §14 OQ-1's
    # concurrent-episode case, and the reason the two anchors cannot be merged.
    assert reference["EP3-2018-11-25"]["anchors"]["prior_ath"] == \
        reference["EP4-2020-03-15"]["anchors"]["prior_ath"]
    assert scope["EP3-2018-11-25"]["el_star"] != scope["EP4-2020-03-15"]["el_star"]


# --------------------------------------------------------------------------
# accumulation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", ACTIVATED)
def test_accumulation_fills_reproduce(label, bars, onchain, scope, reference):
    """All twelve tranches: date, fill price, and the line the fill was tested
    against — walking forward from the first actionable day, never asking the
    reference where to look.

    The line value is asserted as well as the price because on EP3 all three
    prices are identical (the gap fill) and on EP2/EP4/EP5 the price simply IS
    the line; without the line, a rule that priced every tranche off T1 would
    still reproduce EP3 and half of EP4.
    """
    ref, got = reference[label], scope[label]
    fills = _accumulation_fills(bars, onchain, got["first_day"], got["bos"])
    for tranche, (fill, expected) in enumerate(zip(fills, ref["accumulation"])):
        assert fill is not None, f"{label} tranche {tranche} never filled"
        fill_date, fill_price, line = fill
        assert fill_date == expected["date"]
        assert _2dp(fill_price) == expected["px"]
        assert _2dp(line) == expected["line"]
    # The reference records these in T1/T2/T3 order and the tranches are priced
    # realized > midpoint > balanced, so the fills are non-increasing in price
    # and (T1 first) non-decreasing in date. EP5 is the episode where both are
    # strict; asserting it here pins that `lines_for` was indexed, not zipped in
    # some other order.
    prices = [_2dp(f[1]) for f in fills]
    assert prices == sorted(prices, reverse=True)


@pytest.mark.parametrize("label", ACTIVATED)
def test_accumulation_may_not_start_inside_the_trigger_week(label, bars, onchain,
                                                            scope, reference):
    """CLAUDE.md rule 5 / §13.6: the trigger Monday is a week LABEL, and that
    week's RSI is not knowable until its Sunday close.

    Starting the walk on the trigger Monday is a one-week lookahead, and it is
    **observably wrong on EP3 and EP4** — EP3 fills 2018-11-19/20/23 at
    4,877.23 / 4,571.74 / 4,274.79 instead of 4,088.69 x3, and EP4 fills three
    days early on the COVID crash day itself. EP2 and EP5 are inert (no touch
    inside the trigger week), so the assertion is written as "the whole set
    changes for at least one episode" and the two live cases carry it.
    """
    ref, got = reference[label], scope[label]
    peeking = _accumulation_fills(bars, onchain, got["trigger"], got["bos"])
    honest = [(a["date"], a["px"]) for a in ref["accumulation"]]
    peeked = [(f[0], _2dp(f[1])) for f in peeking]
    if label in ("EP3-2018-11-25", "EP4-2020-03-15"):
        assert peeked != honest
    else:
        assert peeked == honest       # inert here, recorded as such


@pytest.mark.parametrize("label", ACTIVATED)
def test_accumulation_lines_reprice_every_day(label, bars, onchain, scope,
                                              reference):
    """SPEC §3 walk-forward: a fill is tested against THAT DAY's line.

    Freezing the lines at the first actionable day and re-running changes EP2's
    prices (349.68 / 338.63 / 327.59 against 346.70 / 335.69 / 324.68) and both
    EP5's prices and two of its dates. EP3 and EP4 gap through all three lines on
    day one, so they are inert — again recorded rather than glossed.
    """
    ref, got = reference[label], scope[label]
    frozen_lines = lines_for(onchain[got["first_day"]])
    frozen = []
    for tranche in range(3):
        hit = next(((b.date, buy_limit_fill(b, frozen_lines[tranche]))
                    for b in bars
                    if got["first_day"] <= b.date <= got["bos"]
                    and buy_limit_fill(b, frozen_lines[tranche]) is not None),
                   None)
        frozen.append(hit)
    honest = [(a["date"], a["px"]) for a in ref["accumulation"]]
    got_frozen = [(d, _2dp(p)) for d, p in frozen]
    if label in ("EP2-2014-09-28", "EP5-2022-05-22"):
        assert got_frozen != honest
    else:
        assert got_frozen == honest   # inert here


def test_ep3_gapped_below_all_three_lines_and_filled_at_the_open(bars, onchain,
                                                                 reference):
    """§13.2's buy-limit semantics, `fill = min(level, open)`, on the one
    episode where the two differ.

    EP3 opened 2018-11-26 at 4,088.69 with all three lines above it
    (4,770.69 / 4,502.89 / 4,235.08), so all three tranches fill at the OPEN, not
    at their levels — a 4.0% to 14.3% improvement that a `fill = level` rule
    would throw away. This is the only place in the historical record where the
    gap clause bites, so if it is not asserted here it is not asserted at all.
    """
    bar = next(b for b in bars if b.date == "2018-11-26")
    lines = lines_for(onchain["2018-11-26"])
    assert bar.open == Decimal("4088.69")
    for tranche, expected in enumerate(reference["EP3-2018-11-25"]["accumulation"]):
        assert bar.open < lines[tranche]
        assert buy_limit_fill(bar, lines[tranche]) == bar.open
        assert _2dp(bar.open) == expected["px"]


def test_the_accumulation_windows_have_complete_on_chain_coverage(bars, onchain,
                                                                  scope):
    """`_accumulation_fills` indexes `onchain` directly and would raise on a hole.

    That is deliberate — a skipped day is a silently missed fill — but it only
    holds while the windows are complete, so the precondition is asserted rather
    than assumed. `load_onchain_with_provenance` reports a different hazard
    (CoinMetrics holes papered over by checkonchain, ~1.78% apart); this is the
    cruder one of a date being absent entirely.
    """
    for label in ACTIVATED:
        got = scope[label]
        missing = [b.date for b in bars
                   if got["first_day"] <= b.date <= got["bos"]
                   and b.date not in onchain]
        assert missing == [], f"{label} has on-chain holes at {missing}"


# --------------------------------------------------------------------------
# Exit 1 — the 1.272 extension
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", ACTIVATED)
def test_exit1_level_and_fill_reproduce(label, bars, scope, reference):
    """§6.1: level = EL* + 1.272 x (prior ATH - EL*), then the first sell-limit
    touch after the BoS.

    Both halves matter. The level alone is arithmetic on two numbers already
    asserted; the FILL is what says the order was resting on the right side of
    the book. All four episodes open below the level on their exit day, so
    `min(level, open)` — the buy-side primitive — would fill 3.3% to 3.8% low on
    every one of them. §13.2's direction is genuinely pinned here.
    """
    ref, got = reference[label], scope[label]
    level = extension_1272(got["el_star"], got["prior_ath"])
    assert _2dp(level) == ref["anchors"]["lvl_1272"]

    fill_date, fill_price = _exit1_fill(bars, level, got["bos"])
    assert fill_date == ref["exit_ext_1272"]["date"]
    assert _2dp(fill_price) == ref["exit_ext_1272"]["px"]
    # Filled AT the level, because the day opened below it — so the sell-side
    # `max(level, open)` and the buy-side `min(level, open)` disagree here.
    exit_bar = next(b for b in bars if b.date == fill_date)
    assert exit_bar.open < level
    assert fill_price == level
    assert buy_limit_fill(exit_bar, level) == exit_bar.open != fill_price


# --------------------------------------------------------------------------
# Exit 2 — the armed mirror
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label", ACTIVATED)
def test_the_local_swing_scan_reproduces_the_engine_under_reading_a(
        label, bars, scope):
    """`_swing_lows` is a harness, and this is what stops it becoming a fork.

    Under `CONFIRM_WEEK_HIGH` it must be byte-identical to `find_swing_lows` on
    the same window — same weeks, same lows, same confirmations, same decline
    percentages, same argmax tops, same ORDER (§6.2 breaks "the most recent"
    swing, so order is part of the contract). Only then does the reading-(b) run
    below isolate one predicate rather than measuring an accidental second
    implementation.

    **This test pins reading (a) as the engine's CURRENT predicate, not as the
    right one.** The test below shows EP5's reference exit requires (b). If the
    owner settles obligation 2 in favour of (b), `find_swing_lows` changes and
    this comparison must move to `CONFIRM_DECLINE_TOP` in the same commit —
    which is the point: the harness cannot silently disagree with the engine.
    """
    window = [b for b in bars if b.date >= scope[label]["bos"]]
    weeks_in_window = to_weeks(window)
    mine = _lifetime_swings(bars, scope[label]["bos"], CONFIRM_WEEK_HIGH)
    engine = [(s.week_monday, s.low, s.confirmed_at, s.decline_pct,
               s.top_week, s.top_high)
              for s in find_swing_lows(weeks_in_window, window)]
    assert mine == engine
    assert mine, f"{label} produced no swings at all"


@pytest.mark.parametrize("label", ACTIVATED)
def test_mirror_exit_reproduces_under_reading_b_and_ep5_separates_the_readings(
        label, bars, scope, reference):
    """§6.2's exit, and the evidence that settles `find_swing_lows`' obligation 2.

    Under reading (b) — confirmation requires a high above the DECLINE'S ARGMAX
    TOP, the strict §4.3 mirror — all four reference exits reproduce exactly,
    dates and prices.

    Under reading (a) — the engine's current predicate, a high above the swing
    WEEK's own high — EP2, EP3 and EP4 still reproduce and **EP5 does not**: it
    signals on 2025-01-09 off the wk-2024-12-30 swing and exits 2025-01-15 @
    98,804.845, **46 days (six and a half weeks) early** and 5.2% above the
    reference's 2025-03-02 @ 93,923.26. Counted rather than eyeballed: an
    "about six weeks" gloss rounds the wrong way and understates the miss.
    The cause is visible in the data: wk 2024-12-30's low is undercut
    on 2025-01-09, but nothing trades above the 108,353 decline top until the
    109,588 print on 2025-01-20, so reading (b) has not yet confirmed that swing
    when reading (a) has.

    `find_swing_lows`' docstring says G4 cannot separate the two readings. That
    is still true of G4 — this gate is the one that can, and it says (b). The
    engine is NOT being changed here (CLAUDE.md rule 3: amendment by addition,
    owner approval); both outcomes are pinned so the divergence cannot be
    forgotten, and so that settling it flips this test rather than hiding in it.
    """
    ref, got = reference[label], scope[label]
    exit1 = ref["exit_ext_1272"]["date"]

    strict = _mirror_exit(bars, got["bos"], exit1, CONFIRM_DECLINE_TOP)
    assert strict is not None
    assert strict["date"] == ref["exit_mirror"]["date"]
    assert _2dp(strict["price"]) == ref["exit_mirror"]["px"]
    # The signal's WEEK, against the reference's `signal_week`.
    #
    # **§13.10 does NOT explain this field, and an earlier version of this
    # comment wrongly said it did.** §13.10's convention is Sunday-*close*
    # labels (a week named by the Sunday that ends it); `signal_week` does not
    # follow it — EP2's 2017-07-10 and EP5's 2025-02-24 are true ISO Mondays
    # needing no normalisation at all. The field is labelled off a **Sunday-
    # START (Sun-Sat) week**, named by the Monday inside it. That coincides with
    # the ISO Monday on every day of the week except Sunday, where it lands one
    # week later — which is exactly EP3/EP4, whose signal prints Sunday
    # 2021-04-18 and is labelled 2021-04-19 against the ISO 2021-04-12.
    #
    # Asserted as the rule rather than excused as a discrepancy on two of four:
    # if the reference ever relabels this field the mechanism fails here instead
    # of two episodes quietly dropping out of the check. The exits themselves are
    # identical to the dollar under both conventions and are asserted above.
    signal_day = date.fromisoformat(strict["signal"])
    sunday_start = signal_day + timedelta(days=1 if signal_day.weekday() == 6 else 0)
    assert monday_of(sunday_start.isoformat()) == ref["exit_mirror"]["signal_week"]
    if label in ("EP3-2018-11-25", "EP4-2020-03-15"):
        assert signal_day.weekday() == 6                      # the Sunday case
        assert monday_of(strict["signal"]) != ref["exit_mirror"]["signal_week"]
    else:
        assert monday_of(strict["signal"]) == ref["exit_mirror"]["signal_week"]

    loose = _mirror_exit(bars, got["bos"], exit1, CONFIRM_WEEK_HIGH)
    assert loose is not None
    if label == "EP5-2022-05-22":
        assert (loose["date"], loose["price"]) == \
            ("2025-01-15", Decimal("98804.845"))
        assert loose["signal"] == "2025-01-09"
        assert loose["swing_week"] == "2024-12-30"
        assert loose["date"] < ref["exit_mirror"]["date"]
    else:
        assert loose["date"] == ref["exit_mirror"]["date"]
        assert _2dp(loose["price"]) == ref["exit_mirror"]["px"]


@pytest.mark.parametrize("label", ACTIVATED)
def test_the_mirror_fill_top_is_the_lifetime_argmax_not_the_swing_top(
        label, bars, scope, reference):
    """`find_swing_lows`: "`top_high` IS NOT the mirror fill's `top_high`".

    G4 shows the two differ by 1,725.63 on one window. Here the substitution
    breaks the reproduction on **all four** episodes — EP2 and EP3/EP4 on both
    date and price, EP5 on price alone (2025-03-02 @ 93,305.76 against
    93,923.26, because the swing's decline top is the 108,353 December high
    rather than the 109,588 January ATH).

    What this does NOT pin is the fill top's scan ORIGIN — obligation 3, still
    open. Re-running with the whole scope narrowed from the BoS to the Exit 1
    print (which moves the swing scan as well as the argmax) returns the
    identical exit on all four episodes, because each episode's ATH postdates its
    own Exit 1 and the swing that breaks is post-Exit-1 structure either way. So
    this gate rules the swing top out and leaves the other two indistinguishable.
    """
    ref, got = reference[label], scope[label]
    exit1 = ref["exit_ext_1272"]["date"]

    swapped = _mirror_exit(bars, got["bos"], exit1, CONFIRM_DECLINE_TOP,
                           top_from_swing=True)
    assert swapped is not None
    assert (swapped["date"], _2dp(swapped["price"])) != \
        (ref["exit_mirror"]["date"], ref["exit_mirror"]["px"])

    # ...and narrowing the scope to the armed window agrees, which is why
    # obligation 3 stays open.
    from_bos = _mirror_exit(bars, got["bos"], exit1, CONFIRM_DECLINE_TOP)
    from_armed = _mirror_exit(bars, exit1, exit1, CONFIRM_DECLINE_TOP)
    assert (from_armed["date"], from_armed["price"]) == \
        (from_bos["date"], from_bos["price"])


# --------------------------------------------------------------------------
# R_down's lower edge — the constant this reproduction constrains
# --------------------------------------------------------------------------

#: The week whose swing, once ADMITTED, breaks each episode's reproduction — the
#: week that sets that episode's lower `R_down` edge. Only the week IDENTITY is
#: named here; every percentage below is read off the engine's own `decline_pct`.
#: Naming the week is what makes the edge attributable instead of a bare number,
#: and it is what fails if a data refresh moves the low that produces it.
R_DOWN_LOWER_EDGE_WEEK = {"EP2-2014-09-28": "2017-06-05",
                          "EP3-2018-11-25": "2021-02-15",
                          "EP4-2020-03-15": "2021-02-15",
                          "EP5-2022-05-22": "2024-12-09"}
#: ...and the week whose swing, once EXCLUDED, breaks it — the upper edge.
R_DOWN_UPPER_EDGE_WEEK = {"EP2-2014-09-28": "2017-05-29",
                          "EP3-2018-11-25": "2021-03-22",
                          "EP4-2020-03-15": "2021-03-22",
                          "EP5-2022-05-22": "2025-01-13"}
EPSILON = Decimal("1e-20")


def _decline_pct(bars, scope, label, week):
    """The ENGINE's decline percentage for one week of one episode's lifetime.

    Scanned at `r_down = 0` so the week is present whatever its depth. Reading
    the edge off the detector rather than pasting a figure is the whole point:
    every wrong number in this build has been a copied one, and a transcribed
    boundary that sits a hair past the true edge fails on correct code.
    """
    swings = _lifetime_swings(bars, scope[label]["bos"], CONFIRM_DECLINE_TOP,
                              Decimal("0"))
    return next(s[3] for s in swings if s[0] == week)


def _reproduces_mirror(bars, scope, reference, label, r_down):
    ref = reference[label]["exit_mirror"]
    got = _mirror_exit(bars, scope[label]["bos"],
                       reference[label]["exit_ext_1272"]["date"],
                       CONFIRM_DECLINE_TOP, r_down=r_down)
    return got is not None and got["date"] == ref["date"] \
        and _2dp(got["price"]) == ref["px"]


@pytest.mark.parametrize("label", ACTIVATED)
def test_each_episode_bounds_r_down_from_below(label, bars, scope, reference):
    """§13.9a said `R_down` had "no lower edge at all". **This run falsifies it.**

    §13.9a's measurement was made on G4's window, where a looser `R_down` only
    ever adds shallower swings and none of them is the most recent confirmed
    swing at the break — so G4 reproduces down to `R_down = -100`. On a full
    episode lifetime that does not hold: a shallower swing admitted anywhere
    between the Exit 1 print and the real signal becomes "the most recent
    confirmed swing", is broken earlier, and the exit moves.

    Measured per episode, `r_down` passed explicitly (never by editing
    `R_DOWN_DEFAULT`, which would measure nothing and would leave the assertion
    at the mercy of whoever changes the default):

        EP2   8.5076627658…   wk 2017-06-05
        EP3   8.3219752057…   wk 2021-02-15
        EP4   8.3219752057…   wk 2021-02-15   (same week: EP3 and EP4 exit together)
        EP5   9.5476423795…   wk 2024-12-09   <- binding

    The edge is EXCLUSIVE at the bottom, and that follows from the detector's own
    `decline < r_down: continue`: a swing whose decline exactly equals `r_down`
    is admitted, so the reproduction fails AT the edge and passes an epsilon
    above it. Both directions are asserted — an assertion that only checked the
    passing side would be satisfied by an `R_down` with no lower edge at all,
    which is precisely the claim being falsified.
    """
    edge = _decline_pct(bars, scope, label, R_DOWN_LOWER_EDGE_WEEK[label])
    expected = {"EP2-2014-09-28": ("8.5076627658", "8.5076627659"),
                "EP3-2018-11-25": ("8.3219752057", "8.3219752058"),
                "EP4-2020-03-15": ("8.3219752057", "8.3219752058"),
                "EP5-2022-05-22": ("9.5476423795", "9.5476423796")}[label]
    assert Decimal(expected[0]) < edge < Decimal(expected[1])

    assert not _reproduces_mirror(bars, scope, reference, label, edge)
    assert _reproduces_mirror(bars, scope, reference, label, edge + EPSILON)

    # ...and the inclusivity is pinned against the ENGINE, not just the harness.
    # Without this the two `_reproduces_mirror` calls above only exercise
    # `_swing_lows`' copy of the predicate, and mutating `find_swing_lows`'
    # `decline < r_down` to `<=` survives the whole file: no week's decline is
    # exactly 10.000…, so the cross-check cannot see it either. Fed a REAL
    # decline as the threshold, it can.
    window = [b for b in bars if b.date >= scope[label]["bos"]]
    weeks_in_window = to_weeks(window)
    at_edge = find_swing_lows(weeks_in_window, window, r_down=edge)
    past_edge = find_swing_lows(weeks_in_window, window, r_down=edge + EPSILON)
    edge_week = R_DOWN_LOWER_EDGE_WEEK[label]
    assert any(s.week_monday == edge_week for s in at_edge)
    assert all(s.week_monday != edge_week for s in past_edge)

    # ...and the upper edge, INCLUSIVE, for the same reason in mirror image:
    # raising `r_down` past a swing's decline removes it, and the swing that the
    # signal actually breaks is the one that goes.
    upper = _decline_pct(bars, scope, label, R_DOWN_UPPER_EDGE_WEEK[label])
    assert _reproduces_mirror(bars, scope, reference, label, upper)
    assert not _reproduces_mirror(bars, scope, reference, label, upper + EPSILON)
    assert edge < upper


def test_ep5_is_the_binding_lower_edge_and_the_frozen_r_down_clears_it(
        bars, scope, reference):
    """What makes 9.5476… the band's floor rather than merely one of four.

    The joint lower edge is the MAXIMUM of the per-episode edges, because the
    band is the intersection: `R_down` must be high enough for every episode.
    EP5's is strictly the largest, and the two below it are what make that a
    binding constraint rather than a coincidence — asserted as an ordering so a
    data change that reshuffles them reports itself here.

        band from these four episodes   (9.5476…, 17.6241…]
        band from §10 G4                (-inf, 13.7570…]     <- test_mirror_gate
        joint                           (9.5476…, 13.7570…]

    **The two authorities are kept apart** (§13.3a's discipline). The floor is
    this file's; the ceiling is G4's, and these episodes tolerate `R_down` up to
    17.6241… on their own — so quoting 13.757 as "the episodes' upper edge" would
    misattribute it. §13.9a's `(9.5476, 13.757]` is correct only as the joint
    band.

    The frozen `R_down = 10` clears the floor by **0.45 points** and sits 3.76
    below the joint ceiling. That is a real defence of the constant and it is
    also the tightest margin any of this system's three constants has: `R_e = 15`
    sits at the TOP of its band (§13.3a) and `QUIET_WEEKS = 26` sits in an
    interior plateau (§13.5), while `R_down = 10` sits near the bottom of its
    own. An `R_down` of 9.5 would break EP5's recorded exit.
    """
    edges = {label: _decline_pct(bars, scope, label,
                                 R_DOWN_LOWER_EDGE_WEEK[label])
             for label in ACTIVATED}
    binding = max(edges.values())
    assert binding == edges["EP5-2022-05-22"]
    for label in ("EP2-2014-09-28", "EP3-2018-11-25", "EP4-2020-03-15"):
        assert edges[label] < binding
    # EP3 and EP4 share an edge because they share an exit — the §14 OQ-1
    # concurrent-episode pair. Asserted so "four episodes, three edges" is a
    # stated fact rather than a surprise.
    assert edges["EP3-2018-11-25"] == edges["EP4-2020-03-15"]
    assert edges["EP2-2014-09-28"] != edges["EP3-2018-11-25"]

    # The frozen constant clears the floor, and every episode reproduces at it.
    assert R_DOWN_DEFAULT == Decimal("10")
    assert binding < R_DOWN_DEFAULT
    assert Decimal("0.45") < R_DOWN_DEFAULT - binding < Decimal("0.46")
    for label in ACTIVATED:
        assert _reproduces_mirror(bars, scope, reference, label, R_DOWN_DEFAULT)
    # ...and a plausible "round it down a bit" value does not.
    assert not _reproduces_mirror(bars, scope, reference, "EP5-2022-05-22",
                                  Decimal("9.5"))

    # The ceiling these episodes impose is their own, and it is well above G4's.
    ceiling = min(_decline_pct(bars, scope, label, R_DOWN_UPPER_EDGE_WEEK[label])
                  for label in ACTIVATED)
    assert Decimal("17.6241636133") < ceiling < Decimal("17.6241636134")
    assert ceiling > Decimal("13.7570094960")     # G4's, from test_mirror_gate


# --------------------------------------------------------------------------
# what has no fills, and what is deliberately not asserted
# --------------------------------------------------------------------------

def test_the_unactivated_episodes_have_no_fills(reference, scope):
    """EP1 expired and EP6 is watching — neither deployed a cent.

    Asserted explicitly because `ACTIVATED` merely omits them, and an omission
    cannot tell the difference between "correctly has no fills" and "was
    forgotten". The engine side is the stronger half: an engine that activated
    EP1 (its D is its own trigger week, §13.3's guard) or EP6 (live, no BoS yet)
    would be wrong in a way no other test in this file can see.
    """
    for label in ("EP1-2011-11-27", "EP6-2026-02-01"):
        row = reference[label]
        assert "accumulation" not in row
        assert "exit_ext_1272" not in row
        assert "exit_mirror" not in row
        assert scope[label]["bos"] is None
        assert scope[label]["el_star"] is None
    # EP6's operative LH is live structure, not a fill: §13.10's Sunday label
    # 2026-05-10 is ISO Monday 2026-05-04 (G5 asserts the engine side).
    ep6 = reference["EP6-2026-02-01"]["lower_high_operative"]
    assert monday_of(ep6["date"]) == "2026-05-04"
    assert ep6["price"] == Decimal("82850.00")


@pytest.mark.parametrize("label", ACTIVATED)
def test_pnl_is_not_asserted_because_spec_and_the_reference_disagree(
        label, reference):
    """§14 OQ-4, pinned as an open divergence rather than left implicit.

    SPEC §11's accumulation-only pnl figures are +480.9 / +881.0 / +715.5 /
    +339.7; the reference's `acc_only_pnl_pct_1_2_4` are 480.20 / 879.89 /
    714.63 / 339.18 — SPEC is high by 0.52 to 1.11 points on every episode. The
    owner has ruled cumulative return non-blocking, so nothing in this file
    asserts a pnl. This test asserts only that the disagreement is still there,
    so that reconciling OQ-4 (or silently "correcting" one side) fails here and
    gets a decision instead of a commit.
    """
    spec_11 = {"EP2-2014-09-28": Decimal("480.9"),
               "EP3-2018-11-25": Decimal("881.0"),
               "EP4-2020-03-15": Decimal("715.5"),
               "EP5-2022-05-22": Decimal("339.7")}
    reference_value = reference[label]["acc_only_pnl_pct_1_2_4"]
    gap = spec_11[label] - reference_value
    assert Decimal("0.4") < gap < Decimal("1.2"), (
        f"{label}: SPEC §11 {spec_11[label]} vs reference {reference_value}. "
        "If these now agree, §14 OQ-4 has been resolved and this test should be "
        "replaced by a real pnl assertion — not deleted.")


# --------------------------------------------------------------------------
# the buy side: BoS-week high, the ladder, the breakout
# --------------------------------------------------------------------------
#
# Until this section existed, the reproduction stopped at the entry. The gates
# asserted the trigger chain, the operative LH, EL*, the accumulation fills and
# both exits — and nothing at all about how the other **fourteen of the
# twenty-one units** get spent. Grepped before writing: `226.93` (EP2's 0.5-rung
# fill), `5275.01`, `12123.46` and `20363` each appeared zero times under
# `tests/`. Every number below already came out right; the point is that nothing
# was holding them there, and mutation testing is structurally blind to the
# class of error that pins a value to the wrong target.
#
# So, as everywhere else in this file, the expected values are read from `cy1` at
# run time and the engine's are read from `compute` — never transcribed.


def _settled_bos_week(bos: str) -> str:
    """The Sunday that closes the BoS week: the earliest `asof` at which the
    ladder and the breakout are priceable at all (`engine.engine`, boundary 3).
    """
    return _week_end(monday_of(bos))


def _ledger_from(reference_row) -> tuple[frozenset, Decimal]:
    """The (filled_purposes, held_units) the reference's own record implies.

    Accumulation is 3/3 on all four episodes, plus whichever rungs the reference
    marks filled, at `LADDER_UNITS`' 2 : 4 : 8. Derived rather than tabulated so
    EP2's two filled rungs and EP5's one are the reference's claim, not this
    file's.
    """
    filled, held = set(ACCUMULATED), ACCUMULATED_UNITS
    for row in reference_row["reserve"]:
        if row["filled"]:
            name, purpose = RESERVE[row["name"]]
            filled.add(purpose)
            held += LADDER_UNITS[name]
    return frozenset(filled), held


def _confirmed_at(bars, onchain, asof, filled, held):
    result = compute(bars, onchain, EpisodeState(), asof=asof,
                     filled_purposes=filled, held_units=held)
    assert result.state.status is EpisodeStatus.CONFIRMED, (
        f"{asof}: expected a CONFIRMED episode, got {result.state.status}")
    return result


def _priced(result) -> dict:
    return {o.purpose: o for o in result.orders}


def _breakout_fill(bars, level: Decimal, after: str, strict: bool):
    """The breakout fallback's fill, with the TOUCH predicate parametrised.

    SPEC contradicts itself here and the record can tell the two apart:

      §0 / §5   "intraweek trade **above** X = any daily high > X" — strict.
      §13.2     buy-stop touch = "daily high **>=** level", and §13 overrides
                the older prose.

    `engine.fills.buy_stop_fill` implements §13.2, and
    `test_the_breakout_reproduces_and_ep5_separates_the_touch_predicate` checks
    this harness against it on the non-strict branch, so the only thing varied
    is the one comparison. The fill PRICE is `max(level, open)` either way.
    """
    for bar in bars:
        if bar.date <= after:
            continue
        if bar.high > level if strict else bar.high >= level:
            return bar.date, max(level, bar.open)
    return None, None


@pytest.mark.parametrize("label", ACTIVATED)
def test_the_bos_week_high_reproduces_and_ep4_needs_the_settled_week(
        label, bars, onchain, scope, reference):
    """`bos_week_high` is the reference's `leg_high`, and it is the input the
    entire buy side is priced off — all three rungs and the breakout level.

    EP4 is the episode that makes this a real assertion rather than a
    restatement of the BoS date. Its BoS prints 2020-07-27 (Monday) but the
    week's high, 12,123.46, does not arrive until the Sunday that closes it. Run
    a day early and the engine's running high is 11,861.00 — 2.2% low — which
    moves every ladder rung down and sets the breakout buy-stop *inside* the
    week that broke structure. The other three episodes print their high before
    the Sunday and are inert here, which is asserted rather than glossed: the
    inequality is `<=` for all four and strict for EP4.
    """
    bos = scope[label]["bos"]
    settled = _confirmed_at(bars, onchain, _settled_bos_week(bos),
                            ACCUMULATED, ACCUMULATED_UNITS)
    assert settled.state.bos_week_high == reference[label]["anchors"]["leg_high"]

    a_day_early = compute(bars, onchain, EpisodeState(),
                          asof=_day_before(_settled_bos_week(bos)),
                          filled_purposes=ACCUMULATED,
                          held_units=ACCUMULATED_UNITS)
    assert a_day_early.state.bos_week_high <= settled.state.bos_week_high
    if label == "EP4-2020-03-15":
        assert a_day_early.state.bos_week_high < settled.state.bos_week_high
    # ...and while the week is open nothing priced off it may rest (boundary 3).
    assert not ({p for p, _ in RESERVE.values()} | {OrderPurpose.BREAKOUT}) & \
        set(_priced(a_day_early))


@pytest.mark.parametrize("label", ACTIVATED)
def test_the_ladder_levels_and_weights_reproduce(label, bars, onchain, scope,
                                                 reference):
    """SPEC §5's three rungs, read off `compute`'s resting orders.

    Taken from the order set rather than from `levels.ladder_levels` directly,
    because the failure this is guarding is not "the retracement arithmetic is
    wrong" — that is two lines and already unit-tested — but "the wrong leg was
    fed to it, or the rungs were joined to their weights by position". EP2 and
    EP3 are the pair that catch the latter: their weights are the same 2 : 4 : 8
    while their levels are three orders of magnitude apart.

    Prices are compared to the reference's 2dp record within half a cent, which
    is exactly the rounding the reference applied. That is not slack —
    `test_the_2dp_record_is_ambiguous_only_at_an_exact_half_cent` shows the
    tolerance is reached by exactly one rung, for a reason, and that no
    quantiser reproduces the record on all twelve.
    """
    bos = scope[label]["bos"]
    orders = _priced(_confirmed_at(bars, onchain, _settled_bos_week(bos),
                                   ACCUMULATED, ACCUMULATED_UNITS))
    for row in reference[label]["reserve"]:
        name, purpose = RESERVE[row["name"]]
        order = orders[purpose]
        assert abs(order.price - row["lvl"]) <= HALF_CENT, (
            f"{label} {row['name']}: engine {order.price} vs reference "
            f"{row['lvl']}")
        assert order.units == row["w"] == LADDER_UNITS[name]
    # The leg the rungs retrace: deepest rung below shallowest, both strictly
    # inside (EL*, BoS-week high]. A ladder that priced off the wrong leg can
    # still land three descending numbers; it cannot land them in this interval.
    prices = [orders[p].price for _, p in RESERVE.values()]
    assert prices == sorted(prices, reverse=True)
    assert scope[label]["el_star"] < prices[-1]
    assert prices[0] < reference[label]["anchors"]["leg_high"]


def test_the_2dp_record_is_ambiguous_only_at_an_exact_half_cent(bars, onchain,
                                                                scope,
                                                                reference):
    """Why the rungs are compared within half a cent instead of by `quantize`.

    The engine returns exact Decimal arithmetic and the reference records two
    decimal places, so the comparison has to name a rounding — and **no single
    rounding mode reproduces the reference on all twelve rungs**. Four of them
    land on an exact half-cent tie:

        EP2 0.786   186.1050    -> record 186.10   (half-even agrees)
        EP3 0.5     4215.635    -> record 4215.64  (half-even agrees)
        EP3 0.62    3961.3850   -> record 3961.39  (half-even gives ...38)
        EP4 0.5     7952.795    -> record 7952.80  (half-even agrees)

    ROUND_HALF_EVEN gets three of the four; ROUND_HALF_UP would get EP3's 0.62
    and then lose EP2's 0.786 (186.11). The pattern is what a float round-trip
    does: 3961.385 as a binary double is 3961.38500000000021..., just above the
    tie, while 186.105 is 186.10499999999999..., just below. The reference was
    produced in floats; the engine is exact by construction and is not wrong
    here.

    So the honest claim is "the reference is this value rounded to the cent, and
    at an exact tie the direction is not determined" — which is what the
    tolerance says. This test is what stops it being slack: every rung must be
    either an exact `_2dp` match or an exact half-cent tie, nothing in between,
    and the tie set must be exactly those four.
    """
    ties, mismatches = [], []
    for label in ACTIVATED:
        orders = _priced(_confirmed_at(
            bars, onchain, _settled_bos_week(scope[label]["bos"]),
            ACCUMULATED, ACCUMULATED_UNITS))
        for row in reference[label]["reserve"]:
            _name, purpose = RESERVE[row["name"]]
            exact = orders[purpose].price
            gap = abs(exact - row["lvl"])
            if gap == HALF_CENT:                     # an exact rounding tie
                ties.append((label, row["name"], exact, row["lvl"]))
            elif _2dp(exact) != row["lvl"]:          # not a tie, and not equal
                mismatches.append((label, row["name"], exact, row["lvl"]))
    assert mismatches == [], (
        "these rungs differ from the reference by something other than a "
        f"rounding tie: {mismatches}")
    assert [(label, name) for label, name, _e, _r in ties] == [
        ("EP2-2014-09-28", "F_0.786"),
        ("EP3-2018-11-25", "F_0.5"),
        ("EP3-2018-11-25", "F_0.62"),
        ("EP4-2020-03-15", "F_0.5"),
    ]
    # ...and the one the two conventions actually disagree about, named.
    disagrees = [(label, name) for label, name, exact, recorded in ties
                 if _2dp(exact) != recorded]
    assert disagrees == [("EP3-2018-11-25", "F_0.62")]


@pytest.mark.parametrize("label", ACTIVATED)
def test_the_ladder_rung_fills_reproduce(label, bars, onchain, scope, reference):
    """§5's rungs are buy-limits, walked forward from the settled BoS week to
    the breakout — and three of the twelve filled.

    The window's far end is the breakout, because the breakout deploys the whole
    remaining pool (SPEC §5) and after it the buy side of the episode is over;
    a rung that "fills" past it is spending capital already spent. That end is
    the reference's own breakout date, so this test does not depend on the touch
    predicate the next one is about.

    Both halves are asserted. The three fills pin date and price — EP2's 0.5 rung
    gap-opens at 226.93, 1.8% below its 231.15 level, so `min(level, open)` is
    genuinely exercised — and the nine non-fills pin that the other rungs were
    never touched, which is what makes EP2's 8-unit and EP5's 12-unit breakout
    the right size rather than a coincidence.
    """
    bos = scope[label]["bos"]
    settled = _settled_bos_week(bos)
    orders = _priced(_confirmed_at(bars, onchain, settled,
                                   ACCUMULATED, ACCUMULATED_UNITS))
    window = [b for b in bars
              if settled < b.date <= reference[label]["breakout"]["date"]]

    for row in reference[label]["reserve"]:
        _name, purpose = RESERVE[row["name"]]
        level = orders[purpose].price
        hit = next(((b.date, buy_limit_fill(b, level)) for b in window
                    if buy_limit_fill(b, level) is not None), None)
        if not row["filled"]:
            assert hit is None, f"{label} {row['name']} filled at {hit}"
            continue
        assert hit is not None, f"{label} {row['name']} never filled"
        fill_date, fill_price = hit
        assert fill_date == row["date"]
        assert _2dp(fill_price) == row["px"]


@pytest.mark.parametrize("label", ACTIVATED)
def test_the_breakout_reproduces_and_ep5_separates_the_touch_predicate(
        label, bars, onchain, scope, reference):
    """SPEC §5's breakout fallback: level, size, and the day it fills.

    **Level and size come from `compute`** and reproduce exactly on all four,
    which is the part that matters most — the size is §14 OQ-3's second leg
    (unfilled ladder rolls into the breakout) measured against the record rather
    than against the owner's sentence. EP3 and EP4 carry the full 14; EP2 carries
    8 because two rungs filled; EP5 carries 12 because one did. A reading that
    rolled to the breakout at the wrong point gets 14 everywhere.

    **The fill day exposes a contradiction inside SPEC, and EP5 is where it
    bites.** §0 and §5 define "intraweek trade above X" as `daily high > X`;
    §13.2's primitive table gives the buy-stop touch as `daily high >= level`,
    and §13 overrides the older prose. The two agree on EP2, EP3 and EP4. On EP5
    they do not: 2023-02-21 printed a high of **exactly** 25,250.00, the
    BoS-week high to the cent.

      strict `>`   breakout 2023-03-14 @ 25,250 — the reference, exactly.
      §13.2 `>=`   breakout 2023-02-21, three weeks earlier.

    It is not a cosmetic date. Under `>=` the breakout fires *before* EP5's 0.5
    rung fills on 2023-03-09, so that rung never fills at all and the breakout
    carries 14 units instead of 12 — a different position, differently sized,
    entered 21 days and ~$1,000 apart. The record needs the strict reading; the
    shipped `buy_stop_fill` implements the other one, and a real exchange stop
    behaves like `>=`.

    Not resolved here (CLAUDE.md rule 3 — amendment by addition, owner
    approval). Both readings are pinned, as §6.2's two confirmation readings are
    above, so settling it flips this test rather than hiding in it.
    """
    ref, bos = reference[label], scope[label]["bos"]
    breakout_ref = ref["breakout"]

    # --- level and size, through compute, with the reference's own ledger ---
    filled, held = _ledger_from(ref)
    at_the_break = _priced(_confirmed_at(bars, onchain,
                                         _day_before(breakout_ref["date"]),
                                         filled, held))
    order = at_the_break[OrderPurpose.BREAKOUT]
    assert order.price == ref["anchors"]["leg_high"] == breakout_ref["px"]
    assert order.units == breakout_ref["units"]
    assert order.kind is OrderKind.STOP_MARKET and order.side is OrderSide.BUY
    # The rungs the reference records as filled are not re-rested beside it.
    assert not (filled & set(at_the_break))

    # --- the fill day, under both readings ---------------------------------
    after_bos_week = _settled_bos_week(bos)
    strict = _breakout_fill(bars, order.price, after_bos_week, strict=True)
    assert strict == (breakout_ref["date"], breakout_ref["px"])

    loose = _breakout_fill(bars, order.price, after_bos_week, strict=False)
    # The harness's non-strict branch IS `buy_stop_fill`; checked, not asserted
    # in prose, so this cannot drift into a second implementation.
    engine_side = next(((b.date, buy_stop_fill(b, order.price)) for b in bars
                        if b.date > after_bos_week
                        and buy_stop_fill(b, order.price) is not None), None)
    assert loose == engine_side

    if label == "EP5-2022-05-22":
        assert loose == ("2023-02-21", Decimal("25250.0"))
        assert loose[0] < strict[0]
        touched = next(b for b in bars if b.date == "2023-02-21")
        assert touched.high == order.price          # the tie, to the cent
        # ...and the consequence: the 0.5 rung's fill day is inside the gap, so
        # under `>=` it never fills and the breakout would carry the full 14.
        rung = next(r for r in ref["reserve"] if r["name"] == "F_0.5")
        assert loose[0] < rung["date"] < strict[0]
        assert order.units == Decimal(12)
    else:
        assert loose == strict
