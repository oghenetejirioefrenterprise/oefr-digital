from decimal import Decimal
from data.loaders import load_onchain, load_onchain_with_provenance, load_bars
from engine.lines import lines_for
from engine.types import OnChain


def approx(a: Decimal, b: str, tol="0.01") -> bool:
    return abs(a - Decimal(b)) <= Decimal(tol)


def test_lines_for_orders_realized_above_mid_above_balanced():
    oc = OnChain("2022-06-13", Decimal("23188.45"), Decimal("19685.61"))
    t1, t2, t3 = lines_for(oc)
    assert t1 == Decimal("23188.45")
    assert t3 == Decimal("19685.61")
    assert t3 < t2 < t1


def test_onchain_series_reproduces_verified_line_values():
    """Verified against cy1_lifecycle.json fills before this plan was written."""
    oc = load_onchain()
    cases = [
        ("2014-10-04", "346.70", "335.69", "324.68"),
        ("2020-03-16", "5566.46", "5135.22", "4703.98"),
        ("2022-06-13", "23188.45", "21437.03", "19685.61"),
    ]
    for date, r, m, b in cases:
        t1, t2, t3 = lines_for(oc[date])
        assert approx(t1, r), f"{date} realized {t1} != {r}"
        assert approx(t2, m), f"{date} midpoint {t2} != {m}"
        assert approx(t3, b), f"{date} balanced {t3} != {b}"


def test_realized_splices_to_checkonchain_after_coinmetrics_ends():
    """CoinMetrics ends 2026-05-23; checkonchain carries the tail.
    EP6's data-end lines are 52,848 / 45,849 / 38,851."""
    oc = load_onchain()
    t1, t2, t3 = lines_for(oc["2026-07-19"])
    assert approx(t1, "52848", tol="1")
    assert approx(t2, "45849", tol="1")
    assert approx(t3, "38851", tol="1")


def test_splice_boundary_is_pinned_to_the_exact_changeover_day():
    """The straddle test the tail test cannot be.

    2026-07-19 is past CoinMetrics under *any* boundary, so the test above
    passes under any policy that has a fallback at all. These two adjacent days
    are the discriminating pair: 2026-05-23 is CoinMetrics' last row and
    2026-05-24 is checkonchain's first. The two sources are $11.77 apart there
    — 1,177x the 0.01 tolerance — so a boundary that slips even one day fails
    loudly. Values re-derived from the raw CSV and JSON, not from loaders.py.

    Stakes: a re-pulled short CSV moves every date up to 2026-05-23 onto a
    source ~1.78% off, about $950 on a $53k T1 line.
    """
    oc = load_onchain()
    assert approx(oc["2026-05-23"].realized, "54164.98"), "last CoinMetrics day"
    assert approx(oc["2026-05-24"].realized, "54154.53"), "first checkonchain day"
    assert not approx(oc["2026-05-23"].realized, "54153.21", tol="1"), (
        "2026-05-23 fell through to checkonchain — the splice boundary moved"
    )


def test_only_known_inert_date_substitutes_source_inside_coinmetrics_coverage():
    """A hole in CoinMetrics mid-history must surface, not be papered over.

    Falling back to checkonchain for a date CoinMetrics is supposed to cover
    swaps in a value ~1.78% off with no signal. Exactly one such date exists
    today — 2010-07-17, more than four years before the earliest date any gate
    reads — so this pins the known-inert case and fails the moment a new hole
    opens.
    """
    _, substituted = load_onchain_with_provenance()
    assert substituted == frozenset({"2010-07-17"}), (
        f"unexpected source substitution inside CoinMetrics coverage: "
        f"{sorted(substituted - {'2010-07-17'})}"
    )


def test_bars_load_with_expected_shape():
    bars = load_bars()
    assert bars[0].date == "2011-08-18"
    by_date = {b.date: b for b in bars}
    assert by_date["2020-03-16"].open == Decimal("5360.33")
    assert by_date["2018-11-26"].open == Decimal("4088.69")
