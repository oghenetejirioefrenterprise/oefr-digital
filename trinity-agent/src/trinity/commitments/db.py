"""SQLite connection helpers + schema for the commitments store.

Same pattern as kanban/db.py and memory/db.py: WAL + busy_timeout +
BEGIN IMMEDIATE so the daemon, scheduler threads, and separate CLI processes
serialise correctly — the old single commitments.json + threading.Lock could
silently drop a status update under cross-process contention.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS commitments (
  id            TEXT PRIMARY KEY,
  kind          TEXT NOT NULL DEFAULT '',
  text          TEXT NOT NULL DEFAULT '',
  chat_id       TEXT NOT NULL DEFAULT '',
  due_at        TEXT NOT NULL DEFAULT '',
  dedupe_key    TEXT UNIQUE,
  confidence    REAL NOT NULL DEFAULT 0,
  status        TEXT NOT NULL DEFAULT 'pending',
  created_at    TEXT NOT NULL DEFAULT '',
  sent_at       TEXT,
  snoozed_until TEXT,
  nudge_text    TEXT
);

CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments(status);
CREATE INDEX IF NOT EXISTS idx_commitments_chat   ON commitments(chat_id);

CREATE TABLE IF NOT EXISTS schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);
"""


def db_path(trinity_dir: Path) -> Path:
    return trinity_dir / "state" / "commitments.db"


_lock = threading.Lock()
_initialised: set[str] = set()


def init(trinity_dir: Path) -> None:
    p = db_path(trinity_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    key = str(p.resolve())
    with _lock:
        if key in _initialised:
            return
        with sqlite3.connect(p) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()
        _initialised.add(key)


def connect(trinity_dir: Path) -> sqlite3.Connection:
    init(trinity_dir)
    conn = sqlite3.connect(db_path(trinity_dir), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def write_txn(trinity_dir: Path):
    conn = connect(trinity_dir)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()
