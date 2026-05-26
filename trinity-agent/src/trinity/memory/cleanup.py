"""Memory cleanup operations — find/delete stale, superseded, and duplicate memories.

This module implements four operations that work directly against the memory
directory (`.trinity/memory/`) on disk:

* :func:`find_stale` — memories untouched for >= ``days`` and not wikilinked elsewhere.
* :func:`find_superseded` — older memories whose newer counterpart declares
  ``supersedes: [<slug>]`` in its frontmatter.
* :func:`find_duplicates` — clusters of memories whose body text is ``>= threshold``
  similar (uses :class:`difflib.SequenceMatcher`, stdlib-only).
* :func:`run_cleanup` — orchestrator that combines the three above, optionally
  deleting the candidates and returning a counts summary.

All file deletions are real; callers should pass ``dry_run=True`` (the default)
when they only want a report.
"""
from __future__ import annotations

import datetime as dt
import re
from difflib import SequenceMatcher
from pathlib import Path


# ── Helpers ────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body) for a memory .md file.

    Frontmatter values are kept as raw strings; list-like values such as
    ``supersedes: [a, b]`` are returned as the raw inner string ``"a, b"``.
    Body is the remainder after the closing ``---``.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    front_text, body = match.group(1), match.group(2)
    meta: dict[str, str] = {}
    for line in front_text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def _iter_memory_files(workspace_dir: Path):
    """Yield every .md file under ``workspace_dir`` (recursively)."""
    if not workspace_dir.exists():
        return
    yield from workspace_dir.rglob("*.md")


def _parse_supersedes(raw: str) -> list[str]:
    """Parse a ``supersedes`` frontmatter value into a list of slugs.

    Accepts ``[a, b]``, ``a, b``, or ``a``. Empty/missing → ``[]``.
    """
    if not raw:
        return []
    raw = raw.strip().lstrip("[").rstrip("]")
    if not raw:
        return []
    return [item.strip().strip('"').strip("'") for item in raw.split(",") if item.strip()]


def _memory_slug(path: Path) -> str:
    """Memory's logical slug = stem of the file (e.g. ``dup_a`` for ``dup_a.md``)."""
    return path.stem


def _last_accessed_ts(path: Path, meta: dict[str, str]) -> float:
    """Return a POSIX timestamp for the memory's last activity.

    Prefers frontmatter ``last_accessed``, falls back to ``created``, then to
    filesystem mtime. Unparseable dates fall through to the next candidate.
    """
    for field in ("last_accessed", "created"):
        raw = meta.get(field, "").strip()
        if not raw:
            continue
        try:
            return dt.datetime.fromisoformat(raw).timestamp()
        except ValueError:
            continue
    return path.stat().st_mtime


# ── Public API ─────────────────────────────────────────────────────

def find_stale(workspace_dir: Path, days: int = 30) -> list[Path]:
    """Memories whose last activity is older than ``days`` AND that nothing else links to.

    A memory is considered referenced if any *other* memory's body contains a
    ``[[<slug>]]`` wikilink pointing at it.
    """
    files = list(_iter_memory_files(workspace_dir))
    if not files:
        return []

    cutoff = dt.datetime.now().timestamp() - (days * 86400)

    # Build an incoming-link set: for every wikilink in every memory body,
    # record the target slug.
    referenced: set[str] = set()
    parsed: dict[Path, tuple[dict[str, str], str]] = {}
    for path in files:
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        meta, body = _split_frontmatter(text)
        parsed[path] = (meta, body)
        for match in _WIKILINK_RE.finditer(body):
            target = match.group(1).strip()
            # Allow ``[[slug|display]]`` form
            target = target.split("|", 1)[0].strip()
            referenced.add(target)

    stale: list[Path] = []
    for path, (meta, _body) in parsed.items():
        slug = _memory_slug(path)
        if slug in referenced:
            # Some other memory points at this one — keep it.
            continue
        if _last_accessed_ts(path, meta) >= cutoff:
            continue
        stale.append(path)
    return stale


def find_superseded(workspace_dir: Path) -> list[tuple[Path, Path]]:
    """Pairs ``(older, newer)`` where ``newer`` declares ``supersedes: [<older>]``."""
    files = list(_iter_memory_files(workspace_dir))
    if not files:
        return []

    by_slug: dict[str, Path] = {}
    supersedes_map: dict[Path, list[str]] = {}
    for path in files:
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        meta, _body = _split_frontmatter(text)
        by_slug[_memory_slug(path)] = path
        raw = meta.get("supersedes", "")
        slugs = _parse_supersedes(raw)
        if slugs:
            supersedes_map[path] = slugs

    pairs: list[tuple[Path, Path]] = []
    for newer, older_slugs in supersedes_map.items():
        for slug in older_slugs:
            older = by_slug.get(slug)
            if older is not None and older != newer:
                pairs.append((older, newer))
    return pairs


def find_duplicates(
    workspace_dir: Path,
    similarity_threshold: float = 0.85,
) -> list[list[Path]]:
    """Cluster memories whose body text is ``>= threshold`` similar.

    Uses :class:`difflib.SequenceMatcher` (stdlib). Pairwise O(n²) — fine for
    the order-of-magnitude (~hundreds) of memories in a typical workspace.
    Empty bodies are skipped (can't sensibly be "duplicates").
    """
    files = list(_iter_memory_files(workspace_dir))
    bodies: list[tuple[Path, str]] = []
    for path in files:
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        _meta, body = _split_frontmatter(text)
        body = body.strip()
        if body:
            bodies.append((path, body))

    # Union-find for clustering similar pairs.
    parent: dict[Path, Path] = {p: p for p, _ in bodies}

    def find(x: Path) -> Path:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: Path, b: Path) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(bodies)):
        path_a, body_a = bodies[i]
        for j in range(i + 1, len(bodies)):
            path_b, body_b = bodies[j]
            ratio = SequenceMatcher(None, body_a, body_b).ratio()
            if ratio >= similarity_threshold:
                union(path_a, path_b)

    clusters: dict[Path, list[Path]] = {}
    for path, _ in bodies:
        root = find(path)
        clusters.setdefault(root, []).append(path)

    return [members for members in clusters.values() if len(members) > 1]


def run_cleanup(
    workspace_dir: Path,
    dry_run: bool = True,
    *,
    stale_days: int = 30,
) -> dict:
    """Run all cleanup operations and (optionally) delete the candidates.

    Returns a counts summary suitable for printing or piping to a report.
    When ``dry_run`` is True (default), no files are deleted.
    """
    stale = find_stale(workspace_dir, days=stale_days)
    superseded = find_superseded(workspace_dir)
    duplicates = find_duplicates(workspace_dir)

    to_delete: set[Path] = set(stale)
    for older, _newer in superseded:
        to_delete.add(older)
    for cluster in duplicates:
        # Keep the most-recently-modified, delete the rest.
        sorted_cluster = sorted(
            cluster, key=lambda p: p.stat().st_mtime, reverse=True
        )
        to_delete.update(sorted_cluster[1:])

    summary: dict = {
        "scanned": sum(1 for _ in _iter_memory_files(workspace_dir)),
        "stale": len(stale),
        "superseded": len([s for s, _ in superseded]),
        "duplicates_to_merge": sum(max(0, len(c) - 1) for c in duplicates),
        "to_delete": len(to_delete),
        "deleted": 0,
        "dry_run": dry_run,
    }

    if not dry_run:
        for path in to_delete:
            try:
                path.unlink()
                summary["deleted"] += 1
            except FileNotFoundError:
                pass

    return summary
