"""Trinity Second Brain — LLM Wiki Engine.

VIEW LAYER over the unified memory system.  Wiki entries are memory
entries with `kind` metadata.  This module queries memory by kind
to generate briefings, log knowledge entries, and provide cycle context.

Backward compatibility: if old flat markdown files exist in knowledge/,
they are read as fallback when memory has no entries for a given kind.

All paths are relative to trinity_dir (the .trinity/ directory).
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from trinity.memory.store import (
    store_memory,
    query_by_kind,
    update_memory_metadata,
    list_memories,
    get_memory,
    TIERS,
)
from trinity.memory.search import search_memories

# Old flat-file names for backward compatibility
KNOWLEDGE_FILES = [
    "issues.md",
    "decisions.md",
    "audit-log.md",
    "lessons.md",
]


# ── Helpers ────────────────────────────────────────────────────────

def _knowledge_dir(trinity_dir: Path) -> Path:
    return trinity_dir / "knowledge"


def _views_dir(trinity_dir: Path) -> Path:
    return trinity_dir / "views"


def _briefing_path(trinity_dir: Path) -> Path:
    return _views_dir(trinity_dir) / "briefing.md"


def _signals_path(trinity_dir: Path) -> Path:
    return _knowledge_dir(trinity_dir) / "signals.md"


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
    entries = re.findall(
        r"(\[\d{4}-\d{2}-\d{2}\][^\n]*(?:\n(?!\[|\#).*)*)", section,
    )
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


def _memory_content_for_entry(trinity_dir: Path, entry: dict) -> str:
    """Read full content for an index entry (no access-stat side effects)."""
    memory_id = entry.get("id", "")
    data = get_memory(trinity_dir, memory_id)
    if not data:
        return entry.get("summary", "")
    return data.get("content") or entry.get("summary", "")


_STATUS_SECTIONS = {
    "open": "Open Issues",
    "fixed": "Fixed",
    "false-positive": "False Positives",
    "wont-fix": "Won't Fix",
}

_BRIEFING_TEMPLATE = """\
# Second Brain Briefing
No data yet. Run a cycle or log entries to populate.
"""


# ── Initialization ─────────────────────────────────────────────────

def init_knowledge(trinity_dir: Path) -> None:
    """Create views/ dir (and legacy knowledge/ dir for backward compat)."""
    views = _views_dir(trinity_dir)
    views.mkdir(parents=True, exist_ok=True)

    # Also keep knowledge/ dir for signals file and backward compat
    kd = _knowledge_dir(trinity_dir)
    kd.mkdir(parents=True, exist_ok=True)

    briefing = _briefing_path(trinity_dir)
    if not briefing.exists():
        briefing.write_text(_BRIEFING_TEMPLATE)

    # Ensure signals file exists
    signals = _signals_path(trinity_dir)
    if not signals.exists():
        signals.write_text(
            "# Daily Signals\n"
            "Cross-cycle intelligence for today. Each cycle appends, next cycle reads.\n"
        )


# ── Briefing generation ───────────────────────────────────────────

def generate_briefing(trinity_dir: Path) -> str:
    """Scan memory by kind and produce a compact summary (~2K chars).

    This is the only thing loaded into the agent's identity prompt.
    Falls back to legacy flat files if memory has no kind-tagged entries.
    """
    today = dt.date.today().isoformat()
    sections = []

    # --- Open issues from memory (one query, partitioned by status) ---
    all_issues = query_by_kind(trinity_dir, "issue")
    open_issues = [e for e in all_issues if e.get("status") == "open"]
    fixed_issues = [e for e in all_issues if e.get("status") == "fixed"]
    fp_issues = [e for e in all_issues if e.get("status") == "false-positive"]
    wontfix_issues = [e for e in all_issues if e.get("status") == "wont-fix"]

    # Fallback to legacy flat files if memory has zero issue entries
    has_memory_issues = any([open_issues, fixed_issues, fp_issues, wontfix_issues])
    if not has_memory_issues:
        kd = _knowledge_dir(trinity_dir)
        issues_content = _read_safe(kd / "issues.md")
        if issues_content and len(issues_content.strip()) > 50:
            open_issues_legacy = _extract_section_entries(issues_content, "Open Issues")
            fixed_legacy = _extract_section_entries(issues_content, "Fixed")
            fp_legacy = _extract_section_entries(issues_content, "False Positives")
            wontfix_legacy = _extract_section_entries(issues_content, "Won't Fix")
            sections.append(
                f"## Product Health\n"
                f"- Open issues: {len(open_issues_legacy)}\n"
                f"- Fixed (total): {len(fixed_legacy)}\n"
                f"- False positives: {len(fp_legacy)}\n"
                f"- Won't fix: {len(wontfix_legacy)}"
            )
            if open_issues_legacy:
                top = open_issues_legacy[-5:]
                items = "\n".join(f"  - {e[:120]}" for e in top)
                sections.append(f"### Top open issues\n{items}")
        else:
            sections.append(
                f"## Product Health\n"
                f"- Open issues: 0\n"
                f"- Fixed: 0"
            )
    else:
        sections.append(
            f"## Product Health\n"
            f"- Open issues: {len(open_issues)}\n"
            f"- Fixed: {len(fixed_issues)}\n"
            f"- False positives: {len(fp_issues)}\n"
            f"- Won't fix: {len(wontfix_issues)}"
        )
        if open_issues:
            top = open_issues[-5:]
            items = "\n".join(
                f"  - {e.get('summary', '')[:120]}" for e in top
            )
            sections.append(f"### Top open issues\n{items}")

    # --- Audits from memory ---
    all_audits = query_by_kind(trinity_dir, "audit")
    if all_audits:
        recent_audits = all_audits[-3:]
        sections.append(
            f"## Audits\n"
            f"- Total logged: {len(all_audits)}\n"
            f"- Recent: {len(recent_audits)}"
        )
        for entry in recent_audits:
            sections.append(f"  - {entry.get('summary', '')[:120]}")
    else:
        # Fallback to legacy
        kd = _knowledge_dir(trinity_dir)
        audit_content = _read_safe(kd / "audit-log.md")
        if audit_content and len(audit_content.strip()) > 50:
            recent_audits = _recent_entries(audit_content, days=7)
            total_audits = _count_entries(audit_content)
            sections.append(
                f"## Audits\n"
                f"- Total logged: {total_audits}\n"
                f"- Last 7 days: {len(recent_audits)}"
            )
            if recent_audits:
                for entry in recent_audits[-3:]:
                    first_line = entry.split("\n")[0][:120]
                    sections.append(f"  - {first_line}")
        else:
            sections.append("## Audits\n- Total logged: 0")

    # --- Decisions from memory ---
    all_decisions = query_by_kind(trinity_dir, "decision")
    if all_decisions:
        recent_decisions = all_decisions[-5:]
        sections.append(f"## Active Decisions: {len(all_decisions)}")
        for entry in recent_decisions:
            sections.append(f"  - {entry.get('summary', '')[:120]}")
    else:
        # Fallback to legacy
        kd = _knowledge_dir(trinity_dir)
        decisions_content = _read_safe(kd / "decisions.md")
        if decisions_content and len(decisions_content.strip()) > 50:
            active_decisions = _extract_section_entries(decisions_content, "Active Decisions")
            sections.append(f"## Active Decisions: {len(active_decisions)}")
        else:
            sections.append("## Active Decisions: 0")

    # --- Lessons from memory ---
    all_lessons = query_by_kind(trinity_dir, "lesson")
    if all_lessons:
        wins = [e for e in all_lessons if e.get("category") == "win"]
        failures = [e for e in all_lessons if e.get("category") == "failure"]
        sections.append(
            f"## Lessons: {len(wins)} wins, {len(failures)} failures logged"
        )
        recent_lessons = all_lessons[-3:]
        for entry in recent_lessons:
            sections.append(f"  - {entry.get('summary', '')[:120]}")
    else:
        # Fallback to legacy
        kd = _knowledge_dir(trinity_dir)
        lessons_content = _read_safe(kd / "lessons.md")
        if lessons_content and len(lessons_content.strip()) > 50:
            wins = _extract_section_entries(lessons_content, "Wins")
            failures = _extract_section_entries(lessons_content, "Failures")
            sections.append(
                f"## Lessons: {len(wins)} wins, {len(failures)} failures logged"
            )
        else:
            sections.append("## Lessons: 0 wins, 0 failures logged")

    # --- Active corrections from permanent tier ---
    all_memories = list_memories(trinity_dir, tier="permanent")
    corrections = [m for m in all_memories if m.get("kind") == "correction"]
    if corrections:
        items = "\n".join(
            f"  - {c.get('summary', '')[:120]}" for c in corrections[-5:]
        )
        sections.append(f"## Active Corrections\n{items}")

    # --- Today's cross-cycle signals ---
    signals = _read_safe(_signals_path(trinity_dir))
    today_signals = [
        line.strip() for line in signals.splitlines()
        if line.strip().startswith(f"[{today}")
    ]

    # Also check memory-based signals from today
    memory_signals = query_by_kind(trinity_dir, "signal")
    today_memory_signals = [
        s for s in memory_signals
        if s.get("created", "").startswith(today)
    ]

    all_today = []
    if today_signals:
        all_today.extend(today_signals[-5:])
    if today_memory_signals:
        all_today.extend(
            s.get("summary", "")[:120] for s in today_memory_signals[-5:]
        )

    if all_today:
        items = "\n".join(f"  - {s}" for s in all_today[:8])
        sections.append(f"## Today's Signals\n{items}")

    briefing = (
        f"# Second Brain Briefing\n"
        f"Generated: {today}\n\n"
        + "\n\n".join(sections)
        + "\n\n---\n"
        f"Use knowledge CLI to search: `trinity knowledge query <topic>`\n"
        f"Use knowledge CLI to write: `trinity knowledge log-issue|log-audit|signal`\n"
    )

    # Write to views/ directory
    views = _views_dir(trinity_dir)
    views.mkdir(parents=True, exist_ok=True)
    _briefing_path(trinity_dir).write_text(briefing)

    # Also write to legacy location for backward compat
    kd = _knowledge_dir(trinity_dir)
    kd.mkdir(parents=True, exist_ok=True)
    legacy_briefing = kd / "briefing.md"
    legacy_briefing.write_text(briefing)

    return briefing


# ── Search ─────────────────────────────────────────────────────────

def query(trinity_dir: Path, topic: str) -> str:
    """Search across memory (all kinds) for entries matching a topic.

    Falls back to legacy flat files if memory search returns nothing.
    """
    # Search unified memory
    results = search_memories(trinity_dir, topic, limit=15)
    if results:
        parts = []
        for r in results:
            kind_tag = f"[{r['kind']}] " if r.get("kind") else ""
            status_tag = f"({r['status']}) " if r.get("status") else ""
            parts.append(
                f"{kind_tag}{status_tag}{r.get('summary', '')}\n"
                f"  {r.get('content', '')[:400]}"
            )
        return "\n\n---\n\n".join(parts)

    # Fallback: search legacy flat files
    kd = _knowledge_dir(trinity_dir)
    legacy_results = []
    pattern = re.compile(re.escape(topic), re.IGNORECASE)

    for filename in KNOWLEDGE_FILES + ["signals.md"]:
        content = _read_safe(kd / filename)
        if not content:
            continue

        chunks = re.split(r"\n(?=\[?\d{4}-\d{2}-\d{2}\]?|### )", content)
        for chunk in chunks:
            if pattern.search(chunk):
                legacy_results.append(f"[{filename}] {chunk.strip()[:500]}")

    if not legacy_results:
        return f"No entries matching '{topic}' found in knowledge base."

    return "\n\n---\n\n".join(legacy_results[:15])


# ── Signal logging ─────────────────────────────────────────────────

def add_signal(trinity_dir: Path, cycle: str, message: str) -> str:
    """Log a cross-cycle signal as a memory entry + append to signals file."""
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"[{ts}] [{cycle}] {message}"

    # Store in unified memory
    store_memory(
        trinity_dir,
        content,
        segment="context",
        kind="signal",
        source=cycle,
    )

    # Also append to legacy signals file for backward compat
    signals_file = _signals_path(trinity_dir)
    if not signals_file.exists():
        init_knowledge(trinity_dir)

    with open(signals_file, "a") as f:
        f.write(content + "\n")

    return f"Signal logged: {content.strip()}"


def reset_daily_signals(trinity_dir: Path) -> None:
    """Clear signals.md content (keep header)."""
    today = dt.date.today().isoformat()
    _signals_path(trinity_dir).write_text(
        f"# Daily Signals -- {today}\n"
        f"Cross-cycle intelligence for today. Each cycle appends, next cycle reads.\n\n"
    )


def get_daily_signals(trinity_dir: Path) -> str:
    """Read today's signals from memory + legacy file."""
    today = dt.date.today().isoformat()
    parts = []

    # Memory-based signals from today
    memory_signals = query_by_kind(trinity_dir, "signal")
    today_signals = [
        s for s in memory_signals
        if s.get("created", "").startswith(today)
    ]
    if today_signals:
        for s in today_signals:
            parts.append(s.get("summary", ""))

    # Legacy file signals
    content = _read_safe(_signals_path(trinity_dir))
    if content:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith(f"[{today}") and stripped not in parts:
                parts.append(stripped)

    if not parts:
        return "(no signals yet today)"
    return "\n".join(parts)


# ── Tiered context loading ─────────────────────────────────────────

def load_for_identity(trinity_dir: Path) -> str:
    """Load ONLY the compact briefing for identity prompt injection.

    Returns ~2K chars instead of potentially 30K+.
    """
    content = _read_safe(_briefing_path(trinity_dir))
    if not content or len(content.strip()) < 50:
        # Also try legacy location
        content = _read_safe(_knowledge_dir(trinity_dir) / "briefing.md")
    if not content or len(content.strip()) < 50:
        content = generate_briefing(trinity_dir)
    return content


def load_for_cycle(trinity_dir: Path, cycle: str) -> str:
    """Load targeted context for a specific cycle type.

    Different cycles need different slices of the knowledge base.
    Returns briefing + kind-filtered context from memory.
    """
    parts = [load_for_identity(trinity_dir)]

    # Always include today's signals for cross-cycle awareness
    signals = get_daily_signals(trinity_dir)
    if signals != "(no signals yet today)":
        parts.append(f"## Cross-Cycle Signals (today)\n{signals}")

    # Cycle-specific knowledge from memory
    if cycle in ("product-loop", "build-doctor", "store-audit"):
        open_issues = query_by_kind(trinity_dir, "issue", status="open")
        if open_issues:
            issue_lines = []
            for entry in open_issues:
                content = _memory_content_for_entry(trinity_dir, entry)
                issue_lines.append(f"- {content[:300]}")
            parts.append(
                f"## Full Known Issues ({len(open_issues)} open)\n"
                + "\n".join(issue_lines[:50])
            )
        else:
            # Fallback to legacy flat file
            kd = _knowledge_dir(trinity_dir)
            issues = _read_safe(kd / "issues.md")
            if issues and len(issues.strip()) > 50:
                parts.append(f"## Full Known Issues\n{issues[:8000]}")

    if cycle == "stripe-pulse":
        stripe_results = query(trinity_dir, "stripe")
        churn_results = query(trinity_dir, "churn")
        revenue_results = query(trinity_dir, "revenue")
        combined = "\n".join(
            r for r in [stripe_results, churn_results, revenue_results]
            if r and "No entries matching" not in r
        )
        if combined.strip():
            parts.append(f"## Stripe-Related History\n{combined[:5000]}")

    if cycle == "brain-review":
        # Load all kinds for full review
        for kind_name in ["issue", "decision", "audit", "lesson"]:
            entries = query_by_kind(trinity_dir, kind_name)
            if entries:
                entry_lines = []
                for entry in entries[-20:]:
                    summary = entry.get("summary", "")
                    status = f" ({entry['status']})" if entry.get("status") else ""
                    entry_lines.append(f"- {summary}{status}")
                parts.append(
                    f"## {kind_name.title()}s ({len(entries)} total)\n"
                    + "\n".join(entry_lines)
                )

        # Also include legacy files if they have content not in memory
        kd = _knowledge_dir(trinity_dir)
        for f in KNOWLEDGE_FILES:
            content = _read_safe(kd / f)
            if content and len(content.strip()) > 50:
                parts.append(f"## Legacy: {f}\n{content[:10000]}")

    return "\n\n---\n\n".join(parts)


# ── Issue status updates ──────────────────────────────────────────

def update_issue_status(trinity_dir: Path, search_text: str, new_status: str) -> str:
    """Find an issue matching search_text, update status via memory metadata.

    Used by the Telegram feedback loop when TJ replies with fp/wontfix/fixed.
    Falls back to legacy flat-file manipulation if no memory match found.
    """
    # Try memory-based lookup first
    all_issues = query_by_kind(trinity_dir, "issue")
    pattern = re.compile(re.escape(search_text), re.IGNORECASE)

    for entry in all_issues:
        summary = entry.get("summary", "")
        memory_id = entry.get("id", "")
        # Check summary and also read content
        content = _memory_content_for_entry(trinity_dir, entry)
        if pattern.search(summary) or pattern.search(content):
            update_memory_metadata(trinity_dir, memory_id, status=new_status)
            generate_briefing(trinity_dir)
            return f"Updated issue status to '{new_status}': {search_text[:80]}"

    # Fallback: try legacy flat-file approach
    issues_path = _knowledge_dir(trinity_dir) / "issues.md"
    content = _read_safe(issues_path)
    if not content:
        return f"No issue matching '{search_text}' found"

    lines = content.splitlines()
    removed_line = None
    for i, line in enumerate(lines):
        if pattern.search(line) and re.search(r"\[\d{4}-\d{2}-\d{2}\]", line):
            removed_line = re.sub(
                r"— (open|fixed|false-positive|wont-fix)\s*$",
                f"— {new_status}",
                line,
            )
            lines.pop(i)
            break

    if not removed_line:
        return f"No issue matching '{search_text}' found"

    content = "\n".join(lines)

    target_section = _STATUS_SECTIONS.get(new_status, "Open Issues")
    section_pattern = rf"(## {re.escape(target_section)}[^\n]*\n)"
    match = re.search(section_pattern, content)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + removed_line + "\n" + content[insert_pos:]
    else:
        content += "\n" + removed_line + "\n"

    issues_path.write_text(content)
    generate_briefing(trinity_dir)

    return f"Updated issue status to '{new_status}': {search_text[:80]}"


# ── Logging functions ─────────────────────────────────────────────

def log_issue(
    trinity_dir: Path,
    product: str,
    description: str,
    status: str = "open",
) -> str:
    """Log an issue as a memory entry with kind='issue'."""
    ts = dt.date.today().isoformat()
    content = f"[{ts}] {product} — {description} — {status}"

    store_memory(
        trinity_dir,
        content,
        segment="projects",
        kind="issue",
        status=status,
        product=product,
        source="knowledge-cli",
    )

    generate_briefing(trinity_dir)
    return f"Logged issue: {product} — {description} [{status}]"


def log_audit(
    trinity_dir: Path,
    audit_type: str,
    product: str,
    findings: str,
    actions: str,
    pushed_to: str = "none",
    needs_review: bool = False,
) -> str:
    """Log an audit entry as a memory with kind='audit'."""
    ts = dt.date.today().isoformat()
    review = "yes" if needs_review else "no"
    content = (
        f"[{ts}] {audit_type} — {product}\n"
        f"Findings: {findings}\n"
        f"Actions taken: {actions}\n"
        f"Pushed to: {pushed_to}\n"
        f"Needs human review: {review}"
    )

    store_memory(
        trinity_dir,
        content,
        segment="projects",
        kind="audit",
        product=product,
        source="knowledge-cli",
    )

    generate_briefing(trinity_dir)
    return f"Logged audit: {audit_type} — {product}"


def log_decision(
    trinity_dir: Path,
    decision: str,
    context: str,
    rationale: str,
) -> str:
    """Log a decision as a memory with kind='decision'."""
    ts = dt.date.today().isoformat()
    content = f"[{ts}] {decision} — {context} — {rationale}"

    store_memory(
        trinity_dir,
        content,
        segment="facts",
        kind="decision",
        source="knowledge-cli",
    )

    generate_briefing(trinity_dir)
    return f"Logged decision: {decision}"


def log_lesson(
    trinity_dir: Path,
    lesson: str,
    context: str,
    category: str = "process",
) -> str:
    """Log a lesson as a memory with kind='lesson'."""
    ts = dt.date.today().isoformat()
    content = f"[{ts}] {lesson} — {context} [{category}]"

    store_memory(
        trinity_dir,
        content,
        segment="skills",
        kind="lesson",
        category=category,
        source="knowledge-cli",
    )

    generate_briefing(trinity_dir)
    return f"Logged lesson: {lesson} [{category}]"
