"""Shared pytest fixtures for Trinity tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """A temporary workspace directory with a .trinity subdirectory."""
    trinity = tmp_path / ".trinity"
    trinity.mkdir()
    for sub in ("memory/short-term", "memory/long-term", "memory/permanent",
                "state", "logs", "employees", "knowledge", "sessions",
                "chat-history"):
        (trinity / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path
