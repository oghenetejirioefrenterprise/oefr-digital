"""Kanban board operations.

State machine:

    triage  →  todo            (specced)
    todo    →  ready           (recompute_ready: all parents done)
    ready   →  running         (atomic claim by assignee, CAS on claim_lock)
    running →  done | blocked
    blocked →  ready           (manual unblock or parent completes)
    *       →  archived

Atomic claim is a single ``UPDATE ... WHERE id=? AND status='ready' AND
(claim_lock IS NULL OR claim_expires < now)`` — ``rowcount=1`` won the
race, ``0`` lost it.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from trinity.kanban import db

log = logging.getLogger(__name__)

CLAIM_TTL_SECONDS = 900  # 15 minutes

STATUS_TRIAGE = "triage"
STATUS_TODO = "todo"
STATUS_READY = "ready"
STATUS_RUNNING = "running"
STATUS_BLOCKED = "blocked"
STATUS_DONE = "done"
STATUS_ARCHIVED = "archived"

VALID_STATUSES = {
    STATUS_TRIAGE, STATUS_TODO, STATUS_READY, STATUS_RUNNING,
    STATUS_BLOCKED, STATUS_DONE, STATUS_ARCHIVED,
}


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _record_event(conn, task_id: int, kind: str, payload: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO task_events(task_id, kind, payload, created_at) VALUES (?, ?, ?, ?)",
        (task_id, kind, json.dumps(payload or {}), _now()),
    )


# ── CRUD ──────────────────────────────────────────────────────────────


def create_task(
    trinity_dir: Path,
    title: str,
    body: str | None = None,
    assignee: str | None = None,
    priority: int = 3,
    created_by: str | None = None,
    parents: list[int] | None = None,
    dedupe_key: str | None = None,
    status: str = STATUS_TODO,
) -> int:
    """Insert a new task. Returns the generated task id.

    If ``dedupe_key`` is supplied and an existing task already uses it,
    that task's id is returned instead — idempotent re-creation.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")

    with db.write_txn(trinity_dir) as conn:
        if dedupe_key:
            row = conn.execute(
                "SELECT id FROM tasks WHERE dedupe_key=?", (dedupe_key,),
            ).fetchone()
            if row is not None:
                return int(row["id"])
        cur = conn.execute(
            """
            INSERT INTO tasks (
                title, body, status, assignee, priority, created_by,
                created_at, dedupe_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title, body, status, assignee, int(priority),
                created_by, _now(), dedupe_key,
            ),
        )
        task_id = int(cur.lastrowid)
        for parent_id in (parents or []):
            conn.execute(
                "INSERT OR IGNORE INTO task_links(parent_id, child_id) VALUES (?, ?)",
                (int(parent_id), task_id),
            )
        _record_event(conn, task_id, "create", {"title": title, "assignee": assignee})

    # Promotion check after insert (status may already be ready if parentless + status=ready was passed)
    recompute_ready(trinity_dir)
    return task_id


def get_task(trinity_dir: Path, task_id: int) -> dict | None:
    conn = db.connect(trinity_dir)
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id=?", (int(task_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_tasks(
    trinity_dir: Path,
    status: str | None = None,
    assignee: str | None = None,
    limit: int = 100,
) -> list[dict]:
    conn = db.connect(trinity_dir)
    try:
        sql = "SELECT * FROM tasks"
        wheres: list[str] = []
        args: list[Any] = []
        if status is not None:
            wheres.append("status=?")
            args.append(status)
        if assignee is not None:
            wheres.append("assignee=?")
            args.append(assignee)
        if wheres:
            sql += " WHERE " + " AND ".join(wheres)
        sql += " ORDER BY priority ASC, id ASC LIMIT ?"
        args.append(int(limit))
        rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def comment_task(trinity_dir: Path, task_id: int, author: str, body: str) -> int:
    with db.write_txn(trinity_dir) as conn:
        cur = conn.execute(
            "INSERT INTO task_comments(task_id, author, body, created_at) "
            "VALUES (?, ?, ?, ?)",
            (int(task_id), author, body, _now()),
        )
        _record_event(conn, int(task_id), "comment", {"author": author})
        return int(cur.lastrowid)


def link_tasks(trinity_dir: Path, parent_id: int, child_id: int) -> None:
    if parent_id == child_id:
        raise ValueError("a task cannot be its own parent")
    with db.write_txn(trinity_dir) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO task_links(parent_id, child_id) VALUES (?, ?)",
            (int(parent_id), int(child_id)),
        )
        _record_event(conn, int(child_id), "link", {"parent_id": parent_id})


# ── State transitions ─────────────────────────────────────────────────


def recompute_ready(trinity_dir: Path) -> int:
    """Promote eligible ``todo`` tasks to ``ready``.

    A task is eligible when every linked parent is ``done`` (or the task
    has no parents). Returns the number promoted.
    """
    with db.write_txn(trinity_dir) as conn:
        # Find all todo tasks
        candidates = conn.execute(
            "SELECT id FROM tasks WHERE status=?", (STATUS_TODO,),
        ).fetchall()
        promoted = 0
        for r in candidates:
            tid = int(r["id"])
            # All parents (if any) must be done
            unmet = conn.execute(
                """
                SELECT 1 FROM task_links tl
                JOIN tasks p ON p.id = tl.parent_id
                WHERE tl.child_id = ? AND p.status != ?
                LIMIT 1
                """,
                (tid, STATUS_DONE),
            ).fetchone()
            if unmet is None:
                conn.execute(
                    "UPDATE tasks SET status=? WHERE id=? AND status=?",
                    (STATUS_READY, tid, STATUS_TODO),
                )
                _record_event(conn, tid, "promote", {"to": STATUS_READY})
                promoted += 1
        return promoted


def claim_task(trinity_dir: Path, task_id: int, claimer: str) -> bool:
    """Atomic claim. Returns True iff this caller now holds the claim."""
    expires = (
        dt.datetime.now() + dt.timedelta(seconds=CLAIM_TTL_SECONDS)
    ).isoformat(timespec="seconds")
    lock = uuid.uuid4().hex
    now_iso = _now()

    with db.write_txn(trinity_dir) as conn:
        cur = conn.execute(
            """
            UPDATE tasks
               SET status=?, claim_lock=?, claim_expires=?, started_at=?, assignee=COALESCE(assignee, ?)
             WHERE id=?
               AND status=?
               AND (claim_lock IS NULL OR claim_expires < ?)
            """,
            (STATUS_RUNNING, lock, expires, now_iso, claimer,
             int(task_id), STATUS_READY, now_iso),
        )
        won = cur.rowcount == 1
        if won:
            _record_event(conn, int(task_id), "claim", {"by": claimer})
        return won


def complete_task(
    trinity_dir: Path,
    task_id: int,
    result: str,
    by: str | None = None,
) -> bool:
    with db.write_txn(trinity_dir) as conn:
        cur = conn.execute(
            """
            UPDATE tasks
               SET status=?, result=?, completed_at=?, claim_lock=NULL, claim_expires=NULL
             WHERE id=? AND status IN (?, ?)
            """,
            (STATUS_DONE, result, _now(), int(task_id), STATUS_RUNNING, STATUS_READY),
        )
        if cur.rowcount != 1:
            return False
        _record_event(conn, int(task_id), "complete", {"by": by})

    recompute_ready(trinity_dir)
    return True


def block_task(trinity_dir: Path, task_id: int, reason: str) -> bool:
    with db.write_txn(trinity_dir) as conn:
        cur = conn.execute(
            """
            UPDATE tasks
               SET status=?, last_failure_error=?, claim_lock=NULL, claim_expires=NULL
             WHERE id=? AND status IN (?, ?, ?)
            """,
            (STATUS_BLOCKED, reason, int(task_id),
             STATUS_RUNNING, STATUS_READY, STATUS_TODO),
        )
        if cur.rowcount != 1:
            return False
        _record_event(conn, int(task_id), "block", {"reason": reason})
        return True


def unblock_task(trinity_dir: Path, task_id: int) -> bool:
    with db.write_txn(trinity_dir) as conn:
        cur = conn.execute(
            "UPDATE tasks SET status=?, last_failure_error=NULL WHERE id=? AND status=?",
            (STATUS_TODO, int(task_id), STATUS_BLOCKED),
        )
        if cur.rowcount != 1:
            return False
        _record_event(conn, int(task_id), "unblock", {})
    recompute_ready(trinity_dir)
    return True


def archive_task(trinity_dir: Path, task_id: int) -> bool:
    with db.write_txn(trinity_dir) as conn:
        cur = conn.execute(
            "UPDATE tasks SET status=? WHERE id=?", (STATUS_ARCHIVED, int(task_id)),
        )
        if cur.rowcount != 1:
            return False
        _record_event(conn, int(task_id), "archive", {})
        return True


# ── Worker context bundling ───────────────────────────────────────────


def build_worker_context(trinity_dir: Path, task_id: int) -> str:
    """Bundle a task into a single Markdown blob for prompt injection."""
    task = get_task(trinity_dir, int(task_id))
    if task is None:
        return f"[task {task_id} not found]"

    conn = db.connect(trinity_dir)
    try:
        comments = conn.execute(
            "SELECT author, body, created_at FROM task_comments "
            "WHERE task_id=? ORDER BY id ASC",
            (int(task_id),),
        ).fetchall()
        parents = conn.execute(
            """
            SELECT p.id, p.title, p.result, p.completed_at
              FROM task_links tl
              JOIN tasks p ON p.id = tl.parent_id
             WHERE tl.child_id = ?
             ORDER BY p.id ASC
            """,
            (int(task_id),),
        ).fetchall()
    finally:
        conn.close()

    lines: list[str] = [
        f"## Task #{task['id']} — {task['title']}",
        f"**Status:** {task['status']}  "
        f"**Assignee:** {task['assignee'] or '(unassigned)'}  "
        f"**Priority:** {task['priority']}",
        "",
    ]
    if task.get("body"):
        lines.append(task["body"])
        lines.append("")

    if comments:
        lines.append("### Comments")
        for c in comments:
            lines.append(f"- [{c['author']} @ {c['created_at']}] {c['body']}")
        lines.append("")

    parents_with_results = [p for p in parents if p["result"]]
    if parents_with_results:
        lines.append("### Parent task results")
        for p in parents_with_results:
            lines.append(f"#### Task #{p['id']} — {p['title']}")
            result = (p["result"] or "")[:4000]
            lines.append(result)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def open_counts(trinity_dir: Path) -> dict[str, int]:
    """Per-employee open-task counts (excludes done/archived)."""
    conn = db.connect(trinity_dir)
    try:
        rows = conn.execute(
            """
            SELECT COALESCE(assignee, '(unassigned)') AS who, COUNT(*) AS n
              FROM tasks
             WHERE status NOT IN (?, ?)
          GROUP BY assignee
            """,
            (STATUS_DONE, STATUS_ARCHIVED),
        ).fetchall()
        return {r["who"]: int(r["n"]) for r in rows}
    finally:
        conn.close()
