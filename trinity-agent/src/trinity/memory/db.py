"""SQLite connection helpers + schema for the memory store.

Mirrors the proven kanban/db.py pattern: WAL journal mode for cross-process
read/write concurrency, a 5s busy_timeout so contending processes wait instead
of failing, and ``BEGIN IMMEDIATE`` write transactions that serialise mutations
across the daemon, scheduler threads, AND separate CLI processes — something the
old ``threading.Lock`` over ``index.json`` could never do.

The memory body lives in the ``content`` column (single source of truth). An
FTS5 virtual table over ``summary`` + ``content`` replaces the old
"re-parse every .md file on every query" search path.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

# WAL + 5s busy_timeout; writes serialise through BEGIN IMMEDIATE.
# memories_fts is an external-content FTS5 table kept in sync by triggers.
_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS memories (
  id            TEXT PRIMARY KEY,
  tier          TEXT NOT NULL DEFAULT 'short-term',
  segment       TEXT NOT NULL,
  importance    REAL NOT NULL DEFAULT 0.5,
  decay_rate    REAL NOT NULL DEFAULT 1.0,
  created       TEXT NOT NULL,
  last_accessed TEXT NOT NULL,
  access_count  INTEGER NOT NULL DEFAULT 1,
  source        TEXT NOT NULL DEFAULT '',
  summary       TEXT NOT NULL DEFAULT '',
  kind          TEXT NOT NULL DEFAULT '',
  status        TEXT NOT NULL DEFAULT '',
  product       TEXT NOT NULL DEFAULT '',
  category      TEXT NOT NULL DEFAULT '',
  scope         TEXT NOT NULL DEFAULT 'global',
  content       TEXT NOT NULL DEFAULT '',
  supersedes    TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_memories_tier        ON memories(tier);
CREATE INDEX IF NOT EXISTS idx_memories_kind_status ON memories(kind, status);
CREATE INDEX IF NOT EXISTS idx_memories_scope       ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_memories_created     ON memories(created);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
  summary,
  content,
  content='memories',
  content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, summary, content)
  VALUES (new.rowid, new.summary, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, summary, content)
  VALUES('delete', old.rowid, old.summary, old.content);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, summary, content)
  VALUES('delete', old.rowid, old.summary, old.content);
  INSERT INTO memories_fts(rowid, summary, content)
  VALUES (new.rowid, new.summary, new.content);
END;

CREATE TABLE IF NOT EXISTS schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);
"""


def db_path(trinity_dir: Path) -> Path:
    return trinity_dir / "memory" / "memory.db"


_lock = threading.Lock()
_initialised: set[str] = set()


def init(trinity_dir: Path) -> None:
    """Create the DB file + schema if absent. Idempotent."""
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
    """Open a connection. Caller is responsible for closing."""
    init(trinity_dir)
    conn = sqlite3.connect(db_path(trinity_dir), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    # synchronous is per-connection (not persisted like journal_mode). WAL +
    # NORMAL is the standard durable-yet-fast combo: commits don't fsync on
    # every write, only at checkpoint; safe across app crashes.
    conn.execute("PRAGMA synchronous=NORMAL")
    # NB: unlike kanban/db.py we do not set PRAGMA foreign_keys — the memories
    # schema has no foreign-key constraints, so it would be a no-op.
    return conn


@contextmanager
def write_txn(trinity_dir: Path):
    """Yield a connection inside a ``BEGIN IMMEDIATE`` transaction.

    ``BEGIN IMMEDIATE`` takes the database write-lock up front, so two
    processes can never interleave a read-modify-write — the second blocks
    (up to busy_timeout) until the first commits. This is the cross-process
    serialisation the JSON-file stores never had.
    """
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
