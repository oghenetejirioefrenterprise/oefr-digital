#!/usr/bin/env python3
"""Trinity Second Brain — CLI for knowledge operations.

This is the bridge that makes the knowledge base usable during
`claude --print` runs. Trinity invokes these via Bash tool.

Usage:
    # Log an issue
    python trinity/knowledge/cli.py log-issue netarch-pro "build fails on missing dep" --status open

    # Log an audit
    python trinity/knowledge/cli.py log-audit build-check netarch-pro "build failure" "installed missing dep"

    # Log a cross-cycle signal
    python trinity/knowledge/cli.py signal product-loop "netarch-pro has broken build, needs react-icons"

    # Search the knowledge base
    python trinity/knowledge/cli.py query netarch-pro

    # Regenerate the compact briefing
    python trinity/knowledge/cli.py briefing

    # Update issue status (used by Telegram feedback)
    python trinity/knowledge/cli.py update-status "netarch-pro" false-positive

    # Get today's signals
    python trinity/knowledge/cli.py signals

    # Get context for a specific cycle
    python trinity/knowledge/cli.py context product-loop

    # Log a decision
    python trinity/knowledge/cli.py log-decision "switched to Tailwind v4" "performance audit" "v4 is 40% smaller"

    # Log a lesson
    python trinity/knowledge/cli.py log-lesson "always run build before commit" "pushed broken code to dev" --category failure

    # Reset daily signals (new day)
    python trinity/knowledge/cli.py reset-signals
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

# Ensure trinity/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge.wiki import (
    add_signal,
    generate_briefing,
    get_daily_signals,
    load_for_cycle,
    load_for_identity,
    query,
    reset_daily_signals,
    update_issue_status,
    KNOWLEDGE_DIR,
)


def _append_to_file(filename: str, entry: str):
    """Append a timestamped entry to a knowledge file."""
    path = KNOWLEDGE_DIR / filename
    with open(path, "a") as f:
        f.write(entry)


def _insert_under_section(filename: str, section_header: str, entry: str):
    """Insert an entry under a specific ## section in a knowledge file."""
    path = KNOWLEDGE_DIR / filename
    content = path.read_text() if path.exists() else ""

    # Find the section header and insert the entry right after it
    pattern = rf"(## {section_header}[^\n]*\n)"
    match = re.search(pattern, content)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + entry + "\n" + content[insert_pos:]
    else:
        # Section not found — append to end
        content += entry + "\n"

    path.write_text(content)


# Map issue status to the section header in known-issues.md
_STATUS_SECTIONS = {
    "open": "Open Issues",
    "fixed": "Fixed",
    "false-positive": "False Positives",
    "wont-fix": "Won't Fix",
}


def cmd_log_issue(args):
    ts = dt.date.today().isoformat()
    status = args.status or "open"
    entry = f"[{ts}] {args.product} — {args.description} — {status}"
    section = _STATUS_SECTIONS.get(status, "Open Issues")
    _insert_under_section("known-issues.md", section, entry)
    generate_briefing()
    print(f"Logged issue: {args.product} — {args.description} [{status}]")


def cmd_log_audit(args):
    ts = dt.date.today().isoformat()
    pushed = args.pushed_to or "none"
    review = "yes" if args.needs_review else "no"
    entry = (
        f"\n### [{ts}] {args.audit_type} — {args.product}\n"
        f"- Findings: {args.findings}\n"
        f"- Actions taken: {args.actions}\n"
        f"- Pushed to: {pushed}\n"
        f"- Needs human review: {review}\n"
    )
    _append_to_file("audit-log.md", entry)
    generate_briefing()
    print(f"Logged audit: {args.audit_type} — {args.product}")


def cmd_signal(args):
    result = add_signal(args.cycle, args.message)
    print(result)


def cmd_query(args):
    result = query(args.topic)
    print(result)


def cmd_briefing(args):
    briefing = generate_briefing()
    print(briefing)


def cmd_update_status(args):
    result = update_issue_status(args.search, args.status)
    print(result)


def cmd_signals(args):
    print(get_daily_signals())


def cmd_context(args):
    print(load_for_cycle(args.cycle))


def cmd_log_decision(args):
    ts = dt.date.today().isoformat()
    entry = f"\n[{ts}] {args.decision} — {args.context} — {args.rationale}\n"
    _append_to_file("product-decisions.md", entry)
    generate_briefing()
    print(f"Logged decision: {args.decision}")


def cmd_log_lesson(args):
    ts = dt.date.today().isoformat()
    category = args.category or "process"
    entry = f"\n[{ts}] {args.lesson} — {args.context} [{category}]\n"
    _append_to_file("lessons-learned.md", entry)
    generate_briefing()
    print(f"Logged lesson: {args.lesson} [{category}]")


def cmd_reset_signals(args):
    reset_daily_signals()
    print("Daily signals reset.")


def cmd_sessions(args):
    """Show session log for a date (default: today)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from chat_history import get_today_sessions, get_sessions_for_date
    if args.date:
        content = get_sessions_for_date(args.date)
    else:
        content = get_today_sessions()
    if content:
        print(content)
    else:
        print(f"No session log for {args.date or 'today'}")


def main():
    parser = argparse.ArgumentParser(
        description="Trinity Second Brain — Knowledge CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # log-issue
    p = sub.add_parser("log-issue", help="Log a known issue")
    p.add_argument("product", help="Product name (e.g. netarch-pro)")
    p.add_argument("description", help="Issue description")
    p.add_argument("--status", default="open",
                   choices=["open", "fixed", "false-positive", "wont-fix"])
    p.set_defaults(func=cmd_log_issue)

    # log-audit
    p = sub.add_parser("log-audit", help="Log an audit result")
    p.add_argument("audit_type", help="Type (build-check, deploy-check, etc.)")
    p.add_argument("product", help="Product audited")
    p.add_argument("findings", help="What was found")
    p.add_argument("actions", help="What actions were taken")
    p.add_argument("--pushed-to", default="none", help="dev, preview, or none")
    p.add_argument("--needs-review", action="store_true")
    p.set_defaults(func=cmd_log_audit)

    # signal
    p = sub.add_parser("signal", help="Log a cross-cycle signal")
    p.add_argument("cycle", help="Which cycle is reporting (e.g. product-loop)")
    p.add_argument("message", help="Signal content")
    p.set_defaults(func=cmd_signal)

    # query
    p = sub.add_parser("query", help="Search the knowledge base")
    p.add_argument("topic", help="Search term")
    p.set_defaults(func=cmd_query)

    # briefing
    p = sub.add_parser("briefing", help="Regenerate the compact briefing")
    p.set_defaults(func=cmd_briefing)

    # update-status
    p = sub.add_parser("update-status", help="Update an issue's status")
    p.add_argument("search", help="Text to match in the issue")
    p.add_argument("status", choices=["open", "fixed", "false-positive", "wont-fix"])
    p.set_defaults(func=cmd_update_status)

    # signals
    p = sub.add_parser("signals", help="Show today's cross-cycle signals")
    p.set_defaults(func=cmd_signals)

    # context
    p = sub.add_parser("context", help="Get targeted knowledge for a cycle")
    p.add_argument("cycle", help="Cycle name (product-loop, stripe-pulse, etc.)")
    p.set_defaults(func=cmd_context)

    # log-decision
    p = sub.add_parser("log-decision", help="Log a product decision")
    p.add_argument("decision", help="What was decided")
    p.add_argument("context", help="What triggered this")
    p.add_argument("rationale", help="Why this was the right call")
    p.set_defaults(func=cmd_log_decision)

    # log-lesson
    p = sub.add_parser("log-lesson", help="Log a lesson learned")
    p.add_argument("lesson", help="The lesson")
    p.add_argument("context", help="What happened")
    p.add_argument("--category", default="process",
                   choices=["win", "failure", "process"])
    p.set_defaults(func=cmd_log_lesson)

    # reset-signals
    p = sub.add_parser("reset-signals", help="Clear daily signals for new day")
    p.set_defaults(func=cmd_reset_signals)

    # sessions
    p = sub.add_parser("sessions", help="Show session log for a date")
    p.add_argument("--date", default=None, help="Date (YYYY-MM-DD), default: today")
    p.set_defaults(func=cmd_sessions)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
