"""Core CRUD operations for the three-tier memory system.

Backed by an embedded SQLite database (``.trinity/memory/memory.db``) with an
FTS5 full-text index — the same engine the kanban board already uses. A single
``memories`` row is the source of truth for each memory; the Markdown files
under ``.trinity/memory/{tier}/`` are kept as a synced, human-readable export
(also consumed by the cross-workspace ``trinity memory publish`` command) but
are never read back on the recall/search hot path.

This replaces the previous design where every operation rewrote a monolithic
``index.json`` (O(N) per write, O(N²) over a run), a *read* rewrote both the
``.md`` file and the whole index, and a ``threading.Lock`` gave no protection
against the separate CLI processes that mutate the same store. SQLite's WAL +
``BEGIN IMMEDIATE`` serialise writes correctly across processes, single-row
UPDATEs are O(1), and FTS5 turns search from "re-parse every file" into an
indexed match. The public API below is byte-for-byte compatible with callers.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from trinity._io import atomic_write_text
from trinity._safety import redact, validate_memory_id
from trinity.memory import db

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

# Columns that callers may set via update_memory_metadata / store.
_MUTABLE_FIELDS = {
    "tier", "segment", "importance", "decay_rate", "source", "summary",
    "kind", "status", "product", "category", "scope", "content", "supersedes",
}

# Order used when writing the human-readable Markdown export frontmatter.
_FRONTMATTER_KEYS = [
    "id", "segment", "importance", "decay_rate",
    "created", "last_accessed", "access_count", "source", "summary",
    "kind", "status", "product", "category", "scope", "supersedes",
]


# ── Helpers ────────────────────────────────────────────────────────

def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _memory_dir(trinity_dir: Path) -> Path:
    return trinity_dir / "memory"


def _tier_dir(trinity_dir: Path, tier: str) -> Path:
    """Directory holding the Markdown export for a tier.

    Kept public-ish (imported historically) for the migrator and export.
    """
    return _memory_dir(trinity_dir) / tier


def _parse_memory_file(path: Path) -> dict[str, Any]:
    """Parse a memory .md file into a dict with frontmatter + content.

    Retained for the one-time legacy migration and as a back-compat helper.
    """
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return {"content": text}

    frontmatter_text = match.group(1)
    content = match.group(2).strip()

    meta: dict[str, Any] = {}
    for line in frontmatter_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
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


def _generate_summary(content: str) -> str:
    """Create a short summary from the first line of content."""
    first_line = content.strip().split("\n")[0]
    if len(first_line) > 120:
        return first_line[:117] + "..."
    return first_line


def _write_memory_file(path: Path, meta: dict[str, Any], content: str) -> None:
    """Write a memory .md file (the human-readable export) atomically.

    Atomic (tmp + fsync + rename) so a crash or a concurrent reader never sees
    a half-written file. A field is emitted when present and not blank — a
    falsy-but-meaningful value such as ``importance: 0.0`` is preserved (the
    old ``if meta[key]`` truthiness test silently dropped it).
    """
    lines = ["---"]
    for key in _FRONTMATTER_KEYS:
        if key in meta and meta[key] not in (None, ""):
            lines.append(f"{key}: {meta[key]}")
    lines.append("---")
    lines.append("")
    lines.append(content)
    # The export is a derived, regenerable artifact (the DB row is the source
    # of truth), so skip the per-write fsync — the atomic rename is enough.
    atomic_write_text(path, "\n".join(lines) + "\n", fsync=False)


def _export_markdown(trinity_dir: Path, row: dict[str, Any]) -> None:
    """Best-effort sync of a DB row to its Markdown export. Never raises."""
    try:
        tier = row.get("tier") or "short-term"
        path = _tier_dir(trinity_dir, tier) / f"{row['id']}.md"
        _write_memory_file(path, row, row.get("content", ""))
    except Exception:
        pass


def _remove_export(trinity_dir: Path, memory_id: str) -> None:
    """Best-effort removal of a memory's Markdown export across all tiers."""
    for tier in TIERS:
        p = _tier_dir(trinity_dir, tier) / f"{memory_id}.md"
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass


def _row_to_index_entry(row: Any) -> dict[str, Any]:
    """Project a DB row into the lightweight index-entry shape callers expect.

    Mirrors the keys the old index.json carried (no body content).
    """
    return {
        "id": row["id"],
        "tier": row["tier"],
        "segment": row["segment"],
        "importance": row["importance"],
        "decay_rate": row["decay_rate"],
        "last_accessed": row["last_accessed"],
        "created": row["created"],
        "access_count": row["access_count"],
        "summary": row["summary"],
        "scope": row["scope"],
        "kind": row["kind"],
        "status": row["status"],
        "product": row["product"],
        "category": row["category"],
    }


def _next_id(conn: Any, today: str) -> str:
    """Generate the next memory ID for *today* (mem_YYYYMMDD_NNN).

    Called inside a ``BEGIN IMMEDIATE`` transaction so the read-then-insert is
    atomic across processes — no two writers can derive the same sequence. The
    MAX(CAST(...)) runs in SQLite over today's rows only (range scan on the PK
    index); non-numeric migrated suffixes cast to 0 and are ignored.
    """
    prefix = f"mem_{today}_"
    row = conn.execute(
        "SELECT MAX(CAST(substr(id, ?) AS INTEGER)) AS m "
        "FROM memories WHERE id LIKE ?",
        (len(prefix) + 1, prefix + "%"),
    ).fetchone()
    max_seq = (row["m"] if row and row["m"] is not None else 0)
    return f"{prefix}{int(max_seq) + 1:03d}"


# ── One-time migration from the legacy index.json + .md layout ──────

_migrate_lock = threading.Lock()
_migrate_checked: set[str] = set()


def _run_migration(trinity_dir: Path) -> None:
    """Import a legacy index.json + tier .md files into the DB. Idempotent.

    Guarded cross-process by a ``schema_meta`` row, so a second process that
    starts mid-migration will not double-import. Existing rows are left intact
    (``INSERT OR IGNORE``). The legacy index.json is renamed aside on success;
    the .md files stay in place and become the export.
    """
    index_path = _memory_dir(trinity_dir) / "index.json"
    with db.write_txn(trinity_dir) as conn:
        done = conn.execute(
            "SELECT value FROM schema_meta WHERE key='legacy_migrated'"
        ).fetchone()
        if done:
            return

        if index_path.exists():
            try:
                index = json.loads(index_path.read_text())
            except (json.JSONDecodeError, ValueError, OSError):
                index = []

            for entry in index if isinstance(index, list) else []:
                mid = entry.get("id")
                if not mid:
                    continue
                tier = entry.get("tier", "short-term")
                file_meta: dict[str, Any] = {}
                for t in TIERS:
                    p = _tier_dir(trinity_dir, t) / f"{mid}.md"
                    if p.exists():
                        try:
                            file_meta = _parse_memory_file(p)
                        except OSError:
                            file_meta = {}
                        tier = t  # file location wins for tier
                        break
                created = str(entry.get("created") or file_meta.get("created") or _now())
                last_acc = str(entry.get("last_accessed") or file_meta.get("last_accessed") or created)
                conn.execute(
                    """INSERT OR IGNORE INTO memories
                       (id, tier, segment, importance, decay_rate, created,
                        last_accessed, access_count, source, summary, kind,
                        status, product, category, scope, content, supersedes)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        str(mid),
                        tier,
                        str(entry.get("segment") or file_meta.get("segment") or "context"),
                        float(entry.get("importance", file_meta.get("importance", 0.5)) or 0.5),
                        float(entry.get("decay_rate", file_meta.get("decay_rate", 1.0)) or 1.0),
                        created,
                        last_acc,
                        int(entry.get("access_count", file_meta.get("access_count", 1)) or 1),
                        str(entry.get("source") or file_meta.get("source") or ""),
                        str(entry.get("summary") or file_meta.get("summary") or ""),
                        str(entry.get("kind") or file_meta.get("kind") or ""),
                        str(entry.get("status") or file_meta.get("status") or ""),
                        str(entry.get("product") or file_meta.get("product") or ""),
                        str(entry.get("category") or file_meta.get("category") or ""),
                        str(entry.get("scope") or file_meta.get("scope") or "global"),
                        # Prefer the .md body; if the file is missing, fall back
                        # to the index summary so the row is not empty.
                        str(file_meta.get("content") or entry.get("summary") or ""),
                        str(file_meta.get("supersedes") or ""),
                    ),
                )

        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('legacy_migrated', ?)",
            (_now(),),
        )

    # Rename the legacy index aside so it is never reloaded (best-effort).
    if index_path.exists():
        try:
            index_path.replace(index_path.with_suffix(".json.migrated"))
        except OSError:
            pass


def _maybe_migrate(trinity_dir: Path) -> None:
    key = str(db.db_path(trinity_dir).resolve())
    with _migrate_lock:
        if key in _migrate_checked:
            return
        _migrate_checked.add(key)
    try:
        _run_migration(trinity_dir)
    except Exception:
        # A failed migration leaves the guard set unmarked in schema_meta, so a
        # later process retries; never let it block normal init.
        _migrate_checked.discard(key)


# ── Public API ─────────────────────────────────────────────────────

def init_memory(trinity_dir: Path) -> None:
    """Create tier dirs + the SQLite DB, and run the one-time migration."""
    mem_dir = _memory_dir(trinity_dir)
    mem_dir.mkdir(parents=True, exist_ok=True)
    for tier in TIERS:
        _tier_dir(trinity_dir, tier).mkdir(parents=True, exist_ok=True)
    db.init(trinity_dir)
    _maybe_migrate(trinity_dir)


@contextmanager
def _read(trinity_dir: Path):
    """init + open a connection + always close it.

    Shared boilerplate for the read and single-statement (autocommit) write
    paths. The ``BEGIN IMMEDIATE`` paths (store/promote) use ``db.write_txn``.
    """
    init_memory(trinity_dir)
    conn = db.connect(trinity_dir)
    try:
        yield conn
    finally:
        conn.close()


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
    scope: str = "global",
) -> str:
    """Create a new memory in the short-term tier. Returns the memory ID.

    Secret-shaped substrings in *content* are masked before persistence — the
    store is the trust boundary, since memories are later spliced back into the
    system prompt.
    """
    if segment not in SEGMENTS:
        raise ValueError(f"Invalid segment '{segment}'. Must be one of: {SEGMENTS}")

    init_memory(trinity_dir)

    now = _now()
    if importance is None:
        importance = SEGMENT_WEIGHTS.get(segment, 0.5)
    decay_rate = SEGMENT_DECAY_MODIFIERS.get(segment, 1.0)

    content = redact(content)
    summary = _generate_summary(content)
    scope = scope or "global"
    today = dt.date.today().strftime("%Y%m%d")

    with db.write_txn(trinity_dir) as conn:
        memory_id = _next_id(conn, today)
        row = conn.execute(
            """INSERT INTO memories
               (id, tier, segment, importance, decay_rate, created,
                last_accessed, access_count, source, summary, kind,
                status, product, category, scope, content, supersedes)
               VALUES (?, 'short-term', ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, '')
               RETURNING *""",
            (
                memory_id, segment, importance, decay_rate, now, now,
                source, summary, kind, status, product, category, scope, content,
            ),
        ).fetchone()

    _export_markdown(trinity_dir, dict(row))
    return memory_id


def recall_memory(trinity_dir: Path, memory_id: str) -> dict[str, Any] | None:
    """Read a memory, bump its access stats (single-row UPDATE), return it.

    Unlike the old implementation this does NOT rewrite the Markdown file or
    re-serialise an index on every read — it is one indexed UPDATE.
    """
    validate_memory_id(memory_id)
    now = _now()
    # One atomic UPDATE ... RETURNING — no write-lock transaction, no extra
    # SELECT, no .md rewrite. This is the read-bump fast path.
    with _read(trinity_dir) as conn:
        row = conn.execute(
            "UPDATE memories SET access_count=access_count+1, last_accessed=? "
            "WHERE id=? RETURNING *",
            (now, memory_id),
        ).fetchone()
    return dict(row) if row is not None else None


def all_memories(trinity_dir: Path) -> list[dict[str, Any]]:
    """Return every memory as a full dict (incl. content), oldest first.

    For maintenance scans (e.g. cleanup) that need the body and authoritative
    ``last_accessed`` from the live DB row, not the frozen Markdown export.
    """
    with _read(trinity_dir) as conn:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY created ASC, id ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_memory(trinity_dir: Path, memory_id: str) -> dict[str, Any] | None:
    """Read a memory WITHOUT mutating access stats (no decay-clock reset).

    Use this for rendering/inspection (briefings, search content); use
    :func:`recall_memory` only for a deliberate reinforcement read.
    """
    if not memory_id:
        return None
    with _read(trinity_dir) as conn:
        row = conn.execute(
            "SELECT * FROM memories WHERE id=?", (memory_id,)
        ).fetchone()
    return dict(row) if row is not None else None


def update_memory(trinity_dir: Path, memory_id: str, content: str) -> bool:
    """Update the content of an existing memory."""
    validate_memory_id(memory_id)
    content = redact(content)
    summary = _generate_summary(content)
    now = _now()
    with _read(trinity_dir) as conn:
        updated = conn.execute(
            "UPDATE memories SET content=?, summary=?, last_accessed=? "
            "WHERE id=? RETURNING *",
            (content, summary, now, memory_id),
        ).fetchone()
    if updated is None:
        return False
    _export_markdown(trinity_dir, dict(updated))
    return True


def forget_memory(trinity_dir: Path, memory_id: str) -> bool:
    """Delete a memory (DB row + Markdown export)."""
    validate_memory_id(memory_id)
    with _read(trinity_dir) as conn:
        row = conn.execute(
            "DELETE FROM memories WHERE id=? RETURNING id", (memory_id,)
        ).fetchone()
    if row is None:
        return False
    _remove_export(trinity_dir, memory_id)
    return True


def promote_memory(trinity_dir: Path, memory_id: str, target_tier: str) -> bool:
    """Move a memory to *target_tier*. Promotion to permanent broadens scope."""
    validate_memory_id(memory_id)
    if target_tier not in TIERS:
        raise ValueError(f"Invalid tier '{target_tier}'. Must be one of: {TIERS}")

    init_memory(trinity_dir)
    with db.write_txn(trinity_dir) as conn:
        row = conn.execute(
            "SELECT tier, scope FROM memories WHERE id=?", (memory_id,)
        ).fetchone()
        if row is None:
            return False
        if row["tier"] == target_tier:
            return True
        if target_tier == "permanent" and row["scope"] and row["scope"] != "global":
            updated = conn.execute(
                "UPDATE memories SET tier=?, scope='global' WHERE id=? RETURNING *",
                (target_tier, memory_id),
            ).fetchone()
        else:
            updated = conn.execute(
                "UPDATE memories SET tier=? WHERE id=? RETURNING *",
                (target_tier, memory_id),
            ).fetchone()
    # Move the export: drop the old-tier file, write the new-tier one.
    _remove_export(trinity_dir, memory_id)
    _export_markdown(trinity_dir, dict(updated))
    return True


def list_memories(trinity_dir: Path, tier: str | None = None) -> list[dict[str, Any]]:
    """List all memories (or one tier), in index-entry shape, oldest first."""
    if tier is not None and tier not in TIERS:
        raise ValueError(f"Invalid tier '{tier}'. Must be one of: {TIERS}")
    where, params = ("WHERE tier=?", (tier,)) if tier is not None else ("", ())
    with _read(trinity_dir) as conn:
        rows = conn.execute(
            f"SELECT * FROM memories {where} ORDER BY created ASC, id ASC", params
        ).fetchall()
    return [_row_to_index_entry(r) for r in rows]


def update_memory_metadata(trinity_dir: Path, memory_id: str, **kwargs: Any) -> bool:
    """Update metadata fields on an existing memory (status, kind, product, ...).

    The .md write and DB update are one atomic statement, so the row and its
    export can never diverge (the old code wrote the .md outside the lock).
    Unknown fields are ignored; ``last_accessed`` is always stamped.
    """
    validate_memory_id(memory_id)
    fields = {k: v for k, v in kwargs.items() if k in _MUTABLE_FIELDS}
    fields["last_accessed"] = _now()  # always stamped; not caller-settable
    set_clause = ", ".join(f"{k}=?" for k in fields)
    params = [*fields.values(), memory_id]
    with _read(trinity_dir) as conn:
        updated = conn.execute(
            f"UPDATE memories SET {set_clause} WHERE id=? RETURNING *", params
        ).fetchone()
    if updated is None:
        return False
    _export_markdown(trinity_dir, dict(updated))
    return True


def query_by_kind(
    trinity_dir: Path,
    kind: str,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return memories matching a kind (and optionally status), oldest first."""
    where, params = "WHERE kind=?", [kind]
    if status is not None:
        where += " AND status=?"
        params.append(status)
    with _read(trinity_dir) as conn:
        rows = conn.execute(
            f"SELECT * FROM memories {where} ORDER BY created ASC, id ASC", params
        ).fetchall()
    return [_row_to_index_entry(r) for r in rows]


# ── Search support (used by memory/search.py) ──────────────────────

def _fts_query(words: list[str]) -> str:
    """Build a lenient FTS5 MATCH query: prefix-match any of the terms."""
    terms = []
    for w in words:
        cleaned = re.sub(r"[^0-9A-Za-z_]", "", w)
        if cleaned:
            terms.append(f'{cleaned}*')
    return " OR ".join(terms)


def search_rows(trinity_dir: Path, words: list[str]) -> list[dict[str, Any]]:
    """Return candidate rows (full dicts) whose summary/content match *words*.

    Uses the FTS5 index for retrieval. Falls back to a full table scan only if
    the FTS query can't be built or errors — keeping search resilient.
    """
    if not words:
        return []
    with _read(trinity_dir) as conn:
        match = _fts_query(words)
        if match:
            try:
                rows = conn.execute(
                    """SELECT m.* FROM memories m
                       JOIN memories_fts f ON f.rowid = m.rowid
                       WHERE memories_fts MATCH ?""",
                    (match,),
                ).fetchall()
                return [dict(r) for r in rows]
            except Exception:
                pass  # fall through to scan
        rows = conn.execute("SELECT * FROM memories").fetchall()
        return [dict(r) for r in rows]
