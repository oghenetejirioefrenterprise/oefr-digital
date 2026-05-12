#!/usr/bin/env python3
"""Trinity Second Brain — CLI for knowledge operations.

This is the bridge that makes the knowledge base usable during
agent runs. Trinity invokes these via Bash tool.

Usage:
    # Log an issue
    python -m trinity.knowledge.cli log-issue netarch-pro "build fails on missing dep" --status open

    # Log an audit
    python -m trinity.knowledge.cli log-audit build-check netarch-pro "build failure" "installed missing dep"

    # Log a cross-cycle signal
    python -m trinity.knowledge.cli signal product-loop "netarch-pro has broken build"

    # Search the knowledge base
    python -m trinity.knowledge.cli query netarch-pro

    # Regenerate the compact briefing
    python -m trinity.knowledge.cli briefing

    # Update issue status (used by Telegram feedback)
    python -m trinity.knowledge.cli update-status "netarch-pro" false-positive

    # Get today's signals
    python -m trinity.knowledge.cli signals

    # Get context for a specific cycle
    python -m trinity.knowledge.cli context product-loop

    # Log a decision
    python -m trinity.knowledge.cli log-decision "switched to Tailwind v4" "performance audit" "v4 is 40% smaller"

    # Log a lesson
    python -m trinity.knowledge.cli log-lesson "always run build before commit" "pushed broken code" --category failure

    # Reset daily signals (new day)
    python -m trinity.knowledge.cli reset-signals
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _find_trinity_dir() -> Path:
    """Walk up from CWD looking for a .trinity/ directory."""
    current = Path.cwd()
    while current != current.parent:
        candidate = current / ".trinity"
        if candidate.is_dir():
            return candidate
        current = current.parent

    # Fallback: create .trinity in CWD
    fallback = Path.cwd() / ".trinity"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _get_wiki():
    """Late import to avoid circular imports and allow standalone usage."""
    from trinity.knowledge import wiki
    return wiki


# ── Command handlers ───────────────────────────────────────────────

def cmd_log_issue(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    status = args.status or "open"
    result = wiki.log_issue(trinity_dir, args.product, args.description, status)
    print(result)


def cmd_log_audit(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    pushed = args.pushed_to or "none"
    needs_review = args.needs_review
    result = wiki.log_audit(
        trinity_dir, args.audit_type, args.product,
        args.findings, args.actions,
        pushed_to=pushed, needs_review=needs_review,
    )
    print(result)


def cmd_signal(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    result = wiki.add_signal(trinity_dir, args.cycle, args.message)
    print(result)


def cmd_query(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    result = wiki.query(trinity_dir, args.topic)
    print(result)


def cmd_briefing(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    briefing = wiki.generate_briefing(trinity_dir)
    print(briefing)


def cmd_update_status(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    result = wiki.update_issue_status(trinity_dir, args.search, args.status)
    print(result)


def cmd_signals(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    print(wiki.get_daily_signals(trinity_dir))


def cmd_context(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    print(wiki.load_for_cycle(trinity_dir, args.cycle))


def cmd_log_decision(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    result = wiki.log_decision(trinity_dir, args.decision, args.context, args.rationale)
    print(result)


def cmd_log_lesson(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    category = args.category or "process"
    result = wiki.log_lesson(trinity_dir, args.lesson, args.context, category)
    print(result)


def cmd_reset_signals(args):
    wiki = _get_wiki()
    trinity_dir = _find_trinity_dir()
    wiki.reset_daily_signals(trinity_dir)
    print("Daily signals reset.")


def main():
    parser = argparse.ArgumentParser(
        description="Trinity Second Brain -- Knowledge CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # log-issue
    p = sub.add_parser("log-issue", help="Log a known issue")
    p.add_argument("product", help="Product name (e.g. netarch-pro)")
    p.add_argument("description", help="Issue description")
    p.add_argument(
        "--status", default="open",
        choices=["open", "fixed", "false-positive", "wont-fix"],
    )
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
    p.add_argument(
        "status",
        choices=["open", "fixed", "false-positive", "wont-fix"],
    )
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
    p.add_argument(
        "--category", default="process",
        choices=["win", "failure", "process"],
    )
    p.set_defaults(func=cmd_log_lesson)

    # reset-signals
    p = sub.add_parser("reset-signals", help="Clear daily signals for new day")
    p.set_defaults(func=cmd_reset_signals)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
