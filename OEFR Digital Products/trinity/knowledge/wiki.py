"""Trinity Second Brain — LLM Wiki Engine.

Generates compact briefings, searches across knowledge files,
and provides tiered context loading so Trinity doesn't blow her
context window with stale audit logs.

The briefing.md file is the "table of contents" — always loaded
into identity. Full knowledge files are read on-demand by cycles
that need them.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent
KNOWLEDGE_FILES = [
    "known-issues.md",
    "product-decisions.md",
    "audit-log.md",
    "lessons-learned.md",
]
BRIEFING_FILE = KNOWLEDGE_DIR / "briefing.md"
SIGNALS_FILE = KNOWLEDGE_DIR / "daily-signals.md"


def _read_safe(path: Path) -> str:
    try:
        return path.read_text()
    except (FileNotFoundError, PermissionError):
        return ""


def _count_entries(content: str) -> int:
    """Count timestamped entries like [2026-04-10]."""
    return len(re.findall(r"\[\d{4}-\d{2}-\d{2}\]", content))


def _extract_section_entries(content: str, header_pattern: str) -> list[str]:
    """Pull timestamped entries under a markdown section matching header_pattern."""
    match = re.search(
        rf"## {header_pattern}[^\n]*\n(.*?)(?=\n## |\Z)",
        content, re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return []
    section = match.group(1).strip()
    if not section:
        return []
    # Only grab lines that start with [date] — ignore everything else
    entries = re.findall(r"(\[\d{4}-\d{2}-\d{2}\][^\n]*(?:\n(?!\[|\#).*)*)", section)
    return [e.strip() for e in entries if e.strip()]


def _recent_entries(content: str, days: int = 7) -> list[str]:
    """Return entries from the last N days."""
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    entries = re.split(r"(?=\[\d{4}-\d{2}-\d{2}\])", content)
    recent = []
    for entry in entries:
        m = re.match(r"\[(\d{4}-\d{2}-\d{2})\]", entry.strip())
        if m and m.group(1) >= cutoff:
            recent.append(entry.strip())
    return recent


# ── Briefing generation ─────────────────────────────────────────

def generate_briefing() -> str:
    """Scan all knowledge files and produce a compact summary (~2K chars).

    This is the only thing loaded into Trinity's identity prompt.
    It tells her what exists and where to look for details.
    """
    today = dt.date.today().isoformat()
    sections = []

    # Known issues summary
    issues_content = _read_safe(KNOWLEDGE_DIR / "known-issues.md")
    open_issues = _extract_section_entries(issues_content, "Open Issues")
    fixed_issues = _extract_section_entries(issues_content, "Fixed")
    false_positives = _extract_section_entries(issues_content, "False Positives")
    wontfix = _extract_section_entries(issues_content, "Won't Fix")

    sections.append(
        f"## Product Health\n"
        f"- Open issues: {len(open_issues)}\n"
        f"- Fixed (last 30d): {len(fixed_issues)}\n"
        f"- False positives: {len(false_positives)}\n"
        f"- Won't fix: {len(wontfix)}"
    )
    if open_issues:
        # Show the 5 most recent open issues
        top = open_issues[-5:]
        items = "\n".join(f"  - {e[:120]}" for e in top)
        sections.append(f"### Top open issues\n{items}")

    # Audit log summary
    audit_content = _read_safe(KNOWLEDGE_DIR / "audit-log.md")
    recent_audits = _recent_entries(audit_content, days=7)
    total_audits = _count_entries(audit_content)
    sections.append(
        f"## Audits\n"
        f"- Total logged: {total_audits}\n"
        f"- Last 7 days: {len(recent_audits)}"
    )
    if recent_audits:
        # Show the 3 most recent
        for entry in recent_audits[-3:]:
            first_line = entry.split("\n")[0][:120]
            sections.append(f"  - {first_line}")

    # Decisions summary
    decisions_content = _read_safe(KNOWLEDGE_DIR / "product-decisions.md")
    active_decisions = _extract_section_entries(decisions_content, "Active Decisions")
    sections.append(
        f"## Active Decisions: {len(active_decisions)}"
    )

    # Lessons summary
    lessons_content = _read_safe(KNOWLEDGE_DIR / "lessons-learned.md")
    wins = _extract_section_entries(lessons_content, "Wins")
    failures = _extract_section_entries(lessons_content, "Failures")
    sections.append(
        f"## Lessons: {len(wins)} wins, {len(failures)} failures logged"
    )

    # Today's cross-cycle signals
    signals = _read_safe(SIGNALS_FILE)
    today_signals = [
        line.strip() for line in signals.splitlines()
        if line.strip().startswith(f"[{today}")
    ]
    if today_signals:
        items = "\n".join(f"  - {s}" for s in today_signals[-5:])
        sections.append(f"## Today's Signals\n{items}")

    briefing = (
        f"# Second Brain Briefing\n"
        f"Generated: {today}\n\n"
        + "\n\n".join(sections)
        + "\n\n---\n"
        f"Full knowledge: ~/apps/OEFR Digital Products/trinity/knowledge/\n"
        f"Use `python trinity/knowledge/cli.py query <topic>` to search.\n"
        f"Use `python trinity/knowledge/cli.py log-issue|log-audit|signal` to write.\n"
    )

    BRIEFING_FILE.write_text(briefing)
    return briefing


# ── Search ──────────────────────────────────────────────────────

def query(topic: str) -> str:
    """Search across all knowledge files for entries matching a topic.

    Returns matching paragraphs/entries with their source file.
    """
    results = []
    pattern = re.compile(re.escape(topic), re.IGNORECASE)

    for filename in KNOWLEDGE_FILES + ["daily-signals.md"]:
        content = _read_safe(KNOWLEDGE_DIR / filename)
        if not content:
            continue

        # Split into entries (paragraphs separated by blank lines or [date] markers)
        chunks = re.split(r"\n(?=\[?\d{4}-\d{2}-\d{2}\]?|### )", content)
        for chunk in chunks:
            if pattern.search(chunk):
                results.append(f"[{filename}] {chunk.strip()[:500]}")

    if not results:
        return f"No entries matching '{topic}' found in knowledge base."

    return "\n\n---\n\n".join(results[:15])  # cap at 15 matches


# ── Signal logging ──────────────────────────────────────────────

def add_signal(cycle: str, signal: str) -> str:
    """Append a cross-cycle signal to today's daily signals file.

    Other cycles read this to see what happened earlier today.
    """
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{ts}] [{cycle}] {signal}\n"

    with open(SIGNALS_FILE, "a") as f:
        f.write(entry)

    return f"Signal logged: {entry.strip()}"


def reset_daily_signals():
    """Clear daily signals (called by brain-review or at midnight)."""
    today = dt.date.today().isoformat()
    SIGNALS_FILE.write_text(
        f"# Daily Signals — {today}\n"
        f"Cross-cycle intelligence for today. Each cycle appends, next cycle reads.\n\n"
    )


def get_daily_signals() -> str:
    """Read today's signals for cross-cycle awareness."""
    content = _read_safe(SIGNALS_FILE)
    if not content or len(content.strip()) < 20:
        return "(no signals yet today)"
    return content


# ── Tiered context loading ──────────────────────────────────────

def load_for_identity() -> str:
    """Load ONLY the compact briefing for identity prompt injection.

    This replaces the old load_knowledge_base() that stuffed everything.
    Returns ~2K chars instead of potentially 30K+.
    """
    content = _read_safe(BRIEFING_FILE)
    if not content or len(content.strip()) < 50:
        # Briefing doesn't exist yet — generate it
        content = generate_briefing()
    return content


def load_for_cycle(cycle_name: str) -> str:
    """Load targeted context for a specific cycle type.

    Different cycles need different slices of the knowledge base.
    This keeps context focused instead of dumping everything.
    """
    parts = [load_for_identity()]  # always include briefing

    # Always include today's signals for cross-cycle awareness
    signals = get_daily_signals()
    if signals != "(no signals yet today)":
        parts.append(f"## Cross-Cycle Signals (today)\n{signals}")

    # Cycle-specific knowledge
    if cycle_name in ("product-loop", "build-doctor", "store-audit", "neo-daily", "neo-weekly"):
        # These need open issues + recent audits
        issues = _read_safe(KNOWLEDGE_DIR / "known-issues.md")
        if issues:
            parts.append(f"## Full Known Issues\n{issues[:8000]}")

    # Neo cycles also need product-roster.md to know which products are alive,
    # and the doctrine snippet so the daily/weekly behaviour stays anchored.
    if cycle_name in ("neo-daily", "neo-weekly"):
        roster = _read_safe(KNOWLEDGE_DIR / "product-roster.md")
        if roster:
            parts.append(f"## Product Roster\n{roster[:8000]}")
        edges = _read_safe(KNOWLEDGE_DIR / "edges.md")
        if edges:
            parts.append(f"## OEFR Edges (read before scoring any market opportunity)\n{edges[:4000]}")

    if cycle_name == "stripe-pulse":
        # Needs recent audit entries mentioning stripe/revenue/churn
        audit = _read_safe(KNOWLEDGE_DIR / "audit-log.md")
        stripe_entries = query("stripe") + "\n" + query("churn") + "\n" + query("revenue")
        if stripe_entries.strip():
            parts.append(f"## Stripe-Related History\n{stripe_entries[:5000]}")

    if cycle_name == "brain-review":
        # Needs everything — but it's designed for that
        for f in KNOWLEDGE_FILES:
            content = _read_safe(KNOWLEDGE_DIR / f)
            if content and len(content.strip()) > 50:
                parts.append(f"## {f}\n{content[:10000]}")

    return "\n\n---\n\n".join(parts)


# ── Issue status updates (for Telegram feedback) ────────────────

_STATUS_SECTIONS = {
    "open": "Open Issues",
    "fixed": "Fixed",
    "false-positive": "False Positives",
    "wont-fix": "Won't Fix",
}


def update_issue_status(search_text: str, new_status: str) -> str:
    """Find an issue matching search_text, update status, and move to correct section.

    Used by the Telegram feedback loop when TJ replies with fp/wontfix/fixed.
    """
    issues_path = KNOWLEDGE_DIR / "known-issues.md"
    content = _read_safe(issues_path)
    if not content:
        return "ERROR: known-issues.md not found"

    pattern = re.compile(re.escape(search_text), re.IGNORECASE)

    # Find and remove the matching line
    lines = content.splitlines()
    removed_line = None
    for i, line in enumerate(lines):
        if pattern.search(line) and re.search(r"\[\d{4}-\d{2}-\d{2}\]", line):
            # Update the status in the line
            removed_line = re.sub(
                r"— (open|fixed|false-positive|wont-fix)\s*$",
                f"— {new_status}",
                line,
            )
            lines.pop(i)
            break

    if not removed_line:
        return f"No issue matching '{search_text}' found"

    # Rebuild content without the old line
    content = "\n".join(lines)

    # Insert under the correct section
    target_section = _STATUS_SECTIONS.get(new_status, "Open Issues")
    section_pattern = rf"(## {re.escape(target_section)}[^\n]*\n)"
    match = re.search(section_pattern, content)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + removed_line + "\n" + content[insert_pos:]
    else:
        content += "\n" + removed_line + "\n"

    issues_path.write_text(content)

    # Regenerate briefing since issue counts changed
    generate_briefing()

    return f"Updated issue status to '{new_status}': {search_text[:80]}"
