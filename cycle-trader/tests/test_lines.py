from decimal import Decimal
from data.loaders import load_onchain, load_bars
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


def test_bars_load_with_expected_shape():
    bars = load_bars()
    assert bars[0].date == "2011-08-18"
    by_date = {b.date: b for b in bars}
    assert by_date["2020-03-16"].open == Decimal("5360.33")
    assert by_date["2018-11-26"].open == Decimal("4088.69")
