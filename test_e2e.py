import pytest
from playwright.sync_api import Page

def test_landing_page_and_login_redirect(page: Page):

    # Start on landing
    page.goto("http://localhost:5000")
    assert page.text_content("h1") == "📁 My Google Drive App"
    assert page.is_visible("text=Sign in with Google")

    
    page.click("text=Sign in with Google")

    assert "accounts.google.com" in page.url

