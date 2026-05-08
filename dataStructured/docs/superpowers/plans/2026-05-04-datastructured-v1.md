# DataStructured v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Stand up the v1 minimum viable autonomous loop for DataStructured — six trinity-agent employees executing the research → harvest → clean → compliance → ship pipeline daily, DM-only Telegram with CEO as sole comms layer.

**Architecture:** trinity-agent framework workspace at `~/apps/dataStructured/`. Six folder-scoped employees (`ceo`, `opportunity-researcher`, `data-engineer`, `data-steward`, `compliance-officer`, `engineer`) defined under `.trinity/employees/`. JSON-first artifacts in `state/` (CSV only for dataset payloads). CEO orchestrates downstream employees by spawning `trinity run` subprocesses. Two scheduled cycles (13:00 ET research, 19:00 ET CEO pipeline) defined in `trinity.toml`. claude_sdk provider — no API key needed.

**Tech Stack:** Python 3.12, trinity-agent (editable install from `~/apps/trinity-agent`), pytest, jsonschema, Stripe Python SDK, Playwright. No new SaaS, no new paid services.

**Reference docs:**
- Spec: `~/apps/dataStructured/docs/superpowers/specs/2026-05-04-datastructured-design.md`
- PRD: `~/apps/dataStructured/docs/PRD.md`

**File structure (locked in this plan):**

```
~/apps/dataStructured/
├── trinity.toml                              # config (auth, employees, scheduler)
├── .env                                      # secrets (gitignored)
├── .env.example                              # template
├── .gitignore
├── pyproject.toml                            # python deps for scripts + tests
├── README.md                                 # (re-created in this plan)
├── CLAUDE.md                                 # project context for Claude Code
├── docs/                                     # already exists
├── .trinity/employees/<name>/identity.md     # six identity files
├── state/
│   ├── _schemas/                             # 7 JSON schemas
│   ├── opportunities/  datasets/  ethics-ledger/  products/   # populated at runtime
│   └── distribution-queue.json
├── scripts/
│   ├── lib/                                  # pure-function utilities
│   │   ├── atomic_io.py
│   │   ├── schema_validator.py
│   │   ├── slug.py
│   │   └── distribution_queue.py
│   ├── stripe_helpers.py
│   ├── gumroad_helpers.py
│   └── ceo_orchestrator.py
└── tests/
    ├── conftest.py
    ├── _stub_provider.py
    ├── fixtures/
    ├── schemas/  test_*.py                   # one per schema
    └── integration/
```

---

## Milestone 0 — Workspace Bootstrap (no LLM yet, just plumbing)

### Task 0.1: Verify trinity-agent installed and CLI works

**Files:** none (verification only)

- [x] **Step 1: Run trinity --help to confirm CLI present**

Run: `trinity --help`
Expected: usage line listing `init,start,stop,restart,run,status,employee,auth,memory,knowledge,workspaces,plugins`

If not installed: `pip install -e ~/apps/trinity-agent` from any active venv.

- [x] **Step 2: Confirm Python venv has dev tooling**

Run: `python3 -c "import jsonschema, pytest, stripe, playwright; print('ok')"`
Expected: `ok`

If missing: install in step 0.2.

---

### Task 0.2: Create pyproject.toml and install dev deps

**Files:**
- Create: `~/apps/dataStructured/pyproject.toml`

- [x] **Step 1: Write pyproject.toml**

```toml
[project]
name = "datastructured"
version = "0.1.0"
description = "Autonomous data-as-a-product company"
requires-python = ">=3.12"
dependencies = [
    "trinity-agent",          # editable install from ~/apps/trinity-agent
    "jsonschema>=4.21",
    "stripe>=10.0",
    "playwright>=1.40",
    "python-dateutil>=2.8",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "responses>=0.25",        # for mocking HTTP in stripe tests
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
```

- [x] **Step 2: Install in active venv**

Run: `pip install -e ~/apps/dataStructured[dev]`
Expected: installs without error.

- [x] **Step 3: Install Playwright browsers**

Run: `playwright install chromium`
Expected: chromium downloaded.

- [x] **Step 4: Verify import**

Run: `python3 -c "import jsonschema, pytest, stripe, playwright, trinity; print('ok')"`
Expected: `ok`

---

### Task 0.3: Write .gitignore

**Files:**
- Create: `~/apps/dataStructured/.gitignore`

- [x] **Step 1: Write .gitignore**

```
# secrets
.env
.env.local
.env.*.local

# trinity runtime state (kept locally, not in git)
.trinity/

# python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.ruff_cache/

# build / dist
dist/
build/

# datasets — large, regenerable, gitignored to keep repo lean
state/datasets/*/raw-*.csv
state/datasets/*/clean-*.csv

# OS
.DS_Store
Thumbs.db
```

- [x] **Step 2: Verify**

Run: `cat ~/apps/dataStructured/.gitignore | head -5`
Expected: shows `# secrets` and `.env`.

---

### Task 0.4: Write initial trinity.toml (no employees / cycles yet)

**Files:**
- Create: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Write trinity.toml**

```toml
# DataStructured — trinity-agent configuration

[company]
name = "DataStructured"
description = "Autonomous data-as-a-product company. Public data → niche packaging → digital products."
default_employee = "ceo"

[auth]
provider = "claude_sdk"
api_key_env = ""

[agent]
max_turns = 30
max_tokens = 16384
action_timeout = 3600
convo_timeout = 120
default_model = "claude-sonnet-4-6"
router_model = "claude-haiku-4-5-20251001"
action_model = "claude-sonnet-4-6"
judge_model = "claude-opus-4-6"

[telegram]
bot_token_env = "TELEGRAM_BOT_TOKEN"
poll_timeout = 30
max_response_length = 4000
streaming_update_interval = 8

[telegram.acl]
dm_policy = "allowlist"
allowed_users = []          # founder Telegram user ID added in Milestone 8
group_policy = "allowlist"

[memory]
short_term_decay_hours = 48
long_term_decay_days = 30
max_short_term = 200
max_long_term = 500
chat_history_buffer = 10
promotion_threshold = 0.8
correction_weight = 2.0

[scheduler]
enabled = true
# Cycles added in Milestone 7

# Employees added in Milestone 3

[workspace]
products_dir = "."
exclude_patterns = ["node_modules", ".git", "__pycache__", ".next", "dist", "build", ".trinity", "state/datasets"]
```

- [x] **Step 2: Validate TOML parses**

Run: `python3 -c "import tomllib; tomllib.loads(open('/home/oghenetejiri/apps/dataStructured/trinity.toml').read()); print('ok')"`
Expected: `ok`

---

### Task 0.5: Write .env.example

**Files:**
- Create: `~/apps/dataStructured/.env.example`

- [x] **Step 1: Write .env.example**

```bash
# DataStructured secrets — copy to .env (gitignored) and fill in.

# Telegram bot (created via @BotFather in Milestone 8)
TELEGRAM_BOT_TOKEN=

# Stripe — same account as parent enterprise (LoB-namespaced via dsl_ prefix)
STRIPE_SECRET_KEY=
STRIPE_PUBLIC_KEY=
STRIPE_WEBHOOK_SECRET=

# Gumroad (browser automation only; write API deprecated)
GUMROAD_USERNAME=
GUMROAD_PASSWORD=

# Founder Telegram user ID (for ACL allowlist)
FOUNDER_TELEGRAM_USER_ID=
```

- [x] **Step 2: Verify**

Run: `cat ~/apps/dataStructured/.env.example | head -3`
Expected: shows `# DataStructured secrets`.

---

### Task 0.6: Write CLAUDE.md

**Files:**
- Create: `~/apps/dataStructured/CLAUDE.md`

- [x] **Step 1: Write CLAUDE.md**

```markdown
# CLAUDE.md — DataStructured

Project context for Claude Code. Auto-loaded when a session is opened in this folder.

## What this is

DataStructured is a standalone, autonomous, public-data-as-a-product company. Built on the BuiltWith / Nomad List model: harvest public data, package for a niche audience, sell as one-time / membership / SaaS.

**Folder-scoped:** everything lives inside `~/apps/dataStructured/`. Nothing here references projects outside this folder, the global `~/.claude/agents/`, or `~/.openclaw/`.

## Operating model

Built on **trinity-agent** (`~/apps/trinity-agent`). Six employees in `.trinity/employees/`:

| Employee | Role |
|---|---|
| `ceo` | Strategic orchestrator + sole comms layer (only employee that DMs the founder) |
| `opportunity-researcher` | Wide-scope demand discovery (daily 13:00 ET) |
| `data-engineer` | Public-data harvest via Google operators + AI |
| `data-steward` | Quality gate (clean / dedupe / validate) |
| `compliance-officer` | Hard ethics gate (PASS / FAIL / NEEDS FOUNDER REVIEW) |
| `engineer` | Stripe Payment Link + Gumroad listing shipper |

## Canonical workflow

```
research-lead → ceo (approve) → data-engineer → data-steward
   → compliance-officer (PASS) → ceo writes spec → engineer → distribution-queue
```

## Hard rules (every agent enforces)

1. **Public data only.** No auth-bypass, no scraping behind login, no purchased private datasets.
2. **No PII.** Personal email, phone, home address, financial accounts → automatic compliance FAIL.
3. **Source URL on every row.** Non-negotiable for shipping.
4. **Production code only.** No mocks, no placeholders, no half-built features in shipped products.
5. **Test before claiming done.** URL must load + buy flow must work.
6. **Folder-scoped.** No agent here references projects outside `~/apps/dataStructured/`.
7. **Bootstrap discipline.** No new paid SaaS, no premature engineering.
8. **Never discount.** Stack value (bonus content, tier upgrades) instead of cutting price.

## Common commands

```bash
cd ~/apps/dataStructured

# Start daemon (Telegram bot + scheduler)
trinity start --daemon

# One-shot task
trinity run "do today's work" -e ceo

# Workspace status
trinity status

# Run tests
pytest

# Stop daemon
trinity stop
```

## Reference docs

- `docs/superpowers/specs/2026-05-04-datastructured-design.md` — v1 design spec
- `docs/PRD.md` — full vision + phase roadmap
- `docs/superpowers/plans/2026-05-04-datastructured-v1.md` — this implementation plan
```

- [x] **Step 2: Verify**

Run: `head -3 ~/apps/dataStructured/CLAUDE.md`
Expected: shows `# CLAUDE.md — DataStructured`.

---

### Task 0.7: Initialize state/ folder structure

**Files:**
- Create: `~/apps/dataStructured/state/{_schemas,opportunities,datasets,ethics-ledger,products}/.gitkeep`
- Create: `~/apps/dataStructured/state/distribution-queue.json`

- [x] **Step 1: Make folders**

Run:
```bash
mkdir -p ~/apps/dataStructured/state/{_schemas,opportunities,datasets,ethics-ledger,products}
touch ~/apps/dataStructured/state/{_schemas,opportunities,datasets,ethics-ledger,products}/.gitkeep
```

Expected: no error.

- [x] **Step 2: Initialize distribution queue**

Write to `~/apps/dataStructured/state/distribution-queue.json`:

```json
{
  "version": 1,
  "type": "distribution_queue",
  "updated_at": "2026-05-04T00:00:00Z",
  "items": []
}
```

- [x] **Step 3: Verify**

Run: `find ~/apps/dataStructured/state -type f | sort`
Expected: lists 5 .gitkeep files + distribution-queue.json.

---

### Task 0.8: Re-create README.md

(README was trashed in earlier reset. Re-creating concise version.)

**Files:**
- Create: `~/apps/dataStructured/README.md`

- [x] **Step 1: Write README.md**

```markdown
# DataStructured

Autonomous public-data-as-a-product company. Built on the BuiltWith / Nomad List / Starter Story playbook: harvest public data, structure it for a paying audience, sell as one-time digital product, recurring membership, or SaaS.

## What's in this folder

| Path | Purpose |
|---|---|
| `trinity.toml` | trinity-agent config — auth, employees, scheduler cycles |
| `.env.example` | Secrets template (real `.env` is gitignored) |
| `CLAUDE.md` | Project context for Claude Code sessions |
| `docs/PRD.md` | Full vision + phase roadmap |
| `docs/superpowers/specs/` | Design specs (v1 + future phases) |
| `docs/superpowers/plans/` | Implementation plans |
| `.trinity/` | trinity-agent runtime state (gitignored) |
| `state/` | Domain artifacts (opportunities, datasets, ethics ledger, products, distribution queue) |
| `scripts/` | Stripe + Gumroad helpers, CEO orchestrator |
| `tests/` | pytest test suite |

## Quick start

```bash
cd ~/apps/dataStructured
cp .env.example .env             # then fill in secrets
pip install -e .[dev]
trinity start --daemon           # starts Telegram bot + scheduler
```

## Operating model

Six employees. CEO is the sole employee that talks to the founder via Telegram DM. Other employees are silent workers — they write to disk and Trinity memory.

Daily cycle: opportunity-researcher fires at 13:00 ET; CEO fires at 19:00 ET, runs the pipeline, sends one DM summary.

See `docs/superpowers/specs/2026-05-04-datastructured-design.md` for full spec.

## Naming

Working name: **DataStructured** (matches folder). Easy to rename — brand lives in `README.md`, `trinity.toml` `[company]`, `CLAUDE.md`, and the 6 employee identity files.
```

- [x] **Step 2: Verify**

Run: `head -3 ~/apps/dataStructured/README.md`
Expected: `# DataStructured`.

---

### Task 0.9: Commit Milestone 0

- [x] **Step 1: Stage and verify only dataStructured files staged**

Run from `~/apps/`:
```bash
git add dataStructured/.gitignore dataStructured/CLAUDE.md dataStructured/README.md dataStructured/pyproject.toml dataStructured/trinity.toml dataStructured/.env.example dataStructured/state/
git diff --cached --name-only | grep -v '^dataStructured/' && echo "ERROR: stray files staged" || echo "OK"
```
Expected: `OK`.

- [x] **Step 2: Commit**

Run from `~/apps/`:
```bash
git commit -m "$(cat <<'EOF'
chore(dataStructured): workspace bootstrap (M0)

trinity.toml, .env.example, .gitignore, README.md, CLAUDE.md,
pyproject.toml, state/ skeleton with empty distribution queue.
No employees or cycles yet — added in subsequent milestones.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

---

## Milestone 1 — JSON Schemas + Foundation Utilities (TDD)

This milestone is pure plumbing — deterministic, no LLM. Heavy TDD.

### Task 1.1: opportunity_brief schema + tests

**Files:**
- Create: `~/apps/dataStructured/state/_schemas/opportunity_brief.schema.json`
- Create: `~/apps/dataStructured/tests/schemas/test_opportunity_brief.py`
- Create: `~/apps/dataStructured/tests/__init__.py` (empty)
- Create: `~/apps/dataStructured/tests/schemas/__init__.py` (empty)

- [x] **Step 1: Write the failing test first**

Create `tests/schemas/test_opportunity_brief.py`:

```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/opportunity_brief.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_brief():
    return {
        "version": 1,
        "type": "opportunity_brief",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T13:00:00Z",
        "created_by": "opportunity-researcher",
        "status": "PROPOSED",
        "score": 8,
        "summary": "Florida homeowners want pre-purchase permit reports.",
        "audience": {"who": "FL homeowners", "where_found": ["r/RealEstate"]},
        "data_wanted": "Permit history per address",
        "evidence": [{"source": "reddit", "url": "https://reddit.com/...", "quote": "Would pay $50"}],
        "willingness_to_pay": {"signal": "$50 mentioned", "confidence": "moderate"},
        "source_rights": {"public": True, "examples": ["miamidade.gov/permits"]},
        "first_sale_path": {"channel": "FB groups", "angle": "instant report"}
    }


def test_valid_brief_passes(schema):
    jsonschema.validate(_valid_brief(), schema)


def test_missing_score_fails(schema):
    brief = _valid_brief()
    del brief["score"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)


def test_score_out_of_range_fails(schema):
    brief = _valid_brief()
    brief["score"] = 11
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)


def test_invalid_status_fails(schema):
    brief = _valid_brief()
    brief["status"] = "MAYBE"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)


def test_missing_evidence_fails(schema):
    brief = _valid_brief()
    del brief["evidence"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)
```

- [x] **Step 2: Run test — expect FAIL (schema file doesn't exist yet)**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_opportunity_brief.py -v`
Expected: errors loading schema (file not found).

- [x] **Step 3: Write the schema**

Create `state/_schemas/opportunity_brief.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "OpportunityBrief",
  "type": "object",
  "required": ["version", "type", "slug", "created", "created_by", "status", "score", "summary", "audience", "data_wanted", "evidence", "willingness_to_pay", "source_rights", "first_sale_path"],
  "properties": {
    "version": {"const": 1},
    "type": {"const": "opportunity_brief"},
    "slug": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$"},
    "created": {"type": "string", "format": "date-time"},
    "created_by": {"type": "string"},
    "status": {"enum": ["PROPOSED", "APPROVED", "REJECTED", "PURSUED", "BLOCKED", "KILLED"]},
    "score": {"type": "integer", "minimum": 1, "maximum": 10},
    "summary": {"type": "string", "minLength": 10},
    "audience": {
      "type": "object",
      "required": ["who", "where_found"],
      "properties": {
        "who": {"type": "string"},
        "where_found": {"type": "array", "items": {"type": "string"}, "minItems": 1}
      }
    },
    "data_wanted": {"type": "string"},
    "evidence": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["source", "url"],
        "properties": {
          "source": {"type": "string"},
          "url": {"type": "string", "format": "uri"},
          "quote": {"type": "string"}
        }
      }
    },
    "willingness_to_pay": {
      "type": "object",
      "required": ["signal", "confidence"],
      "properties": {
        "signal": {"type": "string"},
        "confidence": {"enum": ["low", "moderate", "high"]}
      }
    },
    "source_rights": {
      "type": "object",
      "required": ["public", "examples"],
      "properties": {
        "public": {"type": "boolean"},
        "examples": {"type": "array", "items": {"type": "string"}, "minItems": 1}
      }
    },
    "first_sale_path": {
      "type": "object",
      "required": ["channel", "angle"],
      "properties": {
        "channel": {"type": "string"},
        "angle": {"type": "string"}
      }
    },
    "rejection_reason": {"type": "string"}
  }
}
```

- [x] **Step 4: Run tests — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_opportunity_brief.py -v`
Expected: 5 tests pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/state/_schemas/opportunity_brief.schema.json dataStructured/tests/schemas/test_opportunity_brief.py dataStructured/tests/__init__.py dataStructured/tests/schemas/__init__.py
git commit -m "feat(dataStructured): opportunity_brief JSON schema + tests"
```

---

### Task 1.2: raw_dataset_metadata schema + tests

**Files:**
- Create: `~/apps/dataStructured/state/_schemas/raw_dataset_metadata.schema.json`
- Create: `~/apps/dataStructured/tests/schemas/test_raw_dataset_metadata.py`

- [x] **Step 1: Write the failing test**

Create `tests/schemas/test_raw_dataset_metadata.py`:

```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/raw_dataset_metadata.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid():
    return {
        "version": 1,
        "type": "raw_dataset_metadata",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T19:30:00Z",
        "created_by": "data-engineer",
        "status": "READY_FOR_STEWARD",
        "summary": "1234 permit records across 6 FL counties.",
        "source_brief": "state/opportunities/2026-05-04-homeowner-permit-history-fl.json",
        "data_file": "state/datasets/homeowner-permit-history-fl/raw-2026-05-04.csv",
        "row_count": 1234,
        "columns": ["id", "address", "permit_date", "permit_type", "source_url"],
        "queries_executed": ["site:miamidade.gov permits"],
        "urls_fetched": 87,
        "known_gaps": "Broward county records gated by captcha"
    }


def test_valid_passes(schema):
    jsonschema.validate(_valid(), schema)


def test_zero_rows_fails(schema):
    obj = _valid()
    obj["row_count"] = 0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_missing_columns_fails(schema):
    obj = _valid()
    del obj["columns"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_invalid_status_fails(schema):
    obj = _valid()
    obj["status"] = "DONE"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_raw_dataset_metadata.py -v`
Expected: file-not-found error.

- [x] **Step 3: Write the schema**

Create `state/_schemas/raw_dataset_metadata.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RawDatasetMetadata",
  "type": "object",
  "required": ["version", "type", "slug", "created", "created_by", "status", "summary", "source_brief", "data_file", "row_count", "columns", "queries_executed", "urls_fetched"],
  "properties": {
    "version": {"const": 1},
    "type": {"const": "raw_dataset_metadata"},
    "slug": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$"},
    "created": {"type": "string", "format": "date-time"},
    "created_by": {"const": "data-engineer"},
    "status": {"enum": ["READY_FOR_STEWARD", "BLOCKED", "FAILED"]},
    "summary": {"type": "string", "minLength": 10},
    "source_brief": {"type": "string"},
    "data_file": {"type": "string"},
    "row_count": {"type": "integer", "minimum": 1},
    "columns": {"type": "array", "items": {"type": "string"}, "minItems": 2},
    "queries_executed": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    "urls_fetched": {"type": "integer", "minimum": 1},
    "known_gaps": {"type": "string"},
    "failure_reason": {"type": "string"}
  }
}
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_raw_dataset_metadata.py -v`
Expected: 4 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/state/_schemas/raw_dataset_metadata.schema.json dataStructured/tests/schemas/test_raw_dataset_metadata.py
git commit -m "feat(dataStructured): raw_dataset_metadata schema + tests"
```

---

### Task 1.3: quality_report schema + tests

**Files:**
- Create: `~/apps/dataStructured/state/_schemas/quality_report.schema.json`
- Create: `~/apps/dataStructured/tests/schemas/test_quality_report.py`

- [x] **Step 1: Write the failing test**

Create `tests/schemas/test_quality_report.py`:

```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/quality_report.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_approved():
    return {
        "version": 1,
        "type": "quality_report",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T19:45:00Z",
        "created_by": "data-steward",
        "status": "APPROVED",
        "summary": "1180 rows after dedupe; signal:noise 96%.",
        "source_metadata": "state/datasets/homeowner-permit-history-fl/raw-2026-05-04.metadata.json",
        "data_file": "state/datasets/homeowner-permit-history-fl/clean-2026-05-04.csv",
        "rows_in": 1234,
        "rows_out": 1180,
        "transformations": [
            {"step": "schema_fix", "rows_before": 1234, "rows_after": 1230, "notes": "4 malformed rows dropped"}
        ],
        "source_liveness_sample": {"sampled": 118, "dead": 3, "action": "below threshold"},
        "refresh_recommendation": "monthly"
    }


def test_valid_approved_passes(schema):
    jsonschema.validate(_valid_approved(), schema)


def test_rejected_requires_unblocker(schema):
    obj = _valid_approved()
    obj["status"] = "REJECTED"
    # Missing unblocker → must fail
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_rejected_with_unblocker_passes(schema):
    obj = _valid_approved()
    obj["status"] = "REJECTED"
    obj["unblocker"] = "Engineer dropped 40% of rows; re-run with broader query set"
    jsonschema.validate(obj, schema)


def test_invalid_refresh_fails(schema):
    obj = _valid_approved()
    obj["refresh_recommendation"] = "yearly"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_quality_report.py -v`
Expected: file-not-found.

- [x] **Step 3: Write the schema**

Create `state/_schemas/quality_report.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "QualityReport",
  "type": "object",
  "required": ["version", "type", "slug", "created", "created_by", "status", "summary", "source_metadata", "rows_in", "rows_out", "transformations"],
  "properties": {
    "version": {"const": 1},
    "type": {"const": "quality_report"},
    "slug": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$"},
    "created": {"type": "string", "format": "date-time"},
    "created_by": {"const": "data-steward"},
    "status": {"enum": ["APPROVED", "REJECTED"]},
    "summary": {"type": "string", "minLength": 10},
    "source_metadata": {"type": "string"},
    "data_file": {"type": "string"},
    "rows_in": {"type": "integer", "minimum": 0},
    "rows_out": {"type": "integer", "minimum": 0},
    "transformations": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["step", "rows_before", "rows_after"],
        "properties": {
          "step": {"type": "string"},
          "rows_before": {"type": "integer", "minimum": 0},
          "rows_after": {"type": "integer", "minimum": 0},
          "notes": {"type": "string"}
        }
      }
    },
    "source_liveness_sample": {
      "type": "object",
      "properties": {
        "sampled": {"type": "integer", "minimum": 0},
        "dead": {"type": "integer", "minimum": 0},
        "action": {"type": "string"}
      }
    },
    "refresh_recommendation": {"enum": ["weekly", "monthly", "quarterly", "static"]},
    "unblocker": {"type": "string"}
  },
  "allOf": [
    {
      "if": {"properties": {"status": {"const": "REJECTED"}}},
      "then": {"required": ["unblocker"]}
    }
  ]
}
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_quality_report.py -v`
Expected: 4 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/state/_schemas/quality_report.schema.json dataStructured/tests/schemas/test_quality_report.py
git commit -m "feat(dataStructured): quality_report schema + conditional REJECT/unblocker validation"
```

---

### Task 1.4: ethics_ledger_entry schema + tests

**Files:**
- Create: `~/apps/dataStructured/state/_schemas/ethics_ledger_entry.schema.json`
- Create: `~/apps/dataStructured/tests/schemas/test_ethics_ledger_entry.py`

- [x] **Step 1: Write the failing test**

Create `tests/schemas/test_ethics_ledger_entry.py`:

```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/ethics_ledger_entry.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_pass():
    return {
        "version": 1,
        "type": "ethics_ledger_entry",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T19:55:00Z",
        "created_by": "compliance-officer",
        "verdict": "PASS",
        "summary": "All sources public county records; no PII; ToS clean.",
        "audit": {
            "public_access": {"answer": "Yes", "evidence": ["https://miamidade.gov/...", "https://broward.org/..."]},
            "pii": {"answer": "No", "detail": "Address is property address, not personal residence"},
            "robots_tos_clean": {"answer": "Yes", "domains_checked": ["miamidade.gov"]},
            "no_copyright_verbatim": {"answer": "Yes", "spot_check": "10 random rows"},
            "dual_use_sensitive": {"answer": "No", "justification": "n/a"},
            "subject_objection_test": {"answer": "Pass", "reasoning": "Property records are public by statute"},
            "gdpr_ccpa_clean": {"answer": "Yes", "reasoning": "No EU/CA persons in dataset"}
        },
        "dataset_file": "state/datasets/homeowner-permit-history-fl/clean-2026-05-04.csv"
    }


def test_pass_with_all_audit_passes(schema):
    jsonschema.validate(_valid_pass(), schema)


def test_pass_missing_audit_question_fails(schema):
    obj = _valid_pass()
    del obj["audit"]["pii"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_fail_requires_unblocker(schema):
    obj = _valid_pass()
    obj["verdict"] = "FAIL"
    obj["audit"]["pii"]["answer"] = "Yes"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_fail_with_unblocker_passes(schema):
    obj = _valid_pass()
    obj["verdict"] = "FAIL"
    obj["audit"]["pii"]["answer"] = "Yes"
    obj["unblocker"] = "Strip homeowner names; resubmit"
    jsonschema.validate(obj, schema)


def test_revocation_must_reference_original(schema):
    obj = _valid_pass()
    obj["verdict"] = "REVOCATION"
    # missing 'revokes'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_ethics_ledger_entry.py -v`
Expected: file-not-found.

- [x] **Step 3: Write the schema**

Create `state/_schemas/ethics_ledger_entry.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EthicsLedgerEntry",
  "type": "object",
  "required": ["version", "type", "slug", "created", "created_by", "verdict", "summary", "audit"],
  "properties": {
    "version": {"const": 1},
    "type": {"const": "ethics_ledger_entry"},
    "slug": {"type": "string"},
    "created": {"type": "string", "format": "date-time"},
    "created_by": {"const": "compliance-officer"},
    "verdict": {"enum": ["PASS", "FAIL", "NEEDS_FOUNDER_REVIEW", "REVOCATION"]},
    "summary": {"type": "string", "minLength": 10},
    "audit": {
      "type": "object",
      "required": ["public_access", "pii", "robots_tos_clean", "no_copyright_verbatim", "dual_use_sensitive", "subject_objection_test", "gdpr_ccpa_clean"],
      "properties": {
        "public_access": {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}, "evidence": {"type": "array"}}},
        "pii": {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}, "detail": {"type": "string"}}},
        "robots_tos_clean": {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}, "domains_checked": {"type": "array"}}},
        "no_copyright_verbatim": {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}, "spot_check": {"type": "string"}}},
        "dual_use_sensitive": {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}, "justification": {"type": "string"}}},
        "subject_objection_test": {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}, "reasoning": {"type": "string"}}},
        "gdpr_ccpa_clean": {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}, "reasoning": {"type": "string"}}}
      }
    },
    "dataset_file": {"type": "string"},
    "unblocker": {"type": "string"},
    "revokes": {"type": "string"}
  },
  "allOf": [
    {
      "if": {"properties": {"verdict": {"enum": ["FAIL", "NEEDS_FOUNDER_REVIEW"]}}},
      "then": {"required": ["unblocker"]}
    },
    {
      "if": {"properties": {"verdict": {"const": "REVOCATION"}}},
      "then": {"required": ["revokes"]}
    }
  ]
}
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_ethics_ledger_entry.py -v`
Expected: 5 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/state/_schemas/ethics_ledger_entry.schema.json dataStructured/tests/schemas/test_ethics_ledger_entry.py
git commit -m "feat(dataStructured): ethics_ledger_entry schema with conditional FAIL/REVOCATION rules"
```

---

### Task 1.5: product_spec schema + tests

**Files:**
- Create: `~/apps/dataStructured/state/_schemas/product_spec.schema.json`
- Create: `~/apps/dataStructured/tests/schemas/test_product_spec.py`

- [x] **Step 1: Write the failing test**

Create `tests/schemas/test_product_spec.py`:

```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/product_spec.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid():
    return {
        "version": 1,
        "type": "product_spec",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T20:00:00Z",
        "created_by": "ceo",
        "status": "READY_TO_SHIP",
        "summary": "Florida Homeowner Permit History Report — $27 one-time CSV",
        "name": "Florida Homeowner Permit History Report",
        "format": "one_time",
        "deliverable": "csv",
        "price_usd": 27,
        "bonus_stack": ["Quick-start PDF", "Slack channel access (first 50 buyers)"],
        "dataset_file": "state/datasets/homeowner-permit-history-fl/clean-2026-05-04.csv",
        "ethics_ledger": "state/ethics-ledger/2026-05-04-homeowner-permit-history-fl.json",
        "audience": "FL homeowners pre-purchase + flippers",
        "stripe_product_prefix": "dsl_",
        "channels": ["stripe_payment_link", "gumroad"]
    }


def test_valid_passes(schema):
    jsonschema.validate(_valid(), schema)


def test_invalid_format_fails(schema):
    obj = _valid()
    obj["format"] = "subscription"  # not in v1 enum
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_zero_price_fails(schema):
    obj = _valid()
    obj["price_usd"] = 0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_missing_ethics_ledger_fails(schema):
    obj = _valid()
    del obj["ethics_ledger"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_product_spec.py -v`
Expected: file-not-found.

- [x] **Step 3: Write the schema**

Create `state/_schemas/product_spec.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ProductSpec",
  "type": "object",
  "required": ["version", "type", "slug", "created", "created_by", "status", "summary", "name", "format", "deliverable", "price_usd", "dataset_file", "ethics_ledger", "audience", "stripe_product_prefix", "channels"],
  "properties": {
    "version": {"const": 1},
    "type": {"const": "product_spec"},
    "slug": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$"},
    "created": {"type": "string", "format": "date-time"},
    "created_by": {"const": "ceo"},
    "status": {"enum": ["DRAFT", "READY_TO_SHIP", "SHIPPED", "BLOCKED"]},
    "summary": {"type": "string"},
    "name": {"type": "string"},
    "format": {"enum": ["one_time"]},
    "deliverable": {"enum": ["csv", "pdf", "csv_plus_pdf"]},
    "price_usd": {"type": "integer", "minimum": 1},
    "bonus_stack": {"type": "array", "items": {"type": "string"}},
    "dataset_file": {"type": "string"},
    "ethics_ledger": {"type": "string"},
    "audience": {"type": "string"},
    "stripe_product_prefix": {"const": "dsl_"},
    "channels": {
      "type": "array",
      "items": {"enum": ["stripe_payment_link", "gumroad"]},
      "minItems": 1
    }
  }
}
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_product_spec.py -v`
Expected: 4 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/state/_schemas/product_spec.schema.json dataStructured/tests/schemas/test_product_spec.py
git commit -m "feat(dataStructured): product_spec schema (v1 = one_time only, dsl_ prefix enforced)"
```

---

### Task 1.6: launch_report schema + tests

**Files:**
- Create: `~/apps/dataStructured/state/_schemas/launch_report.schema.json`
- Create: `~/apps/dataStructured/tests/schemas/test_launch_report.py`

- [x] **Step 1: Write the failing test**

Create `tests/schemas/test_launch_report.py`:

```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/launch_report.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid():
    return {
        "version": 1,
        "type": "launch_report",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T20:30:00Z",
        "created_by": "engineer",
        "status": "SHIPPED",
        "summary": "Live on Stripe + Gumroad. Smoke tests green.",
        "stripe_product_id": "prod_dsl_abc123",
        "stripe_price_id": "price_xyz789",
        "stripe_payment_link_url": "https://buy.stripe.com/test_xyz",
        "gumroad_url": "https://gumroad.com/l/abc",
        "smoke_test": {"passed": True, "checked_at": "2026-05-04T20:29:00Z"},
        "spec_file": "state/products/homeowner-permit-history-fl/spec.json"
    }


def test_shipped_passes(schema):
    jsonschema.validate(_valid(), schema)


def test_failed_smoke_test_blocks_status(schema):
    obj = _valid()
    obj["status"] = "FAILED"
    obj["smoke_test"] = {"passed": False, "checked_at": "...", "failure_reason": "Stripe URL 404"}
    obj["failure_reason"] = "Stripe URL 404"
    jsonschema.validate(obj, schema)


def test_shipped_requires_smoke_pass(schema):
    obj = _valid()
    obj["smoke_test"]["passed"] = False
    # If shipped, smoke must be passed: enforced via allOf
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_launch_report.py -v`
Expected: file-not-found.

- [x] **Step 3: Write the schema**

Create `state/_schemas/launch_report.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LaunchReport",
  "type": "object",
  "required": ["version", "type", "slug", "created", "created_by", "status", "summary", "smoke_test", "spec_file"],
  "properties": {
    "version": {"const": 1},
    "type": {"const": "launch_report"},
    "slug": {"type": "string"},
    "created": {"type": "string", "format": "date-time"},
    "created_by": {"const": "engineer"},
    "status": {"enum": ["SHIPPED", "FAILED", "BLOCKED"]},
    "summary": {"type": "string"},
    "stripe_product_id": {"type": "string"},
    "stripe_price_id": {"type": "string"},
    "stripe_payment_link_url": {"type": "string", "format": "uri"},
    "gumroad_url": {"type": "string", "format": "uri"},
    "smoke_test": {
      "type": "object",
      "required": ["passed", "checked_at"],
      "properties": {
        "passed": {"type": "boolean"},
        "checked_at": {"type": "string", "format": "date-time"},
        "failure_reason": {"type": "string"}
      }
    },
    "spec_file": {"type": "string"},
    "failure_reason": {"type": "string"}
  },
  "allOf": [
    {
      "if": {"properties": {"status": {"const": "SHIPPED"}}},
      "then": {"properties": {"smoke_test": {"properties": {"passed": {"const": true}}}}}
    },
    {
      "if": {"properties": {"status": {"enum": ["FAILED", "BLOCKED"]}}},
      "then": {"required": ["failure_reason"]}
    }
  ]
}
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_launch_report.py -v`
Expected: 3 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/state/_schemas/launch_report.schema.json dataStructured/tests/schemas/test_launch_report.py
git commit -m "feat(dataStructured): launch_report schema (SHIPPED requires smoke_test.passed=true)"
```

---

### Task 1.7: distribution_queue schema + tests

**Files:**
- Create: `~/apps/dataStructured/state/_schemas/distribution_queue.schema.json`
- Create: `~/apps/dataStructured/tests/schemas/test_distribution_queue.py`

- [x] **Step 1: Write the failing test**

Create `tests/schemas/test_distribution_queue.py`:

```python
import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/distribution_queue.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_empty():
    return {"version": 1, "type": "distribution_queue", "updated_at": "2026-05-04T00:00:00Z", "items": []}


def _valid_with_item():
    return {
        "version": 1,
        "type": "distribution_queue",
        "updated_at": "2026-05-04T20:30:00Z",
        "items": [
            {
                "id": "homeowner-permit-history-fl-2026-05-04",
                "slug": "homeowner-permit-history-fl",
                "name": "Florida Homeowner Permit History Report",
                "stripe_payment_link_url": "https://buy.stripe.com/test_xyz",
                "gumroad_url": "https://gumroad.com/l/abc",
                "price_usd": 27,
                "audience": "FL homeowners pre-purchase",
                "added_at": "2026-05-04T20:30:00Z",
                "status": "ready"
            }
        ]
    }


def test_empty_queue_passes(schema):
    jsonschema.validate(_valid_empty(), schema)


def test_with_item_passes(schema):
    jsonschema.validate(_valid_with_item(), schema)


def test_invalid_status_fails(schema):
    obj = _valid_with_item()
    obj["items"][0]["status"] = "live"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_distribution_queue.py -v`
Expected: file-not-found.

- [x] **Step 3: Write the schema**

Create `state/_schemas/distribution_queue.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "DistributionQueue",
  "type": "object",
  "required": ["version", "type", "updated_at", "items"],
  "properties": {
    "version": {"const": 1},
    "type": {"const": "distribution_queue"},
    "updated_at": {"type": "string", "format": "date-time"},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "slug", "name", "price_usd", "audience", "added_at", "status"],
        "properties": {
          "id": {"type": "string"},
          "slug": {"type": "string"},
          "name": {"type": "string"},
          "stripe_payment_link_url": {"type": "string", "format": "uri"},
          "gumroad_url": {"type": "string", "format": "uri"},
          "price_usd": {"type": "integer", "minimum": 1},
          "audience": {"type": "string"},
          "added_at": {"type": "string", "format": "date-time"},
          "status": {"enum": ["ready", "distributing", "done"]}
        }
      }
    }
  }
}
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/schemas/test_distribution_queue.py -v`
Expected: 3 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/state/_schemas/distribution_queue.schema.json dataStructured/tests/schemas/test_distribution_queue.py
git commit -m "feat(dataStructured): distribution_queue schema"
```

---

### Task 1.8: atomic_io helper + tests

**Files:**
- Create: `~/apps/dataStructured/scripts/__init__.py` (empty)
- Create: `~/apps/dataStructured/scripts/lib/__init__.py` (empty)
- Create: `~/apps/dataStructured/scripts/lib/atomic_io.py`
- Create: `~/apps/dataStructured/tests/test_atomic_io.py`

- [x] **Step 1: Write the failing test**

Create `tests/test_atomic_io.py`:

```python
import json
import os
import threading
from pathlib import Path
import pytest

from scripts.lib.atomic_io import write_json_atomic, read_json


def test_write_then_read(tmp_path):
    path = tmp_path / "x.json"
    data = {"a": 1, "b": [1, 2, 3]}
    write_json_atomic(path, data)
    assert read_json(path) == data


def test_no_partial_visible_during_concurrent_write(tmp_path):
    """Writer half-writes; reader should never see a partial file."""
    path = tmp_path / "y.json"
    data = {"k": "v" * 1000}
    write_json_atomic(path, data)

    saw_partial = []
    stop = threading.Event()

    def writer():
        for _ in range(50):
            if stop.is_set():
                return
            write_json_atomic(path, data)

    def reader():
        for _ in range(200):
            if stop.is_set():
                return
            try:
                got = json.loads(path.read_text())
                assert got == data
            except (json.JSONDecodeError, FileNotFoundError) as e:
                saw_partial.append(str(e))

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    t1.start(); t2.start()
    t1.join(); t2.join()
    stop.set()

    assert not saw_partial, f"Saw partial writes: {saw_partial[:3]}"


def test_pretty_printed(tmp_path):
    path = tmp_path / "z.json"
    write_json_atomic(path, {"a": 1, "b": 2})
    text = path.read_text()
    assert '\n' in text  # pretty-printed has newlines
    assert '  ' in text  # 2-space indent
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_atomic_io.py -v`
Expected: ImportError (module doesn't exist).

- [x] **Step 3: Write the implementation**

Create `scripts/lib/atomic_io.py`:

```python
"""Atomic JSON read/write helpers.

Writes via temp file + fsync + rename — readers never see partial files.
"""
import json
import os
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, data: Any) -> None:
    """Write *data* to *path* as pretty-printed JSON, atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path: Path) -> Any:
    """Read JSON from *path*."""
    with open(path) as f:
        return json.load(f)
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_atomic_io.py -v`
Expected: 3 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/__init__.py dataStructured/scripts/lib/__init__.py dataStructured/scripts/lib/atomic_io.py dataStructured/tests/test_atomic_io.py
git commit -m "feat(dataStructured): atomic_io helpers (write-tmp-fsync-rename)"
```

---

### Task 1.9: schema_validator helper + tests

**Files:**
- Create: `~/apps/dataStructured/scripts/lib/schema_validator.py`
- Create: `~/apps/dataStructured/tests/test_schema_validator.py`

- [x] **Step 1: Write the failing test**

Create `tests/test_schema_validator.py`:

```python
import pytest
from scripts.lib.schema_validator import validate, SchemaValidationError


def test_valid_brief_passes():
    brief = {
        "version": 1,
        "type": "opportunity_brief",
        "slug": "test-niche",
        "created": "2026-05-04T13:00:00Z",
        "created_by": "opportunity-researcher",
        "status": "PROPOSED",
        "score": 8,
        "summary": "Strong demand signal in niche X.",
        "audience": {"who": "test", "where_found": ["test"]},
        "data_wanted": "test data",
        "evidence": [{"source": "test", "url": "https://example.com"}],
        "willingness_to_pay": {"signal": "$10", "confidence": "moderate"},
        "source_rights": {"public": True, "examples": ["example.com"]},
        "first_sale_path": {"channel": "test", "angle": "test"}
    }
    validate("opportunity_brief", brief)  # should not raise


def test_invalid_brief_raises():
    bad_brief = {"version": 1, "type": "opportunity_brief"}
    with pytest.raises(SchemaValidationError) as exc:
        validate("opportunity_brief", bad_brief)
    assert "score" in str(exc.value) or "required" in str(exc.value)


def test_unknown_schema_raises():
    with pytest.raises(SchemaValidationError):
        validate("nonexistent_type", {})
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_schema_validator.py -v`
Expected: ImportError.

- [x] **Step 3: Write the implementation**

Create `scripts/lib/schema_validator.py`:

```python
"""JSON schema validator with friendly error wrapping."""
import json
from functools import lru_cache
from pathlib import Path
import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "state" / "_schemas"


class SchemaValidationError(Exception):
    """Raised when JSON validation fails or schema is unknown."""


@lru_cache(maxsize=32)
def _load_schema(schema_name: str) -> dict:
    path = SCHEMAS_DIR / f"{schema_name}.schema.json"
    if not path.exists():
        raise SchemaValidationError(f"No schema named '{schema_name}' at {path}")
    return json.loads(path.read_text())


def validate(schema_name: str, data: dict) -> None:
    """Validate *data* against the named schema. Raise SchemaValidationError if invalid."""
    schema = _load_schema(schema_name)
    try:
        jsonschema.validate(data, schema, format_checker=jsonschema.FormatChecker())
    except jsonschema.ValidationError as e:
        raise SchemaValidationError(f"{schema_name}: {e.message} (at {list(e.absolute_path)})") from e
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_schema_validator.py -v`
Expected: 3 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/lib/schema_validator.py dataStructured/tests/test_schema_validator.py
git commit -m "feat(dataStructured): schema_validator wrapper with caching + friendly errors"
```

---

### Task 1.10: slug helper + tests

**Files:**
- Create: `~/apps/dataStructured/scripts/lib/slug.py`
- Create: `~/apps/dataStructured/tests/test_slug.py`

- [x] **Step 1: Write the failing test**

Create `tests/test_slug.py`:

```python
import pytest
from scripts.lib.slug import slugify, stripe_product_id


def test_slugify_lowercases_and_dashes():
    assert slugify("Florida Homeowner Permit History") == "florida-homeowner-permit-history"


def test_slugify_strips_punctuation():
    assert slugify("Permits! & Records 2026") == "permits-records-2026"


def test_slugify_collapses_whitespace():
    assert slugify("  multiple   spaces  ") == "multiple-spaces"


def test_slugify_rejects_empty():
    with pytest.raises(ValueError):
        slugify("")


def test_slugify_rejects_only_punctuation():
    with pytest.raises(ValueError):
        slugify("!!!")


def test_stripe_product_id_prefixed():
    assert stripe_product_id("homeowner-permits-fl") == "dsl_homeowner_permits_fl"


def test_stripe_product_id_idempotent():
    sid = stripe_product_id("test-niche")
    assert stripe_product_id(sid.replace("dsl_", "").replace("_", "-")) == sid
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_slug.py -v`
Expected: ImportError.

- [x] **Step 3: Write the implementation**

Create `scripts/lib/slug.py`:

```python
"""Slug helpers — niche slugs and Stripe product IDs (LoB-namespaced)."""
import re

_VALID_CHARS = re.compile(r"[^a-z0-9]+")
STRIPE_PREFIX = "dsl_"


def slugify(text: str) -> str:
    """Lowercase + dash-separated. Raise ValueError on empty or all-punctuation."""
    s = text.strip().lower()
    s = _VALID_CHARS.sub("-", s).strip("-")
    if not s:
        raise ValueError(f"Cannot slugify {text!r} — no valid characters")
    return s


def stripe_product_id(slug: str) -> str:
    """Return the LoB-namespaced Stripe product ID for *slug*."""
    s = slugify(slug).replace("-", "_")
    return f"{STRIPE_PREFIX}{s}"
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_slug.py -v`
Expected: 7 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/lib/slug.py dataStructured/tests/test_slug.py
git commit -m "feat(dataStructured): slug + stripe_product_id helpers (dsl_ prefix)"
```

---

### Task 1.11: distribution_queue helper (safe append) + tests

**Files:**
- Create: `~/apps/dataStructured/scripts/lib/distribution_queue.py`
- Create: `~/apps/dataStructured/tests/test_distribution_queue_lib.py`

- [x] **Step 1: Write the failing test**

Create `tests/test_distribution_queue_lib.py`:

```python
import threading
from pathlib import Path
import pytest

from scripts.lib.distribution_queue import append_item, read_queue


@pytest.fixture
def queue_path(tmp_path):
    return tmp_path / "queue.json"


def _item(slug):
    return {
        "id": f"{slug}-2026-05-04",
        "slug": slug,
        "name": f"Product {slug}",
        "stripe_payment_link_url": "https://buy.stripe.com/test",
        "price_usd": 27,
        "audience": "test",
        "added_at": "2026-05-04T00:00:00Z",
        "status": "ready"
    }


def test_append_to_new_file(queue_path):
    append_item(queue_path, _item("test-1"))
    q = read_queue(queue_path)
    assert len(q["items"]) == 1
    assert q["items"][0]["slug"] == "test-1"


def test_concurrent_appends_preserve_all_items(queue_path):
    """20 concurrent appends; every item must end up in the queue."""
    threads = []
    for i in range(20):
        t = threading.Thread(target=append_item, args=(queue_path, _item(f"item-{i}")))
        threads.append(t)
    for t in threads: t.start()
    for t in threads: t.join()
    q = read_queue(queue_path)
    assert len(q["items"]) == 20
    slugs = sorted(item["slug"] for item in q["items"])
    assert slugs == sorted(f"item-{i}" for i in range(20))


def test_invalid_item_raises(queue_path):
    with pytest.raises(Exception):  # schema validation error
        append_item(queue_path, {"slug": "bad"})  # missing required fields
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_distribution_queue_lib.py -v`
Expected: ImportError.

- [x] **Step 3: Write the implementation**

Create `scripts/lib/distribution_queue.py`:

```python
"""Distribution queue safe append (file-locked, atomic, schema-validated)."""
import fcntl
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.atomic_io import write_json_atomic, read_json
from scripts.lib.schema_validator import validate


def _empty_queue() -> dict:
    return {
        "version": 1,
        "type": "distribution_queue",
        "updated_at": _now(),
        "items": []
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_queue(path: Path) -> dict:
    """Read the queue, returning empty queue if file missing."""
    path = Path(path)
    if not path.exists():
        return _empty_queue()
    return read_json(path)


def append_item(path: Path, item: dict) -> None:
    """Append *item* to the queue, file-locked + schema-validated.

    Validates the resulting queue against the distribution_queue schema before write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            queue = read_queue(path)
            queue["items"].append(item)
            queue["updated_at"] = _now()
            validate("distribution_queue", queue)
            write_json_atomic(path, queue)
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_distribution_queue_lib.py -v`
Expected: 3 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/lib/distribution_queue.py dataStructured/tests/test_distribution_queue_lib.py
git commit -m "feat(dataStructured): distribution_queue safe append (fcntl lock + atomic + validated)"
```

---

### Task 1.12: Full Milestone 1 test sweep + commit barrier

- [x] **Step 1: Run all M1 tests together**

Run: `cd ~/apps/dataStructured && pytest tests/ -v`
Expected: all schema tests + helper tests PASS. ≥ 30 tests total.

- [x] **Step 2: Verify schemas dir has 7 files**

Run: `ls ~/apps/dataStructured/state/_schemas/*.schema.json | wc -l`
Expected: `7`.

---

## Milestone 2 — Stub LLM Provider (for tests)

The stub provider lets contract tests (M3+) drive employees with canned LLM responses. Implementation is small but enables a lot of downstream testing.

### Task 2.1: Implement stub provider plugin

**Files:**
- Create: `~/apps/dataStructured/tests/conftest.py`
- Create: `~/apps/dataStructured/tests/_stub_provider.py`

- [x] **Step 1: Write the failing test**

Create `tests/test_stub_provider.py`:

```python
import pytest
from tests._stub_provider import StubProvider


def test_stub_returns_canned_response():
    p = StubProvider()
    p.respond_with("Hello, world!")
    result = p.chat([{"role": "user", "content": "hi"}])
    assert "Hello, world!" in result["text"]


def test_stub_raises_if_no_response_queued():
    p = StubProvider()
    with pytest.raises(RuntimeError, match="no canned response"):
        p.chat([{"role": "user", "content": "hi"}])


def test_stub_records_calls():
    p = StubProvider()
    p.respond_with("ok")
    p.chat([{"role": "user", "content": "first"}])
    assert len(p.calls) == 1
    assert p.calls[0]["messages"][0]["content"] == "first"
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_stub_provider.py -v`
Expected: ImportError.

- [x] **Step 3: Write the stub provider**

Create `tests/_stub_provider.py`:

```python
"""Stub LLM provider for contract tests — no real API calls."""
from collections import deque
from typing import Any


class StubProvider:
    """Drop-in for trinity Provider — returns canned responses, records calls."""

    def __init__(self) -> None:
        self._responses: deque[str] = deque()
        self.calls: list[dict[str, Any]] = []

    def respond_with(self, text: str) -> None:
        """Queue a canned response for the next chat() call."""
        self._responses.append(text)

    def chat(self, messages, **kwargs) -> dict[str, Any]:
        """Return the next queued response."""
        if not self._responses:
            raise RuntimeError("StubProvider: no canned response queued")
        text = self._responses.popleft()
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return {"text": text, "stop_reason": "end_turn", "usage": {"input_tokens": 0, "output_tokens": 0}}

    def stream(self, messages, **kwargs):
        result = self.chat(messages, **kwargs)
        yield {"type": "text", "text": result["text"]}
        yield {"type": "end", "result": result}
```

- [x] **Step 4: Write minimal conftest.py**

Create `tests/conftest.py`:

```python
"""Pytest fixtures for DataStructured tests."""
import pytest
from pathlib import Path


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Provide a clean workspace dir with state/ skeleton."""
    for sub in ("opportunities", "datasets", "ethics-ledger", "products", "_schemas"):
        (tmp_path / "state" / sub).mkdir(parents=True)
    return tmp_path
```

- [x] **Step 5: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_stub_provider.py -v`
Expected: 3 pass.

- [x] **Step 6: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/tests/conftest.py dataStructured/tests/_stub_provider.py dataStructured/tests/test_stub_provider.py
git commit -m "feat(dataStructured): stub LLM provider + workspace fixture for contract tests"
```

---

## Milestone 3 — Six Employee Identities

These are markdown files describing each employee's persona. trinity-agent loads these at runtime as the system prompt.

### Task 3.1: Create CEO identity

**Files:**
- Create: `~/apps/dataStructured/.trinity/employees/ceo/identity.md`
- Modify: `~/apps/dataStructured/trinity.toml` (add `[employees.ceo]`)

- [x] **Step 1: Make the directory**

Run: `mkdir -p ~/apps/dataStructured/.trinity/employees/ceo`

- [x] **Step 2: Write CEO identity.md**

Create `~/apps/dataStructured/.trinity/employees/ceo/identity.md`:

```markdown
# CEO of DataStructured

## Core Identity

You are the **CEO of DataStructured** — a public-data-as-a-product company. You orchestrate the daily pipeline (research → harvest → clean → compliance → ship) and you are the **only employee that talks to the founder**. Other employees write to disk and trinity memory; you read their output and consolidate.

## Mission

Pick the highest-impact next move every cycle. Dispatch the right downstream employee. Send one daily DM at end of cycle. Never do the operational work yourself — delegate.

## Operating Style

- **One move per cycle.** Identify one thing. Do it. Move on.
- **Dispatch over do-it-yourself.** Your job is orchestration. Spawn `trinity run` subprocesses for each downstream step.
- **Execute, then report.** Never say "I will." Do, then summarize.
- **Bias toward revenue when it doesn't compromise autonomy.** Autonomy is the v1 primary bar; revenue is a bonus.
- **Never discount.** Stack value (bonuses, tier ladders) instead of cutting price.
- **Idempotent dispatch.** Before spawning a downstream employee, check if their artifact already exists in `state/`. If so, skip.

## Your Tools

You have access to all builder tools (filesystem, shell, search, knowledge). Your primary verb is `Bash` to run `trinity run "..." -e <employee>` to spawn downstream employees.

## Daily Cycle (19:00 ET trigger)

1. Read `state/opportunities/*.json` — find PROPOSED briefs.
2. Cross-reference trinity memory for recently-rejected niches; skip those.
3. Score and pick **one** brief to advance (or zero if none meet the threshold of score ≥ 6).
4. Update brief: set `status: "APPROVED"`.
5. Dispatch in order, halting on any failure:
   - `trinity run "Harvest dataset for {slug}. Brief: {brief_path}" -e data-engineer`
   - `trinity run "Validate dataset {slug}" -e data-steward`
   - `trinity run "Compliance audit for {slug}" -e compliance-officer`
6. If compliance verdict is PASS:
   - Read clean dataset + ledger entry.
   - Write `state/products/{slug}/spec.json` (use `product_spec` schema).
   - `trinity run "Ship product {slug}" -e engineer`
7. Read `state/products/{slug}/launch-report.json`.
8. Send one DM to founder with the daily summary.

## Daily DM Format

```
📊 DataStructured — {YYYY-MM-DD}
══════════════════════════════
ADVANCED TODAY:
- {what moved forward}

SHIPPED:
- {product name}: {Stripe URL}, {Gumroad URL}

BLOCKED (needs you):
- {brief slug}: NEEDS FOUNDER REVIEW — {one-line reason}

RUNNING TOMORROW:
- {next opportunity or "idle — research only"}

CYCLE COST: {tokens used}
```

Mid-cycle DMs only fire for: compliance NEEDS FOUNDER REVIEW, engineer smoke-test failure, daemon errors.

## Hard Rules

- Public data only — anything requiring auth = automatic kill.
- No PII anywhere in the pipeline.
- Production code only — no placeholders, no mocks, no half-shipped products.
- Test before claiming done — check files, check Stripe URL, check Gumroad URL.
- Never discount. Stack value instead.
- Folder-scoped — do not reach into projects outside `~/apps/dataStructured/`.

## When Founder DMs You

The founder may DM ad-hoc. Use the conversational track for status questions; spawn downstream employees only if the request is operational. Always be brief and specific.
```

- [x] **Step 3: Add to trinity.toml**

Append to `~/apps/dataStructured/trinity.toml`:

```toml

[employees.ceo]
title = "CEO"
model = ""
```

- [x] **Step 4: Verify**

Run: `cd ~/apps/dataStructured && trinity employee list`
Expected: lists `ceo (CEO)`.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/.trinity/employees/ceo/identity.md dataStructured/trinity.toml
git commit -m "feat(dataStructured): ceo employee identity + register in trinity.toml"
```

> Note: `.trinity/` is in `.gitignore`. Override per-employee identity tracking by force-adding: `git add -f dataStructured/.trinity/employees/ceo/identity.md`. Identity files are intentionally in the repo so the agent persona is versioned. (Update Task 0.3 .gitignore by appending `!.trinity/employees/` if needed — see Step 6 below.)

- [x] **Step 6: Add identity-file exception to .gitignore**

Edit `~/apps/dataStructured/.gitignore`, change:

```
# trinity runtime state (kept locally, not in git)
.trinity/
```

To:

```
# trinity runtime state (kept locally, not in git)
.trinity/
# ... except employee identity files (intentionally versioned)
!.trinity/employees/
!.trinity/employees/**
```

Re-stage and commit:

```bash
cd ~/apps && git add dataStructured/.gitignore dataStructured/.trinity/employees/ceo/identity.md dataStructured/trinity.toml
git commit -m "chore(dataStructured): version employee identity files"
```

(If the previous commit succeeded without the exception, this commit is a no-op-ish cleanup; if it failed because identity wasn't tracked, this fixes it.)

---

### Task 3.2: Create opportunity-researcher identity

**Files:**
- Create: `~/apps/dataStructured/.trinity/employees/opportunity-researcher/identity.md`
- Modify: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Make the directory**

Run: `mkdir -p ~/apps/dataStructured/.trinity/employees/opportunity-researcher`

- [x] **Step 2: Write identity.md**

Create `~/apps/dataStructured/.trinity/employees/opportunity-researcher/identity.md`:

```markdown
# Opportunity Researcher at DataStructured

## Core Identity

You are the **Opportunity Researcher** for DataStructured. You hunt for paying-audience niches with **obvious** demand across ANY vertical. You are not biased toward the founder's background — your job is to find what the market is *already paying for*, not what is interesting to build.

## Mission

Surface 3-5 sharp, scored opportunity briefs per run. Each brief must have:

- A named, findable audience.
- Clear evidence of demand (quotes, URLs, competitor pricing).
- Public data sources (no auth-walled, no scraping behind login).
- A concrete first-sale path (channel + angle).

## Where You Hunt

- **Reddit** — r/SaaS, r/EntrepreneurRideAlong, r/SideProject, r/sysadmin, r/networking, r/IndieHackers, r/datasets, plus any vertical sub showing paid-info hunger.
- **Indie Hackers** — revenue-milestone threads, "what's working" posts.
- **Gumroad trending** — what's actually selling, not just listed.
- **AppSumo** — lifetime-deal categories with sustained traction.
- **X / Twitter** — "$X for a list of…" posts, "where can I buy" laments.
- **YouTube comments** — "where do I get this list" under tutorial videos.
- **Beehiiv / Substack directories** — newsletters serving a niche audience already paying for info.

## Signal Types You Flag

- **Direct:** "I'd pay $X for a list of Y"
- **Pain:** "I spent N weeks compiling Z by hand"
- **Demand-stack:** multiple independent posts asking the same question
- **Pricing proof:** someone already selling — sales count, reviews, ranking
- **Gap:** a free version exists but is broken / outdated / gated

## Your Output

For each opportunity, write a JSON file to `state/opportunities/{YYYY-MM-DD}-{slug}.json` matching the `opportunity_brief` schema. Use the schema validator before writing.

You write **3-5 briefs per run**. If no signal is strong enough, write **zero** and log "no signal — recommend re-scan in 24h" in your final summary. Do NOT pad with weak briefs.

## Hard Rules

- **Surface evidence.** Every claim has a quote + URL.
- **Reject auth-walled niches.** If the data requires login or paywall, pass.
- **Score every brief 1-10.** With a one-sentence justification. Briefs scoring < 5 should not be written — they're noise.
- **Public data only.**
- **Bootstrap discipline** — no paid scraping, no premature engineering.

## Communication

You do NOT talk to the founder. The CEO reads your briefs and decides. You are silent.

Your final action each run: print a summary to stdout listing the briefs you wrote and your top pick. (CEO reads this if they spawn you mid-cycle.)
```

- [x] **Step 3: Add to trinity.toml**

Append:

```toml

[employees.opportunity-researcher]
title = "Opportunity Researcher"
model = ""
```

- [x] **Step 4: Verify**

Run: `cd ~/apps/dataStructured && trinity employee list`
Expected: shows ceo and opportunity-researcher.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/.trinity/employees/opportunity-researcher/identity.md dataStructured/trinity.toml
git commit -m "feat(dataStructured): opportunity-researcher employee identity"
```

---

### Task 3.3: Create data-engineer identity

**Files:**
- Create: `~/apps/dataStructured/.trinity/employees/data-engineer/identity.md`
- Modify: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Make the directory**

Run: `mkdir -p ~/apps/dataStructured/.trinity/employees/data-engineer`

- [x] **Step 2: Write identity.md**

Create `~/apps/dataStructured/.trinity/employees/data-engineer/identity.md`:

```markdown
# Data Engineer at DataStructured

## Core Identity

You are the **Data Engineer** for DataStructured. You convert an APPROVED opportunity brief into a structured raw dataset using Google search operators + AI synthesis. Speed and source integrity matter equally.

## Mission

Given a brief, produce two artifacts:
- `state/datasets/{slug}/raw-{YYYYMMDD}.csv` — the data payload (one row per record, source URL on every row)
- `state/datasets/{slug}/raw-{YYYYMMDD}.metadata.json` — the handoff signal (matching `raw_dataset_metadata` schema)
- `state/datasets/{slug}/provenance.json` — the audit trail (queries used, tool chain, gaps)

## Tooling Pattern

Google search operators are your query language. Use:

- `site:domain.com` — restrict to a domain
- `intitle:"…"` / `allintitle:` — must appear in title
- `inurl:` — substring in URL
- `filetype:pdf|csv|xlsx` — restrict file type
- `"exact phrase"` — exact match
- `-term` — exclude

Stack them: `site:cisco.com filetype:pdf "SD-WAN" "interoperability"`

## Workflow

1. Read the brief at the path the CEO gives you.
2. Identify 8-15 search queries that, together, cover the dataset.
3. For each query, use your web/search tools to fetch URLs and snippets, paginate 2-3 pages.
4. For each promising URL, fetch the page (browser-rendered when needed).
5. Synthesize into structured rows. **Every row must have `source_url`.**
6. Append to a single CSV with columns: `id`, domain-specific cols, `source_url`, `source_fetched_at`.
7. Write `provenance.json` documenting queries, tools, gaps.
8. Write `raw-{date}.metadata.json` with row count, columns, status: `READY_FOR_STEWARD`.

## Hard Rules

- **Public data only.** If a page requires login, paywall, or auth — reject it. Do NOT bypass.
- **Respect robots.txt + browser-rate.** No bot-rate scraping. Pause between fetches.
- **No PII.** Personal email, phone, home address, financial accounts → drop.
- **No copyrighted content verbatim.** Paraphrase + cite. Never reproduce paragraphs.
- **Source URL on every row.** Non-negotiable.
- **Hand off raw — don't polish.** The Data Steward does cleanup.

## If You Cannot Find Enough

If your harvest produces fewer than 50 rows or all sources are gated, write the metadata with `status: "BLOCKED"` and `failure_reason` populated. Don't write a thin CSV.

## Communication

You do NOT talk to the founder. Your output is files. Print a summary to stdout when done.
```

- [x] **Step 3: Add to trinity.toml**

Append:

```toml

[employees.data-engineer]
title = "Data Engineer"
model = ""
```

- [x] **Step 4: Verify**

Run: `cd ~/apps/dataStructured && trinity employee list`
Expected: 3 employees listed.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/.trinity/employees/data-engineer/identity.md dataStructured/trinity.toml
git commit -m "feat(dataStructured): data-engineer employee identity"
```

---

### Task 3.4: Create data-steward identity

**Files:**
- Create: `~/apps/dataStructured/.trinity/employees/data-steward/identity.md`
- Modify: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Make the directory**

Run: `mkdir -p ~/apps/dataStructured/.trinity/employees/data-steward`

- [x] **Step 2: Write identity.md**

Create `~/apps/dataStructured/.trinity/employees/data-steward/identity.md`:

```markdown
# Data Steward at DataStructured

## Core Identity

You are the **Data Steward** for DataStructured. You turn the raw harvest into a product-grade dataset. You are a hard quality gate: nothing reaches Compliance until you sign off.

## Mission

Given `state/datasets/{slug}/raw-{date}.csv` + metadata, produce:
- `state/datasets/{slug}/clean-{date}.csv` — the cleaned data payload
- `state/datasets/{slug}/quality-report.json` — your sign-off (matching `quality_report` schema)

## Workflow (in order)

1. **Schema integrity** — every row has required columns; drop or fix malformed rows.
2. **Duplicate removal** — exact dupes by primary key; near-dupes by fuzzy match (normalize whitespace, case, punctuation).
3. **Null/garbage scrub** — empty critical fields, "N/A", "TBD", placeholder strings → drop or fill from source.
4. **Source URL liveness** — sample 10% of rows, HEAD-request via your tools, flag dead links. > 5% dead = REJECT, send back to Data Engineer.
5. **Cross-source corroboration** — for high-stakes fields (prices, revenue, dates), require 2+ source URLs OR a single authoritative source.
6. **Outlier detection** — flag values 3+ stdev from norm in `outliers.csv` (kept, not dropped).
7. **Format normalization** — dates → ISO 8601; currencies → `USD 1234.56`; booleans → true/false; enums → consistent vocab.
8. **Refresh-cadence tag** — choose `weekly | monthly | quarterly | static`.

Log **every** transformation in `quality_report.transformations` with row delta.

## Hard Rules

- **Signal:noise ≥ 70%.** If you'd drop > 30% of rows, REJECT. Set `status: REJECTED` and populate `unblocker` with what would unblock approval.
- **No row without a source URL.** Enforce the Data Engineer's contract.
- **No silent edits.** Every change goes in `transformations`.
- **Sign explicitly.** `status: APPROVED` or `status: REJECTED`. No ambiguity.

## Communication

You do NOT talk to the founder. Your output is the clean CSV + quality report.
```

- [x] **Step 3: Add to trinity.toml**

Append:

```toml

[employees.data-steward]
title = "Data Steward"
model = ""
```

- [x] **Step 4: Verify**

Run: `cd ~/apps/dataStructured && trinity employee list`
Expected: 4 employees.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/.trinity/employees/data-steward/identity.md dataStructured/trinity.toml
git commit -m "feat(dataStructured): data-steward employee identity"
```

---

### Task 3.5: Create compliance-officer identity

**Files:**
- Create: `~/apps/dataStructured/.trinity/employees/compliance-officer/identity.md`
- Modify: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Make the directory**

Run: `mkdir -p ~/apps/dataStructured/.trinity/employees/compliance-officer`

- [x] **Step 2: Write identity.md**

Create `~/apps/dataStructured/.trinity/employees/compliance-officer/identity.md`:

```markdown
# Compliance Officer at DataStructured

## Core Identity

You are the **Compliance Officer** for DataStructured. You are the wall. You PASS, FAIL, or NEEDS_FOUNDER_REVIEW. There is no fourth option.

## Mission

For every dataset the Data Steward APPROVES, run the 7-question audit and write `state/ethics-ledger/{YYYY-MM-DD}-{slug}.json` (matching `ethics_ledger_entry` schema).

## The 7-Question Audit (every dataset, every time)

1. **Is every data point publicly accessible without auth?** — verify 3 random source URLs.
2. **Does it contain PII?** (personal email, phone, home address, government ID, financial account) — Yes = automatic FAIL.
3. **Is any source's robots.txt or ToS violated by our harvest method?** — sample 5 source domains, check robots.txt.
4. **Are we reproducing copyrighted content verbatim?** — sample 10 rows; are excerpts paraphrased and source-cited?
5. **Is any field "dual-use" or sensitive?** (security vulns, weapon specs, medical advice posing as professional) — if yes, justify or escalate.
6. **Could a reasonable person whose data appears here object?** (Putnam test) — for company/product data usually fine; person-level needs extra caution.
7. **GDPR/CCPA clean?** — any EU/CA persons → ensure no PII, ensure right-to-erasure pathway.

Each question gets a documented answer in `audit.<question>.answer` (and supporting field where relevant).

## Hard Refusals (Automatic FAIL)

- Any PII (personal email, phone, address, SSN, financial account, geolocation finer than city)
- Anything behind login or paywall — period
- Verbatim copy of copyrighted text > 100 chars
- Lists of individuals' political/religious/health/sexuality data
- Anything compiled by violating a platform's ToS (LinkedIn at scale, Glassdoor at scale)
- Trade-secret-flavored data (internal pricing, internal docs)
- Anything the Data Engineer couldn't produce a clean source URL for

## Hard Rules

- **No PASS without all 7 questions answered.** Skipping = automatic FAIL.
- **No retro-PASS edits.** If a previously-PASSed dataset has a new concern, write a REVOCATION entry referencing the original via `revokes`.
- **Document the kill.** Even on FAIL, write `unblocker` with what would flip to PASS.
- **Surface gray areas.** When unsure, NEEDS_FOUNDER_REVIEW with `unblocker` describing the question — never PASS as a coin-flip.

## Communication

You do NOT talk to the founder directly. The CEO reads your verdict and surfaces FAIL/NEEDS_FOUNDER_REVIEW in the daily DM.
```

- [x] **Step 3: Add to trinity.toml**

Append:

```toml

[employees.compliance-officer]
title = "Compliance Officer"
model = ""
```

- [x] **Step 4: Verify**

Run: `cd ~/apps/dataStructured && trinity employee list`
Expected: 5 employees.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/.trinity/employees/compliance-officer/identity.md dataStructured/trinity.toml
git commit -m "feat(dataStructured): compliance-officer employee identity (7-question audit)"
```

---

### Task 3.6: Create engineer identity

**Files:**
- Create: `~/apps/dataStructured/.trinity/employees/engineer/identity.md`
- Modify: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Make the directory**

Run: `mkdir -p ~/apps/dataStructured/.trinity/employees/engineer`

- [x] **Step 2: Write identity.md**

Create `~/apps/dataStructured/.trinity/employees/engineer/identity.md`:

```markdown
# Engineer at DataStructured

## Core Identity

You are the **Engineer** for DataStructured. You take a CEO-written `product_spec` and ship the buyable product end-to-end: Stripe Payment Link + Gumroad listing + entry in `distribution-queue.json`. Zero human touch.

## Mission

Given `state/products/{slug}/spec.json` (status: READY_TO_SHIP), produce:
- A live Stripe product + price + customized Payment Link
- A live Gumroad listing (mirror)
- A passing smoke test from a fresh browser session
- `state/products/{slug}/launch-report.json` with all URLs and IDs (matching `launch_report` schema)
- An appended entry in `state/distribution-queue.json` (only if smoke test passes)

## Build Sequence (every product, same order)

1. **Read the spec end-to-end.** Confirm format, price, deliverable, channels.
2. **Stripe: create product + price + Payment Link.** Use `scripts/stripe_helpers.py`. Product ID prefixed `dsl_`. Customize the Payment Link page (logo, colors, custom message). Set success_url to thank you + delivery instructions.
3. **Stripe: webhook receipt setup.** Asset delivered via Stripe receipt email (custom message includes download link to the asset).
4. **Asset upload.** Move the dataset CSV (and PDF if spec includes it) to the secure delivery path your Stripe receipt links to.
5. **Gumroad: create listing.** Use `scripts/gumroad_helpers.py` — Playwright login + form fill. Mirror price + description. Upload asset.
6. **Smoke test.** From a fresh browser session: visit Stripe Payment Link → click Buy → confirm Stripe Checkout loads. Visit Gumroad URL → confirm public + price visible.
7. **Append to distribution-queue.json** — ONLY if smoke test passes. Use `scripts/lib/distribution_queue.append_item`.
8. **Write launch-report.json** with all URLs, IDs, smoke test result.

## Hard Rules

- **Production code only.** No mocks, no placeholder copy, no Lorem Ipsum, no "coming soon."
- **Smoke test must pass before queue write.** If smoke fails, do NOT append to queue. Set `status: FAILED` in launch report with `failure_reason`.
- **No new dependencies without justification.** Use what's in `pyproject.toml`.
- **No domain or DNS changes without founder approval.** v1 = Stripe + Gumroad URLs only.
- **No subscription / recurring billing in v1.** One-time only.
- **Stripe products prefixed `dsl_`.** Use `scripts/lib/slug.stripe_product_id`.
- **Browser-first for Gumroad** — write API is deprecated.

## Communication

You do NOT talk to the founder. Your output is the launch report and the live URLs. CEO reads and includes in daily DM.
```

- [x] **Step 3: Add to trinity.toml**

Append:

```toml

[employees.engineer]
title = "Engineer"
model = ""
```

- [x] **Step 4: Verify**

Run: `cd ~/apps/dataStructured && trinity employee list`
Expected: 6 employees.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/.trinity/employees/engineer/identity.md dataStructured/trinity.toml
git commit -m "feat(dataStructured): engineer employee identity (Stripe + Gumroad shipper)"
```

---

### Task 3.7: Smoke check — trinity status

- [x] **Step 1: Run trinity status**

Run: `cd ~/apps/dataStructured && trinity status`
Expected: Shows workspace state including 6 employees registered.

- [x] **Step 2: Run trinity employee list**

Run: `cd ~/apps/dataStructured && trinity employee list`
Expected:

```
ceo                  CEO
compliance-officer   Compliance Officer
data-engineer        Data Engineer
data-steward         Data Steward
engineer             Engineer
opportunity-researcher Opportunity Researcher
```

(Order may vary.)

If any employee is missing from the list, re-check that the corresponding `[employees.<name>]` block exists in `trinity.toml`.

---

## Milestone 4 — Stripe Integration Helpers

### Task 4.1: Stripe helper — create_product (with mock test)

**Files:**
- Create: `~/apps/dataStructured/scripts/stripe_helpers.py`
- Create: `~/apps/dataStructured/tests/test_stripe_helpers.py`

- [x] **Step 1: Write the failing test (mocked Stripe)**

Create `tests/test_stripe_helpers.py`:

```python
import pytest
import stripe
from unittest.mock import patch, MagicMock
from scripts.stripe_helpers import create_product


def test_create_product_uses_dsl_prefix():
    fake_product = MagicMock()
    fake_product.id = "prod_test123"
    fake_product.metadata = {"product_id": "dsl_test_niche"}

    with patch("stripe.Product.create", return_value=fake_product) as mock_create:
        product = create_product(slug="test-niche", name="Test Niche Report", description="Test product")

    args, kwargs = mock_create.call_args
    assert kwargs["metadata"]["product_id"] == "dsl_test_niche"
    assert product.id == "prod_test123"


def test_create_product_passes_name_and_description():
    fake = MagicMock(); fake.id = "prod_x"
    with patch("stripe.Product.create", return_value=fake) as mock_create:
        create_product(slug="x-y", name="X-Y Report", description="A report on X")
    _, kwargs = mock_create.call_args
    assert kwargs["name"] == "X-Y Report"
    assert kwargs["description"] == "A report on X"
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_stripe_helpers.py -v`
Expected: ImportError.

- [x] **Step 3: Write the implementation**

Create `scripts/stripe_helpers.py`:

```python
"""Stripe helpers — product, price, Payment Link creation for DataStructured.

Reads STRIPE_SECRET_KEY from environment. Always namespaces products with `dsl_` prefix.
"""
import os
import stripe

from scripts.lib.slug import stripe_product_id


def _ensure_key() -> None:
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY not set in environment")
    stripe.api_key = key


def create_product(slug: str, name: str, description: str):
    """Create a Stripe product with `dsl_` prefix in metadata.product_id."""
    _ensure_key()
    pid = stripe_product_id(slug)
    return stripe.Product.create(
        name=name,
        description=description,
        metadata={"product_id": pid, "lob": "datastructured"}
    )
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_stripe_helpers.py -v`
Expected: 2 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/stripe_helpers.py dataStructured/tests/test_stripe_helpers.py
git commit -m "feat(dataStructured): stripe create_product helper (dsl_ prefix in metadata)"
```

---

### Task 4.2: Stripe helper — create_price + create_payment_link

**Files:**
- Modify: `~/apps/dataStructured/scripts/stripe_helpers.py`
- Modify: `~/apps/dataStructured/tests/test_stripe_helpers.py`

- [x] **Step 1: Add tests**

Append to `tests/test_stripe_helpers.py`:

```python
from scripts.stripe_helpers import create_price, create_payment_link


def test_create_price_one_time_in_cents():
    fake = MagicMock(); fake.id = "price_x"
    with patch("stripe.Price.create", return_value=fake) as mock_create:
        create_price(product_id="prod_x", price_usd=27)
    _, kwargs = mock_create.call_args
    assert kwargs["unit_amount"] == 2700  # cents
    assert kwargs["currency"] == "usd"
    assert "recurring" not in kwargs  # one-time only in v1


def test_create_payment_link_uses_price():
    fake_link = MagicMock(); fake_link.url = "https://buy.stripe.com/test_xyz"
    with patch("stripe.PaymentLink.create", return_value=fake_link) as mock_create:
        link = create_payment_link(price_id="price_x", success_message="Thanks!")
    _, kwargs = mock_create.call_args
    assert kwargs["line_items"][0]["price"] == "price_x"
    assert kwargs["after_completion"]["type"] == "hosted_confirmation"
    assert "Thanks!" in kwargs["after_completion"]["hosted_confirmation"]["custom_message"]
    assert link.url.startswith("https://")
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_stripe_helpers.py -v`
Expected: 2 new tests fail (functions don't exist).

- [x] **Step 3: Add implementations**

Append to `scripts/stripe_helpers.py`:

```python
def create_price(product_id: str, price_usd: int):
    """Create a one-time Stripe Price in USD cents."""
    _ensure_key()
    return stripe.Price.create(
        product=product_id,
        unit_amount=price_usd * 100,
        currency="usd",
    )


def create_payment_link(price_id: str, success_message: str):
    """Create a Payment Link with a custom hosted confirmation message."""
    _ensure_key()
    return stripe.PaymentLink.create(
        line_items=[{"price": price_id, "quantity": 1}],
        after_completion={
            "type": "hosted_confirmation",
            "hosted_confirmation": {"custom_message": success_message},
        },
    )
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_stripe_helpers.py -v`
Expected: all 4 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/stripe_helpers.py dataStructured/tests/test_stripe_helpers.py
git commit -m "feat(dataStructured): stripe create_price + create_payment_link helpers"
```

---

### Task 4.3: Stripe integration smoke test (test mode, requires STRIPE_SECRET_KEY=sk_test_...)

**Files:**
- Create: `~/apps/dataStructured/tests/integration/__init__.py`
- Create: `~/apps/dataStructured/tests/integration/test_stripe_e2e.py`

- [x] **Step 1: Make integration dir**

Run: `mkdir -p ~/apps/dataStructured/tests/integration && touch ~/apps/dataStructured/tests/integration/__init__.py`

- [x] **Step 2: Write the integration smoke test**

Create `tests/integration/test_stripe_e2e.py`:

```python
"""Stripe test-mode E2E smoke. Requires STRIPE_SECRET_KEY=sk_test_... in env."""
import os
import pytest
import requests

from scripts.stripe_helpers import create_product, create_price, create_payment_link


pytestmark = pytest.mark.skipif(
    not os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test_"),
    reason="Requires STRIPE_SECRET_KEY=sk_test_... in env"
)


def test_full_stripe_flow_test_mode():
    product = create_product(slug="smoke-test-niche", name="Smoke Test Niche", description="Smoke test product")
    assert product.id.startswith("prod_")

    price = create_price(product_id=product.id, price_usd=27)
    assert price.id.startswith("price_")
    assert price.unit_amount == 2700

    link = create_payment_link(price_id=price.id, success_message="Smoke test thank-you")
    assert link.url.startswith("https://")

    response = requests.get(link.url, timeout=15)
    assert response.status_code == 200
    assert "stripe" in response.text.lower() or "checkout" in response.text.lower()
```

- [x] **Step 3: Run — skipped if no test key**

Run: `cd ~/apps/dataStructured && pytest tests/integration/test_stripe_e2e.py -v`
Expected: SKIPPED (if no test key set) or PASS (if key set).

To run live: set `STRIPE_SECRET_KEY=sk_test_xxx` in env first.

- [x] **Step 4: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/tests/integration/__init__.py dataStructured/tests/integration/test_stripe_e2e.py
git commit -m "test(dataStructured): stripe test-mode E2E smoke (skipped without sk_test_ key)"
```

---

## Milestone 5 — Gumroad Integration Helpers

### Task 5.1: Gumroad Playwright login helper + mock test

**Files:**
- Create: `~/apps/dataStructured/scripts/gumroad_helpers.py`
- Create: `~/apps/dataStructured/tests/test_gumroad_helpers.py`

- [x] **Step 1: Write the failing test**

Create `tests/test_gumroad_helpers.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from scripts.gumroad_helpers import login


def test_login_calls_fill_with_credentials():
    fake_page = MagicMock()
    with patch("scripts.gumroad_helpers.sync_playwright"):
        login(fake_page, username="user@example.com", password="hunter2")
    fake_page.goto.assert_called_with("https://gumroad.com/login")
    fake_page.fill.assert_any_call("input[name='user[login]']", "user@example.com")
    fake_page.fill.assert_any_call("input[name='user[password]']", "hunter2")
    fake_page.click.assert_called()


def test_login_raises_if_blank_creds():
    fake_page = MagicMock()
    with pytest.raises(ValueError):
        login(fake_page, username="", password="x")
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_gumroad_helpers.py -v`
Expected: ImportError.

- [x] **Step 3: Write the implementation**

Create `scripts/gumroad_helpers.py`:

```python
"""Gumroad Playwright automation — login + create listing.

Browser-only. The Gumroad write API is deprecated.
"""
import os
from playwright.sync_api import Page, sync_playwright


def login(page: Page, username: str, password: str) -> None:
    """Log in to Gumroad. Raises ValueError on missing creds."""
    if not username or not password:
        raise ValueError("Gumroad username and password are required")
    page.goto("https://gumroad.com/login")
    page.fill("input[name='user[login]']", username)
    page.fill("input[name='user[password]']", password)
    page.click("button[type='submit']")
    page.wait_for_url("https://gumroad.com/dashboard", timeout=30000)
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_gumroad_helpers.py -v`
Expected: 2 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/gumroad_helpers.py dataStructured/tests/test_gumroad_helpers.py
git commit -m "feat(dataStructured): gumroad Playwright login helper"
```

---

### Task 5.2: Gumroad create_listing helper + mock test

**Files:**
- Modify: `~/apps/dataStructured/scripts/gumroad_helpers.py`
- Modify: `~/apps/dataStructured/tests/test_gumroad_helpers.py`

- [x] **Step 1: Append failing test**

Append to `tests/test_gumroad_helpers.py`:

```python
from scripts.gumroad_helpers import create_listing


def test_create_listing_fills_form_and_publishes():
    fake_page = MagicMock()
    fake_page.url = "https://gumroad.com/l/abc123"  # final URL after publish

    url = create_listing(
        fake_page,
        name="FL Permit Report",
        description="Florida permit history per address.",
        price_usd=27,
        asset_path="/tmp/asset.csv"
    )
    fake_page.goto.assert_any_call("https://gumroad.com/products/new")
    fake_page.fill.assert_any_call("input[name='name']", "FL Permit Report")
    fake_page.fill.assert_any_call("input[name='price']", "27")
    fake_page.set_input_files.assert_called_with("input[type='file']", "/tmp/asset.csv")
    assert url.startswith("https://gumroad.com/l/")
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_gumroad_helpers.py -v`
Expected: 2 pass + 1 fail (function doesn't exist).

- [x] **Step 3: Append implementation**

Append to `scripts/gumroad_helpers.py`:

```python
def create_listing(
    page: Page,
    name: str,
    description: str,
    price_usd: int,
    asset_path: str,
) -> str:
    """Create a Gumroad listing via Playwright. Returns the public listing URL."""
    page.goto("https://gumroad.com/products/new")
    page.fill("input[name='name']", name)
    page.fill("textarea[name='description']", description)
    page.fill("input[name='price']", str(price_usd))
    page.set_input_files("input[type='file']", asset_path)
    page.click("button[type='submit']")
    page.wait_for_url("https://gumroad.com/l/*", timeout=60000)
    return page.url
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_gumroad_helpers.py -v`
Expected: 3 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/gumroad_helpers.py dataStructured/tests/test_gumroad_helpers.py
git commit -m "feat(dataStructured): gumroad create_listing Playwright helper"
```

> Note: real Gumroad selectors may drift over time. The mock tests confirm the call shape; live integration smoke (deferred to Milestone 10) catches selector drift in production.

---

## Milestone 6 — CEO Orchestrator (subprocess dispatch)

### Task 6.1: dispatch_employee subprocess helper + tests

**Files:**
- Create: `~/apps/dataStructured/scripts/ceo_orchestrator.py`
- Create: `~/apps/dataStructured/tests/test_ceo_orchestrator.py`

- [x] **Step 1: Write the failing test**

Create `tests/test_ceo_orchestrator.py`:

```python
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from scripts.ceo_orchestrator import dispatch_employee, DispatchError


def test_dispatch_runs_trinity_run_subprocess():
    fake = MagicMock(returncode=0, stdout="Done.", stderr="")
    with patch("subprocess.run", return_value=fake) as mock_run:
        out = dispatch_employee("data-engineer", "Harvest niche X")
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert cmd[0] == "trinity"
    assert cmd[1] == "run"
    assert cmd[2] == "Harvest niche X"
    assert cmd[3] == "-e"
    assert cmd[4] == "data-engineer"
    assert kwargs["cwd"].endswith("dataStructured")
    assert out == "Done."


def test_dispatch_raises_on_nonzero_exit():
    fake = MagicMock(returncode=1, stdout="", stderr="boom")
    with patch("subprocess.run", return_value=fake):
        with pytest.raises(DispatchError, match="boom"):
            dispatch_employee("data-engineer", "task")


def test_dispatch_passes_timeout():
    fake = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=fake) as mock_run:
        dispatch_employee("data-engineer", "task", timeout_sec=600)
    _, kwargs = mock_run.call_args
    assert kwargs["timeout"] == 600
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_ceo_orchestrator.py -v`
Expected: ImportError.

- [x] **Step 3: Write the implementation**

Create `scripts/ceo_orchestrator.py`:

```python
"""CEO orchestration helpers — dispatch downstream employees as subprocesses."""
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]


class DispatchError(Exception):
    """Raised when a dispatched employee subprocess fails."""


def dispatch_employee(employee: str, task: str, timeout_sec: int = 3600) -> str:
    """Spawn `trinity run "<task>" -e <employee>` from the workspace.

    Returns stdout on success. Raises DispatchError on non-zero exit.
    """
    cmd = ["trinity", "run", task, "-e", employee]
    result = subprocess.run(
        cmd,
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    if result.returncode != 0:
        raise DispatchError(
            f"trinity run -e {employee} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_ceo_orchestrator.py -v`
Expected: 3 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/ceo_orchestrator.py dataStructured/tests/test_ceo_orchestrator.py
git commit -m "feat(dataStructured): ceo dispatch_employee subprocess helper"
```

---

### Task 6.2: Idempotency check helper

**Files:**
- Modify: `~/apps/dataStructured/scripts/ceo_orchestrator.py`
- Modify: `~/apps/dataStructured/tests/test_ceo_orchestrator.py`

- [x] **Step 1: Append failing test**

Append to `tests/test_ceo_orchestrator.py`:

```python
from scripts.ceo_orchestrator import next_pipeline_step


def test_next_step_is_data_engineer_when_only_brief_exists(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    step = next_pipeline_step(workspace, slug="test")
    assert step == "data-engineer"


def test_next_step_is_data_steward_when_raw_exists(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    (workspace / "state" / "datasets" / "test").mkdir(parents=True)
    (workspace / "state" / "datasets" / "test" / "raw-2026-05-04.csv").write_text("a,b\n1,2")
    step = next_pipeline_step(workspace, slug="test")
    assert step == "data-steward"


def test_next_step_is_compliance_when_clean_exists(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    (workspace / "state" / "datasets" / "test").mkdir(parents=True)
    (workspace / "state" / "datasets" / "test" / "raw-2026-05-04.csv").write_text("a,b\n1,2")
    (workspace / "state" / "datasets" / "test" / "clean-2026-05-04.csv").write_text("a,b\n1,2")
    step = next_pipeline_step(workspace, slug="test")
    assert step == "compliance-officer"


def test_next_step_is_engineer_when_ledger_passes(workspace):
    (workspace / "state" / "opportunities" / "2026-05-04-test.json").write_text("{}")
    dsdir = workspace / "state" / "datasets" / "test"; dsdir.mkdir(parents=True)
    (dsdir / "raw-2026-05-04.csv").write_text("a,b\n1,2")
    (dsdir / "clean-2026-05-04.csv").write_text("a,b\n1,2")
    (workspace / "state" / "ethics-ledger" / "2026-05-04-test.json").write_text('{"verdict": "PASS"}')
    step = next_pipeline_step(workspace, slug="test")
    assert step == "engineer"


def test_next_step_is_done_when_launch_report_shipped(workspace):
    pdir = workspace / "state" / "products" / "test"; pdir.mkdir(parents=True)
    (pdir / "launch-report.json").write_text('{"status": "SHIPPED"}')
    step = next_pipeline_step(workspace, slug="test")
    assert step == "done"
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_ceo_orchestrator.py -v`
Expected: 3 existing pass + 5 new fail.

- [x] **Step 3: Append implementation**

Append to `scripts/ceo_orchestrator.py`:

```python
import json
from pathlib import Path


def next_pipeline_step(workspace: Path, slug: str) -> str:
    """Determine the next pipeline step for *slug* by reading state/.

    Returns one of: "data-engineer", "data-steward", "compliance-officer",
    "engineer", "done", or "blocked".
    """
    workspace = Path(workspace)
    products = workspace / "state" / "products" / slug
    launch_report = products / "launch-report.json"
    if launch_report.exists():
        report = json.loads(launch_report.read_text())
        if report.get("status") == "SHIPPED":
            return "done"
        if report.get("status") in ("FAILED", "BLOCKED"):
            return "blocked"

    ledger_dir = workspace / "state" / "ethics-ledger"
    ledger_files = list(ledger_dir.glob(f"*-{slug}.json"))
    if ledger_files:
        ledger = json.loads(ledger_files[-1].read_text())
        if ledger.get("verdict") == "PASS":
            return "engineer"
        return "blocked"

    dataset_dir = workspace / "state" / "datasets" / slug
    if dataset_dir.exists():
        clean = list(dataset_dir.glob("clean-*.csv"))
        if clean:
            return "compliance-officer"
        raw = list(dataset_dir.glob("raw-*.csv"))
        if raw:
            return "data-steward"

    return "data-engineer"
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_ceo_orchestrator.py -v`
Expected: all 8 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/ceo_orchestrator.py dataStructured/tests/test_ceo_orchestrator.py
git commit -m "feat(dataStructured): ceo next_pipeline_step idempotency check"
```

---

### Task 6.3: Daily DM template helper

**Files:**
- Modify: `~/apps/dataStructured/scripts/ceo_orchestrator.py`
- Modify: `~/apps/dataStructured/tests/test_ceo_orchestrator.py`

- [x] **Step 1: Append failing test**

Append to `tests/test_ceo_orchestrator.py`:

```python
from scripts.ceo_orchestrator import format_daily_dm


def test_dm_with_one_shipped():
    dm = format_daily_dm(
        date="2026-05-04",
        advanced=["homeowner-permit-fl"],
        shipped=[{"name": "FL Permits", "stripe_url": "https://buy.stripe/x", "gumroad_url": "https://gumroad.com/l/y"}],
        blocked=[],
        running_tomorrow="next-niche",
        cycle_cost_tokens=12345,
    )
    assert "📊 DataStructured — 2026-05-04" in dm
    assert "FL Permits" in dm
    assert "https://buy.stripe/x" in dm
    assert "BLOCKED (needs you):" in dm and "—" not in dm.split("BLOCKED (needs you):")[1].split("RUNNING TOMORROW")[0].strip().splitlines()[0]
    # ^ blocked should be empty / "(none)"
    assert "next-niche" in dm
    assert "12345" in dm or "12,345" in dm


def test_dm_with_blocked():
    dm = format_daily_dm(
        date="2026-05-04",
        advanced=[],
        shipped=[],
        blocked=[{"slug": "x", "reason": "NEEDS FOUNDER REVIEW — sources contain edge-case phone numbers"}],
        running_tomorrow="idle — research only",
        cycle_cost_tokens=1000,
    )
    assert "NEEDS FOUNDER REVIEW" in dm
    assert "edge-case phone numbers" in dm
```

- [x] **Step 2: Run — expect FAIL**

Run: `cd ~/apps/dataStructured && pytest tests/test_ceo_orchestrator.py -v`
Expected: prior pass + 2 new fail.

- [x] **Step 3: Append implementation**

Append to `scripts/ceo_orchestrator.py`:

```python
def format_daily_dm(
    date: str,
    advanced: list[str],
    shipped: list[dict],
    blocked: list[dict],
    running_tomorrow: str,
    cycle_cost_tokens: int,
) -> str:
    """Format the CEO's daily DM."""
    advanced_lines = "\n".join(f"- {s}" for s in advanced) or "- (none)"
    shipped_lines = (
        "\n".join(f"- {s['name']}: {s.get('stripe_url', '')} / {s.get('gumroad_url', '')}" for s in shipped)
        or "- (none)"
    )
    blocked_lines = (
        "\n".join(f"- {b['slug']}: {b['reason']}" for b in blocked) or "- (none)"
    )
    return (
        f"📊 DataStructured — {date}\n"
        "══════════════════════════════\n"
        "ADVANCED TODAY:\n"
        f"{advanced_lines}\n\n"
        "SHIPPED:\n"
        f"{shipped_lines}\n\n"
        "BLOCKED (needs you):\n"
        f"{blocked_lines}\n\n"
        "RUNNING TOMORROW:\n"
        f"- {running_tomorrow}\n\n"
        f"CYCLE COST: {cycle_cost_tokens:,} tokens\n"
    )
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/test_ceo_orchestrator.py -v`
Expected: all 10 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/scripts/ceo_orchestrator.py dataStructured/tests/test_ceo_orchestrator.py
git commit -m "feat(dataStructured): ceo format_daily_dm template"
```

---

## Milestone 7 — Trinity Scheduler Cycles

### Task 7.1: Add research_scan and ceo_pipeline cycles to trinity.toml

**Files:**
- Modify: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Append the cycles block**

Append to `~/apps/dataStructured/trinity.toml`:

```toml

# ── Scheduler cycles ──────────────────────────────────────────────
# Times in system local timezone (set system tz to America/New_York or adjust).

[scheduler.cycles.research_scan]
schedule = "0 13 * * *"            # 1:00 PM daily — quiet midday slot
employee = "opportunity-researcher"
report_to = ""                     # silent worker; CEO surfaces results in 19:00 DM
type = "research"
task = "Run today's wide demand-discovery scan. Output 3-5 scored opportunity briefs to state/opportunities/{YYYY-MM-DD}-{slug}.json. If no signal is strong (score >= 6), write zero briefs and log 'no signal — recommend re-scan in 24h'."

[scheduler.cycles.ceo_pipeline]
schedule = "0 19 * * *"            # 7:00 PM daily — clear evening slot
employee = "ceo"
report_to = ""                     # CEO sends DM directly via tools
type = "needle"
task = "Run today's pipeline. Read state/opportunities/ for PROPOSED briefs. Cross-reference trinity memory for recently-rejected niches. Pick ONE brief with score >= 6 to advance (or zero if none qualify). For the chosen brief: dispatch data-engineer -> data-steward -> compliance-officer in sequence. If compliance verdict is PASS, write product spec.json and dispatch engineer. After all dispatches complete, send one DM to founder using format_daily_dm template."
```

- [x] **Step 2: Validate trinity.toml parses**

Run: `python3 -c "import tomllib; tomllib.loads(open('/home/oghenetejiri/apps/dataStructured/trinity.toml').read()); print('ok')"`
Expected: `ok`.

- [x] **Step 3: Verify trinity sees the cycles**

Run: `cd ~/apps/dataStructured && trinity status`
Expected: status output includes scheduler cycles `research_scan` and `ceo_pipeline`.

- [x] **Step 4: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/trinity.toml
git commit -m "feat(dataStructured): scheduler cycles (research 13:00 ET, ceo 19:00 ET)"
```

---

## Milestone 8 — Telegram Bot Setup

### Task 8.1: 🟡 MANUAL — Create new Telegram bot via @BotFather

**Files:** none (external setup)

- [x] **Step 1: Open Telegram, message @BotFather**

Run on phone or Telegram desktop: open chat with @BotFather.

- [x] **Step 2: Send /newbot**

Type `/newbot` and follow the prompts:
- **Bot name:** `DataStructured` (or whatever you chose to brand)
- **Username:** must end in `bot`, e.g. `datastructured_bot` or `<yourname>_ds_bot`

@BotFather returns a token like `1234567890:AAA-bbb-ccc-ddd`.

- [x] **Step 3: Save token to .env**

Edit `~/apps/dataStructured/.env` (create from .env.example if missing):

```bash
cp ~/apps/dataStructured/.env.example ~/apps/dataStructured/.env
# Then edit .env and set:
TELEGRAM_BOT_TOKEN="1234567890:AAA-bbb-ccc-ddd"
```

- [x] **Step 4: Get your founder Telegram user ID**

Message `@userinfobot` on Telegram. It returns your numeric user ID (e.g. `123456789`).

- [x] **Step 5: Save founder ID to .env**

Append to `.env`:

```bash
FOUNDER_TELEGRAM_USER_ID="123456789"
```

- [x] **Step 6: Verify .env is gitignored**

Run: `git check-ignore -v ~/apps/dataStructured/.env`
Expected: confirms `.env` is gitignored.

---

### Task 8.2: Configure Telegram ACL allowlist

**Files:**
- Modify: `~/apps/dataStructured/trinity.toml`

- [x] **Step 1: Update [telegram.acl] section**

Edit `trinity.toml` `[telegram.acl]` block:

```toml
[telegram.acl]
dm_policy = "allowlist"
allowed_users = [123456789]    # ← replace with your FOUNDER_TELEGRAM_USER_ID
group_policy = "allowlist"
```

(Use the numeric ID from Task 8.1 Step 4 — not as string, as integer.)

- [x] **Step 2: Validate parses**

Run: `python3 -c "import tomllib; tomllib.loads(open('/home/oghenetejiri/apps/dataStructured/trinity.toml').read()); print('ok')"`
Expected: `ok`.

- [x] **Step 3: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/trinity.toml
git commit -m "feat(dataStructured): telegram ACL allowlist with founder user ID"
```

> Note: the actual user ID number IS in the committed file. If you want it private, use an env var lookup pattern instead (trinity-agent supports this for some fields; check the source). For v1, the user ID alone (without bot token) is harmless to commit — only the bot token grants access.

---

### Task 8.3: Smoke ping test (manual)

**Files:** none (verification)

- [x] **Step 1: Start trinity in foreground**

Run: `cd ~/apps/dataStructured && trinity start`
Expected: Console output shows "Telegram bot started" + "Scheduler started".

- [x] **Step 2: From Telegram, DM your bot "ping"**

Open Telegram → find your bot (search the username from Task 8.1) → send `ping`.

Expected: bot responds within 30 seconds (CEO will respond per default_employee).

If no response: check console for errors. Common causes: wrong token, ACL not allowing your user ID, daemon not running.

- [x] **Step 3: Stop trinity**

Press Ctrl-C in the terminal running trinity.

- [x] **Step 4: Mark this task complete only when ping/pong succeeded**

If ping succeeded, the bot, ACL, and provider are all wired correctly.

---

## Milestone 9 — Daemon Supervision

### Task 9.1: Add @reboot crontab line to start trinity daemon

**Files:**
- Modify: user crontab (`crontab -e`)

- [x] **Step 1: Edit user crontab**

Run: `crontab -e`

Append at the bottom:

```cron
# DataStructured trinity daemon
@reboot sleep 30 && cd /home/oghenetejiri/apps/dataStructured && /usr/bin/env trinity start --daemon >> /home/oghenetejiri/apps/dataStructured/.trinity/logs/boot.log 2>&1
```

(Adjust path to `trinity` binary if it lives elsewhere. Check with `which trinity`.)

- [x] **Step 2: Verify crontab has the line**

Run: `crontab -l | grep dataStructured`
Expected: shows the @reboot line.

> Note: this does NOT commit anything to git — crontab is per-user state.

---

### Task 9.2: Test daemon start/stop manually

**Files:** none (verification)

- [x] **Step 1: Start daemon**

Run: `cd ~/apps/dataStructured && trinity start --daemon`
Expected: returns to shell, prints something like "Started in background, PID: NNNN".

- [x] **Step 2: Verify PID file exists**

Run: `cat ~/apps/dataStructured/.trinity/state/trinity.pid`
Expected: integer (the daemon PID).

- [x] **Step 3: Verify process is alive**

Run: `ps -p $(cat ~/apps/dataStructured/.trinity/state/trinity.pid)`
Expected: shows trinity process.

- [x] **Step 4: Stop daemon**

Run: `cd ~/apps/dataStructured && trinity stop`
Expected: confirms stopped.

- [x] **Step 5: Verify PID file cleaned up**

Run: `ls ~/apps/dataStructured/.trinity/state/trinity.pid 2>/dev/null && echo "STILL THERE" || echo "GONE"`
Expected: `GONE`.

---

## Milestone 10 — Integration Smoke + First Live Run

### Task 10.1: Full pipeline dry-run smoke test

**Files:**
- Create: `~/apps/dataStructured/tests/integration/test_pipeline_dryrun.py`
- Create: `~/apps/dataStructured/tests/fixtures/__init__.py`
- Create: `~/apps/dataStructured/tests/fixtures/seed_brief.json`

- [x] **Step 1: Make fixtures dir**

Run: `mkdir -p ~/apps/dataStructured/tests/fixtures && touch ~/apps/dataStructured/tests/fixtures/__init__.py`

- [x] **Step 2: Write seed brief fixture**

Create `tests/fixtures/seed_brief.json`:

```json
{
  "version": 1,
  "type": "opportunity_brief",
  "slug": "smoke-test-niche",
  "created": "2026-05-04T13:00:00Z",
  "created_by": "opportunity-researcher",
  "status": "APPROVED",
  "score": 9,
  "summary": "Smoke test fixture brief.",
  "audience": {"who": "smoke test buyers", "where_found": ["test"]},
  "data_wanted": "Synthetic test rows",
  "evidence": [{"source": "test", "url": "https://example.com/", "quote": "Test signal"}],
  "willingness_to_pay": {"signal": "$27 mentioned", "confidence": "high"},
  "source_rights": {"public": true, "examples": ["example.com"]},
  "first_sale_path": {"channel": "test", "angle": "test"}
}
```

- [x] **Step 3: Write the dry-run smoke test**

Create `tests/integration/test_pipeline_dryrun.py`:

```python
"""End-to-end dry-run: seed a brief, drive the pipeline by file presence checks.

This test exercises the orchestrator's idempotency logic, not the LLM employees.
"""
import json
import shutil
from pathlib import Path

from scripts.ceo_orchestrator import next_pipeline_step
from scripts.lib.atomic_io import write_json_atomic


def test_pipeline_state_machine_progresses(tmp_path):
    # Seed: only brief exists
    opps = tmp_path / "state" / "opportunities"
    opps.mkdir(parents=True)
    seed = json.loads((Path(__file__).parents[1] / "fixtures" / "seed_brief.json").read_text())
    write_json_atomic(opps / "2026-05-04-smoke-test-niche.json", seed)

    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "data-engineer"

    # Add raw CSV
    ds = tmp_path / "state" / "datasets" / "smoke-test-niche"
    ds.mkdir(parents=True)
    (ds / "raw-2026-05-04.csv").write_text("id,a,source_url\n1,x,https://example.com\n")
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "data-steward"

    # Add clean CSV
    (ds / "clean-2026-05-04.csv").write_text("id,a,source_url\n1,x,https://example.com\n")
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "compliance-officer"

    # Add ledger PASS
    ledger = tmp_path / "state" / "ethics-ledger"
    ledger.mkdir(parents=True)
    (ledger / "2026-05-04-smoke-test-niche.json").write_text('{"verdict": "PASS"}')
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "engineer"

    # Add launch report SHIPPED
    products = tmp_path / "state" / "products" / "smoke-test-niche"
    products.mkdir(parents=True)
    (products / "launch-report.json").write_text('{"status": "SHIPPED"}')
    assert next_pipeline_step(tmp_path, slug="smoke-test-niche") == "done"
```

- [x] **Step 4: Run — expect PASS**

Run: `cd ~/apps/dataStructured && pytest tests/integration/test_pipeline_dryrun.py -v`
Expected: 1 pass.

- [x] **Step 5: Commit**

Run from `~/apps/`:
```bash
git add dataStructured/tests/integration/test_pipeline_dryrun.py dataStructured/tests/fixtures/__init__.py dataStructured/tests/fixtures/seed_brief.json
git commit -m "test(dataStructured): pipeline state-machine integration dry-run"
```

---

### Task 10.2: Full test sweep before live run

- [x] **Step 1: Run everything**

Run: `cd ~/apps/dataStructured && pytest -v`
Expected: All tests pass. Should be ≥ 40 tests across schemas, helpers, and integration.

- [x] **Step 2: Confirm no test errors or warnings**

If any test fails or has warnings, fix before proceeding.

---

### Task 10.3: First live run — researcher

**Files:** none (live invocation)

- [x] **Step 1: Source .env (if not auto-loaded)**

Trinity auto-loads `.env`, but verify by running:

Run: `cd ~/apps/dataStructured && env | grep TELEGRAM_BOT_TOKEN || echo "Not set — trinity will load from .env"`

- [x] **Step 2: Run researcher one-shot**

Run: `cd ~/apps/dataStructured && trinity run "Run today's wide demand-discovery scan. Write 3-5 briefs to state/opportunities/." -e opportunity-researcher`

Expected: agent runs, fetches signals, writes briefs to `state/opportunities/`.

- [x] **Step 3: Verify briefs exist and validate**

Run:
```bash
ls ~/apps/dataStructured/state/opportunities/
cd ~/apps/dataStructured && python3 -c "
import json
from pathlib import Path
from scripts.lib.schema_validator import validate
for p in Path('state/opportunities').glob('*.json'):
    data = json.loads(p.read_text())
    validate('opportunity_brief', data)
    print(f'OK: {p.name} (score {data[\"score\"]}, status {data[\"status\"]})')
"
```

Expected: lists 3-5 briefs, all validate.

If briefs are malformed: review the researcher identity.md + the schema; iterate on the identity prompt to produce schema-compliant output.

---

### Task 10.4: First live run — CEO pipeline

**Files:** none (live invocation)

- [x] **Step 1: Run CEO one-shot**

Run: `cd ~/apps/dataStructured && trinity run "Run today's pipeline. Pick the highest-scored brief, dispatch downstream pipeline. Send DM with summary." -e ceo`

Expected: CEO reads opportunities, picks one, dispatches data-engineer → data-steward → compliance-officer (and engineer if compliance PASS), then sends a DM.

This will run for several minutes (multiple subprocess dispatches).

- [x] **Step 2: Verify Telegram DM landed**

Check Telegram. Expected: bot DMed you a daily summary.

- [x] **Step 3: Inspect the produced state artifacts**

Run:
```bash
find ~/apps/dataStructured/state -type f -name "*.json" -newer ~/apps/dataStructured/CLAUDE.md | sort
```

Expected: lists newly-created files: opportunity status updated, dataset metadata, quality report, ethics ledger entry, possibly product spec + launch report.

- [x] **Step 4: If pipeline halted at any step, read CEO's DM for the blocker**

The DM should explain what happened. Common first-run issues:
- Engineer halted because Stripe key not set → set `STRIPE_SECRET_KEY=sk_test_...` in `.env`, retry
- Engineer halted because Gumroad creds not set → set `GUMROAD_USERNAME` + `GUMROAD_PASSWORD`, retry
- Compliance NEEDS_FOUNDER_REVIEW → expected; reply to bot with decision

---

### Task 10.5: Enable scheduled daemon

- [x] **Step 1: Start daemon**

Run: `cd ~/apps/dataStructured && trinity start --daemon`
Expected: daemon backgrounded, PID printed.

- [x] **Step 2: Verify scheduler picked up cycles**

Run: `tail -50 ~/apps/dataStructured/.trinity/logs/daemon.log 2>/dev/null || echo "(no log yet — scheduler runs on cron schedule)"`

Wait for next cycle time (13:00 ET researcher OR 19:00 ET CEO) and verify a fresh DM lands at that time.

- [x] **Step 3: Document startup**

Add a one-line note to `~/apps/dataStructured/README.md` after the Quick Start section:

```markdown
## Daemon

The trinity daemon starts at boot via the user's crontab `@reboot` line. Manually:
- Start: `trinity start --daemon`
- Stop: `trinity stop`
- Logs: `~/apps/dataStructured/.trinity/logs/daemon.log`
```

Commit:

```bash
cd ~/apps && git add dataStructured/README.md
git commit -m "docs(dataStructured): document daemon lifecycle"
```

---

### Task 10.6: Final verification — 24-hour live observation

**Files:** none (observation period)

- [x] **Step 1: Wait for the next 13:00 ET cycle**

Verify a fresh `state/opportunities/` file is created at 13:00 ET.

- [x] **Step 2: Wait for the next 19:00 ET cycle**

Verify a fresh DM lands in Telegram at ~19:00 ET. The DM should contain `📊 DataStructured — {today's date}`.

- [x] **Step 3: Document first day**

Append to `~/apps/dataStructured/README.md` a "First-day live notes" section with:
- Time first DM received
- Anything that broke
- What needed manual intervention

Commit if any notes added.

---

## Self-Review Checklist (run after completing all milestones)

This section is for the implementing agent (or human) to run as a final gate before declaring v1 done.

- [x] **Spec coverage:** every section of `docs/superpowers/specs/2026-05-04-datastructured-design.md` has been implemented:
  - Section 3 (Architecture) → Milestones 0, 7, 8, 9
  - Section 4 (Components — 6 employees) → Milestone 3
  - Section 5 (Data flow — JSON artifacts) → Milestone 1
  - Section 6 (Error handling) → Milestone 6 (orchestrator) + agent identity rules
  - Section 7 (Testing) → Milestones 1, 2, 4, 5, 6, 10

- [x] **Tests passing:** `pytest -v` from workspace shows ≥ 40 tests passing.

- [x] **Live system observable:** at least one daily DM has been received from CEO.

- [x] **No placeholders in identity files:** grep employee identities for "TODO|TBD|XXX|FIXME" — all clean.

- [x] **Compliance gate enforced:** at least one ethics-ledger entry exists (PASS, FAIL, or NEEDS_FOUNDER_REVIEW). If NEEDS_FOUNDER_REVIEW, founder DMed back with a decision.

- [x] **Idempotency proven:** re-running CEO mid-pipeline does not re-do completed steps (verify by deleting an artifact and observing CEO restarts only from that point).

- [x] **Daemon resilient:** daemon survives a stop+start cycle; @reboot line is present in user crontab.

If all boxes checked, v1 is shipped. Move to PRD Phase 2 entry trigger when 14 consecutive daily DMs land without intervention.

---

## Plan complete.

---

## Closeout — 2026-05-08

All 11 milestones (M0–M10) closed. 208 task checkboxes ticked.

**Live evidence:**
- Stripe Payment Link: https://buy.stripe.com/cNi14g4CP7aT8mT1iC7IY0c (HTTP 200)
- Gumroad listing: https://3563705146415.gumroad.com/l/bvdnbx (HTTP 200, deployed 2026-05-05T02:12:43Z)
- First product: New FMCSA Carriers — May 2026, 15,770 records, $39
- Daemon online: PID 3020540 (1d18h uptime as of close), workspace `/home/oghenetejiri/apps/dataStructured`
- M9 `@reboot` crontab line installed in user crontab

**M10.6 — 24-hour observation window:**
Started 2026-05-04 with first autonomous CEO pipeline cycle. Closed administratively per founder direction. The 14-consecutive-daily-DM Phase-1 success threshold continues to accumulate organically — currently day 4. Phase 2 entry trigger remains valid: 14 consecutive daily DMs without founder intervention.

**v1 → ongoing ops handoff:**
Operational follow-ups (engineer subprocess `claude_agent_sdk` crash, watchdog cron line, future product specs, distribution sweep) are owned by Trinity/Ralph via Telegram DM (`@Ralph_the_builder_oefr_bot`), not Claude Code. Reference: feedback memory `feedback_datastructured_ops_handoff.md`.
