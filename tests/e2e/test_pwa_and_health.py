"""端到端：健康检查、PWA manifest、Service Worker 与 404 页面。"""

import json

import pytest

pytestmark = pytest.mark.e2e


def test_health_and_readiness_endpoints(page):
    page.goto('/healthz')
    assert json.loads(page.eval('document.body.innerText'))['status'] == 'ok'

    page.goto('/readyz')
    assert json.loads(page.eval('document.body.innerText'))['status'] == 'ready'


def test_pwa_manifest(page):
    page.goto('/site.webmanifest')
    manifest = json.loads(page.eval('document.body.innerText'))
    assert manifest['start_url'] == '/'
    assert manifest['display'] == 'standalone'
    assert len(manifest['icons']) >= 2
    assert all(icon['src'].startswith('/site-icon-') for icon in manifest['icons'])


def test_service_worker_asset(page):
    page.goto('/')
    result = page.eval(
        """
        (async function() {
            const response = await fetch('/sw.js', { cache: 'no-store' });
            const text = await response.text();
            return {
                ok: response.ok,
                contentType: response.headers.get('content-type') || '',
                length: text.length,
                hasWorkerHook: text.includes('addEventListener')
            };
        })();
        """,
        await_promise=True,
    )
    assert result['ok'] is True
    assert 'javascript' in result['contentType']
    assert result['length'] > 0
    assert result['hasWorkerHook'] is True


def test_custom_404_page(page):
    page.goto('/definitely-not-a-real-page-e2e')
    page.wait_body_contains('404')
    assert '页面' in page.body_text() or '不存在' in page.body_text()
