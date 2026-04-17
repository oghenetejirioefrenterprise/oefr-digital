"""Entry-point discovery helpers.

Isolated in its own module so tests can patch :func:`entry_points` cleanly.
"""
from __future__ import annotations

from importlib.metadata import entry_points


def scan(group: str) -> list:
    """Return the entry points registered under ``group``.

    Wraps the stdlib call so tests can monkeypatch a single symbol.
    """
    return list(entry_points(group=group))
