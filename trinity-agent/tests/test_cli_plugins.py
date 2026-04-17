"""Tests for the `trinity plugins` CLI surface."""
from __future__ import annotations

import subprocess
import sys


def _run(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "trinity", *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_plugins_list_without_group_shows_all_groups():
    rc, out, err = _run("plugins", "list")
    assert rc == 0, err
    # Section headings
    assert "providers" in out
    assert "tools" in out
    assert "agents" in out
    # Sample builtins from each group
    assert "claude_sdk" in out
    assert "read_file" in out
    assert "builder" in out


def test_plugins_list_with_group_filters():
    rc, out, err = _run("plugins", "list", "providers")
    assert rc == 0, err
    assert "claude_sdk" in out
    assert "openai" in out
    assert "read_file" not in out  # other groups excluded


def test_plugins_list_unknown_group_errors():
    rc, out, err = _run("plugins", "list", "bogus")
    assert rc != 0
    assert "unknown" in (out + err).lower() or "invalid" in (out + err).lower()


def test_plugins_show_provider():
    rc, out, err = _run("plugins", "show", "providers/claude_sdk")
    assert rc == 0, err
    assert "claude_sdk" in out
    assert "builtin" in out.lower()


def test_plugins_show_unknown_raises():
    rc, out, err = _run("plugins", "show", "providers/missing")
    assert rc != 0
