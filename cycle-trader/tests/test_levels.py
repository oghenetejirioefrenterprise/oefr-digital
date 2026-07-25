from decimal import Decimal, localcontext

from engine.levels import LADDER, LADDER_UNITS, ladder_levels, extension_1272, mirror_target


def test_ep2_ladder_levels_match_gate_g1():
    """G1: leg 152.40 -> 309.90 gives 231.15 / 212.25 / 186.10."""
    lv = ladder_levels(Decimal("152.40"), Decimal("309.90"))
    assert lv["0.5"] == Decimal("231.150")
    assert lv["0.62"] == Decimal("212.250")
    assert abs(lv["0.786"] - Decimal("186.10")) < Decimal("0.01")


def test_ladder_omits_the_0328_level():
    assert "0.328" not in ladder_levels(Decimal("100"), Decimal("200"))


def test_extension_1272_matches_all_four_episodes():
    cases = [
        ("152.40", "1163.00", "1437.88"),      # EP2
        ("3156.26", "19798.68", "24325.42"),   # EP3
        ("3782.13", "19798.68", "24155.18"),   # EP4
        ("15476", "69000", "83558.53"),        # EP5
    ]
    for el, ath, expected in cases:
        got = extension_1272(Decimal(el), Decimal(ath))
        assert abs(got - Decimal(expected)) < Decimal("0.01"), f"{el}/{ath}: {got}"


def test_mirror_target_is_midpoint_of_the_decline_leg():
    assert mirror_target(Decimal("126200"), Decimal("102000")) == Decimal("114100")


def test_mirror_target_falls_as_the_low_falls():
    first = mirror_target(Decimal("126200"), Decimal("110000"))
    later = mirror_target(Decimal("126200"), Decimal("102000"))
    assert later < first


# --- additions beyond the brief -------------------------------------------
# Declared in the task report. The brief exports LADDER_UNITS without asserting
# it, and the module's decimal-context decision (see engine/levels.py docstring)
# is load-bearing but invisible to the brief's five tests.


def test_ladder_units_are_2_4_8_over_exactly_the_ladder_levels():
    """SPEC §5: the ladder is weighted 2 : 4 : 8 of 14 units. The brief exports
    LADDER_UNITS but asserts nothing about it, so any weight is free to drift.
    The keys must also stay in lockstep with LADDER or the allocator (Task 9)
    silently sizes a level at zero."""
    assert LADDER_UNITS == {"0.5": Decimal(2), "0.62": Decimal(4), "0.786": Decimal(8)}
    assert LADDER_UNITS.keys() == LADDER.keys()
    assert sum(LADDER_UNITS.values()) == Decimal(14)


def test_levels_are_not_quantised_to_the_specs_two_decimal_presentation():
    """SPEC's 186.10 and 83,558.53 are presentational roundings of exact values
    (186.105 and 83,558.528) -- §10 compares at +-0.5%, and §13.1 quotes the
    extension as '83,558.5'. Nothing normative asks for 2dp, so the engine must
    return the exact arithmetic and let each surface format it."""
    lv = ladder_levels(Decimal("152.40"), Decimal("309.90"))
    assert lv["0.786"] == Decimal("186.105")
    assert extension_1272(Decimal("15476"), Decimal("69000")) == Decimal("83558.528")


def test_levels_are_independent_of_the_ambient_decimal_context():
    """`decimal`'s context is process-global mutable state: any library in the
    serverless bundle can lower `prec` and silently move every level. Empirically
    these formulas are exact at prec >= 10; at prec 6 the 1.272 extension moves
    0.028 (breaking the +-0.01 assertions above) and at prec 3 it moves 0.55%
    (breaking §10's +-0.5% gate tolerance). The module therefore pins its own
    context -- this test fails if that pin is ever removed."""
    with localcontext() as ctx:
        ctx.prec = 5
        lv = ladder_levels(Decimal("152.40"), Decimal("309.90"))
        assert lv["0.786"] == Decimal("186.105")
        assert extension_1272(Decimal("15476"), Decimal("69000")) == Decimal("83558.528")
        assert mirror_target(Decimal("126255"), Decimal("102001")) == Decimal("114128")
