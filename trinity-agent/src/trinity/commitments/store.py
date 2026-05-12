"""Persistent JSON store for commitment records.

Single file at ``<trinity_dir>/state/commitments.json``. Atomic writes via
the existing IO helper. Dedup by ``dedupe_key`` — re-extracting the same
promise updates an existing row's text/confidence rather than creating a
duplicate.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
from pathlib import Path
from typing import Iterable

from trinity._io import atomic_write_json
from trinity.commitments.types import CommitmentRecord, PENDING, SENT, SNOOZED

log = logging.getLogger(__name__)

_LOCK = threading.Lock()


def _path(trinity_dir: Path) -> Path:
    return trinity_dir / "state" / "commitments.json"


def _load(trinity_dir: Path) -> list[dict]:
    p = _path(trinity_dir)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        log.warning("commitments file unreadable, starting fresh")
        return []


def _save(trinity_dir: Path, records: list[dict]) -> None:
    p = _path(trinity_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(p, records)


# ── CRUD ─────────────────────────────────────────────────────────────


def add_or_merge(trinity_dir: Path, record: CommitmentRecord) -> str:
    """Insert *record* or merge with an existing row sharing its dedupe_key.

    On merge, the latest text + due_at + confidence win. Existing status
    is preserved unless the existing row is in a terminal state, in
    which case the merge is a no-op (already handled).

    Returns the id of the row in the store.
    """
    with _LOCK:
        records = _load(trinity_dir)
        for r in records:
            if r.get("dedupe_key") == record.dedupe_key:
                if r.get("status") in (SENT, "dismissed", "expired"):
                    return r["id"]  # already handled, don't reopen
                r["text"] = record.text
                r["due_at"] = record.due_at
                r["confidence"] = record.confidence
                if record.nudge_text:
                    r["nudge_text"] = record.nudge_text
                _save(trinity_dir, records)
                return r["id"]
        records.append(record.to_dict())
        _save(trinity_dir, records)
        return record.id


def list_records(
    trinity_dir: Path,
    chat_id: str | None = None,
    status: str | None = None,
) -> list[CommitmentRecord]:
    with _LOCK:
        rows = _load(trinity_dir)
    out: list[CommitmentRecord] = []
    for r in rows:
        if chat_id is not None and r.get("chat_id") != chat_id:
            continue
        if status is not None and r.get("status") != status:
            continue
        out.append(CommitmentRecord.from_dict(r))
    return out


def due_now(trinity_dir: Path, now: dt.datetime | None = None) -> list[CommitmentRecord]:
    """Return pending records whose ``due_at`` is in the past, plus expired snoozes."""
    now_t = (now or dt.datetime.now()).isoformat()
    out: list[CommitmentRecord] = []
    with _LOCK:
        rows = _load(trinity_dir)
    for r in rows:
        status = r.get("status")
        if status == PENDING and r.get("due_at", "") <= now_t:
            out.append(CommitmentRecord.from_dict(r))
        elif status == SNOOZED and (r.get("snoozed_until") or "") <= now_t:
            out.append(CommitmentRecord.from_dict(r))
    return out


def update_status(
    trinity_dir: Path,
    record_id: str,
    status: str,
    *,
    sent_at: str | None = None,
    snoozed_until: str | None = None,
) -> bool:
    with _LOCK:
        rows = _load(trinity_dir)
        for r in rows:
            if r.get("id") == record_id:
                r["status"] = status
                if sent_at is not None:
                    r["sent_at"] = sent_at
                if snoozed_until is not None:
                    r["snoozed_until"] = snoozed_until
                _save(trinity_dir, rows)
                return True
    return False


def purge_terminal(trinity_dir: Path, older_than_days: int = 30) -> int:
    """Drop sent/dismissed/expired records older than *older_than_days*."""
    cutoff = (dt.datetime.now() - dt.timedelta(days=older_than_days)).isoformat()
    removed = 0
    with _LOCK:
        rows = _load(trinity_dir)
        kept: list[dict] = []
        for r in rows:
            if r.get("status") in ("sent", "dismissed", "expired") and r.get("created_at", "") < cutoff:
                removed += 1
                continue
            kept.append(r)
        if removed:
            _save(trinity_dir, kept)
    return removed
