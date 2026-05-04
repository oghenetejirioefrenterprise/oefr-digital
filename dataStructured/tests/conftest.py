"""Pytest fixtures for DataStructured tests."""
import os
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _stripe_dummy_key(monkeypatch):
    """Provide a non-empty placeholder key for unit tests.

    Mocked tests in `test_stripe_helpers.py` patch `stripe.Product.create` etc.
    but the helpers' `_ensure_key()` still runs and requires `STRIPE_SECRET_KEY`
    to be set. We use a value that does NOT start with `sk_test_` so the
    integration smoke test in `tests/integration/test_stripe_e2e.py` remains
    correctly skipped unless a real test-mode key is exported by the operator.
    """
    if not os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test_"):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "dummy_unit_test_key_not_real")


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Provide a clean workspace dir with state/ skeleton."""
    for sub in ("opportunities", "datasets", "ethics-ledger", "products", "_schemas"):
        (tmp_path / "state" / sub).mkdir(parents=True)
    return tmp_path
