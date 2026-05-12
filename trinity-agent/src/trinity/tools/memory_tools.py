"""Memory tools — store, search, recall, update, forget, and promote memories.

Defines tool schemas and handlers that delegate to ``trinity.memory.store``
and ``trinity.memory.search``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trinity.memory import store as memory_store_mod
from trinity.memory.search import search_memories

# ── Module-level trinity_dir (set at app init) ───────────────────
_trinity_dir: Path | None = None


def set_trinity_dir(path: Path) -> None:
    """Set the trinity_dir used by all memory tool handlers."""
    global _trinity_dir
    _trinity_dir = path


def _get_trinity_dir() -> Path:
    if _trinity_dir is None:
        raise RuntimeError(
            "Memory tools not initialized — call memory_tools.set_trinity_dir() at app startup"
        )
    return _trinity_dir


# ── Tool schemas ────────────────────────────────────────────────────

MEMORY_STORE_SCHEMA = {
    "name": "memory_store",
    "description": (
        "Store a piece of information in Trinity's memory system. "
        "Use this to remember facts, decisions, user preferences, or "
        "anything the agent should recall later. Higher importance scores "
        "(0.0-1.0) make memories persist longer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The content to remember.",
            },
            "segment": {
                "type": "string",
                "description": (
                    "Memory segment: categorizes the type of information being stored."
                ),
                "enum": [
                    "corrections", "preferences", "facts",
                    "relationships", "projects", "skills", "context",
                ],
            },
            "importance": {
                "type": "number",
                "description": (
                    "Importance score from 0.0 (trivial) to 1.0 (critical). "
                    "Affects how long the memory is retained."
                ),
            },
        },
        "required": ["content", "segment", "importance"],
    },
}

MEMORY_SEARCH_SCHEMA = {
    "name": "memory_search",
    "description": (
        "Search Trinity's memory for relevant information. Returns the "
        "most relevant stored memories matching the query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query — keywords or a natural-language question.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5).",
            },
        },
        "required": ["query"],
    },
}

MEMORY_FORGET_SCHEMA = {
    "name": "memory_forget",
    "description": (
        "Delete a specific memory by its ID. Use this to remove outdated "
        "or incorrect information from the memory store."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "The unique identifier of the memory to delete.",
            },
        },
        "required": ["id"],
    },
}

MEMORY_RECALL_SCHEMA = {
    "name": "memory_recall",
    "description": (
        "Recall a specific memory by its ID. Returns the full content "
        "and metadata, and updates access statistics."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "The unique identifier of the memory to recall.",
            },
        },
        "required": ["id"],
    },
}

MEMORY_UPDATE_SCHEMA = {
    "name": "memory_update",
    "description": (
        "Update the content of an existing memory. The memory keeps its "
        "ID, segment, and importance but gets new content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "The unique identifier of the memory to update.",
            },
            "content": {
                "type": "string",
                "description": "The new content for the memory.",
            },
        },
        "required": ["id", "content"],
    },
}

MEMORY_PROMOTE_SCHEMA = {
    "name": "memory_promote",
    "description": (
        "Promote (or demote) a memory to a different storage tier. "
        "Tiers are: short-term, long-term, permanent. Higher tiers "
        "have longer retention."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "The unique identifier of the memory to promote.",
            },
            "tier": {
                "type": "string",
                "description": "Target tier to move the memory to.",
                "enum": ["short-term", "long-term", "permanent"],
            },
        },
        "required": ["id", "tier"],
    },
}


# ── Handlers ──────────────────────────────────────────────────────

def memory_store(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Store a memory via trinity.memory.store.store_memory."""
    td = _get_trinity_dir()
    memory_id = memory_store_mod.store_memory(
        td,
        inp["content"],
        inp["segment"],
        importance=inp["importance"],
    )
    return f"Memory stored: {memory_id}"


def memory_search(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Search memories via trinity.memory.search.search_memories."""
    td = _get_trinity_dir()
    results = search_memories(td, inp["query"], limit=inp.get("limit", 5))
    if not results:
        return "No matching memories found."
    return json.dumps(results, indent=2)


def memory_forget(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Forget a memory via trinity.memory.store.forget_memory."""
    td = _get_trinity_dir()
    success = memory_store_mod.forget_memory(td, inp["id"])
    if success:
        return f"Memory {inp['id']} deleted."
    return f"Memory {inp['id']} not found."


def memory_recall(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Recall a memory via trinity.memory.store.recall_memory."""
    td = _get_trinity_dir()
    data = memory_store_mod.recall_memory(td, inp["id"])
    if data is None:
        return f"Memory {inp['id']} not found."
    return json.dumps(data, indent=2, default=str)


def memory_update(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Update a memory via trinity.memory.store.update_memory."""
    td = _get_trinity_dir()
    success = memory_store_mod.update_memory(td, inp["id"], inp["content"])
    if success:
        return f"Memory {inp['id']} updated."
    return f"Memory {inp['id']} not found."


def memory_promote(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Promote a memory via trinity.memory.store.promote_memory."""
    td = _get_trinity_dir()
    success = memory_store_mod.promote_memory(td, inp["id"], inp["tier"])
    if success:
        return f"Memory {inp['id']} promoted to {inp['tier']}."
    return f"Memory {inp['id']} not found."
