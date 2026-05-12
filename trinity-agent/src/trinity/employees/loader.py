"""Identity loading for agent prompts.

Provides two loading modes:
- Full identity: complete identity.md + company context + briefing + memories.
  Used for Track 2 / action agents that need full operational context.
- Compact identity: truncated identity + company name + briefing + memories.
  Used for Track 1 / conversational agents that need to stay within token budgets.
"""
from __future__ import annotations

from pathlib import Path

from trinity.config import CompanyConfig
from trinity.employees.registry import get_employee_identity, get_employee_skills


def _format_skills(skills: list[dict[str, str]]) -> str:
    """Render skill files into a markdown section for the system prompt."""
    if not skills:
        return ""
    lines = ["\n---\n", "## Specialist Skills\n"]
    for skill in skills:
        lines.append(f"### {skill['title']}\n")
        lines.append(skill["content"].strip() + "\n")
    return "\n".join(lines) + "\n"


def load_full_identity(
    trinity_dir: Path,
    employee_name: str,
    company: CompanyConfig,
    briefing: str,
    memories: str = "",
    workspace_root: Path | None = None,
) -> str:
    """Load complete identity for Track 2 / action agents.

    Assembles the full system prompt from:
    1. The employee's complete identity.md
    2. Company context (name + description)
    3. Current briefing (compact knowledge summary)
    4. Relevant memories (if any)

    Args:
        trinity_dir: Path to the .trinity directory.
        employee_name: Name of the employee to load.
        company: CompanyConfig with name and description.
        briefing: Current knowledge briefing text.
        memories: Optional memory context to include.

    Returns:
        Assembled identity string, or a minimal fallback if the employee
        has no identity file.
    """
    identity = get_employee_identity(trinity_dir, employee_name)

    parts: list[str] = []

    if identity:
        parts.append(identity)
    else:
        parts.append(
            f"# {employee_name}\n\n"
            f"You are {employee_name}, a team member at {company.name}."
        )

    # Company context
    parts.append(
        f"\n\n---\n\n"
        f"## Company Context\n\n"
        f"**Company:** {company.name}\n"
    )
    if company.description:
        parts.append(f"**About:** {company.description}\n")

    # Workspace
    ws = workspace_root or trinity_dir.parent
    parts.append(
        f"\n## Workspace\n\n"
        f"Your workspace root is `{ws}`. All file paths and commands default to this directory. "
        f"Stay within this workspace unless explicitly directed elsewhere.\n"
    )

    # Specialist skills (per-employee)
    skills = get_employee_skills(trinity_dir, employee_name)
    skills_block = _format_skills(skills)
    if skills_block:
        parts.append(skills_block)

    # Briefing
    if briefing.strip():
        parts.append(
            f"\n---\n\n"
            f"## Current Briefing\n\n"
            f"{briefing.strip()}\n"
        )

    # Memories
    if memories.strip():
        parts.append(
            f"\n---\n\n"
            f"## Relevant Memories\n\n"
            f"{memories.strip()}\n"
        )

    # Active board tasks for this employee
    board_block = _format_board_block(trinity_dir, employee_name)
    if board_block:
        parts.append(board_block)

    return "".join(parts)


def _format_board_block(trinity_dir: Path, employee_name: str) -> str:
    """Render up to 10 open kanban tasks assigned to ``employee_name``."""
    try:
        from trinity.kanban import board as kanban_board
    except Exception:
        return ""
    try:
        rows = kanban_board.list_tasks(
            trinity_dir, assignee=employee_name, limit=20,
        )
    except Exception:
        return ""
    open_rows = [
        r for r in rows
        if r.get("status") not in (kanban_board.STATUS_DONE, kanban_board.STATUS_ARCHIVED)
    ][:10]
    if not open_rows:
        return ""
    lines = ["\n---\n\n## Active Board Tasks\n"]
    for r in open_rows:
        lines.append(
            f"- #{r['id']} [{r['status']}] P{r['priority']} — {r['title']}",
        )
    lines.append(
        "\nUse `board_show_task` to read a task's full body and parent results "
        "before starting. Use `board_claim_task` to take it off ready, then "
        "`board_complete_task` when done.\n",
    )
    return "\n".join(lines)


def load_compact_identity(
    trinity_dir: Path,
    employee_name: str,
    company: CompanyConfig,
    briefing: str,
    memories: str = "",
    workspace_root: Path | None = None,
) -> str:
    """Load compact identity for Track 1 / conversational agents.

    Uses only the first 500 characters of the identity to keep token
    usage low for quick conversational responses.

    Args:
        trinity_dir: Path to the .trinity directory.
        employee_name: Name of the employee to load.
        company: CompanyConfig with name and description.
        briefing: Current knowledge briefing text.
        memories: Optional memory context to include.

    Returns:
        Compact identity string with truncated identity + context.
    """
    identity = get_employee_identity(trinity_dir, employee_name)

    parts: list[str] = []

    if identity:
        # Truncate to first 500 chars, ending at a clean line break if possible
        truncated = identity[:500]
        last_newline = truncated.rfind("\n")
        if last_newline > 300:
            truncated = truncated[:last_newline]
        parts.append(truncated)
    else:
        parts.append(
            f"You are {employee_name}, a team member at {company.name}."
        )

    # Minimal company context + workspace
    ws = workspace_root or trinity_dir.parent
    parts.append(f"\n\n**Company:** {company.name} | **Workspace:** `{ws}`\n")

    # Specialist skills (compact — titles only, keeps token budget low)
    skills = get_employee_skills(trinity_dir, employee_name)
    if skills:
        titles = ", ".join(s["title"] for s in skills)
        parts.append(f"\n**Skills:** {titles}\n")

    # Briefing
    if briefing.strip():
        parts.append(
            f"\n## Briefing\n\n"
            f"{briefing.strip()}\n"
        )

    # Memories
    if memories.strip():
        parts.append(
            f"\n## Memories\n\n"
            f"{memories.strip()}\n"
        )

    return "".join(parts)
