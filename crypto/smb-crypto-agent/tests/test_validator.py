import json
import pytest
from ingestion.validator import validate_summaries_jsonl, ValidationReport


def _write(tmp_path, lines):
    p = tmp_path / "summaries.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


def _good_row(file="x.md"):
    return {
        "file": file, "video_id": "", "title": "",
        "categories": ["risk_management"], "equity_only": False,
        "crypto_translatable": True, "tactical_score": 2,
        "setups": [], "principles": ["be disciplined"], "skip_reason": None,
    }


def test_all_rows_valid(tmp_path):
    p = _write(tmp_path, [json.dumps(_good_row("a.md")), json.dumps(_good_row("b.md"))])
    rep = validate_summaries_jsonl(p, expected_files={"a.md", "b.md"})
    assert rep.ok
    assert rep.row_count == 2
    assert rep.missing_files == set()
    assert rep.errors == []


def test_detects_missing_files(tmp_path):
    p = _write(tmp_path, [json.dumps(_good_row("a.md"))])
    rep = validate_summaries_jsonl(p, expected_files={"a.md", "b.md"})
    assert not rep.ok
    assert "b.md" in rep.missing_files


def test_detects_schema_errors(tmp_path):
    bad = _good_row()
    bad["tactical_score"] = 99
    p = _write(tmp_path, [json.dumps(bad)])
    rep = validate_summaries_jsonl(p, expected_files={"x.md"})
    assert not rep.ok
    assert any("tactical_score" in e for e in rep.errors)


def test_detects_duplicate_files(tmp_path):
    p = _write(tmp_path, [json.dumps(_good_row("a.md")), json.dumps(_good_row("a.md"))])
    rep = validate_summaries_jsonl(p, expected_files={"a.md"})
    assert not rep.ok
    assert rep.duplicate_files == {"a.md"}


def test_malformed_json_line(tmp_path):
    p = tmp_path / "summaries.jsonl"
    p.write_text(json.dumps(_good_row()) + "\n" + "{not json}\n")
    rep = validate_summaries_jsonl(p, expected_files={"x.md"})
    assert not rep.ok
    assert any("json" in e.lower() for e in rep.errors)
