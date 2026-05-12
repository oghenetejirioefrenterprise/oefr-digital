"""Kanban subsystem tests — schema, lifecycle, atomic claim, worker context."""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from trinity.kanban import board, db


@pytest.fixture
def trinity_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".trinity"
    d.mkdir()
    db.init(d)
    return d


def test_create_and_get(trinity_dir):
    tid = board.create_task(trinity_dir, "First task", body="b", assignee="Wolf")
    t = board.get_task(trinity_dir, tid)
    assert t is not None
    assert t["title"] == "First task"
    assert t["assignee"] == "Wolf"
    # Parentless tasks reach 'ready' immediately via recompute_ready.
    assert t["status"] == board.STATUS_READY


def test_dependency_promotion(trinity_dir):
    parent = board.create_task(trinity_dir, "Parent")
    child = board.create_task(trinity_dir, "Child", parents=[parent])

    assert board.get_task(trinity_dir, parent)["status"] == board.STATUS_READY
    # Child stays 'todo' while parent is not done.
    assert board.get_task(trinity_dir, child)["status"] == board.STATUS_TODO

    # Claim + complete parent.
    assert board.claim_task(trinity_dir, parent, "tester")
    assert board.complete_task(trinity_dir, parent, "parent done")

    assert board.get_task(trinity_dir, parent)["status"] == board.STATUS_DONE
    assert board.get_task(trinity_dir, child)["status"] == board.STATUS_READY


def test_atomic_claim_only_one_winner(trinity_dir):
    tid = board.create_task(trinity_dir, "Race")
    # Two threads racing to claim.
    won: list[bool] = []
    barrier = threading.Barrier(2)

    def attempt(name):
        barrier.wait()
        won.append(board.claim_task(trinity_dir, tid, name))

    threads = [threading.Thread(target=attempt, args=(n,)) for n in ("A", "B")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(won) == 1


def test_complete_unlocks_chain(trinity_dir):
    a = board.create_task(trinity_dir, "A")
    b = board.create_task(trinity_dir, "B", parents=[a])
    c = board.create_task(trinity_dir, "C", parents=[b])

    assert board.claim_task(trinity_dir, a, "x")
    assert board.complete_task(trinity_dir, a, "result A")
    assert board.get_task(trinity_dir, b)["status"] == board.STATUS_READY
    assert board.claim_task(trinity_dir, b, "x")
    assert board.complete_task(trinity_dir, b, "result B")
    assert board.get_task(trinity_dir, c)["status"] == board.STATUS_READY


def test_block_and_unblock(trinity_dir):
    tid = board.create_task(trinity_dir, "T")
    assert board.claim_task(trinity_dir, tid, "x")
    assert board.block_task(trinity_dir, tid, "stuck")
    assert board.get_task(trinity_dir, tid)["status"] == board.STATUS_BLOCKED
    assert board.unblock_task(trinity_dir, tid)
    # Unblock returns to 'todo' then recompute promotes to 'ready'.
    assert board.get_task(trinity_dir, tid)["status"] == board.STATUS_READY


def test_dedupe_key_idempotent(trinity_dir):
    a = board.create_task(trinity_dir, "X", dedupe_key="job-42")
    b = board.create_task(trinity_dir, "X again", dedupe_key="job-42")
    assert a == b


def test_comment_and_link(trinity_dir):
    a = board.create_task(trinity_dir, "Parent", body="parent body")
    c = board.create_task(trinity_dir, "Child", body="child body")
    board.link_tasks(trinity_dir, a, c)
    board.comment_task(trinity_dir, a, "Wolf", "kicking off")
    board.comment_task(trinity_dir, a, "Closer", "thanks")

    # Worker context for a includes its body + comments.
    ctx = board.build_worker_context(trinity_dir, a)
    assert "Parent" in ctx
    assert "kicking off" in ctx
    assert "thanks" in ctx


def test_worker_context_includes_parent_results(trinity_dir):
    a = board.create_task(trinity_dir, "A")
    b = board.create_task(trinity_dir, "B", parents=[a])
    board.claim_task(trinity_dir, a, "x")
    board.complete_task(trinity_dir, a, "Parent finished — see facts X, Y, Z.")

    ctx = board.build_worker_context(trinity_dir, b)
    assert "Parent finished — see facts X, Y, Z." in ctx
    assert "Task #" in ctx


def test_open_counts_excludes_done(trinity_dir):
    board.create_task(trinity_dir, "p1", assignee="Wolf")
    board.create_task(trinity_dir, "p2", assignee="Wolf")
    done_id = board.create_task(trinity_dir, "p3", assignee="Wolf")
    board.claim_task(trinity_dir, done_id, "Wolf")
    board.complete_task(trinity_dir, done_id, "ok")

    counts = board.open_counts(trinity_dir)
    assert counts.get("Wolf") == 2


def test_archive(trinity_dir):
    tid = board.create_task(trinity_dir, "X")
    board.archive_task(trinity_dir, tid)
    assert board.get_task(trinity_dir, tid)["status"] == board.STATUS_ARCHIVED
