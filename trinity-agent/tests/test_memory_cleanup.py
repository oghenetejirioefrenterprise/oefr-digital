"""Regression tests for memory cleanup operations (DB-driven)."""
from __future__ import annotations

from pathlib import Path

from trinity.memory import db, store
from trinity.memory.cleanup import run_cleanup, find_duplicates


def _backdate_all(td: Path, when: str = "2020-01-01T00:00:00") -> None:
    """Force every memory's last_accessed/created old (test-only)."""
    conn = db.connect(td)
    try:
        conn.execute("UPDATE memories SET last_accessed=?, created=?", (when, when))
    finally:
        conn.close()


def _td(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def test_run_cleanup_dry_run_does_not_delete(tmp_path: Path) -> None:
    td = _td(tmp_path)
    store.store_memory(td, "This is duplicate content for testing purposes.", "facts")
    store.store_memory(td, "This is duplicate content for testing purposes.", "facts")

    summary = run_cleanup(td, dry_run=True)
    assert summary["dry_run"] is True
    assert summary["deleted"] == 0
    # Both memories still present.
    assert len(store.list_memories(td)) == 2


def test_run_cleanup_real_run_deletes_duplicates(tmp_path: Path) -> None:
    td = _td(tmp_path)
    store.store_memory(td, "This is duplicate content for testing purposes.", "facts")
    store.store_memory(td, "This is duplicate content for testing purposes.", "facts")

    summary = run_cleanup(td, dry_run=False)
    assert summary["dry_run"] is False
    # Keep-newest rule leaves exactly one of the duplicates.
    assert len(store.list_memories(td)) == 1


def test_find_duplicates_clusters_identical_bodies(tmp_path: Path) -> None:
    td = _td(tmp_path)
    store.store_memory(td, "alpha beta gamma identical body text here", "facts")
    store.store_memory(td, "alpha beta gamma identical body text here", "facts")
    store.store_memory(td, "completely different unrelated content", "facts")

    clusters = find_duplicates(td)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_cleanup_keeps_recently_recalled_memory(tmp_path: Path) -> None:
    """A hot memory (old created, but recalled recently) must NOT be purged.

    Regression for the bug where cleanup judged staleness from the frozen .md
    export instead of the live DB last_accessed, deleting hot memories.
    """
    td = _td(tmp_path)
    mid = store.store_memory(td, "hot memory recalled often unique zzz", "facts")
    _backdate_all(td)            # created + last_accessed far in the past
    store.recall_memory(td, mid)  # bumps DB last_accessed to now

    run_cleanup(td, dry_run=False, stale_days=1)
    assert store.recall_memory(td, mid) is not None
    assert len(store.list_memories(td)) == 1


def test_cleanup_protects_permanent_and_open_issues(tmp_path: Path) -> None:
    """Stale permanent memories and open issues must never be deleted."""
    td = _td(tmp_path)
    # An old, unreferenced permanent memory.
    perm = store.store_memory(td, "permanent canonical fact", "facts")
    store.promote_memory(td, perm, "permanent")
    # An old, unreferenced open issue.
    store.store_memory(td, "an open issue", "facts", kind="issue", status="open")
    # Backdate both so they'd be "stale" by date.
    _backdate_all(td)

    summary = run_cleanup(td, dry_run=False, stale_days=1)
    assert summary["protected"] >= 2
    assert summary["deleted"] == 0
    assert len(store.list_memories(td)) == 2
