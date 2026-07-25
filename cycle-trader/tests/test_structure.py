from decimal import Decimal
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
    """G1's shape, trimmed so 305.00 (wk 2015-01-05, origin 255) is the ONLY
    candidate: 2014-09-01's low is 450, which leaves the 480 week a +6.7%
    rally rather than a second, never-broken candidate."""
    return [wk("2014-09-01", 500, 450), wk("2014-09-29", 480, 275),
            wk("2014-12-29", 300, 255), wk("2015-01-05", 305, 260)]


def two_candidate_weeks():
    """305 (wk 2015-01-05, origin 255) then a LOWER later candidate 260
    (wk 2015-01-19, origin 200). The 290 week between them is +11.5% and is
    not itself a candidate."""
    return g1_weeks() + [wk("2015-01-12", 290, 200), wk("2015-01-19", 260, 210)]


def degree_weeks():
    """The 115 candidate rallies from 100 — exactly R_e = 15%."""
    return [wk("2020-01-06", 200, 150), wk("2020-01-13", 180, 100),
            wk("2020-01-20", 115, 105)]


def test_the_scope_start_week_itself_is_inside_the_scan():
    """§13.3 scans weeks with `monday(i) >= monday(D)` and measures freshness
    from `low[D ..]` — D's own week is in scope on both counts. Here D is a
    wide week (48,000 / 25,000): it is the anchor that makes 42,000 a
    candidate, and its 25,000 low is what denies 36,000 its fresh low."""
    weeks = [wk("2022-01-03", 48000, 25000),   # D
             wk("2022-01-10", 42000, 30000),
             wk("2022-01-17", 36000, 33000)]
    cands = find_lh_candidates(weeks, [], "2022-01-03", "2022-02-07")
    inner = next(c for c in cands if c.price == Decimal("42000"))
    assert inner.anchor_week == "2022-01-03"
    assert inner.origin_low == Decimal("25000")
    # 36,000 rallies +20% off 30,000 — degree passes; only D's 25,000 low
    # stops it. Drop D from the scan and this becomes a valid candidate.
    assert all(c.price != Decimal("36000") for c in cands)


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
    """§4.3 + §13.4: a DAILY low, strictly after week i ends. The candidate
    week runs 2015-01-05..2015-01-11, so neither the mid-week undercut nor the
    Sunday one confirms — the following Monday does."""
    bars = [bar("2015-01-07", 260, 265, 250),   # inside week i
            bar("2015-01-11", 250, 255, 240),   # week i's last day (Sunday)
            bar("2015-01-12", 240, 245, 230)]   # first day after week i
    cands = find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29")
    assert cands[0].confirmed_at == "2015-01-12"


def test_confirmation_undercut_is_strict():
    """'strictly less than L₀' (§13.4). A low that prints exactly 255.00 does
    not confirm the 255 origin."""
    bars = [bar("2015-01-12", 260, 265, 255),   # equal to L0 — not an undercut
            bar("2015-01-13", 255, 258, 254.99)]
    cands = find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29")
    assert cands[0].confirmed_at == "2015-01-13"


def test_invalidation_requires_a_strictly_higher_high():
    """§4.5 kills a candidate when a later high EXCEEDS it. A day printing
    exactly 305.00 is not an exceedance and is not a BoS either."""
    bars = [bar("2015-01-12", 240, 245, 230),      # confirmation
            bar("2015-01-19", 300, 305, 295),      # exact touch — not a break
            bar("2015-01-28", 300, 309.90, 295)]   # the break
    cands = find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29")
    assert cands[0].invalidated_at == "2015-01-28"


def test_operative_lh_is_the_most_recent_candidate_not_the_highest():
    """'Operative LH = the most recent valid candidate' (§4). With 305 and a
    later, lower 260 both live, the operative LH is 260."""
    bars = [bar("2015-01-26", 250, 255, 240),   # confirms 305 (low < 255)
            bar("2015-02-02", 210, 215, 190)]   # confirms 260 (low < 200)
    cands = find_lh_candidates(two_candidate_weeks(), bars, "2014-09-01", "2014-09-29")
    assert {c.price for c in cands} == {Decimal("305"), Decimal("260")}
    assert operative_lh(cands, asof="2015-02-02").price == Decimal("260")
    assert operative_lh(cands, asof="2015-02-01").price == Decimal("305")


def test_an_unconfirmed_candidate_is_never_operative():
    """A more recent candidate that has not been confirmed cannot displace an
    older confirmed one (§4.3 — unusable before confirmation)."""
    bars = [bar("2015-01-26", 250, 255, 240)]   # confirms 305 only
    cands = find_lh_candidates(two_candidate_weeks(), bars, "2014-09-01", "2014-09-29")
    assert next(c for c in cands if c.price == Decimal("260")).confirmed_at is None
    assert operative_lh(cands, asof="2015-12-31").price == Decimal("305")


def test_find_bos_excludes_the_after_day_and_requires_a_strict_break():
    """§4: BoS is a daily high ABOVE the LH, strictly after `after`."""
    bars = [bar("2015-01-14", 300, 306, 295),      # would break, but is `after`
            bar("2015-01-20", 300, 305, 295),      # exact touch — not above
            bar("2015-01-28", 300, 309.90, 295)]
    assert find_bos(bars, Decimal("305"), after="2015-01-14") == "2015-01-28"


def test_first_bos_ignores_a_break_on_the_confirmation_day():
    """Confirmation must strictly precede any use of the candidate (§4.3).
    A day that both confirms 305 and trades through it yields no BoS — and
    kills the candidate, so no later day can produce one either."""
    bars = [bar("2015-01-12", 240, 306, 230)]
    cands = find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29")
    assert cands[0].confirmed_at == "2015-01-12"
    assert cands[0].invalidated_at == "2015-01-12"
    assert first_bos(bars, cands, start="2015-01-01", end="2015-12-31") == (None, None)


def test_first_bos_requires_a_strict_break_and_honours_its_window():
    bars = [bar("2015-01-12", 240, 245, 230),      # confirmation
            bar("2015-01-20", 300, 305, 295),      # exact touch — not a break
            bar("2015-01-28", 300, 309.90, 295)]   # the break
    cands = find_lh_candidates(g1_weeks(), bars, "2014-09-01", "2014-09-29")
    assert first_bos(bars, cands, start="2015-01-01", end="2015-12-31")[0] == "2015-01-28"
    # `end` excludes the break day
    assert first_bos(bars, cands, start="2015-01-01", end="2015-01-27") == (None, None)
    # `start` after the break: the candidate is already dead, so nothing fires
    assert first_bos(bars, cands, start="2015-01-29", end="2015-12-31") == (None, None)
