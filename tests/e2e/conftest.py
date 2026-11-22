"""Fixtures for browser-based E2E tests.

These tests are opt-in. Run them with::

    E2E=1 pytest tests/e2e -v

They start an isolated Flask server (temporary SQLite database, seeded admin
user/content) and drive a headless Chrome instance over CDP. The regular test
suite continues to run without Chrome because all tests here are skipped
unless ``E2E=1`` is set.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

from .harness import CDPClient, Page

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROME_CANDIDATES = [
    os.environ.get('E2E_CHROME_BIN'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    shutil.which('google-chrome'),
    shutil.which('google-chrome-stable'),
    shutil.which('chromium'),
    shutil.which('chromium-browser'),
]


def pytest_collection_modifyitems(config, items):
    if os.environ.get('E2E') == '1':
        return
    skip_marker = pytest.mark.skip(reason='E2E tests are opt-in: set E2E=1 to run them')
    for item in items:
        if item.get_closest_marker('e2e'):
            item.add_marker(skip_marker)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def _wait_for_server(base_url: str, proc: subprocess.Popen, timeout: float = 40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f'E2E server exited early with code {proc.returncode}')
        if _http_ok(f'{base_url}/healthz') and _http_ok(f'{base_url}/readyz'):
            return
        time.sleep(0.2)
    raise TimeoutError(f'E2E server did not become ready at {base_url}')


def _chrome_binary() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _get_page_ws_url(debug_port: int, timeout: float = 20) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{debug_port}/json/list', timeout=1) as resp:
                targets = json.loads(resp.read().decode())
            for target in targets:
                if target.get('type') == 'page' and target.get('webSocketDebuggerUrl'):
                    return target['webSocketDebuggerUrl']
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError('Chrome page target not ready')


@pytest.fixture(scope='session')
def e2e_server():
    if os.environ.get('E2E') != '1':
        pytest.skip('E2E tests are opt-in: set E2E=1 to run them')

    tmpdir = Path(tempfile.mkdtemp(prefix='simple-blog-e2e-'))
    db_path = tmpdir / 'e2e.db'
    seed_path = tmpdir / 'seed.json'
    log_path = tmpdir / 'server.log'
    port = _free_port()
    base_url = f'http://127.0.0.1:{port}'

    env = os.environ.copy()
    env.update({
        'TESTING': '1',
        'DATABASE_URL': f'sqlite:///{db_path}',
        'SECRET_KEY': 'e2e-secret-key-not-for-production',
        'SITE_NAME': 'E2E 博客',
        'SITE_DESCRIPTION': '端到端测试站点',
        'SITE_AUTHOR': 'E2E',
        'BACKUP_SCHEDULE_ENABLED': 'False',
        'FLASK_ENV': 'development',
        'FORCE_HTTPS': 'False',
        'PYTHONUNBUFFERED': '1',
    })

    log_file = log_path.open('w', encoding='utf-8')
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).with_name('_server.py')),
            '--db', str(db_path),
            '--seed-out', str(seed_path),
            '--port', str(port),
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_for_server(base_url, proc)
        seed = json.loads(seed_path.read_text(encoding='utf-8'))
        yield {
            'base_url': base_url,
            'seed': seed,
            'tmpdir': tmpdir,
            'proc': proc,
            'log_path': log_path,
            'frontend_built': (PROJECT_ROOT / 'static/frontend/.vite/manifest.json').exists(),
        }
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.flush()
        tail = log_path.read_text(encoding='utf-8', errors='replace')[-4000:]
        if tail:
            print('\n--- E2E server log tail ---\n' + tail)
        raise
    finally:
        log_file.close()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope='session')
def e2e_browser(e2e_server):
    chrome_binary = _chrome_binary()
    if not chrome_binary:
        pytest.skip('Chrome/Chromium not found; set E2E_CHROME_BIN to enable E2E tests')

    profile_dir = e2e_server['tmpdir'] / 'chrome-profile'
    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    profile_dir.mkdir(parents=True)

    debug_port = _free_port()
    chrome_proc = subprocess.Popen(
        [
            chrome_binary,
            f'--remote-debugging-port={debug_port}',
            '--remote-allow-origins=*',
            f'--user-data-dir={profile_dir}',
            '--headless=new',
            '--no-sandbox',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-background-networking',
            '--window-size=1400,1000',
            'about:blank',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    cdp = None
    try:
        ws_url = _get_page_ws_url(debug_port)
        cdp = CDPClient(ws_url)
        for domain in ('Page.enable', 'Runtime.enable', 'Network.enable'):
            cdp.send(domain)
        cdp.send(
            'Page.addScriptToEvaluateOnNewDocument',
            {'source': 'window.confirm = () => true; window.alert = () => {}; window.prompt = () => null; window.__KB_E2E__ = true;'},
        )
        yield cdp
    finally:
        if cdp is not None:
            try:
                cdp.close()
            except Exception:
                pass
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome_proc.kill()


@pytest.fixture
def page(e2e_server, e2e_browser):
    current = Page(e2e_browser, e2e_server['base_url'])
    e2e_browser.send('Network.clearBrowserCookies')
    try:
        e2e_browser.send(
            'Storage.clearDataForOrigin',
            {'origin': e2e_server['base_url'], 'storageTypes': 'all'},
        )
    except Exception:
        pass
    current.goto('/')
    return current


@pytest.fixture
def seed(e2e_server):
    return e2e_server['seed']


@pytest.fixture
def frontend_built(e2e_server):
    return e2e_server['frontend_built']
