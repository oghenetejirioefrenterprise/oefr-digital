"""``trinity board`` subcommand — human-facing kanban CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from trinity.kanban import board


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("board", help="Kanban board operations")
    sp = p.add_subparsers(dest="board_cmd", required=True)

    p_create = sp.add_parser("create", help="Create a new task")
    p_create.add_argument("title")
    p_create.add_argument("--body")
    p_create.add_argument("--assignee")
    p_create.add_argument("--priority", type=int, default=3)
    p_create.add_argument("--parent", type=int, action="append", default=[])
    p_create.add_argument("--dedupe-key")

    p_list = sp.add_parser("list", help="List tasks")
    p_list.add_argument("--status")
    p_list.add_argument("--assignee")
    p_list.add_argument("--limit", type=int, default=50)

    p_show = sp.add_parser("show", help="Show full task with comments + parent results")
    p_show.add_argument("task_id", type=int)

    p_assign = sp.add_parser("assign", help="Reassign a task")
    p_assign.add_argument("task_id", type=int)
    p_assign.add_argument("assignee")

    p_complete = sp.add_parser("complete", help="Mark a task done")
    p_complete.add_argument("task_id", type=int)
    p_complete.add_argument("--result", default="(manual)")

    p_block = sp.add_parser("block", help="Mark a task blocked")
    p_block.add_argument("task_id", type=int)
    p_block.add_argument("reason")

    p_unblock = sp.add_parser("unblock", help="Unblock a task back to todo")
    p_unblock.add_argument("task_id", type=int)

    p_link = sp.add_parser("link", help="Declare parent → child dependency")
    p_link.add_argument("parent_id", type=int)
    p_link.add_argument("child_id", type=int)

    p_archive = sp.add_parser("archive", help="Archive a task")
    p_archive.add_argument("task_id", type=int)


def dispatch(workspace: Path, args: argparse.Namespace) -> None:
    trinity_dir = workspace / ".trinity"
    cmd = args.board_cmd

    if cmd == "create":
        tid = board.create_task(
            trinity_dir,
            title=args.title,
            body=args.body,
            assignee=args.assignee,
            priority=args.priority,
            parents=args.parent,
            dedupe_key=args.dedupe_key,
        )
        print(f"Created task #{tid}")
        return

    if cmd == "list":
        rows = board.list_tasks(
            trinity_dir,
            status=args.status,
            assignee=args.assignee,
            limit=args.limit,
        )
        if not rows:
            print("No tasks.")
            return
        for r in rows:
            print(
                f"#{r['id']:>3}  P{r['priority']}  {r['status']:<8}  "
                f"{(r['assignee'] or '(unassigned)'):<14}  {r['title']}"
            )
        return

    if cmd == "show":
        print(board.build_worker_context(trinity_dir, args.task_id))
        return

    if cmd == "assign":
        from trinity.kanban import db as kdb
        with kdb.write_txn(trinity_dir) as conn:
            cur = conn.execute(
                "UPDATE tasks SET assignee=? WHERE id=?",
                (args.assignee, args.task_id),
            )
            ok = cur.rowcount == 1
        print(f"Assigned task #{args.task_id} → {args.assignee}" if ok else "Not found")
        return

    if cmd == "complete":
        ok = board.complete_task(trinity_dir, args.task_id, args.result, by="cli")
        print("Completed." if ok else "Not in a completable state.")
        return

    if cmd == "block":
        ok = board.block_task(trinity_dir, args.task_id, args.reason)
        print("Blocked." if ok else "Could not block.")
        return

    if cmd == "unblock":
        ok = board.unblock_task(trinity_dir, args.task_id)
        print("Unblocked." if ok else "Not in blocked state.")
        return

    if cmd == "link":
        board.link_tasks(trinity_dir, args.parent_id, args.child_id)
        print(f"Linked #{args.parent_id} → #{args.child_id}")
        return

    if cmd == "archive":
        ok = board.archive_task(trinity_dir, args.task_id)
        print("Archived." if ok else "Not found.")
        return
