"""Tests for ``@``-prefixed inline references."""
from __future__ import annotations

import subprocess
from pathlib import Path

from trinity.context.references import expand_references


def _make_workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello():\n    return 42\n")
    (tmp_path / "src" / "deep").mkdir()
    (tmp_path / "src" / "deep" / "nested.txt").write_text("deeply nested content")
    (tmp_path / "secrets.txt").write_text("would be redacted by tag")
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "id_rsa").write_text("super secret")
    return tmp_path


def test_no_references_passthrough(tmp_path):
    out = expand_references("hello world", tmp_path)
    assert out == "hello world"


def test_file_reference_expanded(tmp_path):
    ws = _make_workspace(tmp_path)
    out = expand_references("look at @file:src/main.py", ws)
    assert "def hello()" in out
    assert "@file:src/main.py" in out  # original preserved
    assert "# Inline references" in out


def test_sensitive_path_redacted(tmp_path):
    ws = _make_workspace(tmp_path)
    out = expand_references("@file:.ssh/id_rsa", ws)
    assert "super secret" not in out
    assert "[redacted: sensitive path]" in out


def test_path_traversal_blocked(tmp_path):
    ws = _make_workspace(tmp_path)
    out = expand_references("@file:../escape.py", ws)
    assert "[not found or outside workspace]" in out


def test_folder_listing(tmp_path):
    ws = _make_workspace(tmp_path)
    out = expand_references("@folder:src", ws)
    assert "main.py" in out
    assert "deep" in out


def test_diff_via_git(tmp_path):
    ws = _make_workspace(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=ws, check=True)
    subprocess.run(["git", "add", "."], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=ws, check=True)
    (ws / "src" / "main.py").write_text("def hello():\n    return 99\n")
    out = expand_references("@diff", ws)
    assert "99" in out


def test_dedupe_same_reference(tmp_path):
    ws = _make_workspace(tmp_path)
    out = expand_references("@file:src/main.py and again @file:src/main.py", ws)
    # Should appear once in the appended section
    assert out.count("def hello()") == 1


def test_multiple_kinds_in_one_message(tmp_path):
    ws = _make_workspace(tmp_path)
    out = expand_references("@file:src/main.py and @folder:src", ws)
    assert "def hello()" in out
    assert "main.py" in out  # listed by folder
