"""Real Chromium UI smoke test; optional Playwright test dependency.

Run from the repository root: python tests/browser_smoke.py
Uses only synthetic local data. No model runner, account or network required.
"""
from __future__ import annotations

import tempfile
import threading
from pathlib import Path
import shutil

from jarvis.config import ModelTarget, Settings
from jarvis.server import JarvisServer


def main() -> None:
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as temp:
        settings = Settings(Path(temp), "unused", ModelTarget("127.0.0.1", 1, "/v1/chat/completions"), 0)
        with JarvisServer(("127.0.0.1", 0), settings) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as pw:
                    executable = (shutil.which("chromium") or shutil.which("chromium-browser")
                                  or shutil.which("google-chrome"))
                    options = {"executable_path": executable} if executable else {}
                    browser = pw.chromium.launch(headless=True, **options)
                    try:
                        page = browser.new_page(viewport={"width": 1180, "height": 850})
                        page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
                        page.locator('#setup-form input[name="setup_code"]').fill(server.setup_token)
                        page.locator('#setup-form input[name="username"]').fill("admin")
                        page.locator('#setup-form input[name="password"]').fill("safe-test-password-123")
                        page.get_by_role("button", name="Create administrator").click()
                        page.locator('#login-form input[name="username"]').fill("admin")
                        page.locator('#login-form input[name="password"]').fill("safe-test-password-123")
                        page.get_by_role("button", name="Sign in", exact=True).click()
                        page.locator('#note-text').fill("Synthetic local note for approval test")
                        page.get_by_role("button", name="Preview action").click()
                        page.locator('#action-queue').get_by_text("Synthetic local note for approval test").wait_for()
                        assert page.locator('#notes').get_by_text('No saved notes.').is_visible()
                        page.get_by_role("button", name="Pause actions").click()
                        page.get_by_role("button", name="Approve & save").click()
                        page.locator('#status').get_by_text('Actions are paused').wait_for()
                        assert page.locator('#notes').get_by_text('No saved notes.').is_visible()
                        page.get_by_role("button", name="Resume actions").click()
                        page.get_by_role("button", name="Approve & save").click()
                        page.locator('#notes').get_by_text('Synthetic local note for approval test').wait_for()
                        page.get_by_role("button", name="Undo save").click()
                        page.locator('#notes').get_by_text('No saved notes.').wait_for()
                        page.get_by_role("button", name="Sign out").click()
                        page.get_by_role("heading", name="Sign in to Jarvis").wait_for()
                        assert page.locator('#assistant').is_hidden()
                        print("PASS: real Chromium first-run, login, preview, pause, approval, undo, logout")
                    finally:
                        browser.close()
            finally:
                server.shutdown()
                thread.join(timeout=3)


if __name__ == "__main__":
    main()
