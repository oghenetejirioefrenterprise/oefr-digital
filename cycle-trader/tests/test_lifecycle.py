from decimal import Decimal

import pytest

from engine.lifecycle import (
    RSI_TRIGGER,
    QUIET_WEEKS,
    downtrend_anchor,
    find_triggers,
    freeze_el,
    prior_cycle_ath,
    running_low,
)
from engine.levels import extension_1272
from engine.rsi import wilder_rsi
from engine.types import Bar, Week


def wk(monday, h, l, c):
    return Week(monday, Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def bar(date, o, h, l, c):
    return Bar(date, Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def test_quiet_weeks_constant_is_26():
    assert QUIET_WEEKS == 26


def test_armed_weeks_within_26_quiet_weeks_cluster_into_one_episode():
    # 2020-01-06, -13, -20 are consecutive real Mondays
    weeks = [wk(f"2020-01-{i:02d}", 1, 1, 1) for i in (6, 13, 20)]
    rsi = [Decimal("30"), Decimal("40"), Decimal("30")]  # armed, quiet, armed
    assert find_triggers(weeks, rsi) == ["2020-01-06"]


def test_trigger_after_26_quiet_weeks_starts_a_new_episode():
    """Filler weeks must carry REAL ISO Mondays: Task 1 hardened `Week` to
    validate `monday` as an ISO YYYY-MM-DD date, so placeholder labels like
    "w0"/"w1" now raise ValueError at construction."""
    from datetime import date, timedelta
    start = date.fromisoformat("2020-01-06")
    mondays = [(start + timedelta(weeks=k)).isoformat()
               for k in range(QUIET_WEEKS + 3)]
    weeks = [wk(m, 1, 1, 1) for m in mondays]
    rsi = [Decimal("30")] + [Decimal("50")] * (QUIET_WEEKS + 1) + [Decimal("30")]
    assert len(rsi) == len(weeks)
    # armed, then 27 consecutive quiet weeks (>= 26 closes the window), then armed
    assert find_triggers(weeks, rsi) == [mondays[0], mondays[-1]]


def test_none_armed_gives_no_triggers():
    weeks = [wk("2020-01-06", 1, 1, 1)]
    assert find_triggers(weeks, [Decimal("50")]) == []


def test_prior_cycle_ath_is_highest_weekly_high_before_the_trigger():
    weeks = [wk("2021-11-08", 69000, 60000, 61000),
             wk("2022-01-03", 48000, 40000, 41000),
             wk("2022-05-23", 30000, 28000, 29000)]
    ath, ath_week = prior_cycle_ath(weeks, "2022-05-23")
    assert ath == Decimal("69000")
    assert ath_week == "2021-11-08"


def test_running_low_is_lowest_daily_low_walk_forward():
    bars = [bar("2022-06-13", 26574.53, 26895.84, 21925.77, 22487.41),
            bar("2022-06-18", 19000, 19500, 17622, 18000),
            bar("2022-11-09", 18000, 18100, 15476, 15800)]
    assert running_low(bars, "2022-05-23", "2022-06-18") == Decimal("17622")
    assert running_low(bars, "2022-05-23", "2022-11-09") == Decimal("15476")


def test_downtrend_anchor_is_argmax_high_week_of_the_window():
    weeks = [wk("2019-04-01", 5350, 4067, 5250),
             wk("2019-06-24", 13970, 11000, 12000),
             wk("2019-10-21", 10370, 8200, 9200),
             wk("2020-02-10", 10500, 9700, 9900)]
    d_price, d_week = downtrend_anchor(weeks, window_start="2019-04-01",
                                       asof="2020-03-09")
    assert d_price == Decimal("13970")
    assert d_week == "2019-06-24"


def test_ep4_episode_low_from_d_not_from_prior_ath():
    """The disambiguating case: from the Dec-2017 ATH the min low is 3,156.26
    (EP3's low); from D = June-2019 it is 3,782.13, which is what the
    reference records for EP4."""
    bars = [bar("2018-12-15", 3200, 3250, 3156.26, 3180),   # EP3's low
            bar("2019-06-26", 12800, 13970, 12000, 13000),   # D week
            bar("2020-03-13", 5100, 5900, 3782.13, 5500)]    # COVID low
    assert running_low(bars, "2017-12-11", "2020-03-16") == Decimal("3156.26")
    assert running_low(bars, "2019-06-24", "2020-03-16") == Decimal("3782.13")


def test_ep5_frozen_el_reproduces_the_1272_exit():
    """EL* = 15,476 and prior ATH 69,000 give SPEC §11's Exit 1 of 83,558.53.

    §13.1's argument for the frozen anchor: the extension only reconciles with
    the record when it is anchored on EL* rather than on a still-running low.
    Driven through engine.levels so this asserts the engine, not the arithmetic."""
    lvl = extension_1272(Decimal("15476"), Decimal("69000"))
    assert abs(lvl - Decimal("83558.53")) < Decimal("0.01")


# --- additions beyond the brief -------------------------------------------
# Declared in the task report: the brief exports `freeze_el`, `RSI_TRIGGER` and
# the `asof` bound of `downtrend_anchor` without pinning any of them, and the
# weeks<->rsi index alignment that `find_triggers` zips is load-bearing.


def test_find_triggers_indices_align_with_wilder_rsi_output():
    """`find_triggers` zips `weeks` and `rsi` position-for-position, and the
    caller builds `rsi` as `wilder_rsi([w.close for w in weeks])`. A one-slot
    offset would arm the episode on the neighbouring week, so pin the join
    against real RSI output: the first sub-35 reading here is week 17."""
    from datetime import date, timedelta
    closes = [Decimal(str(100 + 2 * i)) for i in range(15)] + \
             [Decimal(str(v)) for v in (110, 95, 80, 70, 60, 55)]
    start = date.fromisoformat("2019-01-07")
    weeks = [Week((start + timedelta(weeks=i)).isoformat(),
                  c, c, c) for i, c in enumerate(closes)]
    rsi = wilder_rsi([w.close for w in weeks])

    assert len(rsi) == len(weeks)
    assert rsi[:14] == [None] * 14          # warm-up: no arming possible
    armed = [i for i, v in enumerate(rsi) if v is not None and v < RSI_TRIGGER]
    assert armed[0] == 17
    assert weeks[17].monday == "2019-05-06"
    assert find_triggers(weeks, rsi) == ["2019-05-06"]


def _armed_run(quiet_count):
    """armed, then `quiet_count` quiet weeks, then armed."""
    from datetime import date, timedelta
    start = date.fromisoformat("2020-01-06")
    n = quiet_count + 2
    mondays = [(start + timedelta(weeks=k)).isoformat() for k in range(n)]
    weeks = [wk(m, 1, 1, 1) for m in mondays]
    rsi = [Decimal("30")] + [Decimal("50")] * quiet_count + [Decimal("30")]
    return weeks, rsi, mondays


def test_exactly_26_quiet_weeks_closes_the_window_but_25_does_not():
    """The boundary the constant names. The brief's case uses 27 quiet weeks,
    which passes under both `>= 26` and `> 26`; only the exact-26 case
    separates them."""
    weeks, rsi, mondays = _armed_run(QUIET_WEEKS)
    assert find_triggers(weeks, rsi) == [mondays[0], mondays[-1]]

    weeks, rsi, mondays = _armed_run(QUIET_WEEKS - 1)
    assert find_triggers(weeks, rsi) == [mondays[0]]


def test_an_armed_week_resets_the_quiet_run():
    """Two 20-week quiet stretches broken by an armed week are still ONE
    episode: the counter measures *consecutive* quiet weeks, not a total."""
    from datetime import date, timedelta
    start = date.fromisoformat("2020-01-06")
    rsi = ([Decimal("30")] + [Decimal("50")] * 20) * 2 + [Decimal("30")]
    mondays = [(start + timedelta(weeks=k)).isoformat() for k in range(len(rsi))]
    weeks = [wk(m, 1, 1, 1) for m in mondays]
    assert 20 < QUIET_WEEKS < 40      # the run only closes if resets are missed
    assert find_triggers(weeks, rsi) == [mondays[0]]


def test_anchors_rank_by_weekly_HIGH_not_by_low_or_close():
    """The anchor week is the argmax *high*. A week that closes or bottoms
    higher but topped lower must not win."""
    weeks = [wk("2019-04-01", 5350, 4067, 5250),
             wk("2019-06-24", 13970, 11000, 12000),   # highest high
             wk("2019-08-05", 13000, 12500, 12900)]   # higher low AND close
    assert prior_cycle_ath(weeks, "2019-12-30") == (Decimal("13970"), "2019-06-24")
    assert downtrend_anchor(weeks, window_start="2019-04-01",
                            asof="2019-12-30") == (Decimal("13970"), "2019-06-24")


def test_running_low_bounds_are_both_inclusive():
    """A bar landing exactly on scope_start or on `upto` is inside the scope."""
    bars = [bar("2022-05-23", 30000, 30100, 28000, 29000),   # == scope_start
            bar("2022-06-18", 19000, 19500, 28500, 19200)]   # == upto
    assert running_low(bars, "2022-05-23", "2022-06-18") == Decimal("28000")
    assert running_low(bars, "2022-05-23", "2022-05-23") == Decimal("28000")
    assert running_low(bars, "2022-06-18", "2022-06-18") == Decimal("28500")


def test_freeze_el_ignores_lows_before_the_scope_start():
    """EL* is measured from D forward — this is the EP4 trap again, at the
    freeze: a lower low predating D must not become the stop."""
    bars = [bar("2018-12-15", 3200, 3250, 3156.26, 3180),   # before D
            bar("2019-06-26", 12800, 13970, 12000, 13000),
            bar("2020-03-13", 5100, 5900, 3782.13, 5500)]
    assert freeze_el(bars, "2019-06-24", "2020-03-16") == Decimal("3782.13")


def test_find_triggers_rejects_length_mismatch():
    """`zip` truncates silently; a short `rsi` list would drop the tail of the
    history and quietly lose triggers instead of failing."""
    weeks = [wk("2020-01-06", 1, 1, 1), wk("2020-01-13", 1, 1, 1)]
    with pytest.raises(ValueError):
        find_triggers(weeks, [Decimal("30")])


def test_find_triggers_ignores_the_rsi_warmup_nones():
    """None is not 'armed' — and a bare `value < 35` would raise TypeError."""
    weeks = [wk("2020-01-06", 1, 1, 1), wk("2020-01-13", 1, 1, 1)]
    assert find_triggers(weeks, [None, Decimal("30")]) == ["2020-01-13"]


def test_rsi_trigger_threshold_is_35_and_is_strict():
    assert RSI_TRIGGER == Decimal("35")
    weeks = [wk("2020-01-06", 1, 1, 1)]
    assert find_triggers(weeks, [Decimal("35")]) == []          # not armed
    assert find_triggers(weeks, [Decimal("34.99")]) == ["2020-01-06"]


def test_downtrend_anchor_ignores_weeks_after_asof():
    """The window is bounded at the episode's OWN trigger. Bounding it at the
    next episode's trigger leaks the following bull market into D: EP2's D
    would become the Dec-2017 top and EP4's the Nov-2021 top."""
    weeks = [wk("2019-04-01", 5350, 4067, 5250),
             wk("2019-06-24", 13970, 11000, 12000),
             wk("2021-11-08", 69000, 60000, 61000)]   # after asof — must not win
    d_price, d_week = downtrend_anchor(weeks, window_start="2019-04-01",
                                       asof="2020-03-09")
    assert d_price == Decimal("13970")
    assert d_week == "2019-06-24"


def test_downtrend_anchor_ignores_weeks_before_the_window_start():
    weeks = [wk("2017-12-11", 19798.68, 16000, 17000),   # prior ATH, out of window
             wk("2019-04-01", 5350, 4067, 5250),
             wk("2019-06-24", 13970, 11000, 12000)]
    assert downtrend_anchor(weeks, window_start="2019-04-01",
                            asof="2020-03-09") == (Decimal("13970"), "2019-06-24")


def test_freeze_el_is_the_running_low_at_the_bos_day():
    """EL* freezes at the BoS: later lows do not move it (SPEC 13.1)."""
    bars = [bar("2022-06-18", 19000, 19500, 17622, 18000),
            bar("2022-11-09", 18000, 18100, 15476, 15800),
            bar("2023-01-01", 16500, 16600, 14000, 16400)]   # after BoS
    assert freeze_el(bars, "2022-05-23", "2022-11-09") == Decimal("15476")
    assert freeze_el(bars, "2022-05-23", "2022-06-18") == Decimal("17622")


def test_prior_cycle_ath_excludes_the_trigger_week_itself():
    weeks = [wk("2022-05-16", 31000, 28000, 29000),
             wk("2022-05-23", 99999, 28000, 29000)]   # trigger week's own high
    assert prior_cycle_ath(weeks, "2022-05-23") == (Decimal("31000"), "2022-05-16")


def test_downtrend_anchor_bounds_are_both_week_inclusive():
    """The argmax sitting exactly ON a bound must still win. `asof` is the
    live case: EP1's D is its own trigger week, and an exclusive bound would
    move it back a step and flip §13.3's `monday(D) < trigger_week` guard
    from failing to passing, un-expiring EP1."""
    at_start = [wk("2019-04-01", 13970, 11000, 12000),   # argmax == window_start
                wk("2019-10-21", 10370, 8200, 9200)]
    assert downtrend_anchor(at_start, window_start="2019-04-01",
                            asof="2020-03-09") == (Decimal("13970"), "2019-04-01")

    at_asof = [wk("2019-04-01", 5350, 4067, 5250),
               wk("2020-03-09", 13970, 11000, 12000)]    # argmax == asof
    assert downtrend_anchor(at_asof, window_start="2019-04-01",
                            asof="2020-03-09") == (Decimal("13970"), "2020-03-09")


def test_downtrend_anchor_normalises_mid_week_bounds_to_their_week():
    """SPEC §13.3 names window_start as a BoS *date*. A mid-week BoS must not
    drop its own week from the window (nor a mid-week asof drop the trigger
    week), and Monday arguments must be unchanged by the normalisation."""
    weeks = [wk("2019-04-01", 13970, 11000, 12000),
             wk("2019-04-08", 9000, 8000, 8500),
             wk("2019-10-21", 10370, 8200, 9200)]
    # 2019-04-03 is the Wednesday of the 2019-04-01 week
    assert downtrend_anchor(weeks, window_start="2019-04-03",
                            asof="2019-10-21") == (Decimal("13970"), "2019-04-01")
    # 2019-04-05 is the Friday of that same week, used as the asof bound
    assert downtrend_anchor(weeks, window_start="2019-04-01",
                            asof="2019-04-05") == (Decimal("13970"), "2019-04-01")


# --- against the frozen reference series ----------------------------------
# `data.loaders` is test-only; `engine/` never imports it.

# SPEC §13.3's executed table (2026-07-25). window_start is the PREVIOUS
# episode's activation (its BoS week; the data start for EP1).
SPEC_EPISODES = [
    # trigger wk,   window_start,  D week,       D high,      BoS week,     EL*
    ("2011-11-21", "2011-08-15", "2011-11-21", "15.0", None, None),
    ("2014-09-22", "2011-11-21", "2013-11-25", "1163.0", "2015-01-26", "152.40"),
    ("2018-11-19", "2015-01-26", "2017-12-11", "19798.68", "2019-04-01", "3156.26"),
    ("2020-03-09", "2019-04-01", "2019-06-24", "13970.0", "2020-07-27", "3782.13"),
    ("2022-05-16", "2020-07-27", "2021-11-08", "69000.0", "2023-02-13", "15476.00"),
    ("2026-01-26", "2023-02-13", "2025-10-06", "126199.63", None, None),
]


@pytest.fixture(scope="module")
def real():
    from data.loaders import load_bars
    from engine.bars import to_weeks
    bars = load_bars()
    return bars, to_weeks(bars)


def test_find_triggers_reproduces_all_six_spec_triggers(real):
    """The module's real-world contract, not a fixture: the whole daily
    history through `to_weeks` and `wilder_rsi` must yield exactly SPEC
    §13.3's six triggers."""
    bars, weeks = real
    triggers = find_triggers(weeks, wilder_rsi([w.close for w in weeks]))
    assert triggers == [ep[0] for ep in SPEC_EPISODES]


def test_downtrend_anchor_reproduces_all_six_spec_D_values(real):
    _, weeks = real
    got = [downtrend_anchor(weeks, window_start=ws, asof=trig)
           for trig, ws, _, _, _, _ in SPEC_EPISODES]
    assert got == [(Decimal(d_high), d_week)
                   for _, _, d_week, d_high, _, _ in SPEC_EPISODES]


def test_freeze_el_reproduces_every_spec_el_star(real):
    """EL* is recorded by BoS *week*; assert at both ends of that week to show
    the day-within-week ambiguity does not move any of the four values."""
    from datetime import date, timedelta
    bars, _ = real
    for _, _, d_week, _, bos_week, el in SPEC_EPISODES:
        if bos_week is None:
            continue
        sunday = (date.fromisoformat(bos_week) + timedelta(days=6)).isoformat()
        assert freeze_el(bars, d_week, bos_week) == Decimal(el)
        assert freeze_el(bars, d_week, sunday) == Decimal(el)


def test_ep4_anchor_separation_holds_on_the_real_series(real):
    """Not a coincidence of the fixtures: on the frozen data EP4's exit anchor
    and its D are different weeks, and swapping them returns EP3's low."""
    bars, weeks = real
    assert prior_cycle_ath(weeks, "2020-03-09") == (Decimal("19798.68"), "2017-12-11")
    assert downtrend_anchor(weeks, window_start="2019-04-01",
                            asof="2020-03-09") == (Decimal("13970.0"), "2019-06-24")
    assert running_low(bars, "2019-06-24", "2020-07-27") == Decimal("3782.13")
    assert running_low(bars, "2017-12-11", "2020-07-27") == Decimal("3156.26")


def test_ep6_running_low_matches_prd_section_8(real):
    """The live episode: no BoS yet, so the low is still running, not frozen."""
    bars, _ = real
    assert running_low(bars, "2025-10-06", "2026-07-20") == Decimal("57800.19")


def test_empty_scopes_raise_rather_than_return_a_wrong_default():
    with pytest.raises(ValueError):
        prior_cycle_ath([wk("2022-05-23", 30000, 28000, 29000)], "2022-05-23")
    with pytest.raises(ValueError):
        running_low([bar("2022-06-18", 19000, 19500, 17622, 18000)],
                    "2023-01-01", "2023-02-01")
    with pytest.raises(ValueError):
        downtrend_anchor([wk("2022-05-23", 30000, 28000, 29000)],
                         window_start="2023-01-02", asof="2023-02-06")
