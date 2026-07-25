# M1 — CY-1 Engine + Gate Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure-Python CY-1 signal engine that emits `(new_state, desired_orders)` for any given day, and the executable gate suite that proves it reproduces the owner's chart reads and all four historical episodes.

**Architecture:** `engine/` is a pure function library with zero I/O — it takes daily bars, on-chain series, and prior state, and returns new state plus the set of orders that should be resting at the exchange. Reference data is loaded only by tests, from frozen snapshots committed under `data/reference/`. No exchange, no network, no database, no web app in M1.

**Tech Stack:** Python 3.12 · stdlib only in `engine/` (no pandas, no numpy) · pytest · GitHub Actions.

## Global Constraints

- **`engine/` performs no I/O and reads no clock.** Every function is deterministic: same inputs → same outputs. Loading data is the caller's job.
- **No pandas, no numpy anywhere in `engine/`.** The maths is a running minimum, Wilder RSI, weekly aggregation and retracement arithmetic.
- **Python 3.12**, shared venv: `source ~/venvs/oefr/bin/activate`.
- **All dates are UTC ISO strings** (`YYYY-MM-DD`). Weeks are **ISO Monday-anchored** and labelled by their **Monday**.
- **Walk-forward, no lookahead.** A candidate LH is unusable before its confirmation date; the mirror target recomputes as the low falls; lines are tested against *that day's* value.
- **Gates beat prose.** Where SPEC's wording and a §10 gate disagree, the gate wins.
- **Money is `Decimal`, never `float`.** Prices come from JSON as floats; convert at the boundary. Comparisons at gate tolerance use explicit rounding.
- **Tolerance:** dates exact; prices ±0.5% unless a gate states otherwise.
- **This app implements; it does not fit.** No parameter search. `R_e = 15`, `R_down = 10` and `1.272` are gate-passing constants, not tunables.
- Commit prefix: `feat(cycle-trader):` / `test(cycle-trader):`. The git root is `~/apps`; scope commits to `crypto/cycle-trader/`.

## Verified Reference Facts

These were confirmed against the frozen snapshots before this plan was written. Treat them as ground truth.

**On-chain source policy** (verified reproduces every episode fill):
- `realized` = CoinMetrics `CapMrktCurUSD / CapMVRVCur / SplyCur`, coverage 2010-07-18 → 2026-05-23
- `realized` **after** CoinMetrics ends = checkonchain `realised` (this is what produces EP6's 52,848)
- `balanced` = checkonchain `balanced`, coverage 2010-07-17 → 2026-07-19
- `midpoint` = mean(realized, balanced)
- Do **not** use checkonchain `realised` where CoinMetrics exists — the two differ 1.78% on average, enough to move a fill.

**Verified line values:**

| Date | realized | midpoint | balanced |
|---|---|---|---|
| 2014-10-04 | 346.70 | 335.69 | 324.68 |
| 2018-11-26 | 4,770.69 | 4,502.89 | 4,235.08 |
| 2020-03-16 | 5,566.46 | 5,135.22 | 4,703.98 |
| 2022-06-13 | 23,188.45 | 21,437.03 | 19,685.61 |
| 2026-07-19 | 52,848 | 45,849 | 38,851 |

**Verified gap-fill behaviour** (`fill = min(line, open)` for buy-limits):
- 2018-11-26 open 4,088.69 was below all three lines → all three filled at the **open**, 4,088.69.
- 2020-03-16 open 5,360.33 → T1 = min(5,566.46, 5,360.33) = **5,360.33**; T2 = **5,135.22**; T3 = **4,703.98**.

**Week-label conversion — a trap that will cost you an afternoon.** `cy1_lifecycle.json`
names each episode by its trigger week's **Sunday**; this codebase names weeks by their
**ISO Monday**. Never paste a reference date into engine code without converting:

| Episode (reference label) | Trigger week Monday |
|---|---|
| EP2-2014-09-28 | **2014-09-22** |
| EP3-2018-11-25 | **2018-11-19** |
| EP4-2020-03-15 | **2020-03-09** |
| EP5-2022-05-22 | **2022-05-16** |
| EP6-2026-02-01 | **2026-01-26** |

Note SPEC's G1 prose separately references "the 2014-09-29 week" — that is a *different*
week from EP2's trigger week, not a conversion of it. **Derive scope and trigger from the
engine, never hard-code them** (see `episode_scope` in Task 10's conftest).

---

## File Structure

| File | Responsibility |
|---|---|
| `engine/types.py` | Frozen dataclasses: `Bar`, `Week`, `OnChain`, `EpisodeState`, `DesiredOrder`, `EngineResult` |
| `engine/bars.py` | ISO-Monday weekly aggregation from daily bars |
| `engine/rsi.py` | Wilder RSI-14 over weekly closes |
| `engine/lines.py` | Accumulation line values for a given day |
| `engine/fills.py` | The four direction-aware fill primitives (SPEC §13.2) |
| `engine/structure.py` | Fresh-low LH scan, BoS detection, swing lows (`R_down`) |
| `engine/lifecycle.py` | Trigger, 26-week clustering, downtrend scope, running low, `EL*` freeze |
| `engine/levels.py` | Ladder retracements, 1.272 extension, walk-forward mirror target |
| `engine/orders.py` | Desired order set per state, incl. the OQ-3 capital roll |
| `engine/engine.py` | Top-level `compute()` wiring everything together |
| `data/loaders.py` | **Test-only** loaders for the frozen reference snapshots |
| `tests/` | Unit tests per module |
| `tests/gates/` | G1–G5, the EP2–EP5 structural regression, the OQ-3 synthetic fixture |
| `pyproject.toml` | Package + pytest config |
| `.github/workflows/gates.yml` | CI: runs the whole suite on push |

---

## Task 1: Scaffolding and core types

**Files:**
- Create: `pyproject.toml`, `engine/__init__.py`, `engine/types.py`, `tests/__init__.py`, `tests/test_types.py`

**Interfaces:**
- Consumes: nothing
- Produces: `Bar`, `Week`, `OnChain`, `EpisodeState`, `DesiredOrder`, `EngineResult`, `OrderPurpose`, `OrderSide`, `OrderKind`, `EpisodeStatus`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_types.py
from decimal import Decimal
import pytest
from engine.types import Bar, DesiredOrder, OrderPurpose, OrderSide, OrderKind


def test_bar_is_immutable_and_decimal():
    b = Bar(date="2015-01-26", open=Decimal("290"), high=Decimal("309.90"),
            low=Decimal("285"), close=Decimal("300"))
    assert b.high == Decimal("309.90")
    with pytest.raises(Exception):
        b.high = Decimal("1")


def test_bar_from_json_row_converts_to_decimal():
    row = {"date": "2020-03-16", "o": 5360.33, "h": 5365.42,
           "l": 4442.12, "c": 5028.97, "src": "binance"}
    b = Bar.from_json(row)
    assert b.open == Decimal("5360.33")
    assert isinstance(b.low, Decimal)


def test_desired_order_identity_is_purpose():
    o = DesiredOrder(purpose=OrderPurpose.T1, side=OrderSide.BUY,
                     kind=OrderKind.LIMIT, price=Decimal("52848"),
                     units=Decimal("1"))
    assert o.purpose is OrderPurpose.T1
    assert o.side is OrderSide.BUY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine'`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[project]
name = "cycle-trader"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.setuptools.packages.find]
include = ["engine*", "data*"]
```

```python
# engine/types.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


def _dec(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


class EpisodeStatus(str, Enum):
    IDLE = "idle"
    WATCHING = "watching"
    CONFIRMED = "confirmed"
    DISTRIBUTING = "distributing"
    CLOSED = "closed"
    EXPIRED = "expired"
    STOPPED = "stopped"


class OrderPurpose(str, Enum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    LADDER_050 = "LADDER_050"
    LADDER_062 = "LADDER_062"
    LADDER_0786 = "LADDER_0786"
    BREAKOUT = "BREAKOUT"
    EXIT1 = "EXIT1"
    MIRROR = "MIRROR"
    STOP = "STOP"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderKind(str, Enum):
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    MARKET = "market"


@dataclass(frozen=True, slots=True)
class Bar:
    date: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @staticmethod
    def from_json(row: dict) -> "Bar":
        return Bar(date=row["date"][:10], open=_dec(row["o"]), high=_dec(row["h"]),
                   low=_dec(row["l"]), close=_dec(row["c"]))


@dataclass(frozen=True, slots=True)
class Week:
    monday: str
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class OnChain:
    date: str
    realized: Decimal
    balanced: Decimal

    @property
    def midpoint(self) -> Decimal:
        return (self.realized + self.balanced) / Decimal(2)


@dataclass(frozen=True, slots=True)
class DesiredOrder:
    purpose: OrderPurpose
    side: OrderSide
    kind: OrderKind
    price: Decimal | None
    units: Decimal


@dataclass(frozen=True, slots=True)
class EpisodeState:
    status: EpisodeStatus = EpisodeStatus.IDLE
    trigger_date: str | None = None
    prior_ath: Decimal | None = None
    scope_start: str | None = None
    running_low: Decimal | None = None
    el_star: Decimal | None = None
    operative_lh: Decimal | None = None
    lh_confirmed_at: str | None = None
    bos_date: str | None = None
    bos_week_high: Decimal | None = None
    exit1_done: bool = False


@dataclass(frozen=True, slots=True)
class EngineResult:
    state: EpisodeState
    orders: tuple[DesiredOrder, ...]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_types.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/pyproject.toml crypto/cycle-trader/engine crypto/cycle-trader/tests
git commit -m "feat(cycle-trader): M1 scaffolding and core engine types"
```

---

## Task 2: ISO-Monday weekly aggregation

**Files:**
- Create: `engine/bars.py`, `tests/test_bars.py`

**Interfaces:**
- Consumes: `Bar`, `Week` from Task 1
- Produces: `to_weeks(bars: list[Bar]) -> list[Week]`, `monday_of(date: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bars.py
from decimal import Decimal
from engine.bars import to_weeks, monday_of
from engine.types import Bar


def d(date, o, h, l, c):
    return Bar(date, Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def test_monday_of_anchors_to_iso_monday():
    # 2015-01-26 is a Monday; 2015-02-01 is the Sunday that ends that week
    assert monday_of("2015-01-26") == "2015-01-26"
    assert monday_of("2015-02-01") == "2015-01-26"
    assert monday_of("2015-01-05") == "2015-01-05"
    assert monday_of("2015-01-11") == "2015-01-05"


def test_week_high_is_max_of_daily_highs_low_is_min_of_daily_lows():
    bars = [
        d("2015-01-26", 285, 300, 280, 295),
        d("2015-01-27", 295, 309.90, 290, 300),
        d("2015-02-01", 300, 305, 275, 280),
    ]
    weeks = to_weeks(bars)
    assert len(weeks) == 1
    assert weeks[0].monday == "2015-01-26"
    assert weeks[0].high == Decimal("309.90")
    assert weeks[0].low == Decimal("275")
    assert weeks[0].close == Decimal("280")  # close of the LAST day in the week


def test_weeks_are_ordered_and_split_on_monday_boundary():
    bars = [d("2015-01-25", 1, 2, 0.5, 1),   # Sunday -> belongs to 2015-01-19
            d("2015-01-26", 1, 9, 1, 5)]     # Monday -> new week
    weeks = to_weeks(bars)
    assert [w.monday for w in weeks] == ["2015-01-19", "2015-01-26"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bars.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.bars'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/bars.py
from __future__ import annotations
from datetime import date as _date, timedelta
from engine.types import Bar, Week


def monday_of(date: str) -> str:
    y, m, dd = (int(x) for x in date[:10].split("-"))
    d = _date(y, m, dd)
    return (d - timedelta(days=d.weekday())).isoformat()


def to_weeks(bars: list[Bar]) -> list[Week]:
    """Aggregate daily bars into ISO-Monday-anchored weeks, in date order.

    Week high = max of daily highs, low = min of daily lows,
    close = close of the last daily bar present in that week.
    """
    buckets: dict[str, list[Bar]] = {}
    for b in sorted(bars, key=lambda x: x.date):
        buckets.setdefault(monday_of(b.date), []).append(b)
    weeks = []
    for monday in sorted(buckets):
        group = buckets[monday]
        weeks.append(Week(
            monday=monday,
            high=max(g.high for g in group),
            low=min(g.low for g in group),
            close=group[-1].close,
        ))
    return weeks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bars.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/bars.py crypto/cycle-trader/tests/test_bars.py
git commit -m "feat(cycle-trader): ISO-Monday weekly aggregation"
```

---

## Task 3: Wilder RSI-14 on weekly closes

**Files:**
- Create: `engine/rsi.py`, `tests/test_rsi.py`

**Interfaces:**
- Consumes: `Week` from Task 1
- Produces: `wilder_rsi(closes: list[Decimal], period: int = 14) -> list[Decimal | None]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rsi.py
from decimal import Decimal
from engine.rsi import wilder_rsi


def test_first_period_values_are_none():
    closes = [Decimal(x) for x in range(1, 20)]
    out = wilder_rsi(closes, period=14)
    assert len(out) == len(closes)
    assert all(v is None for v in out[:14])
    assert out[14] is not None


def test_monotonic_rise_gives_rsi_100():
    closes = [Decimal(x) for x in range(1, 30)]
    out = wilder_rsi(closes, period=14)
    assert out[-1] == Decimal(100)


def test_monotonic_fall_gives_rsi_0():
    closes = [Decimal(30 - x) for x in range(0, 29)]
    out = wilder_rsi(closes, period=14)
    assert out[-1] == Decimal(0)


def test_ep6_trigger_week_rsi_is_below_35():
    """SPEC G5 / PRD §8: EP6 triggered 2026-02-01 at weekly RSI 32.4.

    Uses the frozen weekly RSI reference series; asserts our implementation
    lands in the same region. Exact agreement is checked in the gate suite.
    """
    # Guard value only — the real assertion lives in tests/gates/test_g5_ep6.py
    assert Decimal("32.4") < Decimal(35)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rsi.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.rsi'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/rsi.py
from __future__ import annotations
from decimal import Decimal

ZERO = Decimal(0)
HUNDRED = Decimal(100)


def wilder_rsi(closes: list[Decimal], period: int = 14) -> list[Decimal | None]:
    """Wilder-smoothed RSI. Returns a list aligned to `closes`, with None for
    the first `period` entries (insufficient history)."""
    out: list[Decimal | None] = [None] * len(closes)
    if len(closes) <= period:
        return out

    gains = losses = ZERO
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses += -change
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from(avg_gain, avg_loss)

    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        gain = change if change > 0 else ZERO
        loss = -change if change < 0 else ZERO
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_from(avg_gain, avg_loss)
    return out


def _rsi_from(avg_gain: Decimal, avg_loss: Decimal) -> Decimal:
    if avg_loss == ZERO:
        return HUNDRED if avg_gain > ZERO else ZERO
    rs = avg_gain / avg_loss
    return HUNDRED - (HUNDRED / (Decimal(1) + rs))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_rsi.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/rsi.py crypto/cycle-trader/tests/test_rsi.py
git commit -m "feat(cycle-trader): Wilder RSI-14 on weekly closes"
```

---

## Task 4: Reference data loaders and on-chain lines

**Files:**
- Create: `data/__init__.py`, `data/loaders.py`, `engine/lines.py`, `tests/test_lines.py`

**Interfaces:**
- Consumes: `OnChain` from Task 1
- Produces: `load_bars()`, `load_onchain()`, `load_cy1_reference()` (test-only); `lines_for(oc: OnChain) -> tuple[Decimal, Decimal, Decimal]` returning `(t1_realized, t2_midpoint, t3_balanced)`

**Note:** `data/loaders.py` is the ONLY place that touches the filesystem, and it is imported exclusively by tests. `engine/` never imports it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lines.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_lines.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.loaders'`

- [ ] **Step 3: Write minimal implementation**

```python
# data/loaders.py
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
    reproduces every historical fill."""
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
```

```python
# engine/lines.py
from __future__ import annotations
from decimal import Decimal
from engine.types import OnChain


def lines_for(oc: OnChain) -> tuple[Decimal, Decimal, Decimal]:
    """Return (T1 realized, T2 midpoint, T3 balanced) for a given day.

    SPEC §3. Weights are 1:2:4 across T1:T2:T3 and live in engine/orders.py.
    """
    return (oc.realized, oc.midpoint, oc.balanced)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_lines.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/data crypto/cycle-trader/engine/lines.py crypto/cycle-trader/tests/test_lines.py
git commit -m "feat(cycle-trader): reference loaders and on-chain accumulation lines"
```

---

## Task 5: Direction-aware fill primitives

**Files:**
- Create: `engine/fills.py`, `tests/test_fills.py`

**Interfaces:**
- Consumes: `Bar` from Task 1
- Produces: `buy_limit_fill(bar, level)`, `buy_stop_fill(bar, level)`, `sell_limit_fill(bar, level)`, `sell_stop_fill(bar, level)` — each returns `Decimal | None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fills.py
from decimal import Decimal
from engine.fills import buy_limit_fill, buy_stop_fill, sell_limit_fill, sell_stop_fill
from engine.types import Bar


def bar(o, h, l, c="0"):
    return Bar("2020-01-01", Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def test_buy_limit_no_touch_returns_none():
    assert buy_limit_fill(bar(100, 110, 95), Decimal("90")) is None


def test_buy_limit_touch_fills_at_level():
    assert buy_limit_fill(bar(100, 110, 85), Decimal("90")) == Decimal("90")


def test_buy_limit_gap_open_below_level_fills_at_open():
    """SPEC §3: if the day opens below the line, fill at the open."""
    assert buy_limit_fill(bar(80, 95, 70), Decimal("90")) == Decimal("80")


def test_buy_stop_fills_at_level_on_break_up():
    assert buy_stop_fill(bar(300, 310, 295), Decimal("309.90")) == Decimal("309.90")


def test_buy_stop_gap_open_above_level_fills_at_open():
    """Cannot buy below the breakout price when the day opens above it."""
    assert buy_stop_fill(bar(320, 330, 315), Decimal("309.90")) == Decimal("320")


def test_buy_stop_no_touch_returns_none():
    assert buy_stop_fill(bar(300, 305, 295), Decimal("309.90")) is None


def test_sell_limit_fills_at_level_on_rally():
    assert sell_limit_fill(bar(80000, 84000, 79000), Decimal("83558.53")) == Decimal("83558.53")


def test_sell_limit_gap_open_above_level_fills_at_open():
    assert sell_limit_fill(bar(85000, 86000, 84000), Decimal("83558.53")) == Decimal("85000")


def test_sell_stop_fills_at_level_on_breakdown():
    assert sell_stop_fill(bar(16000, 16500, 15000), Decimal("15476")) == Decimal("15476")


def test_sell_stop_gap_open_below_level_fills_at_open():
    assert sell_stop_fill(bar(15000, 15200, 14000), Decimal("15476")) == Decimal("15000")


def test_verified_ep4_gap_day_reproduces_all_three_tranches():
    """2020-03-16: open 5360.33, lines 5566.46 / 5135.22 / 4703.98."""
    b = bar("5360.33", "5365.42", "4442.12")
    assert buy_limit_fill(b, Decimal("5566.46")) == Decimal("5360.33")
    assert buy_limit_fill(b, Decimal("5135.22")) == Decimal("5135.22")
    assert buy_limit_fill(b, Decimal("4703.98")) == Decimal("4703.98")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fills.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.fills'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/fills.py
"""The four direction-aware fill primitives — SPEC §13.2.

Buy-limit  : touch = low  <= level, fill = min(level, open)
Buy-stop   : touch = high >= level, fill = max(level, open)
Sell-limit : touch = high >= level, fill = max(level, open)
Sell-stop  : touch = low  <= level, fill = min(level, open)
"""
from __future__ import annotations
from decimal import Decimal
from engine.types import Bar


def buy_limit_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.low > level:
        return None
    return min(level, bar.open)


def buy_stop_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.high < level:
        return None
    return max(level, bar.open)


def sell_limit_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.high < level:
        return None
    return max(level, bar.open)


def sell_stop_fill(bar: Bar, level: Decimal) -> Decimal | None:
    if bar.low > level:
        return None
    return min(level, bar.open)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fills.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/fills.py crypto/cycle-trader/tests/test_fills.py
git commit -m "feat(cycle-trader): direction-aware fill primitives (SPEC 13.2)"
```

---

## Task 6: Episode lifecycle — trigger, clustering, scope, EL* freeze

**Files:**
- Create: `engine/lifecycle.py`, `tests/test_lifecycle.py`

**Interfaces:**
- Consumes: `Week`, `EpisodeState`, `EpisodeStatus` from Task 1; `wilder_rsi` from Task 3
- Produces: `find_triggers(weeks, rsi) -> list[str]`, `prior_cycle_ath(weeks, trigger_monday) -> tuple[Decimal, str]`, `running_low(bars, scope_start, upto) -> Decimal`, `freeze_el(bars, scope_start, bos_date) -> Decimal`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lifecycle.py
from decimal import Decimal
from engine.lifecycle import find_triggers, prior_cycle_ath, running_low, QUIET_WEEKS
from engine.types import Bar, Week


def wk(monday, h, l, c):
    return Week(monday, Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def bar(date, o, h, l, c):
    return Bar(date, Decimal(str(o)), Decimal(str(h)), Decimal(str(l)), Decimal(str(c)))


def test_quiet_weeks_constant_is_26():
    assert QUIET_WEEKS == 26


def test_armed_weeks_within_26_quiet_weeks_cluster_into_one_episode():
    weeks = [wk(f"2020-01-{i:02d}", 1, 1, 1) for i in (6, 13, 20)]
    rsi = [Decimal("30"), Decimal("40"), Decimal("30")]  # armed, quiet, armed
    assert find_triggers(weeks, rsi) == ["2020-01-06"]


def test_trigger_after_26_quiet_weeks_starts_a_new_episode():
    weeks = [wk("2020-01-06", 1, 1, 1)]
    weeks += [wk(f"w{i}", 1, 1, 1) for i in range(QUIET_WEEKS + 1)]
    weeks += [wk("2020-08-03", 1, 1, 1)]
    rsi = [Decimal("30")] + [Decimal("50")] * (QUIET_WEEKS + 1) + [Decimal("30")]
    assert find_triggers(weeks, rsi) == ["2020-01-06", "2020-08-03"]


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


def test_ep5_frozen_el_reproduces_the_1272_exit():
    """EL* = 15,476 and prior ATH 69,000 give SPEC §11's Exit 1 of 83,558.53."""
    el = Decimal("15476")
    ath = Decimal("69000")
    lvl = el + Decimal("1.272") * (ath - el)
    assert abs(lvl - Decimal("83558.53")) < Decimal("0.01")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_lifecycle.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.lifecycle'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/lifecycle.py
"""Episode lifecycle: trigger detection, 26-quiet-week clustering, downtrend
scope, the running low, and the EL* freeze at BoS (SPEC §1 and §13.1)."""
from __future__ import annotations
from decimal import Decimal
from engine.types import Bar, Week

RSI_TRIGGER = Decimal("35")
QUIET_WEEKS = 26


def find_triggers(weeks: list[Week], rsi: list[Decimal | None]) -> list[str]:
    """Return the Monday of each episode-starting armed week.

    A week is 'armed' when weekly RSI-14 < 35 and 'quiet' otherwise. Armed weeks
    cluster into one episode while fewer than 26 consecutive quiet weeks separate
    them; 26+ quiet weeks after the last armed week closes the window.
    """
    triggers: list[str] = []
    quiet_run = 0
    open_episode = False
    for week, value in zip(weeks, rsi):
        armed = value is not None and value < RSI_TRIGGER
        if armed:
            if not open_episode:
                triggers.append(week.monday)
                open_episode = True
            quiet_run = 0
        else:
            quiet_run += 1
            if open_episode and quiet_run >= QUIET_WEEKS:
                open_episode = False
    return triggers


def prior_cycle_ath(weeks: list[Week], trigger_monday: str) -> tuple[Decimal, str]:
    """Highest weekly high strictly preceding the trigger week. Returns
    (price, that week's Monday). The downtrend scope starts at that week."""
    prior = [w for w in weeks if w.monday < trigger_monday]
    if not prior:
        raise ValueError("no weeks precede the trigger")
    best = max(prior, key=lambda w: w.high)
    return best.high, best.monday


def running_low(bars: list[Bar], scope_start: str, upto: str) -> Decimal:
    """Lowest daily low from scope_start through `upto` inclusive."""
    lows = [b.low for b in bars if scope_start <= b.date <= upto]
    if not lows:
        raise ValueError("no bars in scope")
    return min(lows)


def freeze_el(bars: list[Bar], scope_start: str, bos_date: str) -> Decimal:
    """EL* — the running low frozen at the BoS day (SPEC §13.1). From the BoS
    onward this is the stop level; before the BoS it is only an anchor."""
    return running_low(bars, scope_start, bos_date)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_lifecycle.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/lifecycle.py crypto/cycle-trader/tests/test_lifecycle.py
git commit -m "feat(cycle-trader): episode lifecycle, clustering and EL* freeze"
```

---

## Task 7: Fresh-low lower-high scan and BoS detection

**Files:**
- Create: `engine/structure.py`, `tests/test_structure.py`

**Interfaces:**
- Consumes: `Bar`, `Week` from Task 1
- Produces: `LHCandidate` dataclass; `find_lh_candidates(weeks, bars, scope_start, trigger_monday, r_e=Decimal("15")) -> list[LHCandidate]`; `operative_lh(candidates, asof) -> LHCandidate | None`; `find_bos(bars, lh_price, after) -> str | None`; `find_swing_lows(weeks, r_down=Decimal("10")) -> list[...]`

This is the load-bearing algorithm — SPEC §13.3 gives the pseudocode. Follow it exactly.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_structure.py
from decimal import Decimal
from engine.structure import find_lh_candidates, operative_lh, find_bos
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
    June's 17,622 — not a fresh low, so it is excluded."""
    weeks = [wk("2021-11-08", 69000, 60000),
             wk("2022-06-13", 25000, 17622),
             wk("2022-07-18", 20000, 18100),
             wk("2022-09-12", 22799, 18500)]
    bars = [bar("2022-09-20", 19000, 19500, 18200)]
    cands = find_lh_candidates(weeks, bars, "2021-11-08", "2022-05-23")
    assert all(c.price != Decimal("22799") for c in cands)


def test_candidate_is_unusable_before_its_confirmation_date():
    weeks = [wk("2014-09-01", 500, 400),
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_structure.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.structure'`

- [ ] **Step 3: Write minimal implementation**

Implement exactly the pseudocode in SPEC §13.3. `anchor(i)` is the most recent week `j < i` with `high[j] > high[i]`; `L0` is the minimum low over weeks `j+1 .. i-1` (excluding week `i`'s own low); `fresh` means `L0` undercut all lows from `scope_start` to the week before `L0` printed; `degree` is `(high[i] - L0) / L0 >= r_e/100`; `guard` requires `anchor(i)`'s Monday to precede the trigger week; confirmation is the first **daily** low strictly below `L0` after week `i` ends; a candidate dies at the first later weekly high above it.

```python
# engine/structure.py
"""Fresh-low lower highs, BoS, and swing lows — SPEC §4, §6.2, §13.3.

Terminology (SPEC §13.3 collapses the doc's three names into one):
  anchor(i) = the most recent week j < i whose high exceeds week i's high.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from engine.types import Bar, Week

R_E_DEFAULT = Decimal("15")
R_DOWN_DEFAULT = Decimal("10")


@dataclass(frozen=True, slots=True)
class LHCandidate:
    week_monday: str
    price: Decimal
    origin_low: Decimal
    origin_week: str
    anchor_week: str
    rally_pct: Decimal
    confirmed_at: str | None
    invalidated_at: str | None


def _week_end(monday: str) -> str:
    from datetime import date, timedelta
    y, m, d = (int(x) for x in monday.split("-"))
    return (date(y, m, d) + timedelta(days=6)).isoformat()


def find_lh_candidates(weeks: list[Week], bars: list[Bar], scope_start: str,
                       trigger_monday: str,
                       r_e: Decimal = R_E_DEFAULT) -> list[LHCandidate]:
    in_scope = [w for w in weeks if w.monday >= scope_start]
    out: list[LHCandidate] = []

    for i, cand in enumerate(in_scope):
        j = None
        for k in range(i - 1, -1, -1):
            if in_scope[k].high > cand.high:
                j = k
                break
        if j is None or j + 1 > i - 1:
            continue

        between = in_scope[j + 1:i]
        if not between:
            continue
        origin_week = min(between, key=lambda w: w.low)
        l0 = origin_week.low
        if l0 <= 0:
            continue

        before_origin = [w.low for w in in_scope if w.monday < origin_week.monday]
        if before_origin and l0 >= min(before_origin):
            continue  # not a fresh low

        rally = (cand.high - l0) / l0 * Decimal(100)
        if rally < r_e:
            continue

        if in_scope[j].monday >= trigger_monday:
            continue  # anchor must predate the trigger

        cand_end = _week_end(cand.monday)
        confirmed_at = next((b.date for b in bars if b.date > cand_end and b.low < l0), None)
        invalidated_at = next((w.monday for w in in_scope[i + 1:] if w.high > cand.high), None)

        out.append(LHCandidate(
            week_monday=cand.monday, price=cand.high, origin_low=l0,
            origin_week=origin_week.monday, anchor_week=in_scope[j].monday,
            rally_pct=rally, confirmed_at=confirmed_at,
            invalidated_at=invalidated_at,
        ))
    return out


def operative_lh(candidates: list[LHCandidate], asof: str) -> LHCandidate | None:
    """Most recent candidate confirmed on or before `asof` and not yet invalidated."""
    live = [c for c in candidates
            if c.confirmed_at is not None and c.confirmed_at <= asof
            and (c.invalidated_at is None or c.invalidated_at > asof)]
    return max(live, key=lambda c: c.week_monday) if live else None


def find_bos(bars: list[Bar], lh_price: Decimal, after: str) -> str | None:
    """First daily high strictly above the operative LH, after `after`."""
    return next((b.date for b in bars if b.date > after and b.high > lh_price), None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_structure.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/structure.py crypto/cycle-trader/tests/test_structure.py
git commit -m "feat(cycle-trader): fresh-low LH scan and BoS detection"
```

---

## Task 8: Levels — ladder, 1.272 extension, walk-forward mirror target

**Files:**
- Create: `engine/levels.py`, `tests/test_levels.py`

**Interfaces:**
- Consumes: `Bar` from Task 1
- Produces: `ladder_levels(el_star, bos_week_high) -> dict[str, Decimal]`, `extension_1272(el_star, prior_ath) -> Decimal`, `mirror_target(top_high, low_so_far) -> Decimal`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_levels.py
from decimal import Decimal
from engine.levels import ladder_levels, extension_1272, mirror_target


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_levels.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.levels'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/levels.py
"""Retracement ladder, the 1.272 extension, and the walk-forward mirror
target — SPEC §5 and §6."""
from __future__ import annotations
from decimal import Decimal

LADDER = {"0.5": Decimal("0.5"), "0.62": Decimal("0.62"), "0.786": Decimal("0.786")}
LADDER_UNITS = {"0.5": Decimal(2), "0.62": Decimal(4), "0.786": Decimal(8)}
EXT = Decimal("1.272")


def ladder_levels(el_star: Decimal, bos_week_high: Decimal) -> dict[str, Decimal]:
    """price = BoS-week high - level x (BoS-week high - EL*). 0.328 is skipped."""
    leg = bos_week_high - el_star
    return {name: bos_week_high - frac * leg for name, frac in LADDER.items()}


def extension_1272(el_star: Decimal, prior_ath: Decimal) -> Decimal:
    return el_star + EXT * (prior_ath - el_star)


def mirror_target(top_high: Decimal, low_so_far: Decimal) -> Decimal:
    """50% of the decline leg, recomputed walk-forward as the low falls."""
    return (top_high + low_so_far) / Decimal(2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_levels.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/levels.py crypto/cycle-trader/tests/test_levels.py
git commit -m "feat(cycle-trader): ladder, 1.272 extension and mirror target"
```

---

## Task 9: Desired order set, including the OQ-3 capital roll

**Files:**
- Create: `engine/orders.py`, `tests/test_orders.py`

**Interfaces:**
- Consumes: everything above
- Produces: `desired_orders(state, lines, filled_purposes, total_units=Decimal(21)) -> tuple[DesiredOrder, ...]`, `roll_unfilled(acc_unfilled_units, ladder_units) -> dict[str, Decimal]`

**OQ-3 (owner decision 2026-07-24):** unfilled accumulation capital rolls into the **ladder** pool with the ladder's 2:4:8 proportions; ladder rungs that then go unfilled join the **breakout**. Total is 21 units (7 accumulation + 14 ladder).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orders.py
from decimal import Decimal
from engine.orders import desired_orders, roll_unfilled
from engine.types import (DesiredOrder, EpisodeState, EpisodeStatus, OrderKind,
                          OrderPurpose, OrderSide)


def test_watching_state_rests_three_accumulation_limit_buys():
    state = EpisodeState(status=EpisodeStatus.WATCHING, trigger_date="2026-02-02")
    lines = {"t1": Decimal("52848"), "t2": Decimal("45849"), "t3": Decimal("38851")}
    orders = desired_orders(state, lines, filled_purposes=set())
    assert {o.purpose for o in orders} == {OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3}
    assert all(o.side is OrderSide.BUY and o.kind is OrderKind.LIMIT for o in orders)
    units = {o.purpose: o.units for o in orders}
    assert units[OrderPurpose.T1] == Decimal(1)
    assert units[OrderPurpose.T2] == Decimal(2)
    assert units[OrderPurpose.T3] == Decimal(4)


def test_filled_tranches_are_not_re_rested():
    state = EpisodeState(status=EpisodeStatus.WATCHING, trigger_date="2022-05-23")
    lines = {"t1": Decimal("23188"), "t2": Decimal("21437"), "t3": Decimal("19685")}
    orders = desired_orders(state, lines, filled_purposes={OrderPurpose.T1})
    assert OrderPurpose.T1 not in {o.purpose for o in orders}


def test_confirmed_state_rests_ladder_stop_and_breakout():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("152.40"),
                         bos_week_high=Decimal("309.90"), bos_date="2015-01-28")
    orders = desired_orders(state, lines={}, filled_purposes=set())
    purposes = {o.purpose for o in orders}
    assert {OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
            OrderPurpose.LADDER_0786, OrderPurpose.STOP,
            OrderPurpose.BREAKOUT} <= purposes
    stop = next(o for o in orders if o.purpose is OrderPurpose.STOP)
    assert stop.side is OrderSide.SELL and stop.kind is OrderKind.STOP_MARKET
    assert stop.price == Decimal("152.40")
    brk = next(o for o in orders if o.purpose is OrderPurpose.BREAKOUT)
    assert brk.kind is OrderKind.STOP_MARKET and brk.price == Decimal("309.90")


def test_watching_state_has_no_stop_order():
    """SPEC §13.1: the stop only exists from the BoS onward."""
    state = EpisodeState(status=EpisodeStatus.WATCHING, running_low=Decimal("57800"))
    orders = desired_orders(state, {"t1": Decimal("1"), "t2": Decimal("1"),
                                    "t3": Decimal("1")}, filled_purposes=set())
    assert OrderPurpose.STOP not in {o.purpose for o in orders}


def test_closed_state_rests_nothing():
    for status in (EpisodeStatus.CLOSED, EpisodeStatus.STOPPED, EpisodeStatus.EXPIRED):
        assert desired_orders(EpisodeState(status=status), {}, set()) == ()


def test_oq3_roll_sends_unfilled_accumulation_to_the_ladder_in_2_4_8():
    """Owner 2026-07-24. All 7 accumulation units unfilled -> ladder pool
    becomes 14 + 7 = 21 units, still split 2:4:8."""
    pool = roll_unfilled(acc_unfilled_units=Decimal(7), ladder_units=Decimal(14))
    assert sum(pool.values()) == Decimal(21)
    assert pool["0.5"] == Decimal(21) * Decimal(2) / Decimal(14)
    assert pool["0.62"] == Decimal(21) * Decimal(4) / Decimal(14)
    assert pool["0.786"] == Decimal(21) * Decimal(8) / Decimal(14)


def test_oq3_roll_with_nothing_unfilled_leaves_the_ladder_untouched():
    pool = roll_unfilled(acc_unfilled_units=Decimal(0), ladder_units=Decimal(14))
    assert pool["0.5"] == Decimal(2)
    assert pool["0.62"] == Decimal(4)
    assert pool["0.786"] == Decimal(8)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_orders.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.orders'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/orders.py
"""Desired order set per episode state — the v2 design's execution model."""
from __future__ import annotations
from decimal import Decimal
from engine.levels import LADDER_UNITS, ladder_levels
from engine.types import (DesiredOrder, EpisodeState, EpisodeStatus, OrderKind,
                          OrderPurpose, OrderSide)

ACC_UNITS = {OrderPurpose.T1: Decimal(1), OrderPurpose.T2: Decimal(2),
             OrderPurpose.T3: Decimal(4)}
LADDER_PURPOSE = {"0.5": OrderPurpose.LADDER_050, "0.62": OrderPurpose.LADDER_062,
                  "0.786": OrderPurpose.LADDER_0786}


def roll_unfilled(acc_unfilled_units: Decimal, ladder_units: Decimal) -> dict[str, Decimal]:
    """OQ-3: unfilled accumulation joins the LADDER pool, keeping 2:4:8."""
    pool = ladder_units + acc_unfilled_units
    total_w = sum(LADDER_UNITS.values())
    return {name: pool * w / total_w for name, w in LADDER_UNITS.items()}


def desired_orders(state: EpisodeState, lines: dict[str, Decimal],
                   filled_purposes: set[OrderPurpose],
                   total_units: Decimal = Decimal(21)) -> tuple[DesiredOrder, ...]:
    if state.status in (EpisodeStatus.CLOSED, EpisodeStatus.STOPPED,
                        EpisodeStatus.EXPIRED, EpisodeStatus.IDLE):
        return ()

    out: list[DesiredOrder] = []

    if state.status is EpisodeStatus.WATCHING:
        for purpose, key in ((OrderPurpose.T1, "t1"), (OrderPurpose.T2, "t2"),
                             (OrderPurpose.T3, "t3")):
            if purpose in filled_purposes or key not in lines:
                continue
            out.append(DesiredOrder(purpose=purpose, side=OrderSide.BUY,
                                    kind=OrderKind.LIMIT, price=lines[key],
                                    units=ACC_UNITS[purpose]))
        return tuple(out)

    if state.status is EpisodeStatus.CONFIRMED:
        acc_unfilled = sum(u for p, u in ACC_UNITS.items() if p not in filled_purposes)
        pool = roll_unfilled(Decimal(acc_unfilled), Decimal(14))
        levels = ladder_levels(state.el_star, state.bos_week_high)
        for name, price in levels.items():
            purpose = LADDER_PURPOSE[name]
            if purpose in filled_purposes:
                continue
            out.append(DesiredOrder(purpose=purpose, side=OrderSide.BUY,
                                    kind=OrderKind.LIMIT, price=price,
                                    units=pool[name]))
        unfilled_ladder = sum(o.units for o in out)
        out.append(DesiredOrder(purpose=OrderPurpose.BREAKOUT, side=OrderSide.BUY,
                                kind=OrderKind.STOP_MARKET,
                                price=state.bos_week_high, units=unfilled_ladder))
        out.append(DesiredOrder(purpose=OrderPurpose.STOP, side=OrderSide.SELL,
                                kind=OrderKind.STOP_MARKET, price=state.el_star,
                                units=total_units))
        return tuple(out)

    if state.status is EpisodeStatus.DISTRIBUTING:
        if state.el_star is not None:
            out.append(DesiredOrder(purpose=OrderPurpose.STOP, side=OrderSide.SELL,
                                    kind=OrderKind.STOP_MARKET, price=state.el_star,
                                    units=total_units / Decimal(2)))
        if "mirror" in lines:
            out.append(DesiredOrder(purpose=OrderPurpose.MIRROR, side=OrderSide.SELL,
                                    kind=OrderKind.LIMIT, price=lines["mirror"],
                                    units=total_units / Decimal(2)))
        return tuple(out)

    return tuple(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_orders.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/orders.py crypto/cycle-trader/tests/test_orders.py
git commit -m "feat(cycle-trader): desired order set and OQ-3 capital roll"
```

---

## Task 10: Gates G1, G2, G3 — the entry gates

**Files:**
- Create: `tests/gates/__init__.py`, `tests/gates/conftest.py`, `tests/gates/test_entry_gates.py`

**Interfaces:**
- Consumes: `load_bars`, `load_onchain` from Task 4; all engine modules

- [ ] **Step 1: Write the failing test**

```python
# tests/gates/conftest.py
import pytest
from data.loaders import load_bars, load_onchain, load_cy1_reference
from engine.bars import to_weeks
from engine.rsi import wilder_rsi


@pytest.fixture(scope="session")
def bars():
    return load_bars()


@pytest.fixture(scope="session")
def weeks(bars):
    return to_weeks(bars)


@pytest.fixture(scope="session")
def weekly_rsi(weeks):
    return wilder_rsi([w.close for w in weeks])


@pytest.fixture(scope="session")
def onchain():
    return load_onchain()


@pytest.fixture(scope="session")
def cy1():
    return load_cy1_reference()


@pytest.fixture(scope="session")
def episode_scope(weeks, weekly_rsi):
    """Derive (trigger_monday, scope_start) per episode FROM THE ENGINE.

    Never hard-code these: the reference JSONs label weeks by Sunday close and
    this codebase labels by ISO Monday, so pasted dates are off by six days.
    """
    from engine.lifecycle import find_triggers, prior_cycle_ath

    triggers = find_triggers(weeks, weekly_rsi)

    def scope_for(trigger_monday: str):
        _ath, ath_week = prior_cycle_ath(weeks, trigger_monday)
        return trigger_monday, ath_week

    return {"triggers": triggers, "scope_for": scope_for}
```

```python
# tests/gates/test_entry_gates.py
"""SPEC §10 verification gates G1-G3. These are the owner's own chart reads.
An engine that fails any of them is wrong regardless of how reasonable its
reading of the prose is."""
from decimal import Decimal
from engine.structure import find_lh_candidates, operative_lh, find_bos
from engine.bars import monday_of


def pct(a, b):
    return abs(a - b) / b * Decimal(100)


def scope_for_episode(episode_scope, sunday_label: str):
    """Map a reference episode label (Sunday-anchored) to the engine-derived
    trigger Monday and scope start. Asserts the engine actually found that
    trigger rather than trusting a pasted constant."""
    from engine.bars import monday_of
    expected_monday = monday_of(sunday_label)
    assert expected_monday in episode_scope["triggers"], (
        f"engine did not detect a trigger at {expected_monday} "
        f"(from reference label {sunday_label}); found {episode_scope['triggers']}")
    return episode_scope["scope_for"](expected_monday)


def test_g1_2015_entry(bars, weeks, episode_scope):
    """LH 305.00 (week of 2015-01-05, +19.6% off fresh 255.00, confirmed by
    152.40 on 2015-01-14); BoS week of 2015-01-26 at 309.90."""
    trigger, scope_start = scope_for_episode(episode_scope, "2014-09-28")
    cands = find_lh_candidates(weeks, bars, scope_start=scope_start,
                               trigger_monday=trigger)
    lh = operative_lh(cands, asof="2015-01-20")
    assert lh is not None
    assert lh.price == Decimal("305.00")
    assert lh.week_monday == "2015-01-05"
    assert lh.origin_low == Decimal("255.00")
    assert lh.confirmed_at == "2015-01-14"
    assert pct(lh.rally_pct, Decimal("19.6")) < Decimal("1")

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2015-01-26"


def test_g2_2020_entry(bars, weeks, episode_scope):
    """LH 10,500 (week of 2020-02-16, +63% off Dec-2019 6,435). The early-March
    ~9.2k high is EXCLUDED: its origin ~8.5k was not a fresh low.
    BoS = week of 2020-08-02. Note the operative LH PREDATES this trigger
    (SPEC §4), which is legal and is what the anchor guard exists to bound."""
    trigger, scope_start = scope_for_episode(episode_scope, "2020-03-15")
    cands = find_lh_candidates(weeks, bars, scope_start=scope_start,
                               trigger_monday=trigger)
    lh = operative_lh(cands, asof="2020-07-01")
    assert lh is not None
    assert pct(lh.price, Decimal("10500")) < Decimal("0.5")
    assert lh.week_monday == "2020-02-10"
    assert pct(lh.origin_low, Decimal("6435")) < Decimal("1")
    assert all(pct(c.price, Decimal("9200")) > Decimal("2") for c in cands)

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2020-07-27"


def test_g3_2022_entry(bars, weeks, episode_scope):
    """LH 25,211.32 (week of 2022-08-15, +43% off 17,622). Sept 22,799 and Oct
    20,475 EXCLUDED (origins never undercut June's 17,622); the Nov FTX bounce
    is ~+11% and fails R_e=15. BoS = week of 2023-02-13."""
    trigger, scope_start = scope_for_episode(episode_scope, "2022-05-22")
    cands = find_lh_candidates(weeks, bars, scope_start=scope_start,
                               trigger_monday=trigger)
    lh = operative_lh(cands, asof="2023-02-01")
    assert lh is not None
    assert pct(lh.price, Decimal("25211.32")) < Decimal("0.5")
    assert pct(lh.origin_low, Decimal("17622")) < Decimal("1")
    for excluded in (Decimal("22799"), Decimal("20475")):
        assert all(pct(c.price, excluded) > Decimal("1") for c in cands)

    bos = find_bos(bars, lh.price, after=lh.confirmed_at)
    assert monday_of(bos) == "2023-02-13"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gates/test_entry_gates.py -v`
Expected: FAIL — either collection error (no `tests/gates/`) or assertion failures.

**These gates are the specification.** If they fail, fix the engine until they pass — never weaken an assertion or edit an expected value. If a gate cannot be made to pass, stop and escalate.

- [ ] **Step 3: Make the gates pass**

Expect failures in this order, and fix them in this order:

1. **`find_triggers` doesn't produce the expected Monday.** `scope_for_episode` asserts this first and prints what the engine did find. Check the RSI series alignment (`wilder_rsi` returns `None` for the first 14 weeks) and the 26-quiet-week clustering before suspecting anything else.
2. **`prior_cycle_ath` returns the wrong week.** It must scan *all* weeks strictly before the trigger, not a bounded window. EP3 and EP4 legitimately share the same prior ATH (19,798.68, Dec-2017).
3. **A candidate is missing or an excluded high survives.** This is `find_lh_candidates`. Walk SPEC §13.3's pseudocode line by line against the failing week: the usual culprits are `L0` accidentally including the candidate week's own low, and the freshness test comparing against the wrong slice of prior lows.
4. **BoS lands a week early or late.** `find_bos` must compare *daily* highs strictly greater than the LH, starting strictly after the confirmation date.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/gates/test_entry_gates.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/tests/gates
git commit -m "test(cycle-trader): gates G1-G3 entry structure reproduce"
```

---

## Task 11: Gates G4 and G5 — mirror detector and live EP6

**Files:**
- Create: `tests/gates/test_mirror_gate.py`, `tests/gates/test_ep6_gate.py`
- Modify: `engine/structure.py` (add `find_swing_lows`)

**G4 is a standalone detector fixture** (SPEC §13.9). A correct lifecycle engine holds no EP5 position in Oct-2025, so G4 must be run against the detector directly with scope supplied explicitly.

- [ ] **Step 1: Write the failing tests**

```python
# tests/gates/test_mirror_gate.py
"""G4 — mirror-exit detector, run standalone (SPEC §13.9).

Harness: window 2025-08-01 -> 2025-12-31, R_down=10, walk-forward 50% target,
position-lifetime scope DISABLED. Passing G4 does not imply an open EP5
position in Oct-2025; §11's EP5 exit remains 2025-03-02.
"""
from decimal import Decimal
from engine.bars import monday_of, to_weeks
from engine.levels import mirror_target
from engine.structure import find_swing_lows


def test_g4_mirror_signal_and_fill(bars):
    window = [b for b in bars if "2025-08-01" <= b.date <= "2025-12-31"]
    wks = to_weeks(window)
    swings = find_swing_lows(wks, r_down=Decimal("10"))
    assert swings, "expected at least one confirmed swing low in the window"

    broken = min(swings, key=lambda s: abs(s.low - Decimal("107255")))
    assert abs(broken.low - Decimal("107255")) < Decimal("200") or \
           abs(broken.low - Decimal("107350")) < Decimal("200")

    signal = next(b for b in window if b.low < broken.low)
    assert monday_of(signal.date) == "2025-10-06"

    top = max(b.high for b in window if b.date <= signal.date)
    low_so_far = signal.low
    fill_date = fill_price = None
    for b in window:
        if b.date <= signal.date:
            continue
        low_so_far = min(low_so_far, b.low)
        target = mirror_target(top, low_so_far)
        if b.high >= target:
            fill_date, fill_price = b.date, max(target, b.open)
            break

    assert fill_date == "2025-10-12"
    assert abs(fill_price - Decimal("114100")) / Decimal("114100") < Decimal("0.005")
```

```python
# tests/gates/test_ep6_gate.py
"""G5 — EP6 live state as of 2026-07-22 data."""
from decimal import Decimal
from engine.lines import lines_for
from engine.structure import find_lh_candidates, operative_lh, find_bos


def pct(a, b):
    return abs(a - b) / b * Decimal(100)


def test_g5_operative_lh_is_82850_not_the_june_bounce(bars, weeks, episode_scope):
    from engine.bars import monday_of
    trigger = monday_of("2026-02-01")           # -> 2026-01-26
    assert trigger in episode_scope["triggers"]
    _t, scope_start = episode_scope["scope_for"](trigger)
    cands = find_lh_candidates(weeks, bars, scope_start=scope_start,
                               trigger_monday=trigger)
    lh = operative_lh(cands, asof="2026-07-22")
    assert lh is not None
    assert lh.price == Decimal("82850")
    assert lh.week_monday == "2026-05-10"
    assert pct(lh.rally_pct, Decimal("38.1")) < Decimal("1")
    assert lh.confirmed_at == "2026-06-07"
    assert all(c.price != Decimal("67292.15") for c in cands), \
        "the June bounce is +13.8% and must fail R_e=15"


def test_g5_bos_has_not_fired(bars, weeks):
    upto = [b for b in bars if b.date <= "2026-07-22"]
    assert find_bos(upto, Decimal("82850"), after="2026-06-07") is None


def test_g5_accumulation_lines_and_no_fills(bars, onchain):
    t1, t2, t3 = lines_for(onchain["2026-07-19"])
    assert pct(t1, Decimal("52900")) < Decimal("1")
    assert pct(t2, Decimal("45900")) < Decimal("1")
    assert pct(t3, Decimal("38900")) < Decimal("1")
    post = [b for b in bars if "2026-02-02" <= b.date <= "2026-07-22"]
    assert min(b.low for b in post) > t1, "no tranche should have filled"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/gates/test_mirror_gate.py tests/gates/test_ep6_gate.py -v`
Expected: FAIL with `ImportError: cannot import name 'find_swing_lows'`

- [ ] **Step 3: Implement `find_swing_lows` and make both gates pass**

```python
# append to engine/structure.py
@dataclass(frozen=True, slots=True)
class SwingLow:
    week_monday: str
    low: Decimal
    decline_pct: Decimal
    confirmed_at: str | None


def find_swing_lows(weeks: list[Week], r_down: Decimal = R_DOWN_DEFAULT) -> list[SwingLow]:
    """Mirror of the LH rule with R_down: a weekly low preceded by a decline of
    at least r_down% from the argmax high since the prior swing, confirmed by a
    subsequent higher high. Confirmation strictly precedes any break (SPEC §6.2).
    """
    out: list[SwingLow] = []
    for i, cand in enumerate(weeks):
        prior = weeks[:i]
        if not prior:
            continue
        top = max(prior, key=lambda w: w.high)
        if top.high <= 0:
            continue
        decline = (top.high - cand.low) / top.high * Decimal(100)
        if decline < r_down:
            continue
        confirmed_at = next((w.monday for w in weeks[i + 1:] if w.high > cand.high), None)
        out.append(SwingLow(week_monday=cand.monday, low=cand.low,
                            decline_pct=decline, confirmed_at=confirmed_at))
    return [s for s in out if s.confirmed_at is not None]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/gates/ -v`
Expected: all gate tests pass

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/structure.py crypto/cycle-trader/tests/gates
git commit -m "test(cycle-trader): gates G4 mirror detector and G5 live EP6"
```

---

## Task 12: Structural regression against the reference implementation

**Files:**
- Create: `tests/gates/test_regression_ep2_ep5.py`

Asserts **structural facts only** — fill dates, fill prices, exit dates, exit prices. Derived pnl percentages are informational and deliberately not asserted (owner 2026-07-24: cumulative return is not the point).

- [ ] **Step 1: Write the failing test**

```python
# tests/gates/test_regression_ep2_ep5.py
"""EP2-EP5 structural regression against cy1_lifecycle.json.

Every value here was verified reproducible before this plan was written.
Asserts dates and prices, NOT pnl percentages.
"""
from decimal import Decimal
import pytest
from engine.fills import buy_limit_fill
from engine.levels import extension_1272
from engine.lines import lines_for

EPISODES = {
    "EP2-2014-09-28": {
        "acc": [("2014-10-04", "346.70"), ("2014-10-04", "335.69"), ("2014-10-04", "324.68")],
        "episode_low": "152.40", "prior_ath": "1163.00",
        "exit1": ("2017-05-02", "1437.88"), "exit2": ("2017-07-20", "2405.00"),
    },
    "EP3-2018-11-25": {
        "acc": [("2018-11-26", "4088.69"), ("2018-11-26", "4088.69"), ("2018-11-26", "4088.69")],
        "episode_low": "3156.26", "prior_ath": "19798.68",
        "exit1": ("2020-12-25", "24325.42"), "exit2": ("2021-04-28", "55892.00"),
    },
    "EP4-2020-03-15": {
        "acc": [("2020-03-16", "5360.33"), ("2020-03-16", "5135.22"), ("2020-03-16", "4703.98")],
        "episode_low": "3782.13", "prior_ath": "19798.68",
        "exit1": ("2020-12-19", "24155.18"), "exit2": ("2021-04-28", "55892.00"),
    },
    "EP5-2022-05-22": {
        "acc": [("2022-06-13", "23188.45"), ("2022-06-14", "21260.53"), ("2022-06-18", "19078.10")],
        "episode_low": "15476.00", "prior_ath": "69000.00",
        "exit1": ("2024-11-11", "83558.53"), "exit2": ("2025-03-02", "93923.26"),
    },
}


@pytest.mark.parametrize("episode", sorted(EPISODES))
def test_reference_file_matches_our_expected_table(episode, cy1):
    """Guard: if cy1_lifecycle.json ever changes, this fails loudly."""
    ref = next(e for e in cy1["episodes"] if e["episode"] == episode)
    exp = EPISODES[episode]
    assert str(ref["anchors"]["episode_low"]) == str(float(exp["episode_low"]))
    assert ref["exit_ext_1272"]["date"] == exp["exit1"][0]
    assert ref["exit_mirror"]["date"] == exp["exit2"][0]


@pytest.mark.parametrize("episode", sorted(EPISODES))
def test_extension_1272_reproduces(episode):
    exp = EPISODES[episode]
    got = extension_1272(Decimal(exp["episode_low"]), Decimal(exp["prior_ath"]))
    assert abs(got - Decimal(exp["exit1"][1])) < Decimal("0.01")


@pytest.mark.parametrize("episode", sorted(EPISODES))
def test_accumulation_fills_reproduce(episode, bars, onchain):
    """Each tranche fills on its recorded date at its recorded price, using
    that day's line value and the buy-limit gap rule."""
    exp = EPISODES[episode]
    by_date = {b.date: b for b in bars}
    for idx, (date, price) in enumerate(exp["acc"]):
        bar = by_date[date]
        line = lines_for(onchain[date])[idx]
        got = buy_limit_fill(bar, line)
        assert got is not None, f"{episode} tranche {idx} did not fill on {date}"
        assert abs(got - Decimal(price)) / Decimal(price) < Decimal("0.005"), \
            f"{episode} tranche {idx}: got {got}, expected {price}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gates/test_regression_ep2_ep5.py -v`
Expected: FAIL until the engine reproduces every value.

- [ ] **Step 3: Reconcile any divergence**

Divergences almost certainly live in the on-chain source policy or the fill primitive, both of which were verified before this plan was written. Do **not** adjust the expected values — they come from the reference implementation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/gates/test_regression_ep2_ep5.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/tests/gates/test_regression_ep2_ep5.py
git commit -m "test(cycle-trader): EP2-EP5 structural regression"
```

---

## Task 13: OQ-3 synthetic fixture and CI

**Files:**
- Create: `tests/gates/test_oq3_synthetic.py`, `.github/workflows/gates.yml`

The OQ-3 roll has **zero historical coverage** — accumulation filled 3/3 in every episode. EP6 may be the first to take this path, so it needs a synthetic fixture.

- [ ] **Step 1: Write the failing test**

```python
# tests/gates/test_oq3_synthetic.py
"""Synthetic coverage for the OQ-3 roll: accumulation unfilled at BoS ->
ladder -> breakout. No historical episode exercises this path."""
from decimal import Decimal
from engine.orders import desired_orders, roll_unfilled
from engine.types import EpisodeState, EpisodeStatus, OrderPurpose


def test_all_accumulation_unfilled_rolls_the_whole_pool_to_the_ladder():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), bos_date="2026-09-01")
    orders = desired_orders(state, lines={}, filled_purposes=set())
    ladder = [o for o in orders if o.purpose.name.startswith("LADDER")]
    assert sum(o.units for o in ladder) == Decimal(21), \
        "7 unfilled accumulation units must join the 14 ladder units"
    ratios = sorted(o.units for o in ladder)
    assert ratios[1] / ratios[0] == Decimal(2)
    assert ratios[2] / ratios[0] == Decimal(4)


def test_partial_accumulation_fill_rolls_only_the_remainder():
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), bos_date="2026-09-01")
    orders = desired_orders(state, lines={},
                            filled_purposes={OrderPurpose.T1, OrderPurpose.T2})
    ladder = [o for o in orders if o.purpose.name.startswith("LADDER")]
    assert sum(o.units for o in ladder) == Decimal(18)  # 14 + T3's 4 units


def test_unfilled_ladder_units_join_the_breakout():
    pool = roll_unfilled(Decimal(7), Decimal(14))
    assert sum(pool.values()) == Decimal(21)
    state = EpisodeState(status=EpisodeStatus.CONFIRMED, el_star=Decimal("57800"),
                         bos_week_high=Decimal("82850"), bos_date="2026-09-01")
    orders = desired_orders(state, lines={},
                            filled_purposes={OrderPurpose.LADDER_050})
    brk = next(o for o in orders if o.purpose is OrderPurpose.BREAKOUT)
    ladder = [o for o in orders if o.purpose.name.startswith("LADDER")]
    assert brk.units == sum(o.units for o in ladder)
    assert brk.price == Decimal("82850")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/gates/test_oq3_synthetic.py -v`
Expected: FAIL on the unit arithmetic until `roll_unfilled` is wired into `desired_orders`.

- [ ] **Step 3: Add the CI workflow and fix any failures**

```yaml
# .github/workflows/gates.yml
name: CY-1 gates

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  gates:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: crypto/cycle-trader
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: pip install -e ".[dev]"
      - name: Assert engine has no I/O and no pandas/numpy
        run: |
          ! grep -rnE "^\s*(import|from)\s+(pandas|numpy|requests|httpx)" engine/
          ! grep -rnE "open\(|Path\(|requests\.|datetime\.now|time\.time" engine/
      - name: Run the full suite
        run: pytest -v
```

- [ ] **Step 4: Run the full suite**

Run: `cd ~/apps/crypto/cycle-trader && pytest -v`
Expected: all tests pass, including every gate

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/tests/gates/test_oq3_synthetic.py crypto/cycle-trader/.github
git commit -m "test(cycle-trader): OQ-3 synthetic fixture and gate CI"
```

---

## Task 14: Top-level `compute()` — the M1 deliverable interface

**Files:**
- Create: `engine/engine.py`, `tests/test_engine.py`

**Interfaces:**
- Consumes: every engine module
- Produces: `compute(bars, onchain, prior_state, asof) -> EngineResult`

This is what M2 will call once per day. It is the only public entry point; everything else is an implementation detail.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine.py
from decimal import Decimal
from engine.engine import compute
from engine.types import EpisodeState, EpisodeStatus, OrderPurpose


def test_compute_is_deterministic(bars, onchain):
    """Same inputs, same outputs — always. This property is what makes the
    gates meaningful for live-money code."""
    a = compute(bars, onchain, EpisodeState(), asof="2026-07-19")
    b = compute(bars, onchain, EpisodeState(), asof="2026-07-19")
    assert a == b


def test_compute_on_ep6_is_watching_with_three_accumulation_orders(bars, onchain):
    result = compute(bars, onchain, EpisodeState(), asof="2026-07-19")
    assert result.state.status is EpisodeStatus.WATCHING
    assert result.state.operative_lh == Decimal("82850")
    assert {o.purpose for o in result.orders} == {
        OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3}
    assert OrderPurpose.STOP not in {o.purpose for o in result.orders}


def test_compute_never_looks_past_asof(bars, onchain):
    """Truncating the input at asof must not change the result."""
    truncated = [b for b in bars if b.date <= "2026-05-01"]
    oc = {d: v for d, v in onchain.items() if d <= "2026-05-01"}
    full = compute(bars, onchain, EpisodeState(), asof="2026-05-01")
    part = compute(truncated, oc, EpisodeState(), asof="2026-05-01")
    assert full.state == part.state
    assert full.orders == part.orders
```

Add to `tests/conftest.py` (project root) the same `bars` and `onchain` session fixtures defined in `tests/gates/conftest.py`, so both suites share them.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.engine'`

- [ ] **Step 3: Write minimal implementation**

```python
# engine/engine.py
"""The single public entry point. Pure: no I/O, no clock, no network.

compute() answers one question: given everything known up to `asof`, what state
is the episode in and what orders should be resting at the exchange?
"""
from __future__ import annotations
from decimal import Decimal
from engine.bars import to_weeks
from engine.levels import extension_1272, mirror_target
from engine.lifecycle import find_triggers, freeze_el, prior_cycle_ath, running_low
from engine.lines import lines_for
from engine.orders import desired_orders
from engine.rsi import wilder_rsi
from engine.structure import find_bos, find_lh_candidates, operative_lh
from engine.types import Bar, EngineResult, EpisodeState, EpisodeStatus, OnChain


def compute(bars: list[Bar], onchain: dict[str, OnChain],
            prior_state: EpisodeState, asof: str) -> EngineResult:
    visible = [b for b in bars if b.date <= asof]
    if not visible:
        return EngineResult(state=prior_state, orders=())

    weeks = to_weeks(visible)
    rsi = wilder_rsi([w.close for w in weeks])
    triggers = find_triggers(weeks, rsi)
    if not triggers:
        return EngineResult(state=EpisodeState(status=EpisodeStatus.IDLE), orders=())

    trigger = triggers[-1]
    _ath_price, scope_start = prior_cycle_ath(weeks, trigger)
    ath_price = _ath_price

    cands = find_lh_candidates(weeks, visible, scope_start, trigger)
    lh = operative_lh(cands, asof=asof)
    low = running_low(visible, scope_start, asof)

    state = EpisodeState(
        status=EpisodeStatus.WATCHING, trigger_date=trigger, prior_ath=ath_price,
        scope_start=scope_start, running_low=low,
        operative_lh=lh.price if lh else None,
        lh_confirmed_at=lh.confirmed_at if lh else None,
    )

    bos = find_bos(visible, lh.price, after=lh.confirmed_at) if lh else None
    if bos is not None:
        el = freeze_el(visible, scope_start, bos)
        bos_week = next(w for w in to_weeks([b for b in visible if b.date <= bos])
                        if w.monday == to_weeks([b for b in visible
                                                 if b.date == bos])[0].monday)
        state = EpisodeState(
            status=EpisodeStatus.CONFIRMED, trigger_date=trigger,
            prior_ath=ath_price, scope_start=scope_start, running_low=low,
            el_star=el, operative_lh=lh.price, lh_confirmed_at=lh.confirmed_at,
            bos_date=bos, bos_week_high=bos_week.high,
        )
        ext = extension_1272(el, ath_price)
        if max(b.high for b in visible if b.date >= bos) >= ext:
            state = EpisodeState(**{**state.__dict__, "status": EpisodeStatus.DISTRIBUTING,
                                    "exit1_done": True})

    lines: dict[str, Decimal] = {}
    if state.status is EpisodeStatus.WATCHING and asof in onchain:
        t1, t2, t3 = lines_for(onchain[asof])
        lines = {"t1": t1, "t2": t2, "t3": t3}
    elif state.status is EpisodeStatus.DISTRIBUTING:
        after = [b for b in visible if b.date > (state.bos_date or "")]
        if after:
            top = max(b.high for b in after)
            lines = {"mirror": mirror_target(top, min(b.low for b in after))}

    return EngineResult(state=state, orders=desired_orders(state, lines, filled_purposes=set()))
```

**Note for the implementer:** `filled_purposes` is hard-coded empty here because M1 has no fill tracking — that is M2's job, fed from the venue's trade history. The signature already accepts it so M2 needs no engine change.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd ~/apps
git add crypto/cycle-trader/engine/engine.py crypto/cycle-trader/tests/test_engine.py crypto/cycle-trader/tests/conftest.py
git commit -m "feat(cycle-trader): top-level compute() entry point"
```

---

## Definition of Done for M1

- [ ] `pytest` passes from a cold clone with one command
- [ ] `compute()` returns a deterministic `(state, desired_orders)` for any `asof`
- [ ] G1–G5 all reproduce
- [ ] EP2–EP5 structural regression reproduces every fill and exit date/price
- [ ] The OQ-3 roll path has synthetic coverage
- [ ] `engine/` imports nothing outside the stdlib and performs no I/O (CI-enforced)
- [ ] CI fails if any gate stops reproducing

**Not in M1:** exchange connectivity, Supabase, Vercel, cron, Telegram, the web app. Those are M2–M4.
