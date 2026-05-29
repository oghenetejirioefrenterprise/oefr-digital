"""Atomic filesystem helpers.

Trinity writes several JSON state files that must never be left half-written
(memory index, usage counters, scheduler state). A crash or concurrent read
mid-write can either corrupt the file or deliver a partial read to another
thread. These helpers use the write-to-tmp + fsync + rename pattern that is
atomic on POSIX filesystems.
"""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def file_lock(path: Path):
    """Cross-process exclusive advisory lock around a read-modify-write.

    The in-process ``threading.Lock`` used by the JSON state stores does not
    serialise *separate processes* (the daemon vs. CLI invocations), so two
    processes can each load → mutate → atomic-write and silently lose one
    update. This wraps the critical section in an ``fcntl.flock`` on a sidecar
    ``.lock`` file, which serialises across processes AND threads.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
        finally:
            fd.close()


def atomic_write_text(path: Path, content: str, *, fsync: bool = True) -> None:
    """Write ``content`` to ``path`` atomically.

    Writes to ``{path}.tmp``, optionally fsyncs the contents, then renames onto
    the target. Readers either see the old file or the new file — never a
    partially-written one.

    ``fsync=False`` skips the durability sync — appropriate for derived,
    regenerable artifacts (e.g. the Markdown export of a SQLite-backed memory)
    where the rename's crash-atomicity is wanted but a per-write fsync is not.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    if fsync:
        with open(tmp, "rb") as fh:
            os.fsync(fh.fileno())
    os.replace(tmp, path)


def atomic_write_json(path: Path, data: Any, *, indent: int | None = 2) -> None:
    """Serialize ``data`` as JSON and write atomically."""
    atomic_write_text(
        path,
        json.dumps(data, indent=indent, default=str, ensure_ascii=False),
    )
