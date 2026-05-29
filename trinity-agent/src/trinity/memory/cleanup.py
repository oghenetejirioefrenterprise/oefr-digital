"""Memory cleanup — find/delete stale, superseded, and duplicate memories.

Operates against the SQLite store (the source of truth), NOT the Markdown
export. This matters: ``recall_memory`` bumps ``last_accessed`` in the DB only
and deliberately does not rewrite the export, so the export's timestamp is
frozen — judging staleness from it would delete hot, frequently-recalled
memories. Reading the live DB row keeps staleness accurate.

Operations:
* :func:`find_stale` — memories untouched for >= ``days`` and not wikilinked from
  another memory's body.
* :func:`find_superseded` — pairs ``(older, newer)`` where ``newer`` declares
  ``supersedes: <id>`` (newest wins).
* :func:`find_duplicates` — clusters of memories whose body is ``>= threshold``
  similar (``difflib.SequenceMatcher``, stdlib only).
* :func:`run_cleanup` — orchestrator. Deletes through ``store.forget_memory`` so
  the index + FTS stay consistent, and never removes permanent-tier or
  open-issue memories.

All deletions are real; callers should pass ``dry_run=True`` (the default) for a
report only.
"""
from __future__ import annotations

import datetime as dt
import re
from difflib import SequenceMatcher
from pathlib import Path

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


# ── Helpers ────────────────────────────────────────────────────────

def _all(trinity_dir: Path) -> list[dict]:
    from trinity.memory.store import all_memories

    return all_memories(trinity_dir)


def _parse_supersedes(raw: str) -> list[str]:
    """Parse a ``supersedes`` value into a list of ids. Accepts ``[a, b]``,
    ``a, b``, or ``a``. Empty/missing → ``[]``."""
    if not raw:
        return []
    raw = raw.strip().lstrip("[").rstrip("]")
    if not raw:
        return []
    return [item.strip().strip('"').strip("'") for item in raw.split(",") if item.strip()]


def _last_accessed_ts(mem: dict) -> float:
    """POSIX timestamp for a memory's last activity (DB last_accessed/created)."""
    for field in ("last_accessed", "created"):
        raw = str(mem.get(field, "")).strip()
        if not raw:
            continue
        try:
            return dt.datetime.fromisoformat(raw).timestamp()
        except ValueError:
            continue
    return 0.0


def _is_protected(mem: dict) -> bool:
    """Never auto-delete permanent memories or open issues (the invariants
    ``decay.check_demotions`` enforces)."""
    if mem.get("tier") == "permanent":
        return True
    return mem.get("kind") == "issue" and mem.get("status") == "open"


# ── Public API ─────────────────────────────────────────────────────

def find_stale(
    trinity_dir: Path, days: int = 30, mems: list[dict] | None = None
) -> list[dict]:
    """Memories whose last activity is older than ``days`` AND that nothing else
    wikilinks to (``[[<id>]]`` in another memory's body)."""
    mems = _all(trinity_dir) if mems is None else mems
    if not mems:
        return []

    cutoff = dt.datetime.now().timestamp() - (days * 86400)

    referenced: set[str] = set()
    for m in mems:
        for match in _WIKILINK_RE.finditer(m.get("content") or ""):
            target = match.group(1).split("|", 1)[0].strip()
            referenced.add(target)

    return [
        m for m in mems
        if m["id"] not in referenced and _last_accessed_ts(m) < cutoff
    ]


def find_superseded(
    trinity_dir: Path, mems: list[dict] | None = None
) -> list[tuple[dict, dict]]:
    """Pairs ``(older, newer)`` where ``newer`` declares ``supersedes: <older id>``."""
    mems = _all(trinity_dir) if mems is None else mems
    by_id = {m["id"]: m for m in mems}
    pairs: list[tuple[dict, dict]] = []
    for newer in mems:
        for old_id in _parse_supersedes(newer.get("supersedes") or ""):
            older = by_id.get(old_id)
            if older is not None and older["id"] != newer["id"]:
                pairs.append((older, newer))
    return pairs


def find_duplicates(
    trinity_dir: Path,
    similarity_threshold: float = 0.85,
    mems: list[dict] | None = None,
) -> list[list[dict]]:
    """Cluster memories whose body text is ``>= threshold`` similar.

    Pairwise O(n²) — fine for the order-of-magnitude (hundreds–low thousands)
    of memories in a workspace. Empty bodies are skipped.
    """
    source = _all(trinity_dir) if mems is None else mems
    mems = [m for m in source if (m.get("content") or "").strip()]

    parent: dict[str, str] = {m["id"]: m["id"] for m in mems}
    by_id = {m["id"]: m for m in mems}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(mems)):
        for j in range(i + 1, len(mems)):
            ratio = SequenceMatcher(
                None, mems[i]["content"], mems[j]["content"]
            ).ratio()
            if ratio >= similarity_threshold:
                union(mems[i]["id"], mems[j]["id"])

    clusters: dict[str, list[dict]] = {}
    for m in mems:
        root = find(m["id"])
        clusters.setdefault(root, []).append(by_id[m["id"]])

    return [members for members in clusters.values() if len(members) > 1]


def run_cleanup(
    trinity_dir: Path,
    dry_run: bool = True,
    *,
    stale_days: int = 30,
) -> dict:
    """Run all cleanup operations and (optionally) delete the candidates.

    Deletions go through ``store.forget_memory`` (DB row + export removed
    together — no ghost rows). Permanent-tier and open-issue memories are never
    removed. When ``dry_run`` is True (default), nothing is deleted.
    """
    from trinity.memory.store import forget_memory

    # Fetch the whole table once and feed all three detectors (each would
    # otherwise re-query, materialising every content body four times over).
    all_mems = _all(trinity_dir)
    stale = find_stale(trinity_dir, days=stale_days, mems=all_mems)
    superseded = find_superseded(trinity_dir, mems=all_mems)
    duplicates = find_duplicates(trinity_dir, mems=all_mems)

    to_delete: dict[str, dict] = {m["id"]: m for m in stale}
    for older, _newer in superseded:
        to_delete[older["id"]] = older
    for cluster in duplicates:
        # Keep the most-recently-accessed; delete the rest.
        ordered = sorted(cluster, key=_last_accessed_ts, reverse=True)
        for m in ordered[1:]:
            to_delete[m["id"]] = m

    protected = {mid for mid, m in to_delete.items() if _is_protected(m)}
    for mid in protected:
        to_delete.pop(mid, None)

    summary: dict = {
        "scanned": len(all_mems),
        "stale": len(stale),
        "superseded": len(superseded),
        "duplicates_to_merge": sum(max(0, len(c) - 1) for c in duplicates),
        "protected": len(protected),
        "to_delete": len(to_delete),
        "deleted": 0,
        "dry_run": dry_run,
    }

    if not dry_run:
        for mid in to_delete:
            if forget_memory(trinity_dir, mid):
                summary["deleted"] += 1

    return summary
