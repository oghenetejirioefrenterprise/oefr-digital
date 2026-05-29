import threading
from pathlib import Path
import pytest

from scripts.lib.distribution_queue import append_item, read_queue


@pytest.fixture
def queue_path(tmp_path):
    return tmp_path / "queue.json"


def _item(slug):
    return {
        "id": f"{slug}-2026-05-04",
        "slug": slug,
        "name": f"Product {slug}",
        "stripe_payment_link_url": "https://buy.stripe.com/test",
        "price_usd": 27,
        "audience": "test",
        "added_at": "2026-05-04T00:00:00Z",
        "status": "ready"
    }


def test_append_to_new_file(queue_path):
    append_item(queue_path, _item("test-1"))
    q = read_queue(queue_path)
    assert len(q["items"]) == 1
    assert q["items"][0]["slug"] == "test-1"


def test_concurrent_appends_preserve_all_items(queue_path):
    """20 concurrent appends; every item must end up in the queue."""
    threads = []
    for i in range(20):
        t = threading.Thread(target=append_item, args=(queue_path, _item(f"item-{i}")))
        threads.append(t)
    for t in threads: t.start()
    for t in threads: t.join()
    q = read_queue(queue_path)
    assert len(q["items"]) == 20
    slugs = sorted(item["slug"] for item in q["items"])
    assert slugs == sorted(f"item-{i}" for i in range(20))


def test_invalid_item_raises(queue_path):
    with pytest.raises(Exception):  # schema validation error
        append_item(queue_path, {"slug": "bad"})  # missing required fields
