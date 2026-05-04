"""Gumroad Playwright automation — login + create listing.

Browser-only. The Gumroad write API is deprecated.
"""
import os
from playwright.sync_api import Page, sync_playwright


def login(page: Page, username: str, password: str) -> None:
    """Log in to Gumroad. Raises ValueError on missing creds."""
    if not username or not password:
        raise ValueError("Gumroad username and password are required")
    page.goto("https://gumroad.com/login")
    page.fill("input[name='user[login]']", username)
    page.fill("input[name='user[password]']", password)
    page.click("button[type='submit']")
    page.wait_for_url("https://gumroad.com/dashboard", timeout=30000)


def create_listing(
    page: Page,
    name: str,
    description: str,
    price_usd: int,
    asset_path: str,
) -> str:
    """Create a Gumroad listing via Playwright. Returns the public listing URL."""
    page.goto("https://gumroad.com/products/new")
    page.fill("input[name='name']", name)
    page.fill("textarea[name='description']", description)
    page.fill("input[name='price']", str(price_usd))
    page.set_input_files("input[type='file']", asset_path)
    page.click("button[type='submit']")
    page.wait_for_url("https://gumroad.com/l/*", timeout=60000)
    return page.url
