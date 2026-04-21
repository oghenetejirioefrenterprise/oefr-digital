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
