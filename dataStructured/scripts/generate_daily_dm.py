#!/usr/bin/env python3
"""Generate today's daily DM from the CFO digest + ethics ledger.

Usage:
  python scripts/generate_daily_dm.py [YYYY-MM-DD]

Defaults to today's date if no date argument is given. Paths and the DM body
are derived from the dated state files rather than hardcoded, so this works on
any day for which a CFO digest exists.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]


def resolve_date(argv) -> str:
    """Return the target date (YYYY-MM-DD): CLI arg if given, else today (UTC)."""
    if len(argv) > 1:
        d = argv[1].strip()
        # Validate format so a bad arg fails loud rather than silently mis-globbing.
        datetime.strptime(d, "%Y-%m-%d")
        return d
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def main(argv) -> int:
    date = resolve_date(argv)

    # Read CFO digest for the target date.
    cfo_path = WORKSPACE / "state" / "cfo-digest" / f"{date}.json"
    if not cfo_path.exists():
        print(f"[daily-dm] ERROR: No CFO digest for {date} at {cfo_path}", file=sys.stderr)
        return 1
    with open(cfo_path) as f:
        cfo = json.load(f)

    # Read compliance ledger entries for the target date (keyed date-slug).
    ledger_dir = WORKSPACE / "state" / "ethics-ledger"
    ledger_paths = sorted(ledger_dir.glob(f"{date}-*.json"))
    ledgers = []
    for lp in ledger_paths:
        try:
            with open(lp) as f:
                ledgers.append(json.load(f))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[daily-dm] WARN: could not read ledger {lp.name}: {e}", file=sys.stderr)

    # Headline — derived from CFO digest data.
    headline = (
        f"💰 MRR: ${cfo.get('mrr', 0)} | "
        f"Revenue today: ${cfo.get('one_time_revenue_today', 0)} | "
        f"30d: ${cfo.get('one_time_revenue_30d', 0)}\n"
        f"Anomalies: {len(cfo.get('anomalies', []))}\n"
    )

    # Body — derived from the ledger entries for the date.
    lines = [
        "",
        f"📊 DataStructured — {date}",
        "══════════════════════════════",
        "COMPLIANCE LEDGER:",
    ]
    if ledgers:
        for lg in ledgers:
            slug = lg.get("slug", "(unknown)")
            verdict = lg.get("verdict", "(no verdict)")
            row_count = lg.get("row_count")
            suffix = f" — {row_count} rows" if row_count is not None else ""
            lines.append(f"- {slug}: {verdict}{suffix}")
    else:
        lines.append("- (no ethics ledger entries for this date)")
    dm_body = "\n".join(lines) + "\n"

    full_dm = headline + dm_body

    print(full_dm)
    print("\n" + "=" * 60)
    print("DM ready to send to founder")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
