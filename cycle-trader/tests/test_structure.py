from decimal import Decimal, Inexact, ROUND_FLOOR, localcontext
from engine.context import CTX
from engine.structure import find_lh_candidates, operative_lh, find_bos, first_bos
from engine.types import Bar, Week


def wk(monday, h, l, c=None):
    return Week(monday, Decimal(str(h)), Decimal(str(l)), Decimal(str(c if c is not None else l)))


def bar(date, o, h, l, c=None):
    return Bar(date, Decimal(str(o)), Decimal(str(h)), Decimal(str(l)),
               Decimal(str(c if c is not None else l)))


def test_rally_below_15_percent_is_rejected():
    """G5: the June-2026 bounce to 67,292 is +13.8% off 59,138 and must NOT
    become operative."""
    weeks = [wk("2026-01-05", 100000, 90000),
             wk("2026-05-04", 62000, 59138),
             wk("2026-06-15", 67292, 60000),
             wk("2026-06-22", 61000, 57800)]
    bars = [bar("2026-06-23", 60000, 61000, 57800)]
    cands = find_lh_candidates(weeks, bars, "2026-01-05", "2026-02-02")
    assert all(c.price != Decimal("67292") for c in cands)


def test_rally_from_non_fresh_low_is_rejected():
    """G3: Sept-2022's 22,799 high rallied from ~18.1k, which never undercut
    June's 17,622 — not a fresh low, so it is excluded.

    FIXTURE CORRECTION (see report): the brief's fixture omitted the
    2022-08-15 week (25,211.32) — G3's own operative LH. Without it,
    `anchor(2022-09-12)` falls back to the June week and the origin window
    swallows June's 17,622, so 22,799 is scored as a *fresh*-low rally and
    admitted. Real weekly data (verbatim below) puts the August high between
    them, and the intervening weeks are carried verbatim so September's origin
    is its real 18,510.77 (wk 2022-09-05). That matters: at 18,510.77 the rally
    is +23.2%, so FRESHNESS ALONE excludes 22,799 — SPEC §10 G3's stated
    reason. Under the brief's abridged fixture the origin came out at 20,761.90
    (+9.8%) and the degree test did the excluding, so every freshness mutation
    survived. The exclusion is only meaningful next to the inclusion, so the LH
    G3 *requires* is asserted here too.
    """
    weeks = [wk("2021-11-08", 69000, 62278),
             wk("2022-06-13", 26895.84, 17622),
             wk("2022-07-18", 24276.74, 20762.45),
             wk("2022-08-15", 25211.32, 20761.90),
             wk("2022-08-22", 21900, 19520),
             wk("2022-08-29", 20576.25, 19540),
             wk("2022-09-05", 21860, 18510.77),
             wk("2022-09-12", 22799, 19320.01)]
    bars = [bar("2022-09-20", 19000, 19500, 18200),
            bar("2022-11-08", 20590.67, 20700.88, 17166.83)]
    cands = find_lh_candidates(weeks, bars, "2021-11-08", "2022-05-23")
    assert all(c.price != Decimal("22799") for c in cands)
    lh = next(c for c in cands if c.price == Decimal("25211.32"))
    assert lh.origin_low == Decimal("17622")
    assert lh.confirmed_at == "2022-11-08"          # G3's "Nov crash"
    assert round(lh.rally_pct, 1) == Decimal("43.1")


def test_candidate_is_unusable_before_its_confirmation_date():
    # 2014-09-01's low is 450, not the brief's 400: at 400 the 2014-09-29 week
    # (high 480) is itself a +20% fresh-low candidate that never gets broken,
    # which masks 305's own life cycle in the sibling test below. At 450 that
    # rally is +6.7% and only 305 survives. See report.
    weeks = [wk("2014-09-01", 500, 450),
             wk("2014-09-29", 480, 275),
             wk("2014-12-29", 300, 255),
             wk("2015-01-05", 305, 260)]
    bars = [bar("2015-01-14", 200, 210, 152.40)]
    cands = find_lh_candidates(weeks, bars, "2014-09-01", "2014-09-29")
    lh = [c for c in cands if c.price == Decimal("305")]
    assert lh, "305 should be a candidate"
    assert lh[0].confirmed_at == "2015-01-14"
    assert operative_lh(cands, asof="2015-01-13") is None
    assert operative_lh(cands, asof="2015-01-14").price == Decimal("305")


def test_bos_is_first_daily_high_above_the_operative_lh():
    bars = [bar("2015-01-20", 290, 300, 285),
            bar("2015-01-28", 300, 309.90, 295)]
    assert find_bos(bars, Decimal("305"), after="2015-01-14") == "2015-01-28"


def test_bos_returns_none_when_never_broken():
    bars = [bar("2026-07-20", 60000, 61000, 59000)]
    assert find_bos(bars, Decimal("82850"), after="2026-06-07") is None


def test_candidate_operative_through_break_day_and_first_bos_finds_it():
    """§4.5's invalidation IS the BoS. Day-resolution invalidation, operative
    through the break day — with `>` instead of `>=`, or with week-Monday
    invalidation labels, the walk can never see its own break.

    The 2014-09-01 low is 450 (brief: 400) so that 305 is the ONLY candidate:
    with 400, the unbroken 480 candidate takes over the moment 305 dies, and
    both boundary assertions below pass under a `>`-mutated operative_lh.
    """
    weeks = [wk("2014-09-01", 500, 450),
             wk("2014-09-29", 480, 275),
             wk("2014-12-29", 300, 255),
             wk("2015-01-05", 305, 260)]
    bars = [bar("2015-01-14", 200, 210, 152.40),
            bar("2015-01-28", 300, 309.90, 295)]   # the break day
    cands = find_lh_candidates(weeks, bars, "2014-09-01", "2014-09-29")
    lh = next(c for c in cands if c.price == Decimal("305"))
    assert lh.invalidated_at == "2015-01-28"                     # daily, not weekly
    assert operative_lh(cands, asof="2015-01-28") is not None    # alive on break day
    assert operative_lh(cands, asof="2015-01-29") is None        # dead after
    bos, broken = first_bos(bars, cands, start="2014-09-29", end="2015-12-31")
    assert bos == "2015-01-28"
    assert broken.price == Decimal("305")


def test_d_guard_rejects_scope_that_postdates_the_trigger():
    """EP1's 2013 trap: no valid downtrend anchor predating the trigger.

    FIXTURE CORRECTION (see report): the brief's one-week fixture was vacuous
    — a lone week has no anchor, so it yields [] with the guard DELETED too.
    These weeks produce a candidate whenever the guard passes, so the guard is
    the only thing returning [] below. The equality case is EP1's real one:
    §13.3's guard is `monday(D) < trigger_week`, and EP1's D *is* its trigger
    week.
    """
    weeks = [wk("2013-12-02", 1163, 800), wk("2013-12-09", 900, 500),
             wk("2013-12-16", 700, 600)]
    assert find_lh_candidates(weeks, [], scope_start="2013-12-02",
                              trigger_monday="2014-01-06"), "guard passing → candidates"
    assert find_lh_candidates(weeks, [], scope_start="2013-12-02",
                              trigger_monday="2013-12-02") == []   # D == trigger (EP1)
    assert find_lh_candidates(weeks, [], scope_start="2013-12-02",
                              trigger_monday="2011-11-21") == []   # D after the trigger


# ---------------------------------------------------------------------------
# Tests beyond the brief.
#
# The brief's seven tests killed 19 of a 44-mutant catalogue. Everything below
# closes a survivor: each pins behaviour that SPEC §4/§13.3 states but that no
# brief test objected to. Exact-touch cases are not hypothetical — Task 5
# established that this dataset has 345 days whose low exactly repeats an
# earlier low and 362 for highs.
# ---------------------------------------------------------------------------


def g1_weeks():
    """G1's real weekly bars, verbatim from the reference dataset.

    This is SPEC §13.3's own proof that the rally-origin window must include
    the anchor week: **2014-12-29 has high 321.00 (the anchor, above the 305.00
    candidate) AND low 255.00 (the origin)**. Under a `j+1` window that week is
    invisible, the origin window is empty and this fixture yields NOTHING.

    Two candidates come out of it — 321.00 (wk 2014-12-29, +16.7% off 275) and
    305.00 (wk 2015-01-05, +19.6% off 255) — so tests below select 305 by price
    rather than by position.
    """
    return [wk("2014-09-01", 497, 470.42), wk("2014-09-29", 397.75, 275),
            wk("2014-12-29", 321.00, 255.00), wk("2015-01-05", 305.00, 262.08)]


def lh305(cands):
    return next(c for c in cands if c.price == Decimal("305"))


def two_candidate_weeks():
    """G1's weeks plus a LOWER later candidate, 260 (wk 2015-01-19, origin
    200). The 290 week between them rallies from a 262.08 low that never
    undercut 255, so it is not itself a candidate."""
    return g1_weeks() + [wk("2015-01-12", 290, 200), wk("2015-01-19", 260, 210)]


def scope_weeks():
    """D (2022-01-03) is a wide week: its 48,000 high is the anchor that makes
    42,000 a candidate, and its 25,000 low is the freshness floor that denies
    36,000. The 2021-12-27 week sits BEFORE the scope start and must be
    invisible on both counts — it has both the higher high and the lower low."""
    return [wk("2021-12-27", 90000, 20000),   # before scope_start
            wk("2022-01-03", 48000, 25000),   # D == scope_start
            wk("2022-01-10", 42000, 30000),
            wk("2022-01-17", 36000, 33000)]


def degree_weeks():
    """The 115 candidate rallies from 100 — exactly R_e = 15%."""
    return [wk("2020-01-06", 200, 150), wk("2020-01-13", 180, 100),
            wk("2020-01-20", 115, 105)]


def test_the_scope_start_week_itself_is_inside_the_scan():
    """§13.3 scans weeks with `monday(i) >= monday(D)` and measures freshness
    from `low[D ..]` — D's own week is in scope on both counts."""
    cands = find_lh_candidates(scope_weeks(), [], "2022-01-03", "2022-02-07")
    inner = next(c for c in cands if c.price == Decimal("42000"))
    assert inner.anchor_week == "2022-01-03"        # D anchors it
    assert inner.origin_low == Decimal("25000")     # D's own low is the origin
    # 36,000 rallies +20% off 30,000 — degree passes; only D's 25,000 low
    # stops it. Drop D from the scan and this becomes a valid candidate.
    assert all(c.price != Decimal("36000") for c in cands)


def test_weeks_before_the_scope_start_are_invisible():
    """The `monday >= scope_start` filter is load-bearing in both roles.

    2021-12-27's 90,000 high is the only thing that could anchor the 48,000
    week, and its 20,000 low is below D's 25,000. If the filter is dropped,
    48,000 becomes a candidate (anchored out of scope) and 42,000 stops being
    one (its 25,000 origin is no longer fresh). On real data that mutation
    takes EP2 from 25 candidates to 6 and every episode's BoS to None.
    """
    cands = find_lh_candidates(scope_weeks(), [], "2022-01-03", "2022-02-07")
    assert all(c.price != Decimal("48000") for c in cands)   # cannot be anchored
    assert any(c.price == Decimal("42000") for c in cands)   # 20,000 is not a floor


def test_anchor_requires_a_strictly_higher_high():
    """`anchor(i)` is the most recent week whose high EXCEEDS week i's — an
    equal high is not higher. The nearer 80 week would shrink the origin
    window to a 70 low (+14.3%, rejected) instead of the correct 40 (+100%)."""
    weeks = [wk("2019-01-07", 120, 50), wk("2019-01-14", 100, 40),
             wk("2019-01-21", 80, 70), wk("2019-01-28", 80, 75)]
    cands = find_lh_candidates(weeks, [], "2019-01-07", "2019-02-04")
    lh = next(c for c in cands if c.week_monday == "2019-01-28")
    assert lh.anchor_week == "2019-01-14"
    assert lh.origin_low == Decimal("40")


def test_degree_is_inclusive_at_exactly_r_e():
    """§4.2 is `rally >= 15%`; the code rejects on `rally < r_e`. A rally of
    exactly R_e is a candidate."""
    cands = find_lh_candidates(degree_weeks(), [], "2020-01-06", "2020-02-03")
    lh = next(c for c in cands if c.price == Decimal("115"))
    assert lh.rally_pct == Decimal("15")


def test_freshness_requires_a_strict_undercut():
    """A low that MATCHES the scope's prior low has not 'undercut ALL prior
    lows' (§4.1). 140 rallies +40% off 100 — degree cannot be what rejects it;
    the earlier, equal 100 low is."""
    weeks = [wk("2020-01-06", 200, 100), wk("2020-01-13", 180, 170),
             wk("2020-01-20", 160, 100), wk("2020-01-27", 140, 120)]
    cands = find_lh_candidates(weeks, [], "2020-01-06", "2020-02-03")
    assert all(c.price != Decimal("140") for c in cands)


def test_confirmation_is_the_first_daily_undercut_after_the_candidate_week():
    """§4.3 + §13.4: a DAILY low, strictly after week i ends. Week 2015-01-05
    runs to Sunday 2015-01-11, so neither the mid-week undercut nor the Sunday
    one confirms — the following Monday does.

    These three bars are constructed, not historical: the real week never
    traded below 255 before it closed (its low was 262.08), so the ordering
    rule has no natural fixture.
    """
    bars = [bar("2015-01-07", 260, 265, 250),   # inside week i
            bar("2015-01-11", 250, 255, 240),   # week i's last day (Sunday)
            bar("2015-01-12", 240, 245, 230)]   # first day after week i
    assert lh305(find_lh_candidates(g1_weeks(), bars, "2014-09-01",
                                    "2014-09-29")).confirmed_at == "2015-01-12"


def test_confirmation_undercut_is_strict():
    """'strictly less than L₀' (§13.4). A low printing exactly 255.00 does not
    confirm the 255 origin; 2015-01-13's real 216.00 low does."""
    bars = [bar("2015-01-12", 266.34, 272.43, 255.00),      # equal to L0
            bar("2015-01-13", 267.10, 268.15, 216.00)]      # real bar
    assert lh305(find_lh_candidates(g1_weeks(), bars, "2014-09-01",
                                    "2014-09-29")).confirmed_at == "2015-01-13"


def test_invalidation_ignores_highs_that_predate_the_candidate_week():
    """§4.5 kills a candidate on a LATER high that EXCEEDS it. Both bounds are
    load-bearing, and both fixtures here are real bars.

    2014-12-31 printed 321.00 — above the 305 candidate — but it belongs to the
    anchor week, before 305 existed. Without the `> cand_end` bound every
    candidate is invalidated on sight and no BoS can ever print. The 2015-01-20
    bar is constructed: an exact 305.00 touch is not an exceedance.
    """
    bars = [bar("2014-12-31", 311.10, 321.00, 310.69, 321.00),   # real, pre-dates week i
            bar("2015-01-13", 267.10, 268.15, 216.00),           # real, confirms
            bar("2015-01-20", 300, 305, 295),                    # exact touch
            bar("2015-01-26", 254.67, 309.90, 254.67, 274.80)]   # real, the break
    lh = lh305(find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29"))
    assert lh.confirmed_at == "2015-01-13"
    assert lh.invalidated_at == "2015-01-26"


def test_operative_lh_is_the_most_recent_candidate_not_the_highest():
    """'Operative LH = the most recent valid candidate' (§4). With 321, 305 and
    a later, lower 260 all live, the operative LH is 260."""
    bars = [bar("2015-01-26", 250, 255, 240),   # confirms 321 and 305
            bar("2015-02-02", 210, 215, 190)]   # confirms 260 (low < 200)
    cands = find_lh_candidates(two_candidate_weeks(), bars, "2014-09-01", "2014-09-29")
    assert {c.price for c in cands} == {Decimal("321"), Decimal("305"), Decimal("260")}
    assert operative_lh(cands, asof="2015-02-02").price == Decimal("260")
    assert operative_lh(cands, asof="2015-02-01").price == Decimal("305")


def test_an_unconfirmed_candidate_is_never_operative():
    """A more recent candidate that has not been confirmed cannot displace an
    older confirmed one (§4.3 — unusable before confirmation)."""
    bars = [bar("2015-01-26", 250, 255, 240)]   # confirms 321 and 305 only
    cands = find_lh_candidates(two_candidate_weeks(), bars, "2014-09-01", "2014-09-29")
    assert next(c for c in cands if c.price == Decimal("260")).confirmed_at is None
    assert operative_lh(cands, asof="2015-12-31").price == Decimal("305")


def test_find_bos_excludes_the_after_day_and_requires_a_strict_break():
    """§4: BoS is a daily high ABOVE the LH, strictly after `after`."""
    bars = [bar("2015-01-14", 300, 306, 295),      # would break, but is `after`
            bar("2015-01-20", 300, 305, 295),      # exact touch — not above
            bar("2015-01-26", 254.67, 309.90, 254.67)]
    assert find_bos(bars, Decimal("305"), after="2015-01-14") == "2015-01-26"


def test_first_bos_ignores_a_break_on_the_confirmation_day():
    """Confirmation must strictly precede any use of the candidate (§4.3).
    A day that both confirms 305 and trades through it yields no BoS — and
    kills the candidate, so no later day can produce one either."""
    bars = [bar("2015-01-12", 240, 306, 230)]
    cands = find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29")
    assert lh305(cands).confirmed_at == "2015-01-12"
    assert lh305(cands).invalidated_at == "2015-01-12"
    assert first_bos(bars, cands, start="2015-01-01", end="2015-12-31") == (None, None)


def test_first_bos_requires_a_strict_break_and_honours_its_window():
    """The real G1 break: 2015-01-26's 309.90 high through the 305 LH."""
    bars = [bar("2015-01-13", 267.10, 268.15, 216.00),           # real, confirms
            bar("2015-01-20", 300, 305, 295),                    # exact touch
            bar("2015-01-26", 254.67, 309.90, 254.67, 274.80)]   # real, the break
    cands = find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29")
    bos, broken = first_bos(bars, cands, start="2015-01-01", end="2015-12-31")
    assert (bos, broken.price) == ("2015-01-26", Decimal("305"))
    # `end` excludes the break day
    assert first_bos(bars, cands, start="2015-01-01", end="2015-01-25") == (None, None)
    # `start` after the break: 305 is already dead
    assert first_bos(bars, cands, start="2015-01-27", end="2015-12-31") == (None, None)


def test_rally_pct_is_independent_of_the_ambient_decimal_context():
    """The rally percentage is this module's only inexact computation, and it
    gates a strict threshold (`rally < r_e`, R_e=15), so an ambient precision
    change can admit or drop a lower-high candidate -- and the operative LH is
    what the BoS, the ladder leg and EL* all hang off.

    Measured on the frozen series the candidate set survives down to prec 3 and
    flips only at prec 1 (EP6 yields 8 candidates instead of 12), but the
    tightest real margin is 0.4988 points (wk 2025-11-24 rallies +15.4988%
    against the 15 cutoff), which the error clears only from prec >= 4.
    engine/context.py pins the context; this test fails if that pin is removed.

    The fixture's rally is deliberately non-terminating -- (82,850 - 60,000) /
    60,000 = 38.0833... -- so precision is actually observable; a fixture with a
    terminating quotient would pass unpinned. That property is asserted against
    `CTX.prec` rather than a literal digit count: the guard is about ambient
    *independence*, and hardcoding 34 digits here would make every future change
    to the pin's magnitude fail this test for no substantive reason. The
    magnitude itself is pinned where it actually binds -- levels.py needs
    prec >= 10, the strictest of the three, and its guard fails at 9."""
    weeks = [wk("2026-01-05", 100000, 90000),
             wk("2026-05-04", 62000, 60000),
             wk("2026-06-15", 82850, 70000)]
    bars = [bar("2026-06-23", 61000, 62000, 59000)]
    expected = find_lh_candidates(weeks, bars, "2026-01-05", "2026-02-02")
    assert [c.price for c in expected] == [Decimal("82850")]
    # saturates the pinned precision => the quotient does not terminate,
    # so a precision change is observable in this fixture
    assert len(expected[0].rally_pct.as_tuple().digits) == CTX.prec

    with localcontext() as ctx:
        ctx.prec = 2
        ctx.rounding = ROUND_FLOOR
        ctx.traps[Inexact] = True
        got = find_lh_candidates(weeks, bars, "2026-01-05", "2026-02-02")
    assert [c.rally_pct for c in got] == [c.rally_pct for c in expected]
