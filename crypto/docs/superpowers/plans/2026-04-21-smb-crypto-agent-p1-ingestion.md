# SMB Crypto Agent — Plan 1: Repo Scaffolding + Ingestion Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the `smb-crypto-agent` repo and run the three-phase ingestion that converts 1,698 SMB YouTube transcripts into a structured crypto-trading knowledge base plus per-setup strategy scaffolding.

**Architecture:** Python 3.12 project at `~/apps/crypto/smb-crypto-agent/`. Ingestion is Claude-orchestrated: support scripts (batch planner, JSONL validator, scaffolder) are unit-tested Python; the actual subagent dispatch happens from the Claude session via the `Agent` tool. Phase 1 fans ~35 subagents out (full transcript read → structured JSONL), Phase 2 fans ~15-20 category-synthesis subagents out (JSONL → distilled setup markdown), Phase 3 scaffolds `strategies/<setup>/` directories for every high/med-confidence setup.

**Tech Stack:** Python 3.12 (venv at `~/venvs/oefr/`), pytest, pydantic for schema validation, sqlite (stdlib), JSONL for ingestion artifacts.

**Source spec:** `/home/oghenetejiri/apps/crypto/docs/superpowers/specs/2026-04-21-smb-crypto-agent-design.md`

---

## File Structure Produced By This Plan

```
~/apps/crypto/smb-crypto-agent/
├── CLAUDE.md                           # T1
├── README.md                           # T1
├── .env.example                        # T1
├── .gitignore                          # T1
├── requirements.txt                    # T1
├── pyproject.toml                      # T1
├── config/
│   ├── runtime.json                    # T2
│   ├── allocation.json                 # T2
│   └── risk.json                       # T2
├── ingestion/
│   ├── __init__.py                     # T3
│   ├── taxonomy.md                     # T3
│   ├── schema.py                       # T4  (pydantic models for JSONL)
│   ├── planner.py                      # T5  (batch sharding)
│   ├── validator.py                    # T6  (JSONL schema validation)
│   ├── synthesize.py                   # T7  (phase-2 helper: groups rows by category)
│   ├── scaffold_strategies.py          # T8  (phase-3 scaffolder)
│   ├── manifest.jsonl                  # Phase-1 output (T10)
│   ├── summaries.jsonl                 # Phase-1 output (T10)
│   └── sources.txt                     # T3 (index of transcript filenames)
├── knowledge_base/
│   ├── INDEX.md                        # T11
│   ├── principles/                     # populated T11
│   ├── setups/                         # populated T11
│   └── context/                        # populated T11
├── strategies/                         # populated T12
├── db/
│   └── .gitkeep                        # T1
├── scripts/
│   └── init_db.py                      # T9
├── tests/
│   ├── __init__.py                     # T4
│   ├── test_schema.py                  # T4
│   ├── test_planner.py                 # T5
│   └── test_validator.py               # T6
├── logs/.gitkeep                       # T1
└── status/.gitkeep                     # T1
```

---

## Task 1: Initialize repo skeleton

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/CLAUDE.md`
- Create: `~/apps/crypto/smb-crypto-agent/README.md`
- Create: `~/apps/crypto/smb-crypto-agent/.env.example`
- Create: `~/apps/crypto/smb-crypto-agent/.gitignore`
- Create: `~/apps/crypto/smb-crypto-agent/requirements.txt`
- Create: `~/apps/crypto/smb-crypto-agent/pyproject.toml`
- Create: `~/apps/crypto/smb-crypto-agent/{db,logs,status,tests,knowledge_base/principles,knowledge_base/setups,knowledge_base/context,strategies,scripts,ingestion,core,core/venues,core/data}/.gitkeep`

- [ ] **Step 1: Create all directories**

```bash
cd ~/apps/crypto
mkdir -p smb-crypto-agent/{config,ingestion,knowledge_base/{principles,setups,context},strategies,core/{venues,data},db,scripts,tests,logs,status}
touch smb-crypto-agent/{db,logs,status,knowledge_base/principles,knowledge_base/setups,knowledge_base/context,strategies,core/venues,core/data}/.gitkeep
```

- [ ] **Step 2: Write `CLAUDE.md`**

```markdown
# CLAUDE.md

Guidance for Claude Code working in `smb-crypto-agent`.

## What This Is

Crypto-native autonomous trading agent. Playbook distilled from 1,698 SMB Capital YouTube transcripts. Trades Hyperliquid (perps, some spot) and Binance (spot + USDⓈ-M futures). Options content from the source corpus is out of scope.

## Architecture Rules

- **Mode read from `config/runtime.json`** — never hardcode `dry_run`.
- **Every entry gates through `core/risk_coordinator.py`** — strategies never place orders without `risk_coordinator.can_enter()` passing first.
- **Capital sizing comes from `core/allocator.py`** which reads `config/allocation.json`. No hard-coded percent-of-equity in strategy code.
- **One DB** at `db/research.db`.
- **Paper mode executes the full stack** (detection, judge call, risk, allocator, DB writes) and only substitutes `venue.place_order` with a JSONL log append.
- **Secrets live in `.env`** inside this directory — never `~/.profile`.

## Commands

```bash
source ~/venvs/oefr/bin/activate
pytest tests/ -v
python scripts/init_db.py
```

## Ingestion

See `ingestion/` for the three-phase pipeline that populates `knowledge_base/` from `~/apps/SMB_youtube_transcripts/`. Phase 1 emits per-transcript structured summaries; Phase 2 synthesizes category playbooks; Phase 3 scaffolds `strategies/<setup>/`.
```

- [ ] **Step 3: Write `README.md`**

```markdown
# smb-crypto-agent

Crypto-native autonomous trading agent. Strategies adapted from 1,698 SMB Capital YouTube transcripts, applied to Hyperliquid and Binance (spot + perps).

## Setup

```bash
cd ~/apps/crypto/smb-crypto-agent
source ~/venvs/oefr/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in
python scripts/init_db.py
```

## Layout

- `ingestion/` — pipeline that converts transcripts → knowledge base
- `knowledge_base/` — distilled setups (`setups/`), principles, and context
- `strategies/<setup>/` — one directory per runnable setup
- `core/` — venues, judge, risk coordinator, allocator, indicators
- `scripts/` — orchestrator, backtester, daily digest
```

- [ ] **Step 4: Write `.env.example`**

```bash
# Hyperliquid
HL_ACCOUNT_ADDRESS=
HL_SECRET_KEY=

# Binance
BINANCE_SPOT_API_KEY=
BINANCE_SPOT_API_SECRET=
BINANCE_FUTURES_API_KEY=
BINANCE_FUTURES_API_SECRET=

# Live-mode gate (set to 'yes' only when ready)
SMB_LIVE_CONFIRMED=no

# Telegram (for daily digest)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

- [ ] **Step 5: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.venv/
.env
db/*.db
db/*.db-journal
logs/*.log
logs/*.jsonl
status/*.lock
ingestion/manifest.jsonl
ingestion/summaries.jsonl
!**/.gitkeep
```

- [ ] **Step 6: Write `requirements.txt`**

```
pydantic>=2.5
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27
websockets>=12.0
pandas>=2.2
numpy>=1.26
python-dotenv>=1.0
anthropic>=0.40
```

- [ ] **Step 7: Write `pyproject.toml`**

```toml
[project]
name = "smb-crypto-agent"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 110
target-version = "py312"
```

- [ ] **Step 8: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent
git commit -m "feat(smb-crypto-agent): scaffold repo skeleton

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Write config files with production defaults

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/config/runtime.json`
- Create: `~/apps/crypto/smb-crypto-agent/config/allocation.json`
- Create: `~/apps/crypto/smb-crypto-agent/config/risk.json`

- [ ] **Step 1: Write `config/runtime.json`**

```json
{
  "mode": "paper",
  "venues_enabled": {
    "hyperliquid": true,
    "binance_spot": true,
    "binance_futures": true
  },
  "pairs": {
    "hyperliquid": ["BTC", "ETH", "SOL", "HYPE"],
    "binance_spot": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "binance_futures": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
  },
  "cycle_interval_seconds": {
    "scalp": 60,
    "intraday": 300,
    "swing": 900
  },
  "judge_model": "claude-sonnet-4-6",
  "daily_digest_utc_hour": 9
}
```

- [ ] **Step 2: Write `config/allocation.json`**

```json
{
  "total_equity_usdt": 10000,
  "per_venue": {
    "hyperliquid": 0.50,
    "binance_spot": 0.30,
    "binance_futures": 0.20
  },
  "per_strategy_default_pct": 0.10,
  "per_strategy_overrides": {},
  "max_leverage": {
    "hyperliquid": 3.0,
    "binance_futures": 2.0,
    "binance_spot": 1.0
  },
  "min_notional_usdt": 25
}
```

- [ ] **Step 3: Write `config/risk.json`**

```json
{
  "daily_realized_loss_cap_pct": 3.0,
  "account_drawdown_cap_pct": 15.0,
  "per_venue_max_exposure_pct": 60.0,
  "per_strategy_max_exposure_pct": 25.0,
  "per_symbol_max_position_pct": 20.0,
  "correlation_cap": {
    "max_long_beta_positions": 4,
    "beta_reference": "BTC"
  },
  "funding_guardrail": {
    "skip_perp_entry_if_funding_annualized_against_pct": 50.0
  }
}
```

- [ ] **Step 4: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/config/
git commit -m "feat(smb-crypto-agent): production config defaults

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Write taxonomy and source index

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/__init__.py` (empty)
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/taxonomy.md`
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/sources.txt`

- [ ] **Step 1: Create `ingestion/__init__.py`** (empty file)

```python
```

- [ ] **Step 2: Write `ingestion/taxonomy.md`**

```markdown
# Controlled Vocabulary — Ingestion Taxonomy

Subagents MUST use these category tags. Do not invent new tags. If a transcript fits no tag, use `other` and explain in `skip_reason`.

## Setup categories (tradeable)

- `breaking_news` — trade an economic print, data release, or news catalyst at the moment of release
- `trend_day_continuation` — recognize a trend day, hold for higher highs, fade counter-moves
- `pullback_in_uptrend` — buy a controlled retrace in an established uptrend (2nd day continuation, etc.)
- `second_chance_retest` — missed the breakout, take the retest of the breakout level
- `fashionably_late` — join a confirmed, mature trend
- `imbalance_scalp` — small tactical scalp into a price imbalance / gap fill
- `relative_strength` — pick the strongest-in-basket when market moves
- `fade_the_extended` — fade a move that has extended beyond ATR / prior range
- `opening_range_breakout` — break of a defined early-session range
- `liquidity_sweep` — stop hunt / liquidity grab, fade the reversal
- `basket_execution` — execution technique (not a setup itself but adjacent)

## Principle categories (not tradeable setups, but rules to consume)

- `game_planning` — pre-session scenario planning and trade preparation
- `risk_management` — sizing, stops, drawdown discipline
- `trade_review` — post-trade / post-session review discipline
- `trader_development` — career, process, psychology advice (usually low tactical score)

## Equity-only categories (use `equity_only: true`)

- `options_expression` — option-specific expression of a trade
- `earnings_trade` — equity earnings-release plays
- `ipo_lockup` — IPO, lockup, secondary offering plays
- `short_interest` — equity-specific short interest / squeeze plays

## Other

- `other` — use only when no tag above fits; explain in `skip_reason`
```

- [ ] **Step 3: Write `ingestion/sources.txt`** (pipe generated listing)

```bash
cd /home/oghenetejiri/apps/SMB_youtube_transcripts
ls *.transcript.md > /home/oghenetejiri/apps/crypto/smb-crypto-agent/ingestion/sources.txt
wc -l /home/oghenetejiri/apps/crypto/smb-crypto-agent/ingestion/sources.txt
```

Expected: 1698 lines.

- [ ] **Step 4: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/ingestion/
git commit -m "feat(smb-crypto-agent): ingestion taxonomy and source index

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Pydantic schema for JSONL rows (TDD)

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/schema.py`
- Create: `~/apps/crypto/smb-crypto-agent/tests/__init__.py` (empty)
- Create: `~/apps/crypto/smb-crypto-agent/tests/test_schema.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_schema.py
import pytest
from pydantic import ValidationError
from ingestion.schema import Setup, TranscriptSummary, VALID_CATEGORIES, VALID_TIMEFRAMES, VALID_CONFIDENCE


def test_valid_setup_parses():
    s = Setup(
        name="Breaking News Long",
        preconditions="Major macro print due; game plan prepared",
        entry_trigger="Buy on confirmed direction 1-3 minutes post-release",
        invalidation="Price closes back through release range mid",
        targets="1R and trail remainder",
        timeframe="intraday",
        confidence="high",
        crypto_adaptation_notes="CPI/FOMC apply; also ETF flow prints, unlock events",
        quotes=["breaking news trade", "pay for the trade"]
    )
    assert s.confidence == "high"


def test_timeframe_must_be_valid():
    with pytest.raises(ValidationError):
        Setup(
            name="X", preconditions="y", entry_trigger="y", invalidation="y",
            targets="y", timeframe="hourly", confidence="high",
            crypto_adaptation_notes="", quotes=[],
        )


def test_confidence_must_be_valid():
    with pytest.raises(ValidationError):
        Setup(
            name="X", preconditions="y", entry_trigger="y", invalidation="y",
            targets="y", timeframe="intraday", confidence="maybe",
            crypto_adaptation_notes="", quotes=[],
        )


def test_valid_summary_parses():
    t = TranscriptSummary(
        file="Example_Video.transcript.md",
        video_id="abc123",
        title="Example",
        categories=["breaking_news", "risk_management"],
        equity_only=False,
        crypto_translatable=True,
        tactical_score=4,
        setups=[],
        principles=["Always pre-plan"],
        skip_reason=None,
    )
    assert t.tactical_score == 4


def test_category_must_be_in_vocab():
    with pytest.raises(ValidationError):
        TranscriptSummary(
            file="x.md", video_id="", title="",
            categories=["made_up_tag"],
            equity_only=False, crypto_translatable=True,
            tactical_score=0, setups=[], principles=[], skip_reason=None,
        )


def test_tactical_score_bounds():
    with pytest.raises(ValidationError):
        TranscriptSummary(
            file="x.md", video_id="", title="",
            categories=[], equity_only=False, crypto_translatable=True,
            tactical_score=6, setups=[], principles=[], skip_reason=None,
        )


def test_vocab_constants_populated():
    assert "breaking_news" in VALID_CATEGORIES
    assert "intraday" in VALID_TIMEFRAMES
    assert "high" in VALID_CONFIDENCE
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/apps/crypto/smb-crypto-agent
source ~/venvs/oefr/bin/activate
python -m pytest tests/test_schema.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.schema'`.

- [ ] **Step 3: Write `ingestion/schema.py`**

```python
# ingestion/schema.py
from typing import Literal
from pydantic import BaseModel, Field, field_validator

VALID_CATEGORIES: set[str] = {
    "breaking_news",
    "trend_day_continuation",
    "pullback_in_uptrend",
    "second_chance_retest",
    "fashionably_late",
    "imbalance_scalp",
    "relative_strength",
    "fade_the_extended",
    "opening_range_breakout",
    "liquidity_sweep",
    "basket_execution",
    "game_planning",
    "risk_management",
    "trade_review",
    "trader_development",
    "options_expression",
    "earnings_trade",
    "ipo_lockup",
    "short_interest",
    "other",
}

VALID_TIMEFRAMES: set[str] = {"scalp", "intraday", "swing"}
VALID_CONFIDENCE: set[str] = {"high", "med", "low"}


class Setup(BaseModel):
    name: str
    preconditions: str
    entry_trigger: str
    invalidation: str
    targets: str
    timeframe: Literal["scalp", "intraday", "swing"]
    confidence: Literal["high", "med", "low"]
    crypto_adaptation_notes: str
    quotes: list[str] = Field(default_factory=list)


class TranscriptSummary(BaseModel):
    file: str
    video_id: str
    title: str
    categories: list[str]
    equity_only: bool
    crypto_translatable: bool
    tactical_score: int = Field(ge=0, le=5)
    setups: list[Setup] = Field(default_factory=list)
    principles: list[str] = Field(default_factory=list)
    skip_reason: str | None = None

    @field_validator("categories")
    @classmethod
    def _validate_categories(cls, v: list[str]) -> list[str]:
        unknown = [c for c in v if c not in VALID_CATEGORIES]
        if unknown:
            raise ValueError(f"Unknown categories: {unknown}")
        return v
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_schema.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/ingestion/schema.py crypto/smb-crypto-agent/tests/
git commit -m "feat(smb-crypto-agent): pydantic schema for transcript summaries

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Batch planner (TDD)

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/planner.py`
- Create: `~/apps/crypto/smb-crypto-agent/tests/test_planner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_planner.py
from ingestion.planner import plan_batches, Batch


def test_plan_batches_evenly():
    files = [f"f{i}.md" for i in range(100)]
    batches = plan_batches(files, batch_size=25)
    assert len(batches) == 4
    assert all(len(b.files) == 25 for b in batches)


def test_plan_batches_trailing_remainder():
    files = [f"f{i}.md" for i in range(1698)]
    batches = plan_batches(files, batch_size=50)
    assert len(batches) == 34
    assert sum(len(b.files) for b in batches) == 1698
    assert len(batches[-1].files) == 48


def test_batch_ids_are_zero_padded_and_ordered():
    files = [f"f{i}.md" for i in range(5)]
    batches = plan_batches(files, batch_size=2)
    ids = [b.batch_id for b in batches]
    assert ids == ["b000", "b001", "b002"]


def test_empty_input_returns_empty_list():
    assert plan_batches([], batch_size=50) == []


def test_batch_size_must_be_positive():
    import pytest
    with pytest.raises(ValueError):
        plan_batches(["a"], batch_size=0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_planner.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.planner'`.

- [ ] **Step 3: Write `ingestion/planner.py`**

```python
# ingestion/planner.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Batch:
    batch_id: str
    files: tuple[str, ...]


def plan_batches(files: list[str], batch_size: int) -> list[Batch]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    batches: list[Batch] = []
    for i in range(0, len(files), batch_size):
        chunk = tuple(files[i : i + batch_size])
        batches.append(Batch(batch_id=f"b{len(batches):03d}", files=chunk))
    return batches
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_planner.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/ingestion/planner.py crypto/smb-crypto-agent/tests/test_planner.py
git commit -m "feat(smb-crypto-agent): transcript batch planner

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: JSONL validator (TDD)

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/validator.py`
- Create: `~/apps/crypto/smb-crypto-agent/tests/test_validator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_validator.py
import json
import pytest
from ingestion.validator import validate_summaries_jsonl, ValidationReport


def _write(tmp_path, lines: list[str]):
    p = tmp_path / "summaries.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


def _good_row(file="x.md"):
    return {
        "file": file, "video_id": "", "title": "",
        "categories": ["risk_management"], "equity_only": False,
        "crypto_translatable": True, "tactical_score": 2,
        "setups": [], "principles": ["be disciplined"], "skip_reason": None,
    }


def test_all_rows_valid(tmp_path):
    p = _write(tmp_path, [json.dumps(_good_row("a.md")), json.dumps(_good_row("b.md"))])
    rep = validate_summaries_jsonl(p, expected_files={"a.md", "b.md"})
    assert rep.ok
    assert rep.row_count == 2
    assert rep.missing_files == set()
    assert rep.errors == []


def test_detects_missing_files(tmp_path):
    p = _write(tmp_path, [json.dumps(_good_row("a.md"))])
    rep = validate_summaries_jsonl(p, expected_files={"a.md", "b.md"})
    assert not rep.ok
    assert "b.md" in rep.missing_files


def test_detects_schema_errors(tmp_path):
    bad = _good_row()
    bad["tactical_score"] = 99
    p = _write(tmp_path, [json.dumps(bad)])
    rep = validate_summaries_jsonl(p, expected_files={"x.md"})
    assert not rep.ok
    assert any("tactical_score" in e for e in rep.errors)


def test_detects_duplicate_files(tmp_path):
    p = _write(tmp_path, [json.dumps(_good_row("a.md")), json.dumps(_good_row("a.md"))])
    rep = validate_summaries_jsonl(p, expected_files={"a.md"})
    assert not rep.ok
    assert rep.duplicate_files == {"a.md"}


def test_malformed_json_line(tmp_path):
    p = tmp_path / "summaries.jsonl"
    p.write_text(json.dumps(_good_row()) + "\n" + "{not json}\n")
    rep = validate_summaries_jsonl(p, expected_files={"x.md"})
    assert not rep.ok
    assert any("json" in e.lower() for e in rep.errors)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_validator.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion.validator'`.

- [ ] **Step 3: Write `ingestion/validator.py`**

```python
# ingestion/validator.py
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from ingestion.schema import TranscriptSummary


@dataclass
class ValidationReport:
    row_count: int = 0
    missing_files: set[str] = field(default_factory=set)
    duplicate_files: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_files and not self.duplicate_files and not self.errors


def validate_summaries_jsonl(path: Path, expected_files: set[str]) -> ValidationReport:
    rep = ValidationReport()
    seen: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                rep.errors.append(f"line {line_no}: invalid json: {e}")
                continue
            try:
                row = TranscriptSummary(**data)
            except ValidationError as e:
                rep.errors.append(f"line {line_no}: {e}")
                continue
            rep.row_count += 1
            if row.file in seen:
                rep.duplicate_files.add(row.file)
            seen.add(row.file)
    rep.missing_files = expected_files - seen
    return rep
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_validator.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/ingestion/validator.py crypto/smb-crypto-agent/tests/test_validator.py
git commit -m "feat(smb-crypto-agent): JSONL schema validator for summaries

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Phase-2 synthesis helper

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/synthesize.py`

No TDD — this is a pure grouping helper over already-validated data. Kept minimal; the synthesis *content* comes from Claude subagents in Task 11, this module just slices JSONL by category.

- [ ] **Step 1: Write `ingestion/synthesize.py`**

```python
# ingestion/synthesize.py
"""
Phase-2 synthesis helper.

Groups validated transcript summaries by category so a subagent can be dispatched
per category cluster. Each group contains the full summary rows plus all extracted
setups tagged with that category.
"""
import json
from collections import defaultdict
from pathlib import Path

from ingestion.schema import TranscriptSummary


def load_summaries(path: Path) -> list[TranscriptSummary]:
    rows: list[TranscriptSummary] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(TranscriptSummary(**json.loads(line)))
    return rows


def group_by_category(rows: list[TranscriptSummary]) -> dict[str, list[TranscriptSummary]]:
    groups: dict[str, list[TranscriptSummary]] = defaultdict(list)
    for row in rows:
        for cat in row.categories:
            groups[cat].append(row)
    return dict(groups)


def tactical_rows(rows: list[TranscriptSummary], min_score: int = 3) -> list[TranscriptSummary]:
    return [r for r in rows if r.tactical_score >= min_score and not r.equity_only]


def write_cluster_files(groups: dict[str, list[TranscriptSummary]], out_dir: Path) -> list[Path]:
    """Write each category's rows to a JSONL file under out_dir for subagent input."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for cat, rows in groups.items():
        p = out_dir / f"cluster_{cat}.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(r.model_dump_json() + "\n")
        written.append(p)
    return written
```

- [ ] **Step 2: Smoke test by import**

```bash
python -c "from ingestion.synthesize import group_by_category, tactical_rows, write_cluster_files; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/ingestion/synthesize.py
git commit -m "feat(smb-crypto-agent): phase-2 category synthesis helper

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Phase-3 strategy scaffolder

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/ingestion/scaffold_strategies.py`

This is a mechanical scaffolder — walks `knowledge_base/setups/*.md`, parses the header block, and creates `strategies/<slug>/` with detector stub, playbook copy, and bot stub for each setup whose confidence is `high` or `med`.

- [ ] **Step 1: Write `ingestion/scaffold_strategies.py`**

```python
# ingestion/scaffold_strategies.py
"""
Phase-3: scaffold strategies/<slug>/ directories for every high/med-confidence
setup found in knowledge_base/setups/.

Reads each setup markdown file, parses the header line containing
`**Category:** X  **Timeframe:** Y  **Confidence:** Z  **Venues:** ...`,
and creates a strategy dir with detector stub + playbook copy + bot stub.
"""
import re
import shutil
from pathlib import Path


SETUP_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base" / "setups"
STRATEGIES_ROOT = Path(__file__).resolve().parent.parent / "strategies"

HEADER_RE = re.compile(
    r"\*\*Category:\*\*\s*(?P<category>[\w_]+)\s+"
    r"\*\*Timeframe:\*\*\s*(?P<timeframe>\w+)\s+"
    r"\*\*Confidence:\*\*\s*(?P<confidence>\w+)\s+"
    r"\*\*Venues:\*\*\s*(?P<venues>.+)"
)


def slugify(path: Path) -> str:
    return path.stem.lower().replace(" ", "_")


def parse_header(text: str) -> dict[str, str] | None:
    for line in text.splitlines():
        m = HEADER_RE.search(line)
        if m:
            return m.groupdict()
    return None


def scaffold_one(setup_md: Path) -> Path | None:
    text = setup_md.read_text(encoding="utf-8")
    header = parse_header(text)
    if not header:
        return None
    if header["confidence"].lower() not in {"high", "med"}:
        return None
    slug = slugify(setup_md)
    dest = STRATEGIES_ROOT / slug
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(setup_md, dest / "playbook.md")
    (dest / "detector.py").write_text(_detector_stub(slug, header), encoding="utf-8")
    (dest / "bot.py").write_text(_bot_stub(slug), encoding="utf-8")
    (dest / "__init__.py").write_text("", encoding="utf-8")
    return dest


def _detector_stub(slug: str, header: dict[str, str]) -> str:
    return f'''"""
Detector for {slug}.
Category: {header['category']}   Timeframe: {header['timeframe']}   Confidence: {header['confidence']}
Venues: {header['venues']}

NOT IMPLEMENTED. Implement `find_candidates` so it emits dict candidates consumed by
`core/judge.py`. See playbook.md in this directory for the distilled rules.
"""
from dataclasses import dataclass


@dataclass
class Candidate:
    symbol: str
    venue: str
    direction: str
    setup: str
    features: dict


def find_candidates(market_ctx) -> list[Candidate]:
    raise NotImplementedError("implement detector from playbook.md")
'''


def _bot_stub(slug: str) -> str:
    return f'''"""
Runner for {slug}. Wires detector -> risk -> judge -> allocator -> venue.
Implementation arrives in Plan 2/3.
"""


def run_once():
    raise NotImplementedError
'''


def scaffold_all() -> list[Path]:
    created: list[Path] = []
    for md in sorted(SETUP_ROOT.glob("*.md")):
        dest = scaffold_one(md)
        if dest:
            created.append(dest)
    return created


if __name__ == "__main__":
    for d in scaffold_all():
        print(f"scaffolded {d}")
```

- [ ] **Step 2: Smoke test**

```bash
python -c "from ingestion.scaffold_strategies import parse_header, slugify; print(parse_header('**Category:** breaking_news  **Timeframe:** intraday  **Confidence:** high  **Venues:** HL perps'))"
```

Expected: `{'category': 'breaking_news', 'timeframe': 'intraday', 'confidence': 'high', 'venues': 'HL perps'}`

- [ ] **Step 3: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/ingestion/scaffold_strategies.py
git commit -m "feat(smb-crypto-agent): phase-3 strategy scaffolder

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: DB init script

**Files:**
- Create: `~/apps/crypto/smb-crypto-agent/scripts/init_db.py`

- [ ] **Step 1: Write `scripts/init_db.py`**

```python
# scripts/init_db.py
"""
Initialize db/research.db with all tables used across the agent.
Idempotent — CREATE TABLE IF NOT EXISTS everywhere.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "research.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    strategy TEXT NOT NULL,
    venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    features_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS judge_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    ts_utc TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence REAL NOT NULL,
    size_multiplier REAL NOT NULL,
    reasoning TEXT NOT NULL,
    prompt_digest TEXT NOT NULL,
    FOREIGN KEY(signal_id) REFERENCES signals(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER,
    ts_utc TEXT NOT NULL,
    mode TEXT NOT NULL,
    venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty REAL NOT NULL,
    price REAL,
    status TEXT NOT NULL,
    raw_response TEXT,
    FOREIGN KEY(signal_id) REFERENCES signals(id)
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    equity_usdt REAL NOT NULL,
    pnl_day REAL NOT NULL,
    pnl_total REAL NOT NULL,
    drawdown_pct REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    strategy TEXT NOT NULL,
    config_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(ts_utc);
CREATE INDEX IF NOT EXISTS idx_orders_ts ON orders(ts_utc);
CREATE INDEX IF NOT EXISTS idx_equity_ts ON equity_snapshots(ts_utc);
"""


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    print(f"initialized {DB_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

```bash
cd ~/apps/crypto/smb-crypto-agent
python scripts/init_db.py
sqlite3 db/research.db ".tables"
```

Expected: `backtest_runs   equity_snapshots  judge_decisions  orders  signals`

- [ ] **Step 3: Commit**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/scripts/init_db.py
git commit -m "feat(smb-crypto-agent): init_db script with full schema

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Phase-1 execution — parallel subagent wave

This task is where the heavy ingestion happens. It is **Claude-orchestrated**, not a standalone script. The implementing session uses the `Agent` tool to dispatch ~34 subagents in waves.

**Files produced:**
- `~/apps/crypto/smb-crypto-agent/ingestion/summaries.jsonl` (accumulated)
- Per-batch temp files: `~/apps/crypto/smb-crypto-agent/ingestion/.batches/b000.jsonl`, etc.

- [ ] **Step 1: Prepare batch manifest**

Run this once to produce the list of batches:

```bash
cd ~/apps/crypto/smb-crypto-agent
source ~/venvs/oefr/bin/activate
python - <<'PY'
from pathlib import Path
from ingestion.planner import plan_batches

src = Path("ingestion/sources.txt").read_text().splitlines()
src = [s.strip() for s in src if s.strip()]
batches = plan_batches(src, batch_size=50)
out = Path("ingestion/.batches")
out.mkdir(exist_ok=True)
for b in batches:
    (out / f"{b.batch_id}.files").write_text("\n".join(b.files))
print(f"wrote {len(batches)} batch files to {out}")
PY
```

Expected: `wrote 34 batch files to ingestion/.batches`.

- [ ] **Step 2: Dispatch Wave 1 — batches b000 through b011 (12 subagents in parallel)**

From the implementing Claude session, send a single message with 12 Agent tool calls. Each subagent prompt template:

```
You are an SMB transcript ingestion worker. Read every file listed under FILES in full from `/home/oghenetejiri/apps/SMB_youtube_transcripts/<file>`. For each file, produce EXACTLY ONE JSON line conforming to this schema:

{
  "file": "<filename>",
  "video_id": "<extract from the transcript header; blank string if missing>",
  "title": "<from the # heading>",
  "categories": ["..."],            // one or more tags from taxonomy (see TAXONOMY)
  "equity_only": <bool>,            // true iff no crypto analog
  "crypto_translatable": <bool>,
  "tactical_score": <0-5 int>,      // 0 = motivational only, 5 = explicit playable setup
  "setups": [
    {
      "name": "...",
      "preconditions": "...",
      "entry_trigger": "...",
      "invalidation": "...",
      "targets": "...",
      "timeframe": "scalp|intraday|swing",
      "confidence": "high|med|low",
      "crypto_adaptation_notes": "...",
      "quotes": ["short verbatim lines that encode the rule"]
    }
  ],
  "principles": ["short extracted lessons that are not full setups"],
  "skip_reason": null
}

RULES:
1. Use ONLY the categories in TAXONOMY below. Do not invent tags.
2. For options-specific plays, extract the mechanic to `principles` but DROP the option-specific expression. Mark the transcript `equity_only: true` only if the ENTIRE transcript has no crypto analog.
3. Every field must be present; use empty strings/arrays/null where appropriate.
4. Output the JSON lines to `/home/oghenetejiri/apps/crypto/smb-crypto-agent/ingestion/.batches/<BATCH_ID>.jsonl` (one JSON object per line, NO blank lines, NO preamble, NO markdown fences).
5. Your last action must be to write that file. Do not print the JSON in your response.
6. Before writing, validate each row parses as JSON and all required keys exist.

TAXONOMY (from ingestion/taxonomy.md):
<paste full taxonomy.md contents>

BATCH_ID: <bXXX>
FILES:
<paste contents of ingestion/.batches/bXXX.files>
```

Dispatch 12 Agent calls in one message, each with its own BATCH_ID and FILES list. Use `subagent_type: "general-purpose"` and `description: "Ingest batch bXXX"`.

After all 12 return, verify each wrote its file:

```bash
ls ingestion/.batches/*.jsonl | wc -l
```

Expected: 12.

- [ ] **Step 3: Dispatch Wave 2 — batches b012 through b023 (12 subagents in parallel)**

Same as Step 2, batch IDs b012-b023.

- [ ] **Step 4: Dispatch Wave 3 — batches b024 through b033 (10 subagents in parallel)**

Same as Step 2, batch IDs b024-b033.

- [ ] **Step 5: Concatenate into summaries.jsonl**

```bash
cd ~/apps/crypto/smb-crypto-agent
cat ingestion/.batches/b*.jsonl > ingestion/summaries.jsonl
wc -l ingestion/summaries.jsonl
```

Expected: 1698.

- [ ] **Step 6: Validate the combined JSONL**

```bash
python - <<'PY'
from pathlib import Path
from ingestion.validator import validate_summaries_jsonl

expected = set(Path("ingestion/sources.txt").read_text().splitlines())
expected = {e.strip() for e in expected if e.strip()}
rep = validate_summaries_jsonl(Path("ingestion/summaries.jsonl"), expected)
print(f"ok={rep.ok} rows={rep.row_count} missing={len(rep.missing_files)} dupes={len(rep.duplicate_files)} errors={len(rep.errors)}")
if not rep.ok:
    for e in rep.errors[:20]:
        print(e)
    if rep.missing_files:
        print("missing:", list(rep.missing_files)[:20])
PY
```

Expected: `ok=True rows=1698 missing=0 dupes=0 errors=0`.

If any rows fail validation, redispatch a targeted repair subagent for just the failing filenames. Loop Steps 5–6 until `ok=True`.

- [ ] **Step 7: Commit Phase-1 artifacts**

```bash
cd /home/oghenetejiri/apps
git add -f crypto/smb-crypto-agent/ingestion/summaries.jsonl
git commit -m "feat(smb-crypto-agent): phase-1 ingestion output (1698 summaries)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

Note: `summaries.jsonl` is normally gitignored but we force-add the Phase-1 output so later plans can reference it without re-running.

---

## Task 11: Phase-2 execution — category synthesis

Produces `knowledge_base/setups/*.md`, `knowledge_base/principles/*.md`, and `knowledge_base/INDEX.md`.

- [ ] **Step 1: Prepare per-category cluster files**

```bash
cd ~/apps/crypto/smb-crypto-agent
python - <<'PY'
from pathlib import Path
from ingestion.synthesize import load_summaries, group_by_category, write_cluster_files, tactical_rows

rows = load_summaries(Path("ingestion/summaries.jsonl"))
groups = group_by_category(tactical_rows(rows, min_score=2))
written = write_cluster_files(groups, Path("ingestion/.clusters"))
for p in sorted(written):
    print(p.name, sum(1 for _ in open(p)))
PY
```

Expected: list of `cluster_<category>.jsonl` files with row counts.

- [ ] **Step 2: Dispatch one subagent per tradeable-setup category (in parallel)**

Tradeable categories (scaffold strategies for these): `breaking_news`, `trend_day_continuation`, `pullback_in_uptrend`, `second_chance_retest`, `fashionably_late`, `imbalance_scalp`, `relative_strength`, `fade_the_extended`, `opening_range_breakout`, `liquidity_sweep`, `basket_execution`.

Subagent prompt template:

```
You are a setup-synthesis worker for smb-crypto-agent. Input: all rows in `/home/oghenetejiri/apps/crypto/smb-crypto-agent/ingestion/.clusters/cluster_<CATEGORY>.jsonl`. Each row has a `setups` array.

Your job: dedupe setups across all rows and emit one OR MORE canonical playbook markdown files under `/home/oghenetejiri/apps/crypto/smb-crypto-agent/knowledge_base/setups/`. Split distinct sub-setups into separate files (e.g., `breaking_news_long.md` and `breaking_news_short.md` are different files).

Each output file MUST follow this schema exactly:

```
# <Setup Name>
**Category:** <category>  **Timeframe:** <scalp|intraday|swing>  **Confidence:** <high|med|low>  **Venues:** <comma list>
**Adapted from:** <comma-separated list of source transcript filenames>

## Preconditions
<prose>

## Entry trigger
<prose>

## Invalidation
<prose>

## Targets
<prose>

## Sizing notes
<prose>

## Crypto adaptation notes
<prose>

## Common mistakes (from review transcripts)
- ...

## Example(s)
<optional>
```

RULES:
1. Prefer high-confidence articulations over low. Keep the cleanest rule expression as canonical; merge supporting nuance from other rows.
2. "Venues" = which of {HL perps, Binance spot, Binance futures} the setup makes sense on. Spot-only if directional long-only with no leverage; futures/perps if short-viable or leverage-relevant.
3. Translate every equity-specific concept to crypto. "9:30 open" -> "US session open around 13:30 UTC" or "daily candle open at 00:00 UTC" depending on context. "Earnings" -> "token unlock / protocol upgrade / scheduled catalyst". Drop the concept entirely if no translation exists.
4. File names: lowercase snake_case of the setup name.
5. Do NOT invent setups not present in the input rows. Only consolidate and refine what is there.
6. Your last action is to write the markdown files. Do not output them in chat.

INPUT FILE: `ingestion/.clusters/cluster_<CATEGORY>.jsonl`
CATEGORY: <category>
```

Dispatch all 11 tradeable-category subagents in a single message with 11 Agent tool calls. Use `subagent_type: "general-purpose"`.

- [ ] **Step 3: Dispatch principles synthesis (one subagent)**

Prompt the subagent to read cluster files for `game_planning`, `risk_management`, `trade_review`, `trader_development` and produce `knowledge_base/principles/<category>.md` files that aggregate the `principles` arrays across rows, deduped and organized.

- [ ] **Step 4: Dispatch context/reference synthesis (one subagent)**

Same pattern for `options_expression`, `earnings_trade`, `ipo_lockup`, `short_interest` but write to `knowledge_base/context/` with a disclaimer at the top of each file: "Reference only — not tradeable on crypto venues."

- [ ] **Step 5: Verify every setup file parses**

```bash
cd ~/apps/crypto/smb-crypto-agent
python - <<'PY'
from pathlib import Path
from ingestion.scaffold_strategies import parse_header

bad = []
for md in sorted(Path("knowledge_base/setups").glob("*.md")):
    if parse_header(md.read_text(encoding="utf-8")) is None:
        bad.append(md.name)
if bad:
    print("MALFORMED HEADERS:")
    for b in bad:
        print(" ", b)
else:
    print("all setup headers parse")
PY
```

Expected: `all setup headers parse`.

If any fail, spawn a targeted repair subagent for those specific files.

- [ ] **Step 6: Generate INDEX.md**

```bash
python - <<'PY'
from pathlib import Path
from ingestion.scaffold_strategies import parse_header, slugify

lines = ["# Knowledge Base Index", ""]
lines.append("## Setups")
lines.append("")
lines.append("| Slug | Category | Timeframe | Confidence | Venues |")
lines.append("|------|----------|-----------|------------|--------|")
for md in sorted(Path("knowledge_base/setups").glob("*.md")):
    h = parse_header(md.read_text(encoding="utf-8"))
    if h:
        lines.append(f"| [{slugify(md)}](setups/{md.name}) | {h['category']} | {h['timeframe']} | {h['confidence']} | {h['venues']} |")

lines += ["", "## Principles", ""]
for md in sorted(Path("knowledge_base/principles").glob("*.md")):
    lines.append(f"- [{md.stem}](principles/{md.name})")

lines += ["", "## Context (reference only, not tradeable)", ""]
for md in sorted(Path("knowledge_base/context").glob("*.md")):
    lines.append(f"- [{md.stem}](context/{md.name})")

Path("knowledge_base/INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote INDEX.md")
PY
```

Expected: `wrote INDEX.md`.

- [ ] **Step 7: Commit Phase-2 artifacts**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/knowledge_base/
git commit -m "feat(smb-crypto-agent): phase-2 distilled knowledge base

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Phase-3 execution — scaffold strategies

- [ ] **Step 1: Run the scaffolder**

```bash
cd ~/apps/crypto/smb-crypto-agent
python -m ingestion.scaffold_strategies
```

Expected: prints `scaffolded strategies/<slug>` for every high/med-confidence setup.

- [ ] **Step 2: Verify scaffolded dirs**

```bash
ls strategies/
find strategies -maxdepth 2 -type f | sort
```

Expected: every `strategies/<slug>/` contains `__init__.py`, `detector.py`, `bot.py`, `playbook.md`.

- [ ] **Step 3: Smoke-test that every detector.py imports (but raises on call)**

```bash
python - <<'PY'
import importlib
from pathlib import Path

fails = []
for d in sorted(Path("strategies").iterdir()):
    if d.is_dir() and (d / "detector.py").exists():
        mod = f"strategies.{d.name}.detector"
        try:
            importlib.import_module(mod)
        except Exception as e:
            fails.append((mod, str(e)))
if fails:
    for m, e in fails:
        print(m, "->", e)
else:
    print("all detectors import ok")
PY
```

Expected: `all detectors import ok`.

- [ ] **Step 4: Commit Phase-3 artifacts**

```bash
cd /home/oghenetejiri/apps
git add crypto/smb-crypto-agent/strategies/
git commit -m "feat(smb-crypto-agent): phase-3 strategy scaffolding

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 13: Final verification

- [ ] **Step 1: Run the full test suite**

```bash
cd ~/apps/crypto/smb-crypto-agent
source ~/venvs/oefr/bin/activate
python -m pytest tests/ -v
```

Expected: all tests pass (schema + planner + validator ≥ 17 tests).

- [ ] **Step 2: Print summary counts**

```bash
echo "Summaries rows: $(wc -l < ingestion/summaries.jsonl)"
echo "Setup files:     $(ls knowledge_base/setups/ | wc -l)"
echo "Principle files: $(ls knowledge_base/principles/ | wc -l)"
echo "Context files:   $(ls knowledge_base/context/ | wc -l)"
echo "Strategy dirs:   $(ls -d strategies/*/ 2>/dev/null | wc -l)"
```

Expected: summaries=1698, setups ≥ 15, strategy dirs = setup count (every setup that's high/med confidence scaffolded).

- [ ] **Step 3: Sanity-check one random setup and one strategy**

```bash
head -60 knowledge_base/setups/$(ls knowledge_base/setups | head -1)
echo "---"
cat strategies/$(ls strategies | head -1)/detector.py
```

Expected: well-formed setup with parseable header; detector stub that mentions the setup and raises NotImplementedError.

- [ ] **Step 4: Tag the milestone**

```bash
cd /home/oghenetejiri/apps
git tag -a smb-crypto-agent/plan1-complete -m "SMB Crypto Agent Plan 1 (ingestion) complete"
```

---

## Plan 1 Self-Review

**Spec coverage:**
- Repo layout (spec §3) → T1 ✓
- Config files (spec §3) → T2 ✓
- Ingestion Phase 1 (spec §4) → T3, T4, T5, T6, T10 ✓
- Ingestion Phase 2 (spec §4) → T7, T11 ✓
- Ingestion Phase 3 (spec §4) → T8, T12 ✓
- Knowledge base schema (spec §5) → T11 (subagent prompt enforces schema) ✓
- DB research.db (spec §6) → T9 ✓
- Testing discipline (spec §7) → T4, T5, T6, T13 ✓
- Build sequence items 1-3 (spec §8) → all covered ✓
- Build sequence items 4-10 → deferred to Plan 2 and Plan 3 (documented as such)

**Placeholder scan:** No TBD/TODO/"implement later" in executable tasks. The detector stubs intentionally raise `NotImplementedError` — that's deferred work, not a plan placeholder, and Plan 2/3 implements them.

**Type consistency:** `TranscriptSummary` and `Setup` pydantic models used consistently across schema.py, validator.py, synthesize.py. `Batch` dataclass used only in planner.py. `parse_header` signature matches between scaffold_strategies.py callers and its own definition.