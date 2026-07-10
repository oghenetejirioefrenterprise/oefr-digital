"""Read/write product-roster.md as structured data.

Roster is the single source of truth for product state. This module
parses the markdown table into Product dataclasses and writes back.

The killer-loop, allocator, and (Phase 2+) opportunity gate all read
from here. Direct markdown edits by TJ are respected on next load.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
ROSTER_FILE = KNOWLEDGE_DIR / "product-roster.md"

PORTFOLIO_MAX = 12
SUNSET_GRACE_DAYS = 7
PRODUCING_OBSERVATION_DAYS = 14


# ── Status ──────────────────────────────────────────────────────

VALID_STATUSES = {
    "candidate",
    "validating",
    "producing",
    "scaling",
    "maintain",
    "sunset-pending",
    "dead",
    "meta",  # for non-product directory entries (e.g. gumroad-products)
}


class Status:
    CANDIDATE = "candidate"
    VALIDATING = "validating"
    PRODUCING = "producing"
    SCALING = "scaling"
    MAINTAIN = "maintain"
    SUNSET_PENDING = "sunset-pending"
    DEAD = "dead"
    META = "meta"


# ── Product dataclass ───────────────────────────────────────────

@dataclass
class Product:
    name: str
    status: str
    thesis: str
    kill_rule: str
    launched: str  # YYYY-MM or "n/a"
    last_signal: str  # YYYY-MM-DD or "—"
    revenue_30d: str  # "0", "?", "n/a", or numeric string
    notes: str = ""
    # Tracking for sunset transitions; not stored in markdown.
    sunset_pending_since: Optional[str] = None

    def revenue_value(self) -> float:
        """Return revenue_30d as a float, or 0.0 if unmeasured/non-numeric."""
        cleaned = self.revenue_30d.strip().lstrip("$").replace(",", "")
        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0

    def days_since_signal(self, today: Optional[dt.date] = None) -> Optional[int]:
        """Days since last positive signal. None if never signaled."""
        if not self.last_signal or self.last_signal in ("—", "-", ""):
            return None
        try:
            sig = dt.date.fromisoformat(self.last_signal)
        except ValueError:
            return None
        today = today or dt.date.today()
        return (today - sig).days

    def days_since_launch(self, today: Optional[dt.date] = None) -> Optional[int]:
        """Approximate days since launch (parses YYYY-MM, treats day=1)."""
        if not self.launched or self.launched in ("n/a", "—", ""):
            return None
        try:
            if len(self.launched) == 7:
                launched = dt.date.fromisoformat(self.launched + "-01")
            else:
                launched = dt.date.fromisoformat(self.launched)
        except ValueError:
            return None
        today = today or dt.date.today()
        return (today - launched).days


# ── Markdown parsing ────────────────────────────────────────────

# Active products live in a table under "## Active products".
_ACTIVE_HEADER = "## Active products"
_OVERRIDE_HEADER = "## Override log"
_POSTMORTEM_HEADER = "## Post-mortems"


def _split_table_row(line: str) -> list[str]:
    """Split a markdown table row by | into trimmed cells.

    Strips the leading and trailing pipes (which produce empty edges).
    """
    parts = [c.strip() for c in line.split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-+:?", c) for c in cells if c)


def _extract_section(content: str, header: str) -> str:
    """Pull the body of a ## section (until next ## or EOF)."""
    pattern = rf"{re.escape(header)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1) if match else ""


def load_roster() -> list[Product]:
    """Parse product-roster.md into a list of Product objects.

    Returns empty list if file missing.
    """
    if not ROSTER_FILE.exists():
        return []

    content = ROSTER_FILE.read_text()
    section = _extract_section(content, _ACTIVE_HEADER)
    if not section:
        return []

    products: list[Product] = []
    headers: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = _split_table_row(line)
        if _is_separator_row(cells):
            continue
        if not headers:
            headers = [c.lower() for c in cells]
            continue
        # Map cells to known columns; tolerate trailing/missing columns.
        row = dict(zip(headers, cells))
        name = row.get("product", "").strip()
        if not name:
            continue
        status = row.get("status", "").strip().lower()
        if status not in VALID_STATUSES:
            # Unknown status — keep the product visible by tagging meta so it doesn't
            # accidentally trigger kill rules. A human can correct.
            status = Status.META
        products.append(Product(
            name=name,
            status=status,
            thesis=row.get("thesis", ""),
            kill_rule=row.get("kill rule", ""),
            launched=row.get("launched", ""),
            last_signal=row.get("last signal", ""),
            revenue_30d=row.get("revenue 30d", "0"),
            notes=row.get("notes", ""),
        ))
    return products


def save_roster(products: list[Product]) -> None:
    """Write the products list back into the Active products table.

    Preserves all other sections of the roster file verbatim. Only the
    Active products table body is replaced.
    """
    if not ROSTER_FILE.exists():
        raise FileNotFoundError(f"Roster file missing: {ROSTER_FILE}")

    content = ROSTER_FILE.read_text()

    # Build the new table body
    columns = [
        "Product", "Status", "Thesis", "Kill rule",
        "Launched", "Last signal", "Revenue 30d", "Notes",
    ]
    header_row = "| " + " | ".join(columns) + " |"
    sep_row = "|" + "|".join(["---"] * len(columns)) + "|"

    body_rows = []
    for p in products:
        body_rows.append(
            "| " + " | ".join([
                p.name, p.status, p.thesis, p.kill_rule,
                p.launched, p.last_signal, p.revenue_30d, p.notes,
            ]) + " |"
        )

    new_table = "\n".join([header_row, sep_row, *body_rows])

    # Replace just the Active products section body (between header and next ##).
    pattern = rf"({re.escape(_ACTIVE_HEADER)}\s*\n)(.*?)(?=\n## |\Z)"
    replacement = rf"\g<1>\n{new_table}\n"
    new_content, n = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if n == 0:
        raise RuntimeError(f"Could not locate '{_ACTIVE_HEADER}' section in roster")

    ROSTER_FILE.write_text(new_content)


# ── Helpers used by killer / allocator / governance ─────────────

def append_postmortem(product: Product, cause: str, lesson: str) -> None:
    """Append a row to the Post-mortems table when a product dies."""
    if not ROSTER_FILE.exists():
        return
    content = ROSTER_FILE.read_text()
    today = dt.date.today().isoformat()
    new_row = f"| {today} | {product.name} | {cause} | {lesson} |"

    # Find the post-mortem table and insert before the placeholder row if present.
    section_pattern = rf"({re.escape(_POSTMORTEM_HEADER)}.*?)(\Z)"
    match = re.search(section_pattern, content, re.DOTALL)
    if not match:
        return

    section = match.group(1)
    # Remove placeholder "| — | — | — | — |" if present.
    section = re.sub(r"\n\| — \| — \| — \| — \|", "", section)
    section = section.rstrip() + "\n" + new_row + "\n"
    new_content = content[: match.start()] + section
    ROSTER_FILE.write_text(new_content)


def append_override_log(product: Product, override: str, rationale: str) -> None:
    """Log a manual override in the Override log table."""
    if not ROSTER_FILE.exists():
        return
    content = ROSTER_FILE.read_text()
    today = dt.date.today().isoformat()
    new_row = f"| {today} | {product.name} | {override} | {rationale} | — |"

    # Insert just before the next ## header after the override section.
    pattern = rf"({re.escape(_OVERRIDE_HEADER)}.*?)(\n## )"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return
    section = match.group(1).rstrip() + "\n" + new_row + "\n"
    new_content = content[: match.start()] + section + match.group(2) + content[match.end():]
    ROSTER_FILE.write_text(new_content)
