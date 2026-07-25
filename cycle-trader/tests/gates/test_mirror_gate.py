"""G4 — mirror-exit detector, run as a STANDALONE fixture (SPEC §10, §13.9).

Harness, taken verbatim from §13.9's table: input window 2025-08-01 → 2025-12-31,
`R_down = 10`, walk-forward 50% target, **position-lifetime scope disabled**.

Why the harness is separate at all: §13.9 says the position exits at the FIRST
armed mirror signal, so EP5 exits 2025-03-02 @ 93,923 and the Oct-2025 signal is
the *second* armed instance. A correct lifecycle engine therefore holds nothing in
Oct-2025 and — because §6.2 scopes the swing scan to the position's lifetime —
never evaluates this window at all. **G4 passing must not be read as implying an
open EP5 position in Oct-2025; §11's EP5 exit stays 2025-03-02.**

SCOPE OF WHAT THIS GATE VERIFIES, stated plainly because it is narrower than it
looks. Only two pieces of `engine/` are exercised here: `find_swing_lows` and
`levels.mirror_target` (plus `fills.sell_limit_fill` for the fill price). §6.2's
break detection and its walk-forward fill scan have **no engine implementation
yet** — `mirror_signal` / `_walk_forward_fill` below are a test-local harness, and
a gate cannot pin code that does not exist. `engine/orders.py` already consumes a
ready-made `lines["mirror"]` value, so whoever computes it (M2/Task 14) inherits an
unpinned rule. That is a real gap, recorded here rather than papered over.
"""
from decimal import Decimal

import pytest

from engine.bars import monday_of, to_weeks
from engine.fills import sell_limit_fill
from engine.levels import mirror_target
from engine.structure import find_swing_lows

WINDOW_START, WINDOW_END = "2025-08-01", "2025-12-31"
R_DOWN = Decimal("10")

# §10 G4: "the ~107k Aug/Sep-2025 double bottom (107,255 / 107,350 — 0.09% apart;
# either attribution acceptable)". Both are asserted, not one: they are different
# weeks with different confirmations, and the 107,350 leg is the only one on which
# §6.2's "confirmation strictly precedes the break" is OBSERVABLE (see below).
DOUBLE_BOTTOM = {
    "2025-08-25": Decimal("107350.10"),
    "2025-09-01": Decimal("107255.00"),
}


@pytest.fixture(scope="module")
def g4_window(bars):
    window = [b for b in bars if WINDOW_START <= b.date <= WINDOW_END]
    return window, to_weeks(window)


@pytest.fixture(scope="module")
def g4_swings(g4_window):
    window, wks = g4_window
    return find_swing_lows(wks, window, r_down=R_DOWN)


def mirror_signal(window, swing):
    """§6.2's signal: the first intraweek trade below a CONFIRMED swing low,
    strictly after that confirmation. Test-local harness — see the module
    docstring."""
    return next((b for b in window
                 if b.date > swing.confirmed_at and b.low < swing.low), None)


def _walk_forward_fill(window, signal, top):
    """§6.2's fill: target = (top_high + low_so_far) / 2, recomputed each day.

    `low_so_far` takes the current day's low BEFORE that day's high is tested,
    and the break day itself is excluded (its high printed pre-break).
    Test-local harness — see the module docstring."""
    low_so_far = signal.low
    for b in window:
        if b.date <= signal.date:
            continue
        low_so_far = min(low_so_far, b.low)
        target = mirror_target(top, low_so_far)
        fill = sell_limit_fill(b, target)
        if fill is not None:
            return b.date, fill, target
    return None, None, None


def test_g4_detects_the_double_bottom_and_nothing_spurious(g4_swings):
    """The detector's whole output on the harness window, asserted as a set.

    Asserting only "the ~107k swing is in there" cannot see a detector that also
    emits half the window. The two double-bottom weeks are the load-bearing rows;
    the rest are the honest consequence of `R_down = 10` on this window and are
    pinned so a rule change reports itself here rather than as a moved signal.
    """
    got = {s.week_monday: s.low for s in g4_swings}
    assert got == {
        "2025-08-18": Decimal("110680.00"),
        "2025-08-25": Decimal("107350.10"),   # double bottom, leg 1
        "2025-09-01": Decimal("107255.00"),   # double bottom, leg 2
        "2025-09-08": Decimal("110621.78"),
        "2025-09-22": Decimal("108620.07"),
        "2025-09-29": Decimal("111560.65"),
        # ...everything below is AFTER the 2025-10-10 break, i.e. later armed
        # instances (§13.9) that the gate's signal must not reach back for.
        "2025-10-13": Decimal("103528.23"),
        "2025-10-20": Decimal("106666.69"),
        "2025-11-24": Decimal("85272.00"),
        "2025-12-01": Decimal("83822.76"),
        "2025-12-15": Decimal("84450.01"),
    }
    # The decline's argmax top flips at the ATH, which is the observable trace of
    # the "argmax over prior weeks in scope" rule this detector actually runs
    # (`find_swing_lows`' KNOWN SIMPLIFICATION note). Pinned so that when M2
    # replaces it with the since-prior-swing argmax, the change shows up here.
    tops = {s.week_monday: s.top_week for s in g4_swings}
    assert set(tops.values()) == {"2025-08-11", "2025-10-06"}
    assert tops["2025-09-01"] == "2025-08-11"
    # 0.09% apart, exactly as §10 G4 states — which is why it names both and
    # accepts either attribution.
    a, b = DOUBLE_BOTTOM["2025-08-25"], DOUBLE_BOTTOM["2025-09-01"]
    assert (a - b) / b * Decimal(100) < Decimal("0.1")


def test_g4_unconfirmed_swings_are_excluded(g4_window, g4_swings):
    """Confirmation is a FILTER, and this is where it bites.

    Wk 2025-10-06 is the crash week the whole gate is about, and it clears
    `R_down` easily (−18.9% off the prior week's 125,708.42 high, down to
    102,000). But nothing in the rest of the window ever trades back above its
    126,199.63 high, so it is never confirmed and must not be emitted as a swing.
    Without the filter it becomes the most recent swing — and the most recent
    swing is exactly what §6.2 breaks, so the detector would then be watching for
    a trade below 102,000 instead of having already signalled at 107k.
    """
    _window, wks = g4_window
    crash = next(w for w in wks if w.monday == "2025-10-06")
    assert crash.low == Decimal("102000.00")
    assert crash.high == Decimal("126199.63")
    assert max(w.high for w in wks if w.monday > "2025-10-06") < crash.high
    assert all(s.week_monday != "2025-10-06" for s in g4_swings)
    # ...and everything that IS emitted carries a confirmation date.
    assert all(s.confirmed_at is not None for s in g4_swings)


@pytest.mark.parametrize("swing_week", sorted(DOUBLE_BOTTOM))
def test_g4_mirror_signal_and_fill(g4_window, g4_swings, swing_week):
    """§10 G4: signal in the week of 2025-10-06; fill 2025-10-12 @ ≈114,100.

    Run against BOTH double-bottom attributions because §10 accepts either, and
    an engine that reproduced the gate off only one of them would be relying on
    an accident of which low it happened to pick.
    """
    window, _wks = g4_window
    swing = next(s for s in g4_swings if s.week_monday == swing_week)
    assert swing.low == DOUBLE_BOTTOM[swing_week]
    assert swing.decline_pct >= R_DOWN

    signal = mirror_signal(window, swing)
    assert signal is not None
    assert monday_of(signal.date) == "2025-10-06"
    assert signal.date == "2025-10-10"          # the crash day itself

    # `top` is the argmax high of the leg being retraced — the 2025-10-06 ATH,
    # NOT the swing's own decline top (wk 2025-08-11, 124,474.00; see
    # `find_swing_lows`' note). It is read off the data rather than pasted
    # because the ATH is 126,199.63 and a 126,200 shorthand moves the target by
    # 18.5 cents, which is exactly the kind of drift the exact assertion below
    # exists to catch.
    top = max(b.high for b in window if b.date <= signal.date)
    assert top == Decimal("126199.63")

    fill_date, fill_price, target = _walk_forward_fill(window, signal, top)
    assert fill_date == "2025-10-12"
    # §10's tolerance is ±0.5% ("≈114,100"; owner: "~$114k"). The exact
    # arithmetic is (126,199.63 + 102,000) / 2 = 114,099.815, asserted exactly
    # as well so a change of a few dollars is visible rather than absorbed.
    assert abs(fill_price - Decimal("114100")) / Decimal("114100") < Decimal("0.005")
    assert fill_price == Decimal("114099.815")
    assert target == Decimal("114099.815")
    # SELL-limit semantics (§13.2): fill = max(target, open). The open that day
    # is 110,644.40, so a buy-side `min(level, open)` would fill 3.0% low — well
    # outside §10's ±0.5% band, i.e. this direction is genuinely pinned here.
    signal_next = next(b for b in window if b.date == fill_date)
    assert signal_next.open == Decimal("110644.40")
    assert fill_price > signal_next.open

    # The 8-week fallback (§6.2) is not reached: the fill is two days out.
    assert fill_date < "2025-12-05"


@pytest.mark.parametrize("swing_week", sorted(DOUBLE_BOTTOM))
def test_g4_break_must_follow_confirmation(g4_window, g4_swings, swing_week):
    """§6.2: "confirmation strictly precedes the break".

    **Observable on the 2025-08-25 leg only, and that is the reason both
    attributions are carried.** Its low is 107,350.10 and 2025-09-01 prints
    107,255.00 — strictly below it, and BEFORE the swing is confirmed on
    2025-09-10. Dropping the ordering guard therefore moves that leg's signal
    from the week of 2025-10-06 to the week of 2025-09-01, and the gate fails.
    On the 2025-09-01 leg the same mutation is INERT (nothing undercuts
    107,255.00 until the crash), so a single-attribution gate would leave the
    guard untested. Asserted for both so the difference is on the record.
    """
    window, _wks = g4_window
    swing = next(s for s in g4_swings if s.week_monday == swing_week)
    signal = mirror_signal(window, swing)

    assert swing.confirmed_at is not None
    assert swing.confirmed_at > swing.week_monday
    assert signal.date > swing.confirmed_at

    unguarded = next(b for b in window if b.low < swing.low)
    if swing_week == "2025-08-25":
        assert unguarded.date == "2025-09-01"
        assert unguarded.date < swing.confirmed_at
        assert monday_of(unguarded.date) != "2025-10-06"   # the wrong answer
    else:
        assert unguarded.date == signal.date               # inert here


def test_g4_break_day_is_excluded_from_fill_checks(g4_window, g4_swings):
    """§6.2: "the break day itself is excluded from fill checks (its high
    printed pre-break)".

    Load-bearing on real data, not a formality. The break day 2025-10-10 opened
    at 121,662.41 and printed a high of 122,550.00 on its way down to 102,000 —
    comfortably above the 114,099.815 target the crash itself creates. Including
    it fills the same day at max(target, open) = 121,662.41, i.e. 6.6% high and
    on the wrong date. Both halves of §10 G4's fill assertion would break.
    """
    window, _wks = g4_window
    swing = next(s for s in g4_swings if s.week_monday == "2025-09-01")
    signal = mirror_signal(window, swing)
    top = max(b.high for b in window if b.date <= signal.date)
    target = mirror_target(top, signal.low)

    assert signal.high > target                     # would fill on the break day
    assert sell_limit_fill(signal, target) == Decimal("121662.41")
    assert abs(Decimal("121662.41") - Decimal("114100")) / Decimal("114100") \
        > Decimal("0.005")                          # outside §10's tolerance


def test_g4_walk_forward_target_is_unobservable_here(g4_window, g4_swings):
    """The two remaining §6.2 fill clauses are NOT pinned by G4, and this test
    says so instead of implying otherwise.

    "target recomputes as the low falls" and "`low_so_far` includes the current
    day's low before testing that day's high" are only observable if a new low
    prints between the signal and the fill. Here the signal day IS the lowest day
    of the fill window (102,000 on 2025-10-10) and the next two days bottom at
    109,561.59 / 109,565.06 — so `low_so_far` never moves, the target is
    constant at 114,099.815, and a detector that froze the target at the signal
    day, or that tested the high before updating the low, produces the identical
    answer.

    Asserted rather than merely commented so the blind spot is self-invalidating:
    if a data refresh ever prints a lower low inside the fill window, this fails
    and whoever sees it gets a real walk-forward test out of the box.

    Partial cover elsewhere: `test_mirror_target_falls_as_the_low_falls` in
    tests/test_levels.py pins that the TARGET FUNCTION falls with the low. The
    LOOP's ordering has no cover anywhere, because the loop has no engine
    implementation to cover (module docstring).
    """
    window, _wks = g4_window
    swing = next(s for s in g4_swings if s.week_monday == "2025-09-01")
    signal = mirror_signal(window, swing)
    between = [b for b in window if "2025-10-10" < b.date <= "2025-10-12"]
    assert [b.date for b in between] == ["2025-10-11", "2025-10-12"]
    assert min(b.low for b in between) > signal.low


def test_g4_r_down_10_is_load_bearing_upward_only(g4_window, g4_swings):
    """`R_down = 10` is a frozen owner choice (§6.2). G4 constrains it from ABOVE
    only, and this test says which direction the evidence actually runs.

    UPPER — real, and tight. Both double-bottom legs decline only −13.76% /
    −13.83% off the wk-2025-08-11 top of 124,474.00, so **`R_down = 14` already
    deletes the structure §10 G4 names**. What survives at 15 is a set of
    post-crash swings whose earliest is wk 2025-10-13 — after the break — so no
    signal can land in the week of 2025-10-06 at all. This also records why §9's
    rejection of `R_down = 10` **for the LH side** does not transfer: the two
    knobs are independent, and the mirror side needs the looser one.

    LOWER — G4 is INSENSITIVE, and pretending otherwise would overstate it.
    Dropping to `R_down = 5` admits exactly one extra week (2025-09-15, −8.11%)
    and changes neither the double-bottom attribution nor the signal, because the
    extra swing is shallower than the ones already present and is never the most
    recent confirmed swing at the break. So nothing in §10 bounds `R_down` from
    below; 10 is the owner's number, not a fitted one.
    """
    window, wks = g4_window

    at_14 = find_swing_lows(wks, window, r_down=Decimal("14"))
    assert all(s.week_monday not in DOUBLE_BOTTOM for s in at_14)

    at_15 = find_swing_lows(wks, window, r_down=Decimal("15"))
    assert min(s.week_monday for s in at_15) == "2025-10-13"
    assert all(mirror_signal(window, s) is None
               or monday_of(mirror_signal(window, s).date) != "2025-10-06"
               for s in at_15)

    at_5 = find_swing_lows(wks, window, r_down=Decimal("5"))
    extra = {s.week_monday for s in at_5} - {s.week_monday for s in g4_swings}
    assert extra == {"2025-09-15"}
    assert next(s for s in at_5 if s.week_monday == "2025-09-15").low \
        > max(DOUBLE_BOTTOM.values())

    # The engine's own numbers for the two named lows, read off the r_down=5 run
    # so they exist as computed values rather than hand arithmetic.
    declines = {s.week_monday: s.decline_pct for s in at_5}
    assert Decimal("13.75") < declines["2025-08-25"] < Decimal("13.76")
    assert Decimal("13.83") < declines["2025-09-01"] < Decimal("13.84")
    assert all(s.top_high == Decimal("124474.00")
               for s in g4_swings if s.week_monday in DOUBLE_BOTTOM)


def test_g4_signal_is_the_same_under_the_mechanical_reading(g4_window, g4_swings):
    """§10 G4 names the ~107k double bottom; §6.2's mechanical rule breaks "the
    MOST RECENT confirmed swing low". On this window those are different objects
    — and they fire on the same day, which is why the gate reconciles.

    The most recent swing confirmed before the break is wk 2025-09-29 @
    111,560.65 (confirmed 2025-10-06), not the double bottom. The 2025-10-10
    crash takes out 111,560.65 and 107,350.10 and 107,255.00 in a single daily
    bar, so all three attributions produce the same signal date and the same
    fill. Asserted so the owner's chart read and the rule's output are recorded
    as agreeing here rather than assumed to agree in general.
    """
    window, _wks = g4_window
    at_break = [s for s in g4_swings if s.confirmed_at < "2025-10-10"]
    latest = max(at_break, key=lambda s: s.week_monday)
    assert latest.week_monday == "2025-09-29"
    assert latest.low == Decimal("111560.65")
    assert latest.week_monday not in DOUBLE_BOTTOM
    assert mirror_signal(window, latest).date == "2025-10-10"
    for week in DOUBLE_BOTTOM:
        swing = next(s for s in g4_swings if s.week_monday == week)
        assert mirror_signal(window, swing).date == "2025-10-10"
