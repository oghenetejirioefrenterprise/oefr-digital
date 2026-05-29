import json
import os
import threading
from pathlib import Path
import pytest

from scripts.lib.atomic_io import write_json_atomic, read_json


def test_write_then_read(tmp_path):
    path = tmp_path / "x.json"
    data = {"a": 1, "b": [1, 2, 3]}
    write_json_atomic(path, data)
    assert read_json(path) == data


def test_no_partial_visible_during_concurrent_write(tmp_path):
    """Writer half-writes; reader should never see a partial file."""
    path = tmp_path / "y.json"
    data = {"k": "v" * 1000}
    write_json_atomic(path, data)

    saw_partial = []
    stop = threading.Event()

    def writer():
        for _ in range(50):
            if stop.is_set():
                return
            write_json_atomic(path, data)

    def reader():
        for _ in range(200):
            if stop.is_set():
                return
            try:
                got = json.loads(path.read_text())
                assert got == data
            except (json.JSONDecodeError, FileNotFoundError) as e:
                saw_partial.append(str(e))

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    t1.start(); t2.start()
    t1.join(); t2.join()
    stop.set()

    assert not saw_partial, f"Saw partial writes: {saw_partial[:3]}"


def test_pretty_printed(tmp_path):
    path = tmp_path / "z.json"
    write_json_atomic(path, {"a": 1, "b": 2})
    text = path.read_text()
    assert '\n' in text  # pretty-printed has newlines
    assert '  ' in text  # 2-space indent
