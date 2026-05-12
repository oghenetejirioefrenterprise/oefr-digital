"""Memory search — keyword matching weighted by effective importance."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trinity.config import MemoryConfig
from trinity.memory.decay import effective_importance
from trinity.memory.store import TIERS, _parse_memory_file, _tier_dir, list_memories


def search_memories(
    trinity_dir: Path,
    query: str,
    limit: int = 10,
    config: MemoryConfig | None = None,
    global_trinity_dir: Path | None = None,
    current_scope: str | None = None,
) -> list[dict[str, Any]]:
    """Search across all tiers using keyword matching.

    Score = (keyword_matches / total_keywords) * effective_importance

    Searches the local workspace memory first, then the global shared
    memory at ``~/.trinity/`` if *global_trinity_dir* is provided.
    Results are merged and deduplicated by ID.

    If *current_scope* is provided, only returns memories whose scope
    is "global" or equals current_scope. Legacy entries (no scope field)
    are treated as global for backward compatibility.

    Returns top `limit` results sorted by score descending.
    Each result includes: id, tier, segment, summary, score, content (first 200 chars).
    """
    if config is None:
        config = MemoryConfig()

    words = [w.lower() for w in query.split() if w.strip()]
    if not words:
        return []

    # Search local, then global
    dirs_to_search = [trinity_dir]
    if global_trinity_dir and global_trinity_dir != trinity_dir:
        dirs_to_search.append(global_trinity_dir)

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for search_dir in dirs_to_search:
        source = "global" if search_dir != trinity_dir else "local"
        all_memories = list_memories(search_dir)

        for entry in all_memories:
            memory_id = entry["id"]
            if memory_id in seen_ids:
                continue

            if current_scope is not None:
                entry_scope = entry.get("scope") or "global"
                if entry_scope != "global" and entry_scope != current_scope:
                    continue

            tier = entry.get("tier", "short-term")
            summary = entry.get("summary", "").lower()

            path = _tier_dir(search_dir, tier) / f"{memory_id}.md"
            if not path.exists():
                continue

            data = _parse_memory_file(path)
            content = data.get("content", "")
            searchable = (summary + " " + content).lower()

            matches = sum(1 for w in words if w in searchable)
            if matches == 0:
                continue

            keyword_score = matches / len(words)
            eff_imp = effective_importance(entry, config)
            score = keyword_score * eff_imp

            result_entry = {
                "id": memory_id,
                "tier": tier,
                "segment": entry.get("segment", ""),
                "summary": entry.get("summary", ""),
                "score": round(score, 4),
                "content": content[:200],
                "source": source,
            }
            if entry.get("kind"):
                result_entry["kind"] = entry["kind"]
            if entry.get("status"):
                result_entry["status"] = entry["status"]
            if entry.get("product"):
                result_entry["product"] = entry["product"]
            if entry.get("category"):
                result_entry["category"] = entry["category"]
            results.append(result_entry)
            seen_ids.add(memory_id)

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
