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
