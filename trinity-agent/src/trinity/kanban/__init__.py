"""Kanban — shared work-tracking surface across employees.

SQLite-backed task board with dependency DAG, atomic claim, and
worker-context bundling. The board is the prompt context: when an
employee cycle runs, the scheduler claims its ready tasks and feeds
``build_worker_context`` output into the system message so the agent
sees the body, comments, and parent results without manual hand-off.
"""
from trinity.kanban import board, db
from trinity.kanban.board import (
    archive_task,
    block_task,
    build_worker_context,
    claim_task,
    comment_task,
    complete_task,
    create_task,
    get_task,
    link_tasks,
    list_tasks,
    recompute_ready,
    unblock_task,
    open_counts,
)

__all__ = [
    "board", "db",
    "archive_task", "block_task", "build_worker_context",
    "claim_task", "comment_task", "complete_task", "create_task",
    "get_task", "link_tasks", "list_tasks", "recompute_ready",
    "unblock_task", "open_counts",
]
