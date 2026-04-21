"""
Phase-2 synthesis helper.

Groups validated transcript summaries by category so a subagent can be dispatched
per category cluster. Each group contains the full summary rows plus all extracted
setups tagged with that category.
"""
import json
from collections import defaultdict
from pathlib import Path

from ingestion.schema import TranscriptSummary


def load_summaries(path: Path) -> list[TranscriptSummary]:
    rows: list[TranscriptSummary] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(TranscriptSummary(**json.loads(line)))
    return rows


def group_by_category(rows: list[TranscriptSummary]) -> dict[str, list[TranscriptSummary]]:
    groups: dict[str, list[TranscriptSummary]] = defaultdict(list)
    for row in rows:
        for cat in row.categories:
            groups[cat].append(row)
    return dict(groups)


def tactical_rows(rows: list[TranscriptSummary], min_score: int = 3) -> list[TranscriptSummary]:
    return [r for r in rows if r.tactical_score >= min_score and not r.equity_only]


def write_cluster_files(groups: dict[str, list[TranscriptSummary]], out_dir: Path) -> list[Path]:
    """Write each category's rows to a JSONL file under out_dir for subagent input."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for cat, rows in groups.items():
        p = out_dir / f"cluster_{cat}.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(r.model_dump_json() + "\n")
        written.append(p)
    return written
