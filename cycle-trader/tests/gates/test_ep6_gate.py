"""G5 — EP6 live state, as of the frozen 2026-07-22 data (SPEC §10).

Two of §10 G5's four dates are stated in conventions that are not this codebase's
(§13.10), and pasting either fails on CORRECT code:

  "week of 2026-05-10"   is a SUNDAY label -> ISO Monday 2026-05-04
  "confirmed 2026-06-07" is a SUNDAY label AND the wrong resolution -> the rule
                         (§4.3/§13.4: first daily low strictly below L0) prints
                         2026-06-05, the Friday inside that week

Both are asserted as the rule's output, with the prose value carried alongside so
the mapping is visible rather than folklore.

Unlike G1-G3 this episode is UNFINISHED: no BoS, no fills, nothing frozen. So the
gate's job is as much about what must NOT have happened as what has, and the
negative assertions (no BoS, no tranche fill, the June bounce not operative) are
the load-bearing half.
"""
from decimal import Decimal

from engine.bars import monday_of
from engine.fills import buy_limit_fill
from engine.lines import lines_for
from engine.structure import find_lh_candidates, operative_lh, find_bos

ASOF = "2026-07-22"


def pct(a, b):
    return abs(a - b) / b * Decimal(100)


def ep6(episode_scope, weeks, bars):
    """EP6's engine-derived (trigger, D) plus its candidate list.

    D is asserted here for the same reason G1-G3 assert theirs: it is the
    algorithm's most consequential hidden input, and it is CHAINED — EP6's D
    depends on EP5's BoS, so a break two episodes upstream would otherwise
    surface as a confusing failure about a lower high.
    """
    trigger = monday_of("2026-02-01")           # -> 2026-01-26
    assert trigger in episode_scope["triggers"]
    d_week, bos, broken = episode_scope["scopes"][trigger]
    assert d_week == "2025-10-06", "EP6's D is the 126,199.63 ATH week"
    assert (bos, broken) == (None, None), "EP6 has not activated"
    return trigger, d_week, find_lh_candidates(weeks, bars, scope_start=d_week,
                                               trigger_monday=trigger)


def test_g5_operative_lh_is_82850_not_the_june_bounce(bars, weeks, episode_scope):
    """§10 G5: operative LH 82,850 (+38.1% off fresh 60,000)."""
    trigger, d_week, cands = ep6(episode_scope, weeks, bars)
    lh = operative_lh(cands, asof=ASOF)
    assert lh is not None
    assert lh.price == Decimal("82850")
    assert lh.week_monday == "2026-05-04"           # §10's "week of 2026-05-10"
    assert monday_of("2026-05-10") == "2026-05-04"  # ...the §13.10 mapping itself
    assert lh.origin_low == Decimal("60000")
    assert lh.origin_week == "2026-02-02"
    assert pct(lh.rally_pct, Decimal("38.1")) < Decimal("1")
    assert lh.confirmed_at == "2026-06-05"          # §10's "confirmed 2026-06-07"
    assert monday_of("2026-06-07") == monday_of(lh.confirmed_at)  # same week
    # ALIVE. `invalidated_at is None` is what makes "operative as of 2026-07-22"
    # a live fact rather than an artefact of the asof cutoff: a candidate whose
    # break already printed would still be returned by `operative_lh` on its
    # break day (§4.5 / operative_lh's `>=`), so the two are different claims.
    assert lh.invalidated_at is None

    # NO LOOKAHEAD (§4.3, §13.4, CLAUDE.md rule 5): unusable before confirmation.
    # EVERY candidate from wk 2026-02-09 through wk 2026-05-04 shares the same
    # confirmation day, because they all rally off the same fresh low L0 = 60,000
    # and 2026-06-05 is the first daily low under it. So on 2026-06-04 the whole
    # 2026 structure is still unusable and the operative LH is the LAST PRE-CRASH
    # one — 97,924.49 @ wk 2026-01-12, confirmed back on 2026-01-31.
    #
    # That flip is the assertion worth having: the operative LH steps DOWN from
    # 97,924.49 to 82,850 on the confirmation day. An engine that ranked
    # candidates by price rather than recency would stay on 97,924.49 (which is
    # never invalidated on this data) and would place its BoS order 18% too high.
    assert {c.confirmed_at for c in cands if "2026-02-09" <= c.week_monday
            <= "2026-05-04"} == {"2026-06-05"}
    assert operative_lh(cands, asof="2026-06-04").price == Decimal("97924.49")
    assert operative_lh(cands, asof="2026-06-04").week_monday == "2026-01-12"
    assert operative_lh(cands, asof="2026-06-05").price == Decimal("82850")

    # ...and it is the LATEST candidate that wins, not the highest-priced: the
    # 97,924.49 structure is still alive at the cutoff and is simply older.
    assert max(cands, key=lambda c: c.week_monday).price == lh.price
    assert max(c.price for c in cands) == Decimal("97924.49")
    assert next(c for c in cands
                if c.week_monday == "2026-01-12").invalidated_at is None


def test_g5_june_bounce_fails_r_e_and_is_not_a_candidate(bars, weeks,
                                                         episode_scope):
    """§10 G5: "The June bounce high 67,292 (+13.8%) fails R_e=15 and must NOT be
    operative."

    Excluded by WEEK, not by a price band (see test_entry_gates' module docstring
    for why), and its rally is read off a loosened `r_e=10` run: at R_e=15 the
    week is not a candidate at all, so no engine-computed `rally_pct` for it
    exists in `cands` and hand arithmetic would silently pick the wrong L0.

    This is the exclusion that matters most in EP6, because the June bounce is the
    MOST RECENT structure — `operative_lh` takes the latest candidate, so admitting
    it does not add a row, it *replaces* 82,850 and moves the BoS trigger 19% down
    to 67,292. That is a live order-placement error, not a reporting one.
    """
    trigger, d_week, cands = ep6(episode_scope, weeks, bars)
    june = next(w for w in weeks if w.monday == "2026-06-15")
    assert june.high == Decimal("67292.15")
    assert pct(june.high, Decimal("67292")) < Decimal("0.01")
    assert all(c.week_monday != "2026-06-15" for c in cands)

    loosened = find_lh_candidates(weeks, bars, scope_start=d_week,
                                  trigger_monday=trigger, r_e=Decimal("10"))
    bounce = next(c for c in loosened if c.week_monday == "2026-06-15")
    assert bounce.price == Decimal("67292.15")
    assert bounce.origin_low == Decimal("59130.91")
    assert pct(bounce.rally_pct, Decimal("13.8")) < Decimal("1")
    assert bounce.rally_pct < Decimal("15")           # the stated reason
    # And the consequence, made concrete: at R_e=10 it IS the operative LH.
    assert operative_lh(loosened, asof=ASOF).price == Decimal("67292.15")


def test_g5_bos_has_not_fired(bars, weeks, episode_scope):
    """§10 G5: "BoS trigger = intraweek trade > 82,850". It has not printed.

    Checked from the LH's own confirmation date rather than from §10's Sunday
    label — starting at 2026-06-07 would skip 06-05 and 06-06 unexamined, which
    is a weaker claim than the one G5 makes.
    """
    trigger, _d_week, cands = ep6(episode_scope, weeks, bars)
    lh = operative_lh(cands, asof=ASOF)
    upto = [b for b in bars if b.date <= ASOF]
    assert find_bos(upto, Decimal("82850"), after=lh.confirmed_at) is None
    # Stronger than §10's own window: nothing has traded above 82,850 since the
    # LH's own week either, so the candidate is un-invalidated as well as
    # unbroken. (`trigger` is deliberately NOT the start here — the episode
    # OPENS at 90,600 on 2026-01-28, well above 82,850, because the LH forms
    # three months into the episode. A scan from the trigger measures the
    # pre-crash rally, not the break.)
    assert max(b.high for b in upto if b.date >= trigger) == Decimal("90600")
    since_lh = [b for b in upto if b.date >= lh.week_monday]
    assert max(b.high for b in since_lh) == Decimal("82850")   # the LH's own print
    assert find_bos(since_lh, Decimal("82850"), after=lh.week_monday) is None
    # ...and the margin, so "no BoS" is a measured distance, not a bare None.
    assert pct(upto[-1].close, Decimal("82850")) > Decimal("15")


def test_g5_accumulation_lines_and_no_fills(bars, weeks, onchain, episode_scope):
    """§10 G5: "Lines: T1 ≈52.9k / T2 ≈45.9k / T3 ≈38.9k; no fills."

    The quoted line values are a SNAPSHOT — §3's lines move daily — so the
    no-fill claim is checked walk-forward against each day's own line, not
    against the snapshot. The distinction is not cosmetic: T1 was 55,215.58 on
    2026-02-06 and is 52,848.37 by 2026-07-19, and it is the earlier, higher
    value that the 60,000 episode low had to clear.
    """
    trigger, _d_week, _cands = ep6(episode_scope, weeks, bars)
    t1, t2, t3 = lines_for(onchain["2026-07-19"])
    assert pct(t1, Decimal("52900")) < Decimal("1")
    assert pct(t2, Decimal("45900")) < Decimal("1")
    assert pct(t3, Decimal("38900")) < Decimal("1")
    assert t3 < t2 < t1                                   # §3's ordering

    # WALK-FORWARD no-fill check. Lines are live from the trigger through the BoS
    # day inclusive (§13.6); there is no BoS, so the window runs to the end of the
    # on-chain series. A tranche fills when the daily low <= that day's line, so
    # the claim to verify is that the worst daily margin over T1 stayed positive.
    priced = [b for b in bars if trigger <= b.date <= ASOF and b.date in onchain]
    assert priced, "no on-chain-covered bars in the EP6 window"
    # Through the ENGINE's buy-limit primitive (§13.2), not a hand-rolled
    # comparison: T1 is the shallowest of the three lines, so `buy_limit_fill`
    # returning None on every day is the whole "no fills" claim for all of T1-T3.
    assert all(buy_limit_fill(b, lines_for(onchain[b.date])[0]) is None
               for b in priced)
    worst = min(((b.low - lines_for(onchain[b.date])[0])
                 / lines_for(onchain[b.date])[0], b.date)
                for b in priced)
    assert worst[0] > 0, f"T1 would have filled on {worst[1]}"
    # Pinned tightly so "no fills" is a measured 8.7% clearance rather than a
    # boolean that a data refresh could flip silently. The tightest day is the
    # 60,000 episode low itself.
    assert worst[1] == "2026-02-06"
    assert Decimal("0.086") < worst[0] < Decimal("0.087")

    # The on-chain series ends a day before the bar series, so the last bar is
    # NOT covered above. Asserted rather than left implicit: a silent gap here
    # would let an untested day hide inside a passing walk-forward loop.
    assert max(onchain) == "2026-07-19"
    assert bars[-1].date == "2026-07-20"
    assert min(b.low for b in bars if b.date > max(onchain)) > t1
