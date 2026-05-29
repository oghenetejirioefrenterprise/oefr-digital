import pytest
from unittest.mock import MagicMock

from scripts.lib.gumroad_publish import _normalize_permalink, login, GumroadError


def test_normalize_accepts_absolute_permalink():
    assert _normalize_permalink("https://gumroad.com/l/abc") == "https://gumroad.com/l/abc"


def test_normalize_promotes_relative_permalink():
    assert _normalize_permalink("/l/abc") == "https://gumroad.com/l/abc"


def test_normalize_rejects_edit_id_url():
    # The /products/<id>/edit token must NEVER be treated as a public permalink.
    assert _normalize_permalink("https://app.gumroad.com/products/xYz/edit") is None


def test_normalize_rejects_empty():
    assert _normalize_permalink(None) is None
    assert _normalize_permalink("") is None


def test_login_raises_on_blank_creds():
    with pytest.raises(GumroadError):
        login(MagicMock(), username="", password="x")


def test_login_fills_credentials_and_submits():
    page = MagicMock()
    page.url = "https://gumroad.com/dashboard"
    login(page, username="u@example.com", password="pw")
    page.fill.assert_any_call("input[type='email']", "u@example.com")
    page.fill.assert_any_call("input[type='password']", "pw")
    page.click.assert_called()
