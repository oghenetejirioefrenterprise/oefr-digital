"""SPEC §10 verification gates G1-G3. These are the owner's own chart reads.
An engine that fails any of them is wrong regardless of how reasonable its
reading of the prose is.

**Exclusions are asserted by WEEK, not by a price band.** The gates name three
highs that must NOT become candidates (G2's early-March ~9.2k, G3's Sept 22,799
and Oct 20,475) plus one that must fail `R_e` (G3's Nov FTX bounce). Each of
those is a specific week, and a `|price - X| > tol` sweep over the whole
candidate list is not the same claim: it also fires on any *unrelated* week that
happens to print a near-identical high. That is not hypothetical here — see
`test_g2_2020_entry`'s note on wk 2020-01-13 (high 9,198.98, i.e. 0.011% from
G2's "~9.2k"), a fully valid candidate off the fresh 6,435 low that a 2% band
rejects. Naming the week asserts strictly more: the right object is absent, and
absent *for SPEC's stated reason*.
"""
from decimal import Decimal
from engine.structure import find_lh_candidates, operative_lh, find_bos
from engine.lifecycle import freeze_el, running_low
from engine.bars import monday_of


def pct(a, b):
    return abs(a - b) / b * Decimal(100)


def scope_for_episode(episode_scope, sunday_label: str, expected_d: str):
    """Map a reference episode label (Sunday-anchored) to the engine-derived
    (trigger Monday, D). Asserts the engine actually found that trigger, and
    that D is SPEC §13.3's verified anchor, rather than trusting a pasted
    constant.

    D is checked here because it is this algorithm's most consequential hidden
    input: it sets the scan scope, the freshness window and the trigger guard,
    and a wrong D still yields a plausible-looking LH (feeding the prior-ATH
    week instead of D gives EP4 an LH off 3,156.26 and G2 fails). D is also
    chained — EP4's D depends on EP3's BoS — so an unasserted D lets a break
    two episodes upstream surface as a confusing failure here."""
    from engine.bars import monday_of
    expected_monday = monday_of(sunday_label)
    assert expected_monday in episode_scope["triggers"], (
        f"engine did not detect a trigger at {expected_monday} "
        f"(from reference label {sunday_label}); found {episode_scope['triggers']}")
    d_week, _bos, _broken = episode_scope["scopes"][expected_monday]
    assert d_week == expected_d, (
        f"D for trigger {expected_monday} is {d_week}, expected {expected_d} "
        "(SPEC §13.3 verified table). If this episode's D is wrong the bug may "
        "be in the PREVIOUS episode's BoS — the scope window chains.")
    return expected_monday, d_week


def walk_forward_bos(episode_scope, trigger: str) -> str:
    """The BoS the engine finds walking forward, with no LH handed to it.

    The per-gate `find_bos(bars, lh.price, ...)` calls below test a different,
    weaker thing: "given this LH, when is it broken?". They cannot catch an
    engine that would never have had that LH operative on the break day. This
    returns `first_bos`'s answer — derived only from the candidate list — so
    each gate can assert the two agree."""
    return episode_scope["scopes"][trigger][1]


def broken_lh(episode_scope, trigger: str):
    """The price of the candidate `first_bos` actually broke.

    Asserting only the BoS *date* leaves the identity of the broken structure
    untested — `return b.date, candidates[0]` yields every correct date off the
    wrong LH — and that LH anchors the §5 ladder leg and the §6.1 extension."""
    return episode_scope["scopes"][trigger][2]


def test_episode_chain_matches_spec_13_3(bars, episode_scope):
    """SPEC §13.3's executed table: the six triggers, each episode's D, and each
    activation — the shared precondition of G1, G2 and G3.

    `scope_for_episode` only asserts that a given trigger EXISTS in the list. It
    cannot see a spurious seventh episode, and a spurious episode is not a
    harmless extra row: `episode_scope` chains `window_start` through the
    activations, so one bogus entry shifts every later episode's D and the gates
    fail somewhere far from the cause. Asserting the whole chain once makes that
    break report itself here, in the units SPEC states it in.

    Note the direction of the check on EP1 and EP6: their activation is `None`.
    EP1 must EXPIRE (§13.3's trigger guard — its D is its own trigger week, so
    `monday(D) < trigger_week` fails and it never produces a candidate), and EP6
    is live with no BoS yet as of the frozen data. An engine that activates
    either one is wrong, and only an explicit `None` catches it — a test that
    merely looked up the episodes it needed would pass straight over both."""
    assert episode_scope["triggers"] == [
        "2011-11-21",   # EP1 — expires, see below
        "2014-09-22",   # EP2 — G1
        "2018-11-19",   # EP3
        "2020-03-09",   # EP4 — G2
        "2022-05-16",   # EP5 — G3
        "2026-01-26",   # EP6 — live
    ]
    # trigger -> (D's Monday, activation day or None, price of the LH broken).
    # SPEC §13.3 states BoS at WEEK resolution; the day is the engine's output
    # and is checked as such. The third slot pins WHICH structure was broken —
    # EP3's 4,450.38 is asserted nowhere else in the suite.
    assert episode_scope["scopes"] == {
        "2011-11-21": ("2011-11-21", None, None),                    # guard
        "2014-09-22": ("2013-11-25", "2015-01-26", Decimal("305.00")),
        "2018-11-19": ("2017-12-11", "2019-04-02", Decimal("4450.38")),
        "2020-03-09": ("2019-06-24", "2020-07-27", Decimal("10500.00")),
        "2022-05-16": ("2021-11-08", "2023-02-16", Decimal("25211.32")),
        "2026-01-26": ("2025-10-06", None, None),                    # live
    }
    # EP4's D is the June-2019 13,970 week, NOT the Dec-2017 19,798.68 ATH —
    # SPEC §13.3's proof that structure and exits use different anchors. It is
    # asserted as an inequality against EP3's D so the point survives a data
    # refresh: if these two ever coincide, the distinction has been lost.
    assert episode_scope["scopes"]["2020-03-09"][0] != \
        episode_scope["scopes"]["2018-11-19"][0]

    # EL* — SPEC §13.1/§13.3, the running low frozen at the BoS. **This is the
    # stop level.** Every other number in this gate is a signal that can be
    # re-derived tomorrow; EL* is the one the position is risked against, so a
    # silent drift here is the failure mode that costs money rather than
    # accuracy. §13.3's executed table carries all four and `freeze_el`
    # reproduces them exactly. Scope is D's Monday, NOT the prior-ATH week.
    data_end = bars[-1].date
    for trigger, expected in (("2014-09-22", Decimal("152.40")),
                              ("2018-11-19", Decimal("3156.26")),
                              ("2020-03-09", Decimal("3782.13")),
                              ("2022-05-16", Decimal("15476.00"))):
        d_week, bos, _broken = episode_scope["scopes"][trigger]
        assert freeze_el(bars, d_week, bos) == expected
        # EL* RATCHETS DOWN before the BoS (§13.1: "a running anchor, not a
        # stop level" — a new low pre-BoS updates the anchor and is not a stop
        # event). Observable and strict on every episode, so it pins EL* as a
        # running minimum over the scope rather than any fixed level.
        assert running_low(bars, d_week, trigger) > expected

        # ...and it FREEZES at the BoS. **This gate cannot test that, and the
        # assertion below records why rather than pretending otherwise.**
        # min() over a longer window is monotonically non-increasing, so the
        # freeze is only observable if a new low prints AFTER the BoS — and on
        # the frozen 2011->2026 series that never happens: for all four
        # activated episodes the running low to the END OF DATA still equals
        # EL*. Consequently a `freeze_el` that ignored `bos_date` entirely and
        # ran to today would return the identical four numbers, so no
        # value-based assertion here can distinguish frozen from running.
        # The freeze is pinned by the synthetic fixture in
        # tests/test_lifecycle.py, which is the only place it is reachable.
        #
        # Asserted rather than merely commented so the blind spot is
        # self-invalidating: if a data refresh ever prints a post-BoS low, this
        # fails and whoever sees it gets a real freeze test out of the box.
        assert running_low(bars, d_week, data_end) == expected


def test_r_e_15_is_the_upper_edge_of_the_passing_interval(bars, weeks,
                                                          episode_scope):
    """`R_e = 15` bounds an INTERVAL; it is not uniquely determined by evidence.

    CLAUDE.md rule 2 calls 15 "the unique gate-passing value, not a tunable",
    and an earlier version of this test was named for that claim. **Measured,
    the claim is false**, so the name and the docstring now state what the
    evidence actually shows. Swept by editing `R_E_DEFAULT` and re-running:

      historical gates alone   PASS over R_e in (12.0422, 19.60784]
      full suite               PASS over R_e in [13.78809, 15.00]

    Neither interval pins 15. All three gates return the identical operative
    LH at 14 and at 15, so no chart read in §10 can tell them apart.

    Both full-suite edges come from SYNTHETIC fixtures in
    tests/test_structure.py, not from history: the upper edge is
    `test_degree_is_inclusive_at_exactly_r_e` (a constructed exactly-15%
    rally), the lower is `test_rally_below_15_percent_is_rejected` (G5's June
    bounce at +13.78809%). So "the suite fails at 15.01" is a fact about a
    hand-built fixture, and the honest summary is that 15 sits at the top of a
    wide passing band whose edges the owner chose rather than the data forcing.

    What history DOES force is the two-sided bound below — SPEC §9 rejects R10
    and R20, and both are reproduced here. That is the real claim §9 makes.

    This is also where the Nov-2022 FTX bounce's rally is asserted. At R_e=15
    that week is not a candidate, so the engine computes no `rally_pct` for it;
    reading it off the r_e=10 run is the only way to assert the ENGINE's number
    rather than re-deriving one by hand. The distinction is not academic: hand
    arithmetic off EL* (15,476) gives +11.07%, while the engine's L0 is wk
    2022-11-07's low 15,588 and its rally is +10.28%. Both fall inside any
    loose (10, 15) band, so a hand-rolled check passes while observing nothing.
    """
    ep5_trigger, ep5_d = "2022-05-16", "2021-11-08"
    ep2_trigger, ep2_d = "2014-09-22", "2013-11-25"
    assert episode_scope["scopes"][ep5_trigger][0] == ep5_d
    assert episode_scope["scopes"][ep2_trigger][0] == ep2_d

    # Lowering R_e admits what §10 G3 says must be excluded: the FTX bounce.
    loosened = find_lh_candidates(weeks, bars, scope_start=ep5_d,
                                  trigger_monday=ep5_trigger, r_e=Decimal("10"))
    ftx = next(c for c in loosened if c.week_monday == "2022-11-14")
    assert ftx.origin_week == "2022-11-07"
    assert ftx.origin_low == Decimal("15588.00")
    assert Decimal("10") < ftx.rally_pct < Decimal("15")      # engine's number
    assert pct(ftx.rally_pct, Decimal("10.28")) < Decimal("1")

    # Raising R_e destroys G1: 305.00 stops being generated and the operative
    # LH reverts to the previous structure — §4's failure signature exactly.
    at_15 = find_lh_candidates(weeks, bars, scope_start=ep2_d,
                               trigger_monday=ep2_trigger, r_e=Decimal("15"))
    at_20 = find_lh_candidates(weeks, bars, scope_start=ep2_d,
                               trigger_monday=ep2_trigger, r_e=Decimal("20"))
    assert any(c.price == Decimal("305.00") for c in at_15)
    assert all(c.price != Decimal("305.00") for c in at_20)
    assert operative_lh(at_20, asof="2015-01-20").price == Decimal("453.92")
    assert operative_lh(at_20, asof="2015-01-20").week_monday == "2014-11-10"

    # --- the measured edges of the passing interval, pinned directly ---
    # UPPER: set by G1's own LH. Its rally is 19.60784...%, so R_e may rise all
    # the way to that value before 305.00 stops being generated. Bisected.
    lh305 = next(c for c in at_15 if c.price == Decimal("305.00"))
    assert Decimal("19.6078") < lh305.rally_pct < Decimal("19.6079")
    at_edge = find_lh_candidates(weeks, bars, scope_start=ep2_d,
                                 trigger_monday=ep2_trigger,
                                 r_e=Decimal("19.60784"))
    past_edge = find_lh_candidates(weeks, bars, scope_start=ep2_d,
                                   trigger_monday=ep2_trigger,
                                   r_e=Decimal("19.6079"))
    assert any(c.price == Decimal("305.00") for c in at_edge)
    assert all(c.price != Decimal("305.00") for c in past_edge)

    # LOWER: set by EP3's wk 2018-12-10 (high 3,610.00 off L0 3,222.00,
    # +12.0422%). It is the highest-rallying week the gates require to stay
    # OUT; admitting it perturbs EP3's structure and the chain carries that
    # into EP4, which is how a too-low R_e breaks G2 rather than G3.
    ep3_d, ep3_trigger = "2017-12-11", "2018-11-19"
    assert episode_scope["scopes"][ep3_trigger][0] == ep3_d
    admits = find_lh_candidates(weeks, bars, scope_start=ep3_d,
                                trigger_monday=ep3_trigger,
                                r_e=Decimal("12.0422"))
    excludes = find_lh_candidates(weeks, bars, scope_start=ep3_d,
                                  trigger_monday=ep3_trigger,
                                  r_e=Decimal("12.0423"))
    edge_wk = next(c for c in admits if c.week_monday == "2018-12-10")
    assert edge_wk.origin_low == Decimal("3222.00")
    assert Decimal("12.0422") < edge_wk.rally_pct < Decimal("12.0423")
    assert all(c.week_monday != "2018-12-10" for c in excludes)

    # --- and the insensitivity itself: 14 and 15 are indistinguishable ---
    # This is the assertion that makes the "unique value" claim falsifiable.
    # If a future gate ever DOES separate them, this fails and the docstring
    # above must be rewritten — which is the outcome we want.
    for d_week, trigger, asof in (("2013-11-25", "2014-09-22", "2015-01-20"),
                                  ("2019-06-24", "2020-03-09", "2020-07-01"),
                                  ("2021-11-08", "2022-05-16", "2023-02-01")):
        at14 = find_lh_candidates(weeks, bars, scope_start=d_week,
                                  trigger_monday=trigger, r_e=Decimal("14"))
        at15 = find_lh_candidates(weeks, bars, scope_start=d_week,
                                  trigger_monday=trigger, r_e=Decimal("15"))
        assert operative_lh(at14, asof=asof).price == \
            operative_lh(at15, asof=asof).price


def test_g1_2015_entry(bars, weeks, episode_scope):
    """LH 305.00 (week of 2015-01-05, +19.6% off fresh 255.00, confirmed by
    152.40 on 2015-01-14); BoS week of 2015-01-26 at 309.90."""
    trigger, scope_start = scope_for_episode(episode_scope, "2014-09-28",
                                             expected_d="2013-11-25")
    cands = find_lh_candidates(weeks, bars, scope_start=scope_start,
                               trigger_monday=trigger)
    lh = operative_lh(cands, asof="2015-01-20")
    assert lh is not None
    assert lh.price == Decimal("305.00")
    assert lh.week_monday == "2015-01-05"
    assert lh.origin_low == Decimal("255.00")
    # SPEC §13.3 v1.2.2's proof that the rally-origin window INCLUDES the anchor
    # week j: wk 2014-12-29 is simultaneously the anchor (high 321.00 > 305.00)
    # and the origin (low 255.00). Asserting both fields pins that identity, so
    # an `in_scope[j+1:i]` regression fails here on the field that explains it
    # rather than only downstream on a changed LH price.
    assert lh.anchor_week == "2014-12-29"
    assert lh.origin_week == "2014-12-29"
    # G1's prose says "confirmed by 152.40 on 2015-01-14" — but 152.40 is the
    # EPISODE LOW, and 2015-01-14 is the day it printed. §4.3/§13.4's rule is
    # the first daily low STRICTLY BELOW L0=255, which is 2015-01-13 (216.00).
    # Verified against the frozen data. Asserting the prose date fails correct code.
    assert lh.confirmed_at == "2015-01-13"
    assert pct(lh.rally_pct, Decimal("19.6")) < Decimal("1")

    # NO LOOKAHEAD (CLAUDE.md rule 5, SPEC §4.3): the candidate is unusable
    # before its confirmation date. One day earlier the operative LH is still
    # the PREVIOUS structure, 453.92 @ wk 2014-11-10 (confirmed 2015-01-04);
    # it flips to 305.00 on 2015-01-13, the day the low first breaks L0 = 255.
    #
    # This is the gate's only guard on that rule. `walk_forward_bos` below does
    # NOT catch it: deleting `b.date > op.confirmed_at` from `first_bos` leaves
    # all four gates green, because G1's break (2015-01-26) postdates its
    # confirmation anyway and the two BoS routines then agree on a wrong rule.
    # Asserting the flip is what makes premature usability observable.
    assert operative_lh(cands, asof="2015-01-12").price == Decimal("453.92")
    assert operative_lh(cands, asof="2015-01-12").week_monday == "2014-11-10"
    assert operative_lh(cands, asof="2015-01-13").price == Decimal("305.00")

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2015-01-26"
    assert bos == walk_forward_bos(episode_scope, trigger)
    # ...and it broke THIS structure, not merely something on this day.
    assert broken_lh(episode_scope, trigger) == lh.price
    # §10: "BoS = week of 2015-01-26 (weekly high 309.90 > 305)".
    bos_bar = next(b for b in bars if b.date == bos)
    assert bos_bar.high == Decimal("309.90")


def test_g2_2020_entry(bars, weeks, episode_scope):
    """LH 10,500 (week of 2020-02-16, +63% off Dec-2019 6,435). The early-March
    ~9.2k high is EXCLUDED: its origin ~8.5k was not a fresh low.
    BoS = week of 2020-08-02. Note the operative LH PREDATES this trigger
    (SPEC §4), which is legal and is what the anchor guard exists to bound."""
    trigger, scope_start = scope_for_episode(episode_scope, "2020-03-15",
                                             expected_d="2019-06-24")
    cands = find_lh_candidates(weeks, bars, scope_start=scope_start,
                               trigger_monday=trigger)
    lh = operative_lh(cands, asof="2020-07-01")
    assert lh is not None
    assert pct(lh.price, Decimal("10500")) < Decimal("0.5")
    assert lh.week_monday == "2020-02-10"
    assert pct(lh.origin_low, Decimal("6435")) < Decimal("1")
    assert pct(lh.rally_pct, Decimal("63")) < Decimal("1")
    # §10: "confirmed by the COVID crash" — the rule's output is the first daily
    # low strictly below L0 = 6,435, which is 2020-03-12 (the crash day itself).
    assert lh.confirmed_at == "2020-03-12"

    # The excluded high is a WEEK, not a price. SPEC's "early-March ~9.2k" is
    # wk 2020-03-02 (high 9,188.00); its would-be rally origin is wk 2020-02-24's
    # low 8,411.00 — SPEC's "origin ~8.5k".
    #
    # HONEST SCOPE OF THIS EXCLUSION: it is OVER-DETERMINED on the frozen data.
    # Wk 2020-03-02 fails freshness (L0 = 8,411 >= the 6,435 already in scope
    # from D) AND degree (rally +9.24% < R_e = 15). Proven by mutation: deleting
    # EITHER rule leaves this test green. So this block does NOT pin freshness,
    # and an earlier version of this comment claiming it "fails loudly if some
    # other rule starts doing the excluding" was wrong.
    # **Freshness is pinned by G3's wk 2022-09-12 (+23.17%, clears R_e), not
    # here.** Kept regardless: it is still strictly stronger than the price band
    # it replaced, which failed on correct code (see below).
    march = next(w for w in weeks if w.monday == "2020-03-02")
    assert pct(march.high, Decimal("9200")) < Decimal("1")
    assert all(c.week_monday != "2020-03-02" for c in cands)
    prior_origin = next(w for w in weeks if w.monday == "2020-02-24")
    assert pct(prior_origin.low, Decimal("8500")) < Decimal("2")
    scope_lows = [w.low for w in weeks if scope_start <= w.monday < "2020-02-24"]
    assert min(scope_lows) < prior_origin.low       # 6,435 < 8,411 -> not fresh
    # NOT asserted as `all(pct(c.price, 9200) > 2)`: wk 2020-01-13's high is
    # 9,198.98 — 0.011% from "~9.2k" — and it is a CORRECT candidate (origin the
    # fresh 6,435, rally +42.95%, never operative because 2020-02-10 is later).
    # A price band rejects the engine for producing it. Verified against the
    # frozen data: that week is present and must stay present.
    assert any(c.week_monday == "2020-01-13" for c in cands)

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2020-07-27"
    assert bos == walk_forward_bos(episode_scope, trigger)
    assert broken_lh(episode_scope, trigger) == lh.price
    # §10: "first trade > 10,500".
    bos_bar = next(b for b in bars if b.date == bos)
    assert bos_bar.high > Decimal("10500")


def test_g3_2022_entry(bars, weeks, episode_scope):
    """LH 25,211.32 (week of 2022-08-15, +43% off 17,622). Sept 22,799 and Oct
    20,475 EXCLUDED (origins never undercut June's 17,622); the Nov FTX bounce
    is ~+11% and fails R_e=15. BoS = week of 2023-02-13."""
    trigger, scope_start = scope_for_episode(episode_scope, "2022-05-22",
                                             expected_d="2021-11-08")
    cands = find_lh_candidates(weeks, bars, scope_start=scope_start,
                               trigger_monday=trigger)
    lh = operative_lh(cands, asof="2023-02-01")
    assert lh is not None
    assert pct(lh.price, Decimal("25211.32")) < Decimal("0.5")
    assert pct(lh.origin_low, Decimal("17622")) < Decimal("1")
    assert lh.week_monday == "2022-08-15"
    assert lh.origin_week == "2022-06-13"
    assert pct(lh.rally_pct, Decimal("43")) < Decimal("1")
    # §10: "confirmed by the Nov crash" — first daily low below L0 = 17,622.
    assert lh.confirmed_at == "2022-11-08"

    # Excluded by week, with the stated price attached so a data change that
    # moves the high cannot let the assertion pass vacuously, and each paired
    # with the origin the ENGINE actually computes for it — naming a plausible
    # nearby week instead makes the "stated reason" assertion vacuous, which is
    # the whole failure mode that week-identification exists to prevent.
    #
    # These two are NOT equally load-bearing, and the difference matters:
    #
    #   wk 2022-09-12 (22,799) — origin wk 2022-09-05, L0 = 18,510.77,
    #       rally +23.17%. Clears R_e comfortably, so FRESHNESS ALONE excludes
    #       it. This is the one assertion in the suite that isolates the
    #       freshness rule on real data, and it is what kills the freshness
    #       mutant. SPEC §10 G3's stated reason, exactly.
    #   wk 2022-10-03 (20,475) — origin wk 2022-09-19, L0 = 18,125.98,
    #       rally +12.96%. OVER-DETERMINED: it fails freshness AND degree, so it
    #       proves nothing on its own and is kept only because §10 names it.
    for week_monday, high, origin_monday, origin_low in (
            ("2022-09-12", Decimal("22799"), "2022-09-05", Decimal("18510.77")),
            ("2022-10-03", Decimal("20475"), "2022-09-19", Decimal("18125.98"))):
        week = next(w for w in weeks if w.monday == week_monday)
        assert week.high == high
        assert all(c.week_monday != week_monday for c in cands)
        origin = next(w for w in weeks if w.monday == origin_monday)
        assert origin.low == origin_low
        # SPEC's stated reason: the origin never undercut June's 17,622.
        assert origin.low > Decimal("17622")
    # The load-bearing half, spelled out: 22,799's rally clears R_e, so its
    # exclusion cannot be attributed to the degree test.
    sept = next(w for w in weeks if w.monday == "2022-09-12")
    sept_origin = next(w for w in weeks if w.monday == "2022-09-05")
    assert (sept.high - sept_origin.low) / sept_origin.low * Decimal(100) \
        > Decimal("15")

    # The Nov FTX bounce is excluded by a DIFFERENT rule — degree, not freshness.
    # Its rally is asserted in test_r_e_15_is_the_unique_gate_passing_value,
    # which reads the ENGINE's rally_pct off the r_e=10 candidate rather than
    # recomputing it here: at R_e=15 this week is not a candidate at all, so no
    # engine-computed number for it exists in `cands` to assert against, and
    # hand-arithmetic off EL* would silently use the wrong L0 (see that test).
    assert all(c.week_monday != "2022-11-14" for c in cands)

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2023-02-13"
    assert bos == walk_forward_bos(episode_scope, trigger)
    assert broken_lh(episode_scope, trigger) == lh.price
    # §10: "weekly high ~25,250".
    bos_bar = next(b for b in bars if b.date == bos)
    assert pct(bos_bar.high, Decimal("25250")) < Decimal("0.5")
