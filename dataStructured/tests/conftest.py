"""Pytest fixtures for DataStructured tests."""
import pytest
from pathlib import Path


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Provide a clean workspace dir with state/ skeleton."""
    for sub in ("opportunities", "datasets", "ethics-ledger", "products", "_schemas"):
        (tmp_path / "state" / sub).mkdir(parents=True)
    return tmp_path
