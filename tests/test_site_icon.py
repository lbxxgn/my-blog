"""站点图标（后台上传自定义 favicon / iOS 主屏 / PWA 图标）测试"""

import io
from pathlib import Path

import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _login(client, user):
    client.post('/login', data={
        'username': user['username'],
        'password': user['password'],
    })


def _png_bytes(size=512, color=(200, 30, 30, 255)):
    buf = io.BytesIO()
    Image.new('RGBA', (size, size), color).save(buf, format='PNG')
    return buf.getvalue()


@pytest.fixture
def icon_dir(tmp_path, monkeypatch):
    """把图标输出目录重定向到临时目录，避免污染仓库。"""
    import backend.utils.site_icon as site_icon

    monkeypatch.setattr(site_icon, 'UPLOAD_FOLDER', tmp_path)
    return tmp_path / 'site'


class TestSiteSettingsModel:
    def test_set_get_delete(self, temp_db):
        from models import set_site_setting, get_site_setting, delete_site_setting

        assert get_site_setting('foo') is None
        assert get_site_setting('foo', 'bar') == 'bar'

        set_site_setting('foo', 'baz')
        assert get_site_setting('foo') == 'baz'

        set_site_setting('foo', 'qux')
        assert get_site_setting('foo') == 'qux'

        delete_site_setting('foo')
        assert get_site_setting('foo') is None

    def test_icon_version_default(self, temp_db):
        from models import get_site_icon_version
        assert get_site_icon_version() == '0'


class TestSiteIconRoutes:
    def test_fallback_icons_available(self, client):
        for path in ('/favicon.ico', '/favicon-32.png', '/site-icon-48.png',
                     '/apple-touch-icon.png', '/apple-touch-icon-precomposed.png',
                     '/site-icon-192.png', '/site-icon-512.png'):
            response = client.get(path)
            assert response.status_code == 200, path
            assert response.data, path

    def test_versioned_icon_routes(self, client):
        # 版本化路径可用于绕开 iOS 图标缓存
        response = client.get('/site-icon-180-0.png')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'image/png'

        # 未知尺寸 404
        assert client.get('/site-icon-999-0.png').status_code == 404

    def test_apple_touch_icon_is_no_cache(self, client):
        response = client.get('/apple-touch-icon.png')
        assert response.headers['Cache-Control'] == 'no-cache'

    def test_manifest_has_share_target_and_icons(self, client):
        response = client.get('/site.webmanifest')
        assert response.status_code == 200
        assert response.headers['Content-Type'].startswith('application/manifest+json')
        data = response.get_json()
        assert data['share_target']['action'] == '/quick-capture'
        assert any('192x192' in icon['sizes'] for icon in data['icons'])
        assert any('512x512' in icon['sizes'] for icon in data['icons'])
        assert any('/site-icon-192-' in icon['src'] for icon in data['icons'])

    def test_base_html_uses_dynamic_routes(self):
        base = (PROJECT_ROOT / 'templates' / 'base.html').read_text()
        assert "url_for('favicon')" in base
        assert "url_for('site_icon_versioned'" in base
        assert "url_for('site_webmanifest')" in base
        assert 'apple-mobile-web-app-title' in base


class TestSiteIconAdmin:
    def test_site_page_requires_admin(self, client, test_user, icon_dir):
        _login(client, test_user)
        response = client.get('/admin/site')
        assert response.status_code in (301, 302)

    def test_admin_upload_generates_icons(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)

        response = client.post(
            '/admin/site/icon',
            data={'icon': (io.BytesIO(_png_bytes()), 'logo.png')},
            content_type='multipart/form-data',
        )
        assert response.status_code in (301, 302)

        from models import get_site_icon_version
        assert get_site_icon_version() != '0'

        for name in ('icon-16.png', 'icon-32.png', 'icon-48.png',
                     'icon-180.png', 'icon-192.png', 'icon-512.png', 'favicon.ico'):
            assert (icon_dir / name).exists(), name

        img = Image.open(icon_dir / 'icon-512.png')
        assert img.size == (512, 512)

        # 上传后动态路由返回自定义图标
        served = client.get('/site-icon-192.png')
        assert served.status_code == 200
        assert served.data == (icon_dir / 'icon-192.png').read_bytes()

    def test_upload_rejects_tiny_image(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        response = client.post(
            '/admin/site/icon',
            data={'icon': (io.BytesIO(_png_bytes(size=32)), 'tiny.png')},
            content_type='multipart/form-data',
        )
        assert response.status_code in (301, 302)
        assert not (icon_dir / 'icon-512.png').exists()

    def test_upload_rejects_non_image_extension(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        response = client.post(
            '/admin/site/icon',
            data={'icon': (io.BytesIO(b'not an image'), 'evil.txt')},
            content_type='multipart/form-data',
        )
        assert response.status_code in (301, 302)
        assert not (icon_dir / 'icon-512.png').exists()

    def test_reset_restores_default(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        client.post(
            '/admin/site/icon',
            data={'icon': (io.BytesIO(_png_bytes()), 'logo.png')},
            content_type='multipart/form-data',
        )
        assert (icon_dir / 'icon-512.png').exists()

        response = client.post('/admin/site/icon/reset')
        assert response.status_code in (301, 302)
        assert not (icon_dir / 'icon-512.png').exists()

        # 恢复默认后仍可访问（走 fallback）
        assert client.get('/apple-touch-icon.png').status_code == 200
