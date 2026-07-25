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
    rows = json.loads((REF / "btc_daily_full.json").read_text())
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


def load_onchain() -> dict[str, OnChain]:
    """Realized = CoinMetrics where available, checkonchain `realised` after it
    ends. Balanced = checkonchain `balanced`. This exact policy is what
    reproduces every historical fill.

    The two realized sources differ by ~1.78% on average, which is more than
    enough to move a fill price, so the splice boundary is load-bearing: never
    substitute checkonchain for a date CoinMetrics covers.
    """
    coc = json.loads((REF / "checkonchain_pricing.json").read_text())
    balanced = {d: Decimal(str(v)) for d, v in coc["balanced"].items()}
    coc_real = {d: Decimal(str(v)) for d, v in coc["realised"].items()}
    cm_real = _coinmetrics_realized()
    cm_last = max(cm_real) if cm_real else ""

    out: dict[str, OnChain] = {}
    for date, bal in balanced.items():
        realized = cm_real.get(date) if date <= cm_last else coc_real.get(date)
        if realized is None:
            realized = coc_real.get(date)
        if realized is None:
            continue
        out[date] = OnChain(date=date, realized=realized, balanced=bal)
    return out


def load_cy1_reference() -> dict:
    return json.loads((REF / "cy1_lifecycle_reference.json").read_text())
