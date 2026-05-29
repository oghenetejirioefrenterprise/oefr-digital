"""Tests for the commitments subsystem."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from trinity.commitments import store
from trinity.commitments.types import (
    CommitmentRecord,
    KIND_DEADLINE_CHECK,
    KIND_OPEN_LOOP,
    PENDING,
    SENT,
    SNOOZED,
    DISMISSED,
    make_dedupe_key,
    make_id,
)


def _ws(tmp_path):
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_record(**kw) -> CommitmentRecord:
    defaults = dict(
        id=make_id(),
        kind=KIND_OPEN_LOOP,
        text="check on X",
        chat_id="42",
        due_at=dt.datetime.now().isoformat(),
        dedupe_key=make_dedupe_key("42", KIND_OPEN_LOOP, "check on X"),
        confidence=0.8,
    )
    defaults.update(kw)
    return CommitmentRecord(**defaults)


def test_add_and_list(tmp_path):
    ws = _ws(tmp_path)
    r = _make_record()
    store.add_or_merge(ws, r)
    rows = store.list_records(ws)
    assert len(rows) == 1
    assert rows[0].id == r.id


def test_dedupe_merges(tmp_path):
    ws = _ws(tmp_path)
    r1 = _make_record(text="check on X", confidence=0.7)
    r2 = _make_record(
        id=make_id(),
        text="check on X",
        confidence=0.95,
        dedupe_key=r1.dedupe_key,
    )
    store.add_or_merge(ws, r1)
    store.add_or_merge(ws, r2)
    rows = store.list_records(ws)
    assert len(rows) == 1
    assert rows[0].confidence == 0.95


def test_due_now_returns_past_pending(tmp_path):
    ws = _ws(tmp_path)
    past = (dt.datetime.now() - dt.timedelta(minutes=5)).isoformat()
    future = (dt.datetime.now() + dt.timedelta(hours=2)).isoformat()
    store.add_or_merge(ws, _make_record(due_at=past, text="due-now"))
    store.add_or_merge(ws, _make_record(due_at=future, text="future", dedupe_key="future-x"))
    due = store.due_now(ws)
    texts = {r.text for r in due}
    assert "due-now" in texts
    assert "future" not in texts


def test_update_status(tmp_path):
    ws = _ws(tmp_path)
    r = _make_record()
    store.add_or_merge(ws, r)
    assert store.update_status(ws, r.id, SENT, sent_at="2026-05-06T10:00:00")
    rows = store.list_records(ws)
    assert rows[0].status == SENT
    assert rows[0].sent_at == "2026-05-06T10:00:00"


def test_terminal_state_no_reopen(tmp_path):
    ws = _ws(tmp_path)
    r = _make_record()
    store.add_or_merge(ws, r)
    store.update_status(ws, r.id, DISMISSED)
    # Re-add same dedupe_key — should NOT reopen
    store.add_or_merge(ws, _make_record(text="updated", dedupe_key=r.dedupe_key))
    rows = store.list_records(ws)
    assert rows[0].status == DISMISSED


def test_snoozed_due_when_until_passes(tmp_path):
    ws = _ws(tmp_path)
    past = (dt.datetime.now() - dt.timedelta(minutes=5)).isoformat()
    r = _make_record(text="zzz")
    store.add_or_merge(ws, r)
    store.update_status(ws, r.id, SNOOZED, snoozed_until=past)
    due = store.due_now(ws)
    assert any(d.id == r.id for d in due)


# ── Extraction (with stub provider) ──────────────────────────────────


class _ExtractStub:
    def __init__(self, raw):
        self._raw = raw

    def chat(self, **kw):
        class R:
            text = self._raw
        return R()


def test_extraction_parses_well_formed_json(tmp_path):
    from trinity.commitments.extraction import extract_commitments
    from trinity.config import TrinityConfig, AgentConfig, MemoryConfig
    cfg = TrinityConfig(
        memory=MemoryConfig(),
        agent=AgentConfig(),
        workspace_root=tmp_path,
        trinity_dir=tmp_path,
    )
    future = (dt.datetime.now() + dt.timedelta(days=1)).replace(microsecond=0).isoformat()
    raw = json.dumps([{
        "kind": "event_check_in",
        "text": "follow up on Reddit access",
        "due_at": future,
        "nudge_text": "Did Reddit get back to you?",
        "confidence": 0.85,
    }])
    provider = _ExtractStub(raw)
    out = extract_commitments(
        "I'll check tomorrow", "noted, I'll ping you", "42", cfg, provider,
    )
    assert len(out) == 1
    assert out[0].text == "follow up on Reddit access"
    assert out[0].nudge_text.startswith("Did Reddit")


def test_extraction_drops_low_confidence(tmp_path):
    from trinity.commitments.extraction import extract_commitments
    from trinity.config import TrinityConfig, AgentConfig, MemoryConfig
    cfg = TrinityConfig(
        memory=MemoryConfig(),
        agent=AgentConfig(),
        workspace_root=tmp_path,
        trinity_dir=tmp_path,
    )
    future = (dt.datetime.now() + dt.timedelta(days=1)).isoformat()
    raw = json.dumps([{
        "kind": "open_loop",
        "text": "maybe X",
        "due_at": future,
        "confidence": 0.3,
    }])
    out = extract_commitments(
        "user", "asst", "42", cfg, _ExtractStub(raw),
    )
    assert out == []


def test_extraction_handles_garbage(tmp_path):
    from trinity.commitments.extraction import extract_commitments
    from trinity.config import TrinityConfig, AgentConfig, MemoryConfig
    cfg = TrinityConfig(
        memory=MemoryConfig(),
        agent=AgentConfig(),
        workspace_root=tmp_path,
        trinity_dir=tmp_path,
    )
    out = extract_commitments(
        "u", "a", "42", cfg, _ExtractStub("not even close to JSON"),
    )
    assert out == []


def test_migrates_legacy_json(tmp_path):
    """A legacy commitments.json is imported into the DB once, then renamed."""
    ws = _ws(tmp_path)
    rec = _make_record(text="legacy promise", dedupe_key="legacydk", id="cmt_legacy01")
    (ws / "state" / "commitments.json").write_text(json.dumps([rec.to_dict()]))

    recs = store.list_records(ws)
    assert len(recs) == 1
    assert recs[0].text == "legacy promise"
    assert not (ws / "state" / "commitments.json").exists()
    assert (ws / "state" / "commitments.json.migrated").exists()
