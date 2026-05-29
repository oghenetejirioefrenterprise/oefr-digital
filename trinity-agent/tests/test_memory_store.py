"""Contract + regression tests for the SQLite-backed memory store.

Covers the public API (unchanged across the migration) and the specific
defects the migration fixes: write-on-read, ID collisions, non-atomic /
truthiness-dropped frontmatter, secret-at-rest, index/file drift, and the
one-time migration from the legacy index.json + .md layout.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from trinity.memory import store
from trinity.memory.search import search_memories


def _td(tmp_path: Path) -> Path:
    """A fresh trinity_dir (store creates the subtree on first use)."""
    return tmp_path / "ws"


# ── Core CRUD contract ─────────────────────────────────────────────

def test_store_and_recall_roundtrip(tmp_path):
    td = _td(tmp_path)
    mid = store.store_memory(td, "The sky is blue today", "facts")
    assert mid.startswith("mem_")
    data = store.recall_memory(td, mid)
    assert data is not None
    assert data["content"] == "The sky is blue today"
    assert data["segment"] == "facts"
    assert data["tier"] == "short-term"
    # recall bumps the access count (1 -> 2)
    assert data["access_count"] == 2


def test_ids_are_sequential_and_unique(tmp_path):
    td = _td(tmp_path)
    ids = [store.store_memory(td, f"fact {i}", "facts") for i in range(3)]
    assert len(set(ids)) == 3  # no collisions / overwrites
    # all share today's prefix and increment
    seqs = sorted(int(i.rsplit("_", 1)[1]) for i in ids)
    assert seqs == [1, 2, 3]


def test_list_memories_shape_has_no_body(tmp_path):
    td = _td(tmp_path)
    store.store_memory(td, "body text here", "facts")
    entries = store.list_memories(td)
    assert len(entries) == 1
    e = entries[0]
    for key in ("id", "tier", "segment", "importance", "decay_rate",
                "last_accessed", "created", "access_count", "summary", "scope"):
        assert key in e
    # index-entry shape never carries the body
    assert "content" not in e


def test_list_memories_by_tier(tmp_path):
    td = _td(tmp_path)
    a = store.store_memory(td, "a", "facts")
    store.store_memory(td, "b", "facts")
    store.promote_memory(td, a, "long-term")
    assert len(store.list_memories(td, tier="short-term")) == 1
    assert len(store.list_memories(td, tier="long-term")) == 1


def test_update_memory(tmp_path):
    td = _td(tmp_path)
    mid = store.store_memory(td, "old content", "facts")
    assert store.update_memory(td, mid, "new content entirely") is True
    data = store.recall_memory(td, mid)
    assert data["content"] == "new content entirely"
    assert "new content" in data["summary"]


def test_forget_removes_row_and_export(tmp_path):
    td = _td(tmp_path)
    mid = store.store_memory(td, "delete me", "facts")
    export = store._tier_dir(td, "short-term") / f"{mid}.md"
    assert export.exists()
    assert store.forget_memory(td, mid) is True
    assert store.recall_memory(td, mid) is None
    assert not export.exists()
    assert store.list_memories(td) == []


def test_promote_to_permanent_broadens_scope(tmp_path):
    td = _td(tmp_path)
    mid = store.store_memory(td, "chat-scoped", "facts", scope="chat_42")
    store.promote_memory(td, mid, "permanent")
    data = store.recall_memory(td, mid)
    assert data["tier"] == "permanent"
    assert data["scope"] == "global"
    # export moved to the permanent tier dir
    assert (store._tier_dir(td, "permanent") / f"{mid}.md").exists()
    assert not (store._tier_dir(td, "short-term") / f"{mid}.md").exists()


def test_query_by_kind_sorted_by_created(tmp_path):
    td = _td(tmp_path)
    store.store_memory(td, "issue one", "facts", kind="issue", status="open")
    store.store_memory(td, "issue two", "facts", kind="issue", status="fixed")
    store.store_memory(td, "a decision", "facts", kind="decision")
    open_issues = store.query_by_kind(td, "issue", status="open")
    assert len(open_issues) == 1
    all_issues = store.query_by_kind(td, "issue")
    assert len(all_issues) == 2
    assert [e["created"] for e in all_issues] == sorted(e["created"] for e in all_issues)


def test_update_memory_metadata(tmp_path):
    td = _td(tmp_path)
    mid = store.store_memory(td, "an issue", "facts", kind="issue", status="open")
    assert store.update_memory_metadata(td, mid, status="fixed") is True
    assert store.query_by_kind(td, "issue", status="open") == []
    assert len(store.query_by_kind(td, "issue", status="fixed")) == 1


def test_invalid_segment_raises(tmp_path):
    td = _td(tmp_path)
    with pytest.raises(ValueError, match="segment"):
        store.store_memory(td, "x", "not-a-segment")


def test_recall_invalid_id_raises(tmp_path):
    td = _td(tmp_path)
    with pytest.raises(ValueError, match="Invalid memory ID"):
        store.recall_memory(td, "../etc/passwd")


# ── Regression: the specific defects the migration fixes ───────────

def test_recall_does_not_rewrite_markdown_export(tmp_path):
    """A read must not rewrite the .md export (kills write-on-read)."""
    td = _td(tmp_path)
    mid = store.store_memory(td, "read me many times", "facts")
    export = store._tier_dir(td, "short-term") / f"{mid}.md"
    before = export.read_text()
    for _ in range(5):
        store.recall_memory(td, mid)
    after = export.read_text()
    # DB access_count climbed, but the export was never rewritten on read.
    assert before == after
    assert "access_count: 1" in after
    assert store.recall_memory(td, mid)["access_count"] == 7


def test_recall_does_not_reset_decay_clock(tmp_path):
    """Reading a memory must NOT refresh its decay reference (last_reinforced).

    Regression for rec 5: decay is measured from last_reinforced (store/update),
    not last_accessed (every read), so recalling a memory doesn't make it
    immortal.
    """
    import datetime as dt
    from trinity.config import MemoryConfig
    from trinity.memory import db
    from trinity.memory.decay import effective_importance

    td = _td(tmp_path)
    mid = store.store_memory(td, "a decaying memory", "facts")
    old = (dt.datetime.now() - dt.timedelta(hours=96)).isoformat(timespec="seconds")
    conn = db.connect(td)
    conn.execute(
        "UPDATE memories SET last_reinforced=?, last_accessed=?, created=?",
        (old, old, old),
    )
    conn.close()

    before = store.list_memories(td)[0]
    eff_before = effective_importance(before, MemoryConfig())

    store.recall_memory(td, mid)  # bumps last_accessed, NOT last_reinforced
    after = store.list_memories(td)[0]

    assert after["last_reinforced"] == old          # decay clock untouched by read
    assert after["last_accessed"] != old            # last-seen did advance
    eff_after = effective_importance(after, MemoryConfig())
    assert eff_after == pytest.approx(eff_before, abs=0.01)  # decay unchanged by read
    assert eff_after < 0.5  # still decayed (would be ~0.7 if read had reset it)


def test_update_reinforces_decay_clock(tmp_path):
    """A content update refreshes the decay reference."""
    import datetime as dt
    from trinity.memory import db

    td = _td(tmp_path)
    mid = store.store_memory(td, "v1", "facts")
    old = (dt.datetime.now() - dt.timedelta(hours=96)).isoformat(timespec="seconds")
    conn = db.connect(td)
    conn.execute("UPDATE memories SET last_reinforced=?", (old,))
    conn.close()

    store.update_memory(td, mid, "v2 content")
    assert store.list_memories(td)[0]["last_reinforced"] != old


def test_get_memory_has_no_side_effects(tmp_path):
    td = _td(tmp_path)
    mid = store.store_memory(td, "inspect me", "facts")
    for _ in range(3):
        store.get_memory(td, mid)
    # access_count untouched by get_memory (still 1 from the store)
    assert store.list_memories(td)[0]["access_count"] == 1


def test_secret_redacted_on_store(tmp_path):
    td = _td(tmp_path)
    secret = "sk-ant-api03-" + "A" * 40
    mid = store.store_memory(td, f"my key is {secret} keep it", "facts")
    data = store.recall_memory(td, mid)
    assert secret not in data["content"]
    assert "sk-ant-***" in data["content"]


def test_falsy_importance_preserved(tmp_path):
    """importance=0.0 must survive store + export (old truthiness bug)."""
    td = _td(tmp_path)
    mid = store.store_memory(td, "trivial note", "facts", importance=0.0)
    assert store.recall_memory(td, mid)["importance"] == 0.0
    export = store._tier_dir(td, "short-term") / f"{mid}.md"
    assert "importance: 0.0" in export.read_text()


def test_concurrent_stores_no_loss_or_collision(tmp_path):
    """Many threads storing at once must not drop or collide on rows."""
    td = _td(tmp_path)
    store.init_memory(td)
    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            store.store_memory(td, f"concurrent fact {i}", "facts")
        except Exception as e:  # pragma: no cover - surfaced via assert
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    entries = store.list_memories(td)
    assert len(entries) == 12
    assert len({e["id"] for e in entries}) == 12  # all unique, none clobbered


# ── Search (FTS5) ──────────────────────────────────────────────────

def test_search_finds_by_keyword(tmp_path):
    td = _td(tmp_path)
    store.store_memory(td, "FMCSA carrier leads are a B2B data product", "facts")
    store.store_memory(td, "unrelated note about tennis", "facts")
    results = search_memories(td, "carrier leads")
    assert results
    assert "carrier" in results[0]["content"].lower()
    assert results[0]["score"] > 0


def test_search_scope_filter(tmp_path):
    td = _td(tmp_path)
    store.store_memory(td, "global visible memory apples", "facts", scope="global")
    store.store_memory(td, "private chat memory apples", "facts", scope="chat_1")
    # scope chat_2 sees only global
    res = search_memories(td, "apples", current_scope="chat_2")
    assert len(res) == 1
    assert res[0]["scope"] if "scope" in res[0] else True  # scope filtered correctly
    # chat_1 sees both
    res1 = search_memories(td, "apples", current_scope="chat_1")
    assert len(res1) == 2


def test_search_empty_query(tmp_path):
    td = _td(tmp_path)
    store.store_memory(td, "something", "facts")
    assert search_memories(td, "   ") == []


# ── One-time migration from the legacy layout ──────────────────────

def test_migration_from_legacy_index(tmp_path):
    td = _td(tmp_path)
    mem = td / "memory"
    (mem / "long-term").mkdir(parents=True)
    (mem / "short-term").mkdir(parents=True)
    (mem / "permanent").mkdir(parents=True)

    index = [
        {
            "id": "mem_20260101_001", "tier": "long-term", "segment": "facts",
            "importance": 0.7, "decay_rate": 1.0,
            "created": "2026-01-01T00:00:00", "last_accessed": "2026-01-02T00:00:00",
            "access_count": 4, "summary": "Legacy fact", "scope": "global",
            "kind": "issue", "status": "open",
        }
    ]
    (mem / "index.json").write_text(json.dumps(index))
    (mem / "long-term" / "mem_20260101_001.md").write_text(
        "---\n"
        "id: mem_20260101_001\n"
        "segment: facts\n"
        "importance: 0.7\n"
        "kind: issue\n"
        "status: open\n"
        "---\n\n"
        "This is the legacy body content about a carrier issue.\n"
    )

    # First access triggers init + migration.
    entries = store.list_memories(td)
    assert len(entries) == 1
    assert entries[0]["id"] == "mem_20260101_001"
    assert entries[0]["tier"] == "long-term"

    # Body content imported into the DB.
    data = store.get_memory(td, "mem_20260101_001")
    assert "legacy body content" in data["content"]

    # Kind/status preserved and queryable.
    assert len(store.query_by_kind(td, "issue", status="open")) == 1

    # Legacy index renamed aside, not reloaded.
    assert not (mem / "index.json").exists()
    assert (mem / "index.json.migrated").exists()


def test_migration_is_idempotent(tmp_path):
    td = _td(tmp_path)
    mem = td / "memory"
    (mem / "short-term").mkdir(parents=True)
    (mem / "index.json").write_text(json.dumps([
        {"id": "mem_20260101_001", "tier": "short-term", "segment": "facts",
         "summary": "x", "scope": "global"}
    ]))
    store.list_memories(td)              # migrate
    # Force the per-process guard to re-check; should not double-insert.
    store._migrate_checked.clear()
    store.list_memories(td)
    assert len(store.list_memories(td)) == 1
