"""Title-based identity template generators.

Each supported title gets a complete, opinionated identity.md template
that serves as the system prompt driving the AI agent's behavior.
"""
from __future__ import annotations

from pathlib import Path

# ── Template loading ────────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "employees"

_TITLE_TO_FILE: dict[str, str] = {
    "CEO": "ceo.md",
    "CMO": "cmo.md",
    "CTO": "cto.md",
    "CFO": "cfo.md",
    "COO": "coo.md",
    "Research IC": "research_ic.md",
    "SEO Operator": "seo_operator.md",
    "Product Mgr": "product_mgr.md",
    "Custom": "custom.md",
}

SUPPORTED_TITLES: list[str] = list(_TITLE_TO_FILE.keys())


def _load_template(filename: str) -> str:
    """Load a template file from the templates/employees/ directory."""
    path = _TEMPLATES_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    # Fallback: return the custom template content inline if file is missing
    return (
        "# {name} — {title} at {company_name}\n\n"
        "## Core Identity\n\n"
        "You are {name}, a team member at {company_name}. {company_description}\n\n"
        "## Operating Style\n\n"
        "<!-- Define your operating principles here. -->\n\n"
        "## Focus Areas\n\n"
        "<!-- List areas of responsibility. -->\n\n"
        "## Rules\n\n"
        "<!-- Define hard constraints. -->\n\n"
        "## Communication Style\n\n"
        "<!-- Define communication preferences. -->\n"
    )


def generate_identity(
    name: str,
    title: str,
    company_name: str,
    company_description: str,
) -> str:
    """Generate a complete identity.md for an employee based on their title.

    Args:
        name: The employee's display name (e.g., "Trinity", "Morpheus").
        title: One of the supported titles (CEO, CMO, etc.) or any string.
        company_name: The company name for context.
        company_description: A brief description of what the company does.

    Returns:
        A fully rendered Markdown identity document ready to write to disk.
    """
    filename = _TITLE_TO_FILE.get(title)
    if filename is None:
        # Unknown title — use the Custom template but replace the title line
        filename = "custom.md"

    template = _load_template(filename)

    # Replace placeholders
    rendered = template.replace("{name}", name)
    rendered = rendered.replace("{company_name}", company_name)
    rendered = rendered.replace("{company_description}", company_description)

    # For non-standard titles using the custom template, fix the header
    if title not in _TITLE_TO_FILE:
        rendered = rendered.replace("Custom Role", title, 1)

    return rendered
