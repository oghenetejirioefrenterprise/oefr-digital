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
structural facts" list, all of which reconcile exactly.

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
from engine.fills import buy_limit_fill, sell_limit_fill
from engine.levels import extension_1272, mirror_target
from engine.lifecycle import freeze_el, prior_cycle_ath
from engine.lines import lines_for
from engine.structure import R_DOWN_DEFAULT, find_swing_lows

#: The four episodes that activated. EP1 expired and EP6 is still watching, so
#: neither has a fill; `test_the_unactivated_episodes_have_no_fills` asserts that
#: rather than this list quietly omitting them.
ACTIVATED = ("EP2-2014-09-28", "EP3-2018-11-25", "EP4-2020-03-15",
             "EP5-2022-05-22")

#: §6.2's confirmation reference price, the two readings of `find_swing_lows`'
#: obligation 2. (a) is what the engine implements.
CONFIRM_WEEK_HIGH = "a"
CONFIRM_DECLINE_TOP = "b"


def _2dp(value: Decimal) -> Decimal:
    """The reference records prices to 2dp; the engine returns exact arithmetic
    (`engine/levels.py`: "the 2dp is presentational, not normative")."""
    return value.quantize(Decimal("0.01"))


def _week_end(monday: str) -> str:
    y, m, d = (int(x) for x in monday.split("-"))
    return (date(y, m, d) + timedelta(days=6)).isoformat()


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
_SWING_SCANS: dict[tuple[str, str], list] = {}


def _lifetime_swings(bars, scope_start, confirm):
    key = (scope_start, confirm)
    if key not in _SWING_SCANS:
        window = [b for b in bars if b.date >= scope_start]
        _SWING_SCANS[key] = _swing_lows(to_weeks(window), window, confirm)
    return _SWING_SCANS[key]


def _mirror_exit(bars, scope_start, armed_from, confirm, top_from_swing=False):
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
    swings = _lifetime_swings(bars, scope_start, confirm)

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
    98,804.845, six weeks early and 5.2% above the reference's 2025-03-02 @
    93,923.26. The cause is visible in the data: wk 2024-12-30's low is undercut
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
    # The signal's WEEK is the reference's `signal_week` on three of four
    # (§13.10 normalisation applies: the reference labels EP3/EP4's by the
    # FOLLOWING Monday, 2021-04-19 against the engine's 2021-04-12 — a
    # reference-side labelling difference on the signal only; the fill it
    # produces is identical to the dollar and is asserted above).
    if label in ("EP2-2014-09-28", "EP5-2022-05-22"):
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
