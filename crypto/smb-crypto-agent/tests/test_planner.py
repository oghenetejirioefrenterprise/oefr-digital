from ingestion.planner import plan_batches, Batch


def test_plan_batches_evenly():
    files = [f"f{i}.md" for i in range(100)]
    batches = plan_batches(files, batch_size=25)
    assert len(batches) == 4
    assert all(len(b.files) == 25 for b in batches)


def test_plan_batches_trailing_remainder():
    files = [f"f{i}.md" for i in range(1698)]
    batches = plan_batches(files, batch_size=50)
    assert len(batches) == 34
    assert sum(len(b.files) for b in batches) == 1698
    assert len(batches[-1].files) == 48


def test_batch_ids_are_zero_padded_and_ordered():
    files = [f"f{i}.md" for i in range(5)]
    batches = plan_batches(files, batch_size=2)
    ids = [b.batch_id for b in batches]
    assert ids == ["b000", "b001", "b002"]


def test_empty_input_returns_empty_list():
    assert plan_batches([], batch_size=50) == []


def test_batch_size_must_be_positive():
    import pytest
    with pytest.raises(ValueError):
        plan_batches(["a"], batch_size=0)
