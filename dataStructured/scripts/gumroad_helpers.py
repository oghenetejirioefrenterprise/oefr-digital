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
