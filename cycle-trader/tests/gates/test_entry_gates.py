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
    d_week, _bos = episode_scope["scopes"][expected_monday]
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


def test_episode_chain_matches_spec_13_3(episode_scope):
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
    # trigger -> (D's Monday, activation day or None). SPEC §13.3 states BoS at
    # WEEK resolution; the day is the engine's output and is checked as such.
    assert episode_scope["scopes"] == {
        "2011-11-21": ("2011-11-21", None),          # D == trigger week -> guard
        "2014-09-22": ("2013-11-25", "2015-01-26"),  # BoS wk 2015-01-26
        "2018-11-19": ("2017-12-11", "2019-04-02"),  # BoS wk 2019-04-01
        "2020-03-09": ("2019-06-24", "2020-07-27"),  # BoS wk 2020-07-27
        "2022-05-16": ("2021-11-08", "2023-02-16"),  # BoS wk 2023-02-13
        "2026-01-26": ("2025-10-06", None),          # live, no BoS yet
    }
    # EP4's D is the June-2019 13,970 week, NOT the Dec-2017 19,798.68 ATH —
    # SPEC §13.3's proof that structure and exits use different anchors. It is
    # asserted as an inequality against EP3's D so the point survives a data
    # refresh: if these two ever coincide, the distinction has been lost.
    assert episode_scope["scopes"]["2020-03-09"][0] != \
        episode_scope["scopes"]["2018-11-19"][0]


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

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2015-01-26"
    assert bos == walk_forward_bos(episode_scope, trigger)
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
    # low 8,411.00 — SPEC's "origin ~8.5k". Assert the identification, then the
    # exclusion, then SPEC's stated REASON (8,411 is not fresh: the scope from D
    # already holds 6,435), so the test fails loudly if some other rule starts
    # doing the excluding.
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
    # moves the high cannot let the assertion pass vacuously.
    for week_monday, high in (("2022-09-12", Decimal("22799")),
                              ("2022-10-03", Decimal("20475"))):
        week = next(w for w in weeks if w.monday == week_monday)
        assert week.high == high
        assert all(c.week_monday != week_monday for c in cands)
    # SPEC's stated reason for both: their origins (~18.1-18.2k) never undercut
    # June's 17,622, so they are not fresh lows.
    for origin_monday in ("2022-09-05", "2022-09-26"):
        assert next(w for w in weeks
                    if w.monday == origin_monday).low > Decimal("17622")

    # The Nov FTX bounce is excluded by a DIFFERENT rule — degree, not freshness
    # (~+11% < R_e = 15) — and the brief's original G3 omitted it entirely.
    # Asserting it separately keeps R_e's role in this gate observable.
    ftx = next(w for w in weeks if w.monday == "2022-11-14")
    assert all(c.week_monday != "2022-11-14" for c in cands)
    el = Decimal("15476")                            # EP5's EL* / the FTX low
    assert Decimal("10") < (ftx.high - el) / el * Decimal(100) < Decimal("15")

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2023-02-13"
    assert bos == walk_forward_bos(episode_scope, trigger)
    # §10: "weekly high ~25,250".
    bos_bar = next(b for b in bars if b.date == bos)
    assert pct(bos_bar.high, Decimal("25250")) < Decimal("0.5")
