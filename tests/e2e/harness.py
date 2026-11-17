"""Minimal Chrome DevTools Protocol helpers used by the E2E tests.

Only the small subset of CDP needed for browser-level assertions is wrapped
here: navigation, evaluating JS, filling fields and clicking elements.
"""

import json
import time

import websocket


class CDPClient:
    def __init__(self, ws_url: str, timeout: float = 30):
        self.ws = websocket.create_connection(ws_url, timeout=timeout)
        self._msg_id = 0

    def send(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        payload = {'id': self._msg_id, 'method': method, 'params': params or {}}
        self.ws.send(json.dumps(payload))
        while True:
            data = json.loads(self.ws.recv())
            if data.get('id') == self._msg_id:
                if 'error' in data:
                    raise RuntimeError(f"CDP {method} failed: {data['error']}")
                return data

    def close(self):
        self.ws.close()


class Page:
    def __init__(self, cdp: CDPClient, base_url: str):
        self.cdp = cdp
        self.base_url = base_url.rstrip('/')

    # ------------------------------------------------------------------ eval
    def eval(self, expression: str, await_promise: bool = False):
        result = self.cdp.send(
            'Runtime.evaluate',
            {
                'expression': expression,
                'returnByValue': True,
                'awaitPromise': await_promise,
            },
        )
        payload = result.get('result', {})
        if payload.get('exceptionDetails'):
            detail = payload['exceptionDetails']
            text = detail.get('exception', {}).get('description') or detail.get('text') or str(detail)
            raise AssertionError(f'JavaScript error: {text}')
        return payload.get('result', {}).get('value')

    # ------------------------------------------------------------ navigation
    def goto(self, path: str, expect: str | None = None, timeout: float = 20):
        url = path if path.startswith('http') else f'{self.base_url}{path}'
        self.cdp.send('Page.navigate', {'url': url})
        if expect is None:
            target = url
        elif expect.startswith('http'):
            target = expect
        else:
            target = f'{self.base_url}{expect}'
        self.wait_for(
            f"document.readyState === 'complete' && location.href.indexOf({json.dumps(target)}) === 0",
            timeout=timeout,
        )

    def path(self) -> str:
        return self.eval('location.pathname')

    def wait_path(self, prefix: str, timeout: float = 20):
        return self.wait_for(
            f"location.pathname.indexOf({json.dumps(prefix)}) === 0",
            timeout=timeout,
        )

    def wait_for(self, expression: str, timeout: float = 20, interval: float = 0.15):
        deadline = time.time() + timeout
        last_error = None
        while time.time() < deadline:
            try:
                value = self.eval(expression)
            except Exception as exc:  # page may still be loading/navigating
                last_error = exc
                value = None
            if value:
                return value
            time.sleep(interval)
        suffix = f' (last error: {last_error})' if last_error else ''
        raise TimeoutError(f'Condition never became truthy: {expression}{suffix}')

    def wait_for_async(self, expression: str, timeout: float = 20, interval: float = 0.2):
        deadline = time.time() + timeout
        last_error = None
        while time.time() < deadline:
            try:
                value = self.eval(expression, await_promise=True)
            except Exception as exc:
                last_error = exc
                value = None
            if value:
                return value
            time.sleep(interval)
        suffix = f' (last error: {last_error})' if last_error else ''
        raise TimeoutError(f'Async condition never became truthy: {expression}{suffix}')

    # ---------------------------------------------------------- interactions
    def exists(self, selector: str) -> bool:
        return bool(self.eval(f'!!document.querySelector({json.dumps(selector)})'))

    def count(self, selector: str) -> int:
        return int(self.eval(f'document.querySelectorAll({json.dumps(selector)}).length') or 0)

    def set_value(self, selector: str, value: str):
        script = (
            '(function() {'
            f'const el = document.querySelector({json.dumps(selector)});'
            'if (!el) return false;'
            'el.focus();'
            'const proto = el instanceof HTMLSelectElement'
            '    ? HTMLSelectElement.prototype'
            '    : (el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype);'
            'const setter = Object.getOwnPropertyDescriptor(proto, "value").set;'
            f'setter.call(el, {json.dumps(value)});'
            "el.dispatchEvent(new Event('input', { bubbles: true }));"
            "el.dispatchEvent(new Event('change', { bubbles: true }));"
            'return true;'
            '})()'
        )
        if not self.eval(script):
            raise AssertionError(f'Input not found: {selector}')

    def select_value(self, selector: str, value: str):
        self.set_value(selector, value)

    def click(self, selector: str):
        script = (
            '(function() {'
            f'const el = document.querySelector({json.dumps(selector)});'
            'if (!el) return false;'
            "el.scrollIntoView({ block: 'center', inline: 'center' });"
            'el.click();'
            'return true;'
            '})()'
        )
        if not self.eval(script):
            raise AssertionError(f'Clickable element not found: {selector}')

    def click_by_text(self, selector: str, text: str, last: bool = False):
        script = (
            '(function() {'
            f'const items = Array.from(document.querySelectorAll({json.dumps(selector)}));'
            f'const matches = items.filter((el) => (el.textContent || "").trim() === {json.dumps(text)});'
            'if (!matches.length) return false;'
            f'const el = matches[{"matches.length - 1" if last else "0"}];'
            "el.scrollIntoView({ block: 'center', inline: 'center' });"
            'el.click();'
            'return true;'
            '})()'
        )
        if not self.eval(script):
            raise AssertionError(f'Element with text {text!r} not found for {selector}')

    def click_in_row(self, row_contains: str, button_text: str):
        script = (
            '(function() {'
            f'const needle = {json.dumps(row_contains)};'
            f'const label = {json.dumps(button_text)};'
            "const rows = Array.from(document.querySelectorAll('tr'));"
            'const row = rows.find((item) => (item.innerText || "").includes(needle));'
            'if (!row) return false;'
            "const buttons = Array.from(row.querySelectorAll('button, a'));"
            'const target = buttons.find((item) => (item.textContent || "").trim() === label);'
            'if (!target) return false;'
            "target.scrollIntoView({ block: 'center', inline: 'center' });"
            'target.click();'
            'return true;'
            '})()'
        )
        if not self.eval(script):
            raise AssertionError(f'Row button {button_text!r} not found for row containing {row_contains!r}')

    def row_text(self, row_contains: str) -> str:
        script = (
            '(function() {'
            f'const needle = {json.dumps(row_contains)};'
            "const rows = Array.from(document.querySelectorAll('tr'));"
            'const row = rows.find((item) => (item.innerText || "").includes(needle));'
            'return row ? row.innerText : "";'
            '})()'
        )
        return self.eval(script) or ''

    def body_text(self) -> str:
        return self.eval('document.body ? document.body.innerText : ""') or ''

    def wait_body_contains(self, needle: str, timeout: float = 20):
        return self.wait_for(
            f'document.body && document.body.innerText.includes({json.dumps(needle)})',
            timeout=timeout,
        )

    def wait_body_missing(self, needle: str, timeout: float = 20):
        return self.wait_for(
            f'document.body && !document.body.innerText.includes({json.dumps(needle)})',
            timeout=timeout,
        )

    # ----------------------------------------------------------------- fetch
    def fetch_text(self, path: str) -> str:
        script = (
            '(async function() {'
            'try {'
            f'const response = await fetch({json.dumps(path)}, {{ cache: "no-store" }});'
            'return await response.text();'
            '} catch (error) {'
            'return "";'
            '}'
            '})()'
        )
        return self.eval(script, await_promise=True) or ''

    def wait_fetch_contains(self, path: str, needle: str, timeout: float = 20):
        script = (
            '(async function() {'
            'try {'
            f'const response = await fetch({json.dumps(path)}, {{ cache: "no-store" }});'
            'const text = await response.text();'
            f'return text.includes({json.dumps(needle)});'
            '} catch (error) {'
            'return false;'
            '}'
            '})()'
        )
        return self.wait_for_async(script, timeout=timeout)

    def fetch_json(self, path: str, method: str = 'GET', payload: dict | None = None):
        options = {'method': method, 'credentials': 'same-origin', 'cache': 'no-store'}
        headers = {'Accept': 'application/json'}
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            options['body'] = payload
        script = (
            '(async function() {'
            'const headers = ' + json.dumps(headers) + ';'
            'const token = document.querySelector(\'meta[name="csrf_token"]\');'
            'if (token && token.content) headers["X-CSRFToken"] = token.content;'
            'const options = ' + json.dumps(options) + ';'
            'options.headers = headers;'
            'if (options.body && typeof options.body === "object") options.body = JSON.stringify(options.body);'
            f'const response = await fetch({json.dumps(path)}, options);'
            'const text = await response.text();'
            'let data = null;'
            'try { data = JSON.parse(text); } catch (error) { data = text; }'
            'return { ok: response.ok, status: response.status, data: data };'
            '})()'
        )
        return self.eval(script, await_promise=True)


def login(page: Page, username: str, password: str):
    """Log in through the real login form and wait for the admin dashboard."""
    page.goto('/login')
    page.wait_for("!!document.querySelector('#username')")
    page.set_value('#username', username)
    page.set_value('#password', password)
    page.click('.login-form button[type="submit"]')
    try:
        page.wait_path('/admin')
    except TimeoutError as exc:
        raise AssertionError(
            f'Login did not reach /admin (current path {page.path()!r}): {page.body_text()[:800]}'
        ) from exc
    page.wait_for("document.readyState === 'complete'")
