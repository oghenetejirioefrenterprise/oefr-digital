"""Test-only loaders for the frozen reference snapshots in data/reference/.

engine/ must NEVER import this module. Production data access is M2's job.
"""
from __future__ import annotations
import csv
import json
from decimal import Decimal
from pathlib import Path
from engine.types import Bar, OnChain

REF = Path(__file__).resolve().parent / "reference"


def load_bars() -> list[Bar]:
    rows = json.loads((REF / "btc_daily_full.json").read_text(), parse_float=Decimal)
    return [Bar.from_json(r) for r in sorted(rows, key=lambda r: r["date"])]


def _coinmetrics_realized() -> dict[str, Decimal]:
    """Realized price derived as ``CapMrktCurUSD / CapMVRVCur / SplyCur``.

    The community feed carries no ``CapRealUSD`` column, so it is reconstructed
    from market cap, MVRV and supply. Rows whose three inputs are not all
    present and parseable are skipped — the early-2009 rows are blank — and a
    zero MVRV or supply would be a division by zero rather than a price.
    """
    out: dict[str, Decimal] = {}
    with open(REF / "coinmetrics_btc.csv") as f:
        for row in csv.DictReader(f):
            try:
                mc = Decimal(row["CapMrktCurUSD"])
                mv = Decimal(row["CapMVRVCur"])
                sp = Decimal(row["SplyCur"])
            except Exception:
                continue
            if mv > 0 and sp > 0:
                out[row["time"][:10]] = mc / mv / sp
    return out


def load_onchain_with_provenance() -> tuple[dict[str, OnChain], frozenset[str]]:
    """Build the on-chain series and report where the realized source was
    substituted against policy.

    Realized = CoinMetrics where available, checkonchain `realised` after it
    ends. Balanced = checkonchain `balanced`. This exact policy is what
    reproduces every historical fill.

    The two realized sources differ by ~1.78% on average, which is more than
    enough to move a fill price, so the splice boundary is load-bearing: never
    substitute checkonchain for a date CoinMetrics covers.

    The second return value is the set of dates at or before CoinMetrics' last
    row that nonetheless fell through to checkonchain — i.e. holes in the
    CoinMetrics feed. Silently papering one over would degrade a price by
    ~1.78% with no signal, so the substitution is surfaced rather than hidden,
    matching the project's "alert loudly on staleness" rule for the other
    fragile data dependency. Callers decide what to do; the chosen value is
    unaffected.
    """
    coc = json.loads((REF / "checkonchain_pricing.json").read_text(),
                     parse_float=Decimal)
    balanced = {d: Decimal(str(v)) for d, v in coc["balanced"].items()}
    coc_real = {d: Decimal(str(v)) for d, v in coc["realised"].items()}
    cm_real = _coinmetrics_realized()
    cm_last = max(cm_real) if cm_real else ""

    out: dict[str, OnChain] = {}
    substituted: set[str] = set()
    for date, bal in balanced.items():
        in_cm_coverage = date <= cm_last
        realized = cm_real.get(date) if in_cm_coverage else coc_real.get(date)
        if realized is None:
            realized = coc_real.get(date)
            if realized is not None and in_cm_coverage:
                substituted.add(date)
        if realized is None:
            continue
        out[date] = OnChain(date=date, realized=realized, balanced=bal)
    return out, frozenset(substituted)


def load_onchain() -> dict[str, OnChain]:
    """The on-chain series alone. See `load_onchain_with_provenance`."""
    return load_onchain_with_provenance()[0]


def load_cy1_reference() -> dict:
    return json.loads((REF / "cy1_lifecycle_reference.json").read_text(),
                      parse_float=Decimal)
