"""Distribution log — atomic, file-locked, schema-validated append.

Mirrors distribution_queue.py conventions exactly.
"""
import fcntl
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.atomic_io import write_json_atomic, read_json
from scripts.lib.schema_validator import validate

LOG_FILE = "distribution-log.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _empty_log() -> dict:
    return {
        "version": 1,
        "type": "distribution_log",
        "updated_at": _now(),
        "entries": [],
    }


def log_path(workspace: Path) -> Path:
    return Path(workspace) / "state" / LOG_FILE


def read_log(workspace: Path) -> dict:
    """Read the distribution log, returning an empty log if the file is missing."""
    path = log_path(workspace)
    if not path.exists():
        return _empty_log()
    return read_json(path)


def already_posted(workspace: Path, item_id: str, channel: str) -> bool:
    """Return True if *item_id* has a 'posted' entry for *channel* in the log."""
    log = read_log(workspace)
    return any(
        e["item_id"] == item_id and e["channel"] == channel and e["status"] == "posted"
        for e in log.get("entries", [])
    )


def append_entry(workspace: Path, entry: dict) -> None:
    """Append one log entry atomically under LOCK_EX.

    *entry* must contain at minimum: item_id, slug, channel, posted_at, status.
    """
    path = log_path(Path(workspace))
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")

    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            log = read_log(workspace)
            log["entries"].append(entry)
            log["updated_at"] = _now()
            validate("distribution_log", log)
            write_json_atomic(path, log)
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
