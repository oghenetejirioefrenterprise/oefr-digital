"""Atomic JSON I/O — write-to-tmp then rename for crash safety."""
import json
import os
import tempfile
from pathlib import Path


def read_json(path: Path) -> dict:
    """Read and parse a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically: write to a temp file then rename into place."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.rename(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
