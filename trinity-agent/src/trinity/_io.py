"""Atomic filesystem helpers.

Trinity writes several JSON state files that must never be left half-written
(memory index, usage counters, scheduler state). A crash or concurrent read
mid-write can either corrupt the file or deliver a partial read to another
thread. These helpers use the write-to-tmp + fsync + rename pattern that is
atomic on POSIX filesystems.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


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
