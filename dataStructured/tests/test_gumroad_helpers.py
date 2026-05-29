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


from scripts.gumroad_helpers import create_listing


def test_create_listing_fills_form_and_publishes():
    fake_page = MagicMock()
    fake_page.url = "https://gumroad.com/l/abc123"  # final URL after publish

    url = create_listing(
        fake_page,
        name="FL Permit Report",
        description="Florida permit history per address.",
        price_usd=27,
        asset_path="/tmp/asset.csv"
    )
    fake_page.goto.assert_any_call("https://gumroad.com/products/new")
    fake_page.fill.assert_any_call("input[name='name']", "FL Permit Report")
    fake_page.fill.assert_any_call("input[name='price']", "27")
    fake_page.set_input_files.assert_called_with("input[type='file']", "/tmp/asset.csv")
    assert url.startswith("https://gumroad.com/l/")
