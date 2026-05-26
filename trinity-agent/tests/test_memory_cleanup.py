"""Regression tests for memory cleanup operations."""
from __future__ import annotations

from pathlib import Path

from trinity.memory.cleanup import run_cleanup


def test_run_cleanup_dry_run_does_not_delete(tmp_workspace: Path) -> None:
    memory = tmp_workspace / ".trinity" / "memory"
    (memory / "long-term").mkdir(parents=True, exist_ok=True)

    # Create 2 obvious duplicates.
    (memory / "long-term" / "dup_a.md").write_text(
        "---\nname: dup-a\n---\n\n"
        "This is duplicate content for testing purposes."
    )
    (memory / "long-term" / "dup_b.md").write_text(
        "---\nname: dup-b\n---\n\n"
        "This is duplicate content for testing purposes."
    )

    summary = run_cleanup(memory, dry_run=True)
    assert summary["dry_run"] is True
    assert summary["deleted"] == 0
    # Files still on disk.
    assert (memory / "long-term" / "dup_a.md").exists()
    assert (memory / "long-term" / "dup_b.md").exists()


def test_run_cleanup_real_run_deletes_duplicates(tmp_workspace: Path) -> None:
    memory = tmp_workspace / ".trinity" / "memory"
    (memory / "long-term").mkdir(parents=True, exist_ok=True)
    (memory / "long-term" / "dup_a.md").write_text(
        "---\nname: dup-a\n---\n\n"
        "This is duplicate content for testing purposes."
    )
    (memory / "long-term" / "dup_b.md").write_text(
        "---\nname: dup-b\n---\n\n"
        "This is duplicate content for testing purposes."
    )

    summary = run_cleanup(memory, dry_run=False)
    assert summary["dry_run"] is False
    # One of the duplicates should be deleted (keep-newest rule keeps one).
    remaining = list((memory / "long-term").glob("*.md"))
    assert len(remaining) == 1
