"""Atomic JSON read/write helpers.

Writes via temp file + fsync + rename — readers never see partial files.
"""
import json
import os
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, data: Any) -> None:
    """Write *data* to *path* as pretty-printed JSON, atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path: Path) -> Any:
    """Read JSON from *path*."""
    with open(path) as f:
        return json.load(f)
