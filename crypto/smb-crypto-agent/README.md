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
