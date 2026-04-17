"""Core CRUD operations for the three-tier memory system.

Memories are Markdown files with YAML frontmatter, stored in
.trinity/memory/{tier}/.  An index.json file tracks all memories
for fast listing and lookup.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
from pathlib import Path
from typing import Any

from trinity._io import atomic_write_json
from trinity._safety import validate_memory_id

# Module-level lock for thread-safe index.json access.
# Every function that reads+writes the index must acquire this lock.
_index_lock = threading.Lock()

TIERS = ["short-term", "long-term", "permanent"]
SEGMENTS = [
    "corrections", "preferences", "facts",
    "relationships", "projects", "skills", "context",
]

SEGMENT_WEIGHTS: dict[str, float] = {
    "corrections": 0.95,
    "preferences": 0.85,
    "facts": 0.7,
    "relationships": 0.8,
    "projects": 0.6,
    "skills": 0.75,
    "context": 0.5,
}

SEGMENT_DECAY_MODIFIERS: dict[str, float] = {
    "corrections": 0.5,
    "preferences": 0.5,
    "facts": 1.0,
    "relationships": 0.3,
    "projects": 1.5,
    "skills": 0.7,
    "context": 2.0,
}


# ── Helpers ────────────────────────────────────────────────────────

def _memory_dir(trinity_dir: Path) -> Path:
    return trinity_dir / "memory"


def _index_path(trinity_dir: Path) -> Path:
    return _memory_dir(trinity_dir) / "index.json"


def _load_index(trinity_dir: Path) -> list[dict[str, Any]]:
    idx = _index_path(trinity_dir)
    if not idx.exists():
        return []
    try:
        return json.loads(idx.read_text())
    except (json.JSONDecodeError, ValueError):
        return []


def _save_index(trinity_dir: Path, index: list[dict[str, Any]]) -> None:
    atomic_write_json(_index_path(trinity_dir), index)


def _next_id(trinity_dir: Path) -> str:
    """Generate a memory ID like mem_20260413_001."""
    today = dt.date.today().strftime("%Y%m%d")
    prefix = f"mem_{today}_"
    index = _load_index(trinity_dir)

    # Find the highest sequence number for today
    max_seq = 0
    for entry in index:
        mid = entry.get("id", "")
        if mid.startswith(prefix):
            try:
                seq = int(mid[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass

    return f"{prefix}{max_seq + 1:03d}"


def _tier_dir(trinity_dir: Path, tier: str) -> Path:
    return _memory_dir(trinity_dir) / tier


def _find_memory_file(trinity_dir: Path, memory_id: str) -> Path | None:
    """Find a memory file across all tiers."""
    for tier in TIERS:
        path = _tier_dir(trinity_dir, tier) / f"{memory_id}.md"
        if path.exists():
            return path
    return None


def _find_memory_tier(trinity_dir: Path, memory_id: str) -> str | None:
    """Find which tier a memory lives in."""
    for tier in TIERS:
        path = _tier_dir(trinity_dir, tier) / f"{memory_id}.md"
        if path.exists():
            return tier
    return None


def _parse_memory_file(path: Path) -> dict[str, Any]:
    """Parse a memory .md file into a dict with frontmatter + content."""
    text = path.read_text()
    # Split on YAML frontmatter delimiters
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return {"content": text}

    frontmatter_text = match.group(1)
    content = match.group(2).strip()

    # Parse YAML-like frontmatter manually (simple key: value)
    meta: dict[str, Any] = {}
    for line in frontmatter_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Type coercion
            if value.lower() in ("true", "false"):
                meta[key] = value.lower() == "true"
            else:
                try:
                    meta[key] = int(value)
                except ValueError:
                    try:
                        meta[key] = float(value)
                    except ValueError:
                        meta[key] = value

    meta["content"] = content
    return meta


def _write_memory_file(path: Path, meta: dict[str, Any], content: str) -> None:
    """Write a memory file with YAML frontmatter."""
    lines = ["---"]
    for key in [
        "id", "segment", "importance", "decay_rate",
        "created", "last_accessed", "access_count", "source", "summary",
        "kind", "status", "product", "category",
    ]:
        if key in meta and meta[key]:
            lines.append(f"{key}: {meta[key]}")
    lines.append("---")
    lines.append("")
    lines.append(content)
    path.write_text("\n".join(lines) + "\n")


def _generate_summary(content: str) -> str:
    """Create a short summary from the first line of content."""
    first_line = content.strip().split("\n")[0]
    if len(first_line) > 120:
        return first_line[:117] + "..."
    return first_line


# ── Public API ─────────────────────────────────────────────────────

def init_memory(trinity_dir: Path) -> None:
    """Create tier directories and index.json if missing."""
    mem_dir = _memory_dir(trinity_dir)
    mem_dir.mkdir(parents=True, exist_ok=True)

    for tier in TIERS:
        _tier_dir(trinity_dir, tier).mkdir(parents=True, exist_ok=True)

    with _index_lock:
        idx = _index_path(trinity_dir)
        if not idx.exists():
            _save_index(trinity_dir, [])


def store_memory(
    trinity_dir: Path,
    content: str,
    segment: str,
    importance: float | None = None,
    source: str = "",
    kind: str = "",
    status: str = "",
    product: str = "",
    category: str = "",
) -> str:
    """Create a new memory in short-term tier.

    Returns the generated memory ID.

    kind: wiki entry type (issue, decision, audit, lesson, signal, correction)
    status: for issues — open, fixed, false-positive, wont-fix
    product: for issues/audits — product name
    category: for lessons — win, failure, process
    """
    if segment not in SEGMENTS:
        raise ValueError(f"Invalid segment '{segment}'. Must be one of: {SEGMENTS}")

    init_memory(trinity_dir)

    now = dt.datetime.now().isoformat(timespec="seconds")

    # Default importance from segment weight
    if importance is None:
        importance = SEGMENT_WEIGHTS.get(segment, 0.5)

    decay_rate = SEGMENT_DECAY_MODIFIERS.get(segment, 1.0)
    summary = _generate_summary(content)

    meta = {
        "id": "",  # placeholder, set under lock
        "segment": segment,
        "importance": importance,
        "decay_rate": decay_rate,
        "created": now,
        "last_accessed": now,
        "access_count": 1,
        "source": source,
        "summary": summary,
        "kind": kind,
        "status": status,
        "product": product,
        "category": category,
    }

    with _index_lock:
        memory_id = _next_id(trinity_dir)
        meta["id"] = memory_id

        # Write the file
        path = _tier_dir(trinity_dir, "short-term") / f"{memory_id}.md"
        _write_memory_file(path, meta, content)

        # Update index
        index = _load_index(trinity_dir)
        index_entry = {
            "id": memory_id,
            "tier": "short-term",
            "segment": segment,
            "importance": importance,
            "decay_rate": decay_rate,
            "last_accessed": now,
            "created": now,
            "access_count": 1,
            "summary": summary,
        }
        if kind:
            index_entry["kind"] = kind
        if status:
            index_entry["status"] = status
        if product:
            index_entry["product"] = product
        if category:
            index_entry["category"] = category
        index.append(index_entry)
        _save_index(trinity_dir, index)

    return memory_id


def recall_memory(trinity_dir: Path, memory_id: str) -> dict[str, Any] | None:
    """Read a memory, update access stats, and return parsed dict."""
    validate_memory_id(memory_id)
    with _index_lock:
        path = _find_memory_file(trinity_dir, memory_id)
        if path is None:
            return None

        data = _parse_memory_file(path)
        tier = _find_memory_tier(trinity_dir, memory_id)

        # Update access stats
        now = dt.datetime.now().isoformat(timespec="seconds")
        data["last_accessed"] = now
        data["access_count"] = data.get("access_count", 0) + 1

        content = data.pop("content", "")
        _write_memory_file(path, data, content)
        data["content"] = content
        data["tier"] = tier

        # Update index
        index = _load_index(trinity_dir)
        for entry in index:
            if entry["id"] == memory_id:
                entry["last_accessed"] = now
                entry["access_count"] = data["access_count"]
                break
        _save_index(trinity_dir, index)

    return data


def update_memory(trinity_dir: Path, memory_id: str, content: str) -> bool:
    """Update the content of an existing memory."""
    validate_memory_id(memory_id)
    with _index_lock:
        path = _find_memory_file(trinity_dir, memory_id)
        if path is None:
            return False

        data = _parse_memory_file(path)
        now = dt.datetime.now().isoformat(timespec="seconds")
        data["last_accessed"] = now
        data["summary"] = _generate_summary(content)
        data.pop("content", None)
        _write_memory_file(path, data, content)

        index = _load_index(trinity_dir)
        for entry in index:
            if entry["id"] == memory_id:
                entry["last_accessed"] = now
                entry["summary"] = data["summary"]
                break
        _save_index(trinity_dir, index)

    return True


def forget_memory(trinity_dir: Path, memory_id: str) -> bool:
    """Delete a memory file and remove from index."""
    validate_memory_id(memory_id)
    with _index_lock:
        path = _find_memory_file(trinity_dir, memory_id)
        if path is None:
            return False

        path.unlink()

        index = _load_index(trinity_dir)
        index = [e for e in index if e["id"] != memory_id]
        _save_index(trinity_dir, index)

    return True


def promote_memory(trinity_dir: Path, memory_id: str, target_tier: str) -> bool:
    """Move a memory from its current tier to the target tier."""
    validate_memory_id(memory_id)
    if target_tier not in TIERS:
        raise ValueError(f"Invalid tier '{target_tier}'. Must be one of: {TIERS}")

    with _index_lock:
        current_tier = _find_memory_tier(trinity_dir, memory_id)
        if current_tier is None:
            return False

        if current_tier == target_tier:
            return True  # already there

        src = _tier_dir(trinity_dir, current_tier) / f"{memory_id}.md"
        dst = _tier_dir(trinity_dir, target_tier) / f"{memory_id}.md"

        dst.parent.mkdir(parents=True, exist_ok=True)

        dst.write_text(src.read_text())
        src.unlink()

        index = _load_index(trinity_dir)
        for entry in index:
            if entry["id"] == memory_id:
                entry["tier"] = target_tier
                break
        _save_index(trinity_dir, index)

    return True


def list_memories(trinity_dir: Path, tier: str | None = None) -> list[dict[str, Any]]:
    """List all memories (or filtered by tier) from the index."""
    index = _load_index(trinity_dir)

    if tier is not None:
        if tier not in TIERS:
            raise ValueError(f"Invalid tier '{tier}'. Must be one of: {TIERS}")
        return [e for e in index if e.get("tier") == tier]

    return index


def update_memory_metadata(trinity_dir: Path, memory_id: str, **kwargs: Any) -> bool:
    """Update metadata fields on an existing memory (e.g. status, kind, product).

    Updates both the memory file frontmatter and the index entry.
    Returns True if memory was found and updated, False otherwise.
    """
    validate_memory_id(memory_id)
    path = _find_memory_file(trinity_dir, memory_id)
    if path is None:
        return False

    # Update the memory file
    data = _parse_memory_file(path)
    content = data.pop("content", "")
    for key, value in kwargs.items():
        data[key] = value
    data["last_accessed"] = dt.datetime.now().isoformat(timespec="seconds")
    _write_memory_file(path, data, content)

    # Update the index
    with _index_lock:
        index = _load_index(trinity_dir)
        for entry in index:
            if entry["id"] == memory_id:
                for key, value in kwargs.items():
                    entry[key] = value
                entry["last_accessed"] = data["last_accessed"]
                break
        _save_index(trinity_dir, index)

    return True


def query_by_kind(
    trinity_dir: Path,
    kind: str,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return all memories matching a kind (and optionally status).

    Results are sorted by creation date ascending (oldest first).
    Each result includes the full index entry data.
    """
    index = _load_index(trinity_dir)
    results = []
    for entry in index:
        if entry.get("kind") != kind:
            continue
        if status is not None and entry.get("status") != status:
            continue
        results.append(entry)

    # Sort by created date ascending
    results.sort(key=lambda e: e.get("created", ""))
    return results
