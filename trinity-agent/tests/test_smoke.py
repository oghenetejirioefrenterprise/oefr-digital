"""Sanity check: the trinity package imports and the test runner works."""
from __future__ import annotations


def test_trinity_imports():
    import trinity
    assert trinity is not None


def test_tmp_workspace_fixture(tmp_workspace):
    assert (tmp_workspace / ".trinity" / "memory").is_dir()
