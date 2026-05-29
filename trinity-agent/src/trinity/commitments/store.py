"""Persistent store for commitment records, backed by SQLite.

Single table at ``<trinity_dir>/state/commitments.db`` (WAL + BEGIN IMMEDIATE),
replacing the previous single-file ``commitments.json`` that rewrote the whole
list on every op and had no cross-process safety. Dedup is by ``dedupe_key`` —
re-extracting the same promise updates the existing row rather than duplicating
it. The public API is unchanged. A legacy ``commitments.json`` is migrated into
the DB once on first use.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
from pathlib import Path

from trinity.commitments import db
from trinity.commitments.types import CommitmentRecord, PENDING, SENT, SNOOZED

log = logging.getLogger(__name__)

_COLUMNS = [
    "id", "kind", "text", "chat_id", "due_at", "dedupe_key", "confidence",
    "status", "created_at", "sent_at", "snoozed_until", "nudge_text",
]

_migrate_lock = threading.Lock()
_migrated: set[str] = set()


def _path(trinity_dir: Path) -> Path:
    """Legacy JSON path (migrated away on first use)."""
    return trinity_dir / "state" / "commitments.json"


def _ensure(trinity_dir: Path) -> None:
    db.init(trinity_dir)
    key = str(db.db_path(trinity_dir).resolve())
    with _migrate_lock:
        if key in _migrated:
            return
        _migrated.add(key)
    try:
        _run_migration(trinity_dir)
    except Exception:
        _migrated.discard(key)


def _run_migration(trinity_dir: Path) -> None:
    """Import a legacy commitments.json once. Idempotent (schema_meta guard)."""
    legacy = _path(trinity_dir)
    with db.write_txn(trinity_dir) as conn:
        done = conn.execute(
            "SELECT value FROM schema_meta WHERE key='legacy_migrated'"
        ).fetchone()
        if done:
            return
        if legacy.exists():
            try:
                rows = json.loads(legacy.read_text())
            except (json.JSONDecodeError, OSError):
                rows = []
            # NOT NULL columns must never receive an explicit None (SQLite
            # column DEFAULTs apply only to OMITTED columns, not bound NULLs),
            # so coalesce missing/null values — otherwise OR IGNORE would
            # silently drop a partial/hand-edited legacy row.
            _NOT_NULL = {
                "kind": "", "text": "", "chat_id": "", "due_at": "",
                "confidence": 0, "status": PENDING, "created_at": "",
            }
            for r in rows if isinstance(rows, list) else []:
                if not r.get("id"):
                    continue
                vals = []
                for c in _COLUMNS:
                    v = r.get(c)
                    if v is None and c in _NOT_NULL:
                        v = _NOT_NULL[c]
                    vals.append(v)
                conn.execute(
                    f"INSERT OR IGNORE INTO commitments ({', '.join(_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
                    tuple(vals),
                )
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('legacy_migrated', ?)",
            (dt.datetime.now().isoformat(),),
        )
    if legacy.exists():
        try:
            legacy.replace(legacy.with_suffix(".json.migrated"))
        except OSError:
            pass


def _row_to_record(row) -> CommitmentRecord:
    return CommitmentRecord.from_dict(dict(row))


# ── CRUD ─────────────────────────────────────────────────────────────


def add_or_merge(trinity_dir: Path, record: CommitmentRecord) -> str:
    """Insert *record* or merge with an existing row sharing its dedupe_key.

    On merge, latest text/due_at/confidence win; existing status is preserved
    unless the existing row is terminal (then merge is a no-op).
    Returns the id of the row in the store.
    """
    _ensure(trinity_dir)
    with db.write_txn(trinity_dir) as conn:
        existing = conn.execute(
            "SELECT id, status FROM commitments WHERE dedupe_key=?",
            (record.dedupe_key,),
        ).fetchone()
        if existing is not None:
            if existing["status"] in (SENT, "dismissed", "expired"):
                return existing["id"]  # already handled, don't reopen
            conn.execute(
                "UPDATE commitments SET text=?, due_at=?, confidence=?, "
                "nudge_text=COALESCE(?, nudge_text) WHERE id=?",
                (record.text, record.due_at, record.confidence,
                 record.nudge_text, existing["id"]),
            )
            return existing["id"]
        d = record.to_dict()
        conn.execute(
            f"INSERT INTO commitments ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
            tuple(d.get(c) for c in _COLUMNS),
        )
        return record.id


def list_records(
    trinity_dir: Path,
    chat_id: str | None = None,
    status: str | None = None,
) -> list[CommitmentRecord]:
    _ensure(trinity_dir)
    where, params = [], []
    if chat_id is not None:
        where.append("chat_id=?")
        params.append(chat_id)
    if status is not None:
        where.append("status=?")
        params.append(status)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    conn = db.connect(trinity_dir)
    try:
        rows = conn.execute(
            f"SELECT * FROM commitments{clause} ORDER BY created_at ASC", params
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_record(r) for r in rows]


def due_now(trinity_dir: Path, now: dt.datetime | None = None) -> list[CommitmentRecord]:
    """Pending records whose ``due_at`` is in the past, plus expired snoozes."""
    _ensure(trinity_dir)
    now_t = (now or dt.datetime.now()).isoformat()
    conn = db.connect(trinity_dir)
    try:
        rows = conn.execute(
            "SELECT * FROM commitments WHERE "
            "(status=? AND due_at <> '' AND due_at <= ?) OR "
            "(status=? AND COALESCE(snoozed_until,'') <> '' AND snoozed_until <= ?)",
            (PENDING, now_t, SNOOZED, now_t),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_record(r) for r in rows]


def update_status(
    trinity_dir: Path,
    record_id: str,
    status: str,
    *,
    sent_at: str | None = None,
    snoozed_until: str | None = None,
) -> bool:
    _ensure(trinity_dir)
    sets = ["status=?"]
    params: list = [status]
    if sent_at is not None:
        sets.append("sent_at=?")
        params.append(sent_at)
    if snoozed_until is not None:
        sets.append("snoozed_until=?")
        params.append(snoozed_until)
    params.append(record_id)
    with db.write_txn(trinity_dir) as conn:
        row = conn.execute(
            f"UPDATE commitments SET {', '.join(sets)} WHERE id=? RETURNING id",
            params,
        ).fetchone()
    return row is not None


def purge_terminal(trinity_dir: Path, older_than_days: int = 30) -> int:
    """Drop sent/dismissed/expired records older than *older_than_days*."""
    _ensure(trinity_dir)
    cutoff = (dt.datetime.now() - dt.timedelta(days=older_than_days)).isoformat()
    with db.write_txn(trinity_dir) as conn:
        rows = conn.execute(
            "DELETE FROM commitments WHERE status IN ('sent','dismissed','expired') "
            "AND created_at <> '' AND created_at < ? RETURNING id",
            (cutoff,),
        ).fetchall()
    return len(rows)
