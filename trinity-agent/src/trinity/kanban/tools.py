"""Kanban tool handlers — agent-facing surface registered with the tool registry."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from trinity.kanban import board

log = logging.getLogger(__name__)

_trinity_dir: Path | None = None


def set_trinity_dir(path: Path) -> None:
    global _trinity_dir
    _trinity_dir = path


def _ensure_dir() -> Path:
    if _trinity_dir is None:
        raise RuntimeError("kanban tools used before set_trinity_dir() was called")
    return _trinity_dir


# ── Schemas + handlers ────────────────────────────────────────────────


BOARD_CREATE_SCHEMA: dict[str, Any] = {
    "name": "board_create_task",
    "description": (
        "Create a task on the shared kanban board. Returns the new task id. "
        "Use 'parents' to declare dependencies — the task becomes 'ready' "
        "only when every parent reaches 'done'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short task title."},
            "body": {"type": "string", "description": "Full description / spec."},
            "assignee": {"type": "string", "description": "Employee name."},
            "priority": {"type": "integer", "description": "1=high … 5=low. Default 3."},
            "parents": {
                "type": "string",
                "description": "JSON-encoded array of parent task IDs (integers).",
            },
            "dedupe_key": {
                "type": "string",
                "description": "Optional unique key to make creation idempotent.",
            },
        },
        "required": ["title"],
    },
}


def board_create_task(inp: dict, _ws: Path, **_ctx: Any) -> str:
    parents_raw = inp.get("parents") or "[]"
    try:
        parents = json.loads(parents_raw) if isinstance(parents_raw, str) else parents_raw
        parents = [int(p) for p in (parents or [])]
    except (json.JSONDecodeError, ValueError):
        return "Error: 'parents' must be a JSON array of integers."
    tid = board.create_task(
        _ensure_dir(),
        title=inp["title"],
        body=inp.get("body"),
        assignee=inp.get("assignee"),
        priority=int(inp.get("priority") or 3),
        parents=parents,
        dedupe_key=inp.get("dedupe_key"),
    )
    return f"Created task #{tid}"


BOARD_LIST_SCHEMA: dict[str, Any] = {
    "name": "board_list_tasks",
    "description": "List tasks on the board, optionally filtered by status and/or assignee.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "triage | todo | ready | running | blocked | done | archived",
            },
            "assignee": {"type": "string"},
            "limit": {"type": "integer", "description": "Default 50."},
        },
    },
}


def board_list_tasks(inp: dict, _ws: Path, **_ctx: Any) -> str:
    rows = board.list_tasks(
        _ensure_dir(),
        status=inp.get("status"),
        assignee=inp.get("assignee"),
        limit=int(inp.get("limit") or 50),
    )
    if not rows:
        return "No tasks match."
    lines = []
    for t in rows:
        lines.append(
            f"#{t['id']:>3}  P{t['priority']}  {t['status']:<8}  "
            f"{(t['assignee'] or '(unassigned)'):<14}  {t['title']}"
        )
    return "\n".join(lines)


BOARD_SHOW_SCHEMA: dict[str, Any] = {
    "name": "board_show_task",
    "description": (
        "Show a task's full body, comments, and the results of any "
        "completed parent tasks. Use this before starting work."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"task_id": {"type": "integer"}},
        "required": ["task_id"],
    },
}


def board_show_task(inp: dict, _ws: Path, **_ctx: Any) -> str:
    return board.build_worker_context(_ensure_dir(), int(inp["task_id"]))


BOARD_CLAIM_SCHEMA: dict[str, Any] = {
    "name": "board_claim_task",
    "description": (
        "Atomically claim a 'ready' task. Returns success or fail; another "
        "worker may have grabbed it first."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "claimer": {"type": "string", "description": "Your employee name."},
        },
        "required": ["task_id", "claimer"],
    },
}


def board_claim_task(inp: dict, _ws: Path, **_ctx: Any) -> str:
    won = board.claim_task(_ensure_dir(), int(inp["task_id"]), str(inp["claimer"]))
    return "Claim acquired." if won else "Claim failed (already taken or not ready)."


BOARD_COMPLETE_SCHEMA: dict[str, Any] = {
    "name": "board_complete_task",
    "description": "Mark a running task as done with a result summary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "result": {"type": "string", "description": "Result summary."},
            "by": {"type": "string"},
        },
        "required": ["task_id", "result"],
    },
}


def board_complete_task(inp: dict, _ws: Path, **_ctx: Any) -> str:
    ok = board.complete_task(
        _ensure_dir(), int(inp["task_id"]), str(inp["result"]),
        by=inp.get("by"),
    )
    return "Completed." if ok else "Could not complete (wrong state?)."


BOARD_BLOCK_SCHEMA: dict[str, Any] = {
    "name": "board_block_task",
    "description": "Mark a task as blocked with a reason.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "reason": {"type": "string"},
        },
        "required": ["task_id", "reason"],
    },
}


def board_block_task(inp: dict, _ws: Path, **_ctx: Any) -> str:
    ok = board.block_task(_ensure_dir(), int(inp["task_id"]), str(inp["reason"]))
    return "Blocked." if ok else "Could not block (wrong state?)."


BOARD_COMMENT_SCHEMA: dict[str, Any] = {
    "name": "board_comment_task",
    "description": "Add a comment to a task.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer"},
            "author": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["task_id", "author", "body"],
    },
}


def board_comment_task(inp: dict, _ws: Path, **_ctx: Any) -> str:
    cid = board.comment_task(
        _ensure_dir(),
        int(inp["task_id"]), str(inp["author"]), str(inp["body"]),
    )
    return f"Comment #{cid} added."


BOARD_LINK_SCHEMA: dict[str, Any] = {
    "name": "board_link_tasks",
    "description": "Declare a parent→child dependency. Child cannot become 'ready' until parent is 'done'.",
    "input_schema": {
        "type": "object",
        "properties": {
            "parent_id": {"type": "integer"},
            "child_id": {"type": "integer"},
        },
        "required": ["parent_id", "child_id"],
    },
}


def board_link_tasks(inp: dict, _ws: Path, **_ctx: Any) -> str:
    board.link_tasks(_ensure_dir(), int(inp["parent_id"]), int(inp["child_id"]))
    return f"Linked #{inp['parent_id']} → #{inp['child_id']}."


ALL_SPECS = [
    (BOARD_CREATE_SCHEMA, board_create_task),
    (BOARD_LIST_SCHEMA, board_list_tasks),
    (BOARD_SHOW_SCHEMA, board_show_task),
    (BOARD_CLAIM_SCHEMA, board_claim_task),
    (BOARD_COMPLETE_SCHEMA, board_complete_task),
    (BOARD_BLOCK_SCHEMA, board_block_task),
    (BOARD_COMMENT_SCHEMA, board_comment_task),
    (BOARD_LINK_SCHEMA, board_link_tasks),
]
