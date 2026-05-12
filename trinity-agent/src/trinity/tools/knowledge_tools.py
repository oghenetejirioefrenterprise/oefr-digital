"""Knowledge-base tools — log issues, decisions, audits, and lessons.

Defines tool schemas and handlers that delegate to ``trinity.knowledge.wiki``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trinity.knowledge import wiki

# ── Module-level trinity_dir (set at app init) ───────────────────
_trinity_dir: Path | None = None


def set_trinity_dir(path: Path) -> None:
    """Set the trinity_dir used by all knowledge tool handlers."""
    global _trinity_dir
    _trinity_dir = path


def _get_trinity_dir() -> Path:
    if _trinity_dir is None:
        raise RuntimeError(
            "Knowledge tools not initialized — call knowledge_tools.set_trinity_dir() at app startup"
        )
    return _trinity_dir


# ── Tool schemas ────────────────────────────────────────────────────

LOG_ISSUE_SCHEMA = {
    "name": "log_issue",
    "description": (
        "Log a product issue to the knowledge base. Tracks bugs, regressions, "
        "and problems across products with their current status."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "product": {
                "type": "string",
                "description": "Product name (e.g. 'netarch-pro', 'habitforge').",
            },
            "description": {
                "type": "string",
                "description": "Description of the issue.",
            },
            "status": {
                "type": "string",
                "description": "Current status of the issue.",
                "enum": ["open", "fixed", "false-positive", "wont-fix"],
            },
        },
        "required": ["product", "description", "status"],
    },
}

LOG_DECISION_SCHEMA = {
    "name": "log_decision",
    "description": (
        "Record a product or business decision with its rationale. "
        "Prevents future reversals by documenting why a decision was made."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "description": "What was decided.",
            },
            "context": {
                "type": "string",
                "description": "Background context — what prompted this decision.",
            },
            "rationale": {
                "type": "string",
                "description": "Why this option was chosen over alternatives.",
            },
        },
        "required": ["decision", "context", "rationale"],
    },
}

LOG_AUDIT_SCHEMA = {
    "name": "log_audit",
    "description": (
        "Log an audit of a product or system. Records what was checked, "
        "what was found, and what actions were taken."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "audit_type": {
                "type": "string",
                "description": "Type of audit (e.g. 'build', 'store', 'stripe', 'security').",
            },
            "product": {
                "type": "string",
                "description": "Product or system that was audited.",
            },
            "findings": {
                "type": "string",
                "description": "What was found during the audit.",
            },
            "actions": {
                "type": "string",
                "description": "Actions taken or recommended based on findings.",
            },
        },
        "required": ["audit_type", "product", "findings", "actions"],
    },
}

LOG_LESSON_SCHEMA = {
    "name": "log_lesson",
    "description": (
        "Record a lesson learned — wins, failures, and process improvements. "
        "Helps the agent avoid repeating mistakes and replicate successes."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "lesson": {
                "type": "string",
                "description": "The lesson learned.",
            },
            "context": {
                "type": "string",
                "description": "Context in which the lesson was learned.",
            },
            "category": {
                "type": "string",
                "description": "Category of the lesson.",
                "enum": ["win", "failure", "process"],
            },
        },
        "required": ["lesson", "context", "category"],
    },
}


# ── Handlers ──────────────────────────────────────────────────────

def log_issue(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Log a product issue via trinity.knowledge.wiki.log_issue."""
    td = _get_trinity_dir()
    return wiki.log_issue(td, inp["product"], inp["description"], inp["status"])


def log_decision(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Log a decision via trinity.knowledge.wiki.log_decision."""
    td = _get_trinity_dir()
    return wiki.log_decision(td, inp["decision"], inp["context"], inp["rationale"])


def log_audit(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Log an audit via trinity.knowledge.wiki.log_audit."""
    td = _get_trinity_dir()
    return wiki.log_audit(td, inp["audit_type"], inp["product"], inp["findings"], inp["actions"])


def log_lesson(inp: dict[str, Any], workspace_root: Path, **context: Any) -> str:
    """Log a lesson via trinity.knowledge.wiki.log_lesson."""
    td = _get_trinity_dir()
    return wiki.log_lesson(td, inp["lesson"], inp["context"], inp["category"])
