"""Memory search — FTS5 candidate retrieval, ranked by keyword overlap × decay.

Candidate rows come from the SQLite FTS5 index (one indexed match) instead of
re-opening and re-parsing every ``.md`` file on disk. The ranking formula is
unchanged:  score = (keyword_matches / total_keywords) × effective_importance.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trinity.config import MemoryConfig
from trinity.memory.decay import effective_importance
from trinity.memory.store import search_rows


def search_memories(
    trinity_dir: Path,
    query: str,
    limit: int = 10,
    config: MemoryConfig | None = None,
    global_trinity_dir: Path | None = None,
    current_scope: str | None = None,
) -> list[dict[str, Any]]:
    """Search across all tiers using keyword matching over FTS5 candidates.

    Searches the local workspace memory first, then the global shared memory
    at ``~/.trinity/`` if *global_trinity_dir* is provided. Results are merged,
    deduplicated by ID, and returned top-*limit* by score descending.

    If *current_scope* is provided, only memories whose scope is "global" or
    equals current_scope are returned (legacy/blank scope counts as global).

    Each result includes: id, tier, segment, summary, score, content (first
    200 chars), source.
    """
    if config is None:
        config = MemoryConfig()

    words = [w.lower() for w in query.split() if w.strip()]
    if not words:
        return []

    dirs_to_search = [trinity_dir]
    if global_trinity_dir and global_trinity_dir != trinity_dir:
        dirs_to_search.append(global_trinity_dir)

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for search_dir in dirs_to_search:
        source = "global" if search_dir != trinity_dir else "local"

        for row in search_rows(search_dir, words):
            memory_id = row["id"]
            if memory_id in seen_ids:
                continue

            if current_scope is not None:
                entry_scope = row.get("scope") or "global"
                if entry_scope != "global" and entry_scope != current_scope:
                    continue

            summary = (row.get("summary") or "").lower()
            content = row.get("content") or ""
            searchable = (summary + " " + content).lower()

            matches = sum(1 for w in words if w in searchable)
            if matches == 0:
                continue

            keyword_score = matches / len(words)
            eff_imp = effective_importance(row, config)
            score = keyword_score * eff_imp

            result_entry = {
                "id": memory_id,
                "tier": row.get("tier", "short-term"),
                "segment": row.get("segment", ""),
                "summary": row.get("summary", ""),
                "score": round(score, 4),
                "content": content[:200],
                "source": source,
            }
            if row.get("kind"):
                result_entry["kind"] = row["kind"]
            if row.get("status"):
                result_entry["status"] = row["status"]
            if row.get("product"):
                result_entry["product"] = row["product"]
            if row.get("category"):
                result_entry["category"] = row["category"]
            results.append(result_entry)
            seen_ids.add(memory_id)

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
