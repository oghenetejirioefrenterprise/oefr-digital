import pytest
from unittest.mock import MagicMock, patch
from scripts.gumroad_helpers import login


def test_login_calls_fill_with_credentials():
    fake_page = MagicMock()
    with patch("scripts.gumroad_helpers.sync_playwright"):
        login(fake_page, username="user@example.com", password="hunter2")
    fake_page.goto.assert_called_with("https://gumroad.com/login")
    fake_page.fill.assert_any_call("input[name='user[login]']", "user@example.com")
    fake_page.fill.assert_any_call("input[name='user[password]']", "hunter2")
    fake_page.click.assert_called()


def test_login_raises_if_blank_creds():
    fake_page = MagicMock()
    with pytest.raises(ValueError):
        login(fake_page, username="", password="x")
