#!/usr/bin/env python3
"""Headless end-to-end smoke test for the BlockNote KB editor.

Uses Chrome DevTools Protocol (CDP) to:
1. Inject a logged-in Flask session cookie.
2. Navigate to /knowledge/doc/new.
3. Wait for the BlockNote editor to mount.
4. Type a title, select a category, and insert content into the editor.
5. Click the save button.
6. Assert the browser navigates to the newly created doc detail page.
7. (Optional extras) Verify autosave, image upload, and AI panel wiring.

Run with a Flask dev server already listening on http://127.0.0.1:5001.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websocket  # from websocket-client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ["TESTING"] = "1"

# Load the same .env configuration as the running Flask server so the
# signed session cookie we synthesize is valid.
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)

from backend.app import app  # noqa: E402
from backend.config import SECRET_KEY  # noqa: E402

PORT = 9222
USER_DATA_DIR = Path("/tmp/kb-e2e-chrome-profile")
CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE_URL = "http://127.0.0.1:5001"


def build_session_cookie() -> str:
    """Sign a Flask session cookie containing a logged-in user."""
    from flask.sessions import SecureCookieSessionInterface

    si = SecureCookieSessionInterface()
    serializer = si.get_signing_serializer(app)
    return serializer.dumps({"user_id": 1, "csrf_token": "e2e-test-csrf"})


def start_chrome() -> subprocess.Popen:
    if USER_DATA_DIR.exists():
        shutil.rmtree(USER_DATA_DIR)
    USER_DATA_DIR.mkdir(parents=True)
    cmd = [
        CHROME_BINARY,
        f"--remote-debugging-port={PORT}",
        "--remote-allow-origins=*",
        f"--user-data-dir={USER_DATA_DIR}",
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--window-size=1400,900",
        "about:blank",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_page_ws_url() -> str:
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list") as resp:
                targets = json.loads(resp.read().decode())
                for target in targets:
                    if target.get("type") == "page":
                        return target["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Chrome page target not ready")


class CDPClient:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self._msg_id = 0

    def send(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        payload = {"id": self._msg_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        return self._wait_for(self._msg_id)

    def _wait_for(self, msg_id: int) -> dict:
        while True:
            raw = self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == msg_id:
                return data

    def close(self):
        self.ws.close()


def wait_for_eval(cdp: CDPClient, expression: str, timeout: float = 20.0, interval: float = 0.5):
    """Repeatedly evaluate `expression` until it returns a truthy value."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = cdp.send("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        value = result.get("result", {}).get("result", {}).get("value")
        if value:
            return value
        time.sleep(interval)
    raise TimeoutError(f"Expression never truthy: {expression}")


def eval_async(cdp: CDPClient, expression: str) -> dict:
    """Evaluate an async JS expression and return its result."""
    return cdp.send(
        "Runtime.evaluate",
        {
            "expression": expression,
            "awaitPromise": True,
            "returnByValue": True,
        },
    )


def type_text(cdp: CDPClient, selector: str, text: str):
    """Type text into a focusable element using real keyboard events."""
    cdp.send(
        "Runtime.evaluate",
        {
            "expression": f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    el.focus();
                    el.select && el.select();
                    return !!el;
                }})();
            """,
            "returnByValue": True,
        },
    )
    for char in text:
        cdp.send("Input.dispatchKeyEvent", {"type": "keyDown", "text": char})
        cdp.send("Input.dispatchKeyEvent", {"type": "keyUp"})


def click_save_button(cdp: CDPClient):
    """Click the React save button via CDP mouse events."""

    rect = json.loads(
        cdp.send(
            "Runtime.evaluate",
            {
                "expression": """
                    (function() {
                        const btn = document.querySelector('button[type="button"].btn-primary');
                        if (!btn) throw new Error('Save button not found');
                        btn.scrollIntoView({ block: 'center', inline: 'center' });
                        const r = btn.getBoundingClientRect();
                        return JSON.stringify({ x: r.left + r.width/2, y: r.top + r.height/2 });
                    })();
                """,
                "returnByValue": True,
            },
        )["result"]["result"]["value"]
    )
    cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": rect["x"], "y": rect["y"], "button": "left", "clickCount": 1},
    )
    cdp.send(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": rect["x"], "y": rect["y"], "button": "left", "clickCount": 1},
    )


def verify_autosave(cdp: CDPClient, doc_id: str) -> None:
    """Navigate to the edit page, change content, and confirm a draft is saved."""
    print(f"Navigating to edit page for doc {doc_id} to verify autosave...")
    cdp.send("Page.navigate", {"url": f"{BASE_URL}/knowledge/doc/{doc_id}/edit"})
    wait_for_eval(
        cdp,
        f"location.pathname === '/knowledge/doc/{doc_id}/edit'",
        timeout=20,
    )
    wait_for_eval(cdp, "document.readyState === 'complete'", timeout=20)
    wait_for_eval(
        cdp,
        "!!document.querySelector('#kb-editor-root [contenteditable=\"true\"]')",
        timeout=20,
    )

    print("Triggering editor change for autosave...")
    eval_async(
        cdp,
        """
        (async function() {
            const editor = window.__KB_EDITOR_INSTANCE__;
            await editor.insertBlocks(
                [{ type: 'paragraph', content: ' autosave addition' }],
                editor.document[editor.document.length - 1],
                'after'
            );
            return 'changed';
        })();
        """,
    )

    # The autosave debounce is 3s; wait a little longer to be safe.
    time.sleep(4.5)

    draft = eval_async(
        cdp,
        f"""
        (async function() {{
            const res = await fetch('/knowledge/doc/{doc_id}/draft', {{
                headers: {{ 'Accept': 'application/json' }}
            }});
            return await res.json();
        }})();
        """,
    )
    result = draft.get("result", {}).get("result", {}).get("value", {})
    if not result.get("success") or not result.get("draft"):
        raise RuntimeError(f"Autosave did not produce a draft: {result}")
    print("✅ Autosave verified, draft saved at", result["draft"].get("saved_at"))


def verify_image_upload(cdp: CDPClient) -> dict:
    """Upload a small PNG via the editor upload endpoint and insert it into the doc."""
    print("Verifying image upload end-to-end...")

    result = eval_async(
        cdp,
        """
        (async function() {
            // Generate a small PNG blob using an offscreen canvas.
            const canvas = document.createElement('canvas');
            canvas.width = 20;
            canvas.height = 20;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#4285f4';
            ctx.fillRect(0, 0, 20, 20);
            const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
            const file = new File([blob], 'e2e-test.png', { type: 'image/png' });
            const formData = new FormData();
            formData.append('file', file);
            const csrf = window.__KB_EDITOR_INIT__.csrfToken;
            const res = await fetch(window.__KB_EDITOR_INIT__.uploadImageUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf },
                body: formData,
            });
            const text = await res.text();
            try { return { ok: res.ok, status: res.status, body: JSON.parse(text) }; }
            catch (e) { return { ok: res.ok, status: res.status, text: text.slice(0, 500) }; }
        })();
        """,
    )
    value = result.get("result", {}).get("result", {}).get("value", {})
    if not value.get("ok") or not value.get("body", {}).get("success") or not value.get("body", {}).get("url"):
        raise RuntimeError(f"Image upload failed: {value}")
    value = value["body"]
    image_url = value["url"]
    print("✅ Image uploaded to", image_url)

    eval_async(
        cdp,
        f"""
        (async function() {{
            const editor = window.__KB_EDITOR_INSTANCE__;
            await editor.insertBlocks(
                [{{ type: 'image', props: {{ url: '{image_url}', caption: 'E2E upload' }} }}],
                editor.document[editor.document.length - 1],
                'after'
            );
            return 'image-inserted';
        }})();
        """,
    )
    return value


def verify_ai_panel(cdp: CDPClient) -> None:
    """Open the AI side panel and confirm it renders without throwing."""
    print("Verifying AI panel wiring...")
    result = eval_async(
        cdp,
        """
        (function() {
            const tabs = document.querySelectorAll('.kb-editor-sidebar button');
            for (const tab of tabs) {
                if (tab.textContent.includes('AI')) {
                    tab.click();
                    return true;
                }
            }
            return false;
        })();
        """,
    )
    opened = result.get("result", {}).get("result", {}).get("value", False)
    if not opened:
        print("WARN: AI tab not found, skipping AI panel check")
        return
    time.sleep(0.5)
    panel_visible = cdp.send(
        "Runtime.evaluate",
        {
            "expression": "!!document.querySelector('.kb-ai-panel')",
            "returnByValue": True,
        },
    )
    visible = panel_visible.get("result", {}).get("result", {}).get("value", False)
    if not visible:
        raise RuntimeError("AI panel did not render after clicking the AI tab")
    print("✅ AI panel opens and renders")


def main() -> int:
    print("Building session cookie...")
    session_cookie = build_session_cookie()

    print("Starting Chrome...")
    chrome_proc = start_chrome()
    try:
        print("Connecting to CDP...")
        ws_url = get_page_ws_url()
        cdp = CDPClient(ws_url)

        cdp.send("Network.enable")
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        cdp.send("Input.enable")

        cdp.send(
            "Network.setCookie",
            {
                "name": "session",
                "value": session_cookie,
                "url": BASE_URL,
                "httpOnly": True,
                "sameSite": "Lax",
            },
        )

        print(f"Navigating to {BASE_URL}/knowledge/doc/new ...")
        cdp.send("Page.navigate", {"url": f"{BASE_URL}/knowledge/doc/new"})

        wait_for_eval(cdp, "document.readyState === 'complete'", timeout=20)
        print("Page loaded, waiting for editor to mount...")
        wait_for_eval(
            cdp,
            "!!document.querySelector('#kb-editor-root [contenteditable=\"true\"]')",
            timeout=20,
        )

        print("Filling form fields...")
        type_text(cdp, 'input[name="title"]', "E2E BlockNote Doc")
        cdp.send(
            "Runtime.evaluate",
            {
                "expression": """
                    (function() {
                        const select = document.querySelector('select[name="category_id"]');
                        if (select && select.options.length > 1) {
                            select.value = select.options[1].value;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            return select.value;
                        }
                        return '';
                    })();
                """,
                "returnByValue": True,
            },
        )

        print("Inserting BlockNote content...")
        cdp.send(
            "Runtime.evaluate",
            {
                "expression": """
                    (async function() {
                        const editor = window.__KB_EDITOR_INSTANCE__;
                        await editor.insertBlocks(
                            [{ type: 'paragraph', content: 'Hello from BlockNote E2E test.' }],
                            editor.document[editor.document.length - 1],
                            'after'
                        );
                        return 'inserted';
                    })();
                """,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        time.sleep(1)

        print("Clicking save button...")
        click_save_button(cdp)

        print("Waiting for save redirect...")
        wait_for_eval(
            cdp,
            "location.pathname.match(/^\\/knowledge\\/doc\\/\\d+/) !== null",
            timeout=15,
        )
        final_url = cdp.send(
            "Runtime.evaluate", {"expression": "location.href", "returnByValue": True}
        )
        print("Saved doc URL:", final_url["result"]["result"]["value"])

        # Extract the created doc id and run extra end-to-end checks.
        doc_id = cdp.send(
            "Runtime.evaluate",
            {
                "expression": "(location.pathname.match(/\\/knowledge\\/doc\\/(\\d+)/) || [])[1]",
                "returnByValue": True,
            },
        )["result"]["result"]["value"]
        if doc_id:
            verify_autosave(cdp, doc_id)
            uploaded = verify_image_upload(cdp)
            verify_ai_panel(cdp)
        else:
            print("WARN: could not extract doc id, skipping extras")

        cdp.close()
        print("\n✅ KB editor E2E smoke test passed")
        return 0
    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome_proc.kill()


if __name__ == "__main__":
    sys.exit(main())
