import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from ingestion.schema import TranscriptSummary


@dataclass
class ValidationReport:
    row_count: int = 0
    missing_files: set[str] = field(default_factory=set)
    duplicate_files: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_files and not self.duplicate_files and not self.errors


def validate_summaries_jsonl(path: Path, expected_files: set[str]) -> ValidationReport:
    rep = ValidationReport()
    seen: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                rep.errors.append(f"line {line_no}: invalid json: {e}")
                continue
            try:
                row = TranscriptSummary(**data)
            except ValidationError as e:
                rep.errors.append(f"line {line_no}: {e}")
                continue
            rep.row_count += 1
            if row.file in seen:
                rep.duplicate_files.add(row.file)
            seen.add(row.file)
    rep.missing_files = expected_files - seen
    return rep
