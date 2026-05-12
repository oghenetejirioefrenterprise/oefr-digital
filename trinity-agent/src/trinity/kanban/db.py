"""SQLite connection helpers + schema for the kanban board."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

# WAL mode + 5s busy_timeout; CAS-style updates serialize through SQLite.
_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  body TEXT,
  status TEXT NOT NULL DEFAULT 'triage',
  assignee TEXT,
  priority INTEGER NOT NULL DEFAULT 3,
  created_by TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  result TEXT,
  claim_lock TEXT,
  claim_expires TEXT,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  last_failure_error TEXT,
  dedupe_key TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_assignee
  ON tasks(status, assignee);
CREATE INDEX IF NOT EXISTS idx_tasks_dedupe_key
  ON tasks(dedupe_key);

CREATE TABLE IF NOT EXISTS task_links (
  parent_id INTEGER NOT NULL,
  child_id INTEGER NOT NULL,
  PRIMARY KEY (parent_id, child_id),
  FOREIGN KEY (parent_id) REFERENCES tasks(id),
  FOREIGN KEY (child_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS task_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  author TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_comments_task ON task_comments(task_id);

CREATE TABLE IF NOT EXISTS task_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  payload TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_events_task ON task_events(task_id);
"""


def db_path(trinity_dir: Path) -> Path:
    return trinity_dir / "kanban" / "board.db"


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
    """Open a connection; caller is responsible for closing/committing."""
    init(trinity_dir)
    conn = sqlite3.connect(db_path(trinity_dir), isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def write_txn(trinity_dir: Path):
    """Yield a connection inside a ``BEGIN IMMEDIATE`` transaction."""
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
