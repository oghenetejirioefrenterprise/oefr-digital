"""Distribution queue safe append (file-locked, atomic, schema-validated)."""
import fcntl
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.atomic_io import write_json_atomic, read_json
from scripts.lib.schema_validator import validate


def _empty_queue() -> dict:
    return {
        "version": 1,
        "type": "distribution_queue",
        "updated_at": _now(),
        "items": []
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_queue(path: Path) -> dict:
    """Read the queue, returning empty queue if file missing."""
    path = Path(path)
    if not path.exists():
        return _empty_queue()
    return read_json(path)


def append_item(path: Path, item: dict) -> None:
    """Append *item* to the queue, file-locked + schema-validated.

    Validates the resulting queue against the distribution_queue schema before write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            queue = read_queue(path)
            queue["items"].append(item)
            queue["updated_at"] = _now()
            validate("distribution_queue", queue)
            write_json_atomic(path, queue)
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
