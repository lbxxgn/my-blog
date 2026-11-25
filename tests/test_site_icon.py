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


def _png_bytes(size=512, color=(200, 30, 30, 255), box=None):
    """生成测试用 PNG；box 不为空时只填充指定矩形区域。"""
    img = Image.new('RGBA', (size, size), (255, 255, 255, 255) if box else color)
    if box:
        img.paste(color, box)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _half_split_png(size=512):
    """左半红、右半蓝的测试图，便于验证裁剪区域。"""
    img = Image.new('RGBA', (size, size), (220, 20, 20, 255))
    img.paste((20, 40, 220, 255), (size // 2, 0, size, size))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _square_png_bytes(size, color=(20, 40, 220, 255)):
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
        from backend.models import set_site_setting, get_site_setting, delete_site_setting

        assert get_site_setting('foo') is None
        assert get_site_setting('foo', 'bar') == 'bar'

        set_site_setting('foo', 'baz')
        assert get_site_setting('foo') == 'baz'

        set_site_setting('foo', 'qux')
        assert get_site_setting('foo') == 'qux'

        delete_site_setting('foo')
        assert get_site_setting('foo') is None

    def test_icon_version_default(self, temp_db):
        from backend.models import get_site_icon_version
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

    def test_manifest_has_icons(self, client):
        response = client.get('/site.webmanifest')
        assert response.status_code == 200
        assert response.headers['Content-Type'].startswith('application/manifest+json')
        data = response.get_json()
        assert any('192x192' in icon['sizes'] for icon in data['icons'])
        assert any('512x512' in icon['sizes'] for icon in data['icons'])
        assert any('/site-icon-192-' in icon['src'] for icon in data['icons'])

    def test_base_html_uses_dynamic_routes(self):
        base = (PROJECT_ROOT / 'templates' / 'base.html').read_text()
        assert "url_for('favicon')" in base
        assert "url_for('site_icon_versioned'" in base
        assert "url_for('site_webmanifest')" in base
        assert 'apple-mobile-web-app-title' in base

    def test_site_settings_page_has_crop_editor(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        response = client.get('/admin/site')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'iconCropStage' in html
        assert 'id="siteIconCrop"' in html
        assert 'admin-site-icon.js' in html


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

        from backend.models import get_site_icon_version
        assert get_site_icon_version() != '0'

        for name in ('icon-16.png', 'icon-32.png', 'icon-48.png',
                     'icon-180.png', 'icon-192.png', 'icon-512.png', 'favicon.ico'):
            assert (icon_dir / name).exists(), name

        img = Image.open(icon_dir / 'icon-512.png')
        assert img.size == (512, 512)

        # 原图会保留下来，供之后重新调整选区
        assert (icon_dir / 'source.img').exists()
        assert (icon_dir / 'source.img').read_bytes() == _png_bytes()

        # 上传后动态路由返回自定义图标
        served = client.get('/site-icon-192.png')
        assert served.status_code == 200
        assert served.data == (icon_dir / 'icon-192.png').read_bytes()

    def test_upload_uses_selected_crop_region(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        response = client.post(
            '/admin/site/icon',
            data={
                'icon': (io.BytesIO(_half_split_png()), 'logo.png'),
                # 只选右半边（蓝色）作为图标
                'cropped': (io.BytesIO(_square_png_bytes(256, (20, 40, 220, 255))), 'crop.png'),
                'crop': '{"x": 0.5, "y": 0, "w": 0.5, "h": 1}',
            },
            content_type='multipart/form-data',
        )
        assert response.status_code in (301, 302)

        icon = Image.open(icon_dir / 'icon-512.png').convert('RGB')
        assert icon.getpixel((256, 256)) == (20, 40, 220)

        from backend.models import get_site_setting
        assert get_site_setting('icon_crop') == '{"x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0}'

    def test_recrop_saved_source_without_new_upload(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        client.post(
            '/admin/site/icon',
            data={'icon': (io.BytesIO(_half_split_png()), 'logo.png')},
            content_type='multipart/form-data',
        )
        source_before = (icon_dir / 'source.img').read_bytes()

        # 不再上传原图，只提交新的裁剪结果（左半边红色）
        response = client.post(
            '/admin/site/icon',
            data={
                'cropped': (io.BytesIO(_square_png_bytes(256, (220, 20, 20, 255))), 'crop.png'),
                'crop': '{"x": 0, "y": 0, "w": 0.5, "h": 1}',
            },
            content_type='multipart/form-data',
        )
        assert response.status_code in (301, 302)

        icon = Image.open(icon_dir / 'icon-512.png').convert('RGB')
        assert icon.getpixel((256, 256)) == (220, 20, 20)
        # 原图保持不变
        assert (icon_dir / 'source.img').read_bytes() == source_before

    def test_invalid_crop_metadata_is_ignored(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        response = client.post(
            '/admin/site/icon',
            data={
                'icon': (io.BytesIO(_png_bytes()), 'logo.png'),
                'cropped': (io.BytesIO(_square_png_bytes(256)), 'crop.png'),
                'crop': 'not-json',
            },
            content_type='multipart/form-data',
        )
        assert response.status_code in (301, 302)
        assert (icon_dir / 'icon-512.png').exists()

        from backend.models import get_site_setting
        assert get_site_setting('icon_crop') is None

    def test_upload_rejects_tiny_crop(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        response = client.post(
            '/admin/site/icon',
            data={
                'icon': (io.BytesIO(_png_bytes()), 'logo.png'),
                'cropped': (io.BytesIO(_square_png_bytes(32)), 'crop.png'),
            },
            content_type='multipart/form-data',
        )
        assert response.status_code in (301, 302)
        assert not (icon_dir / 'icon-512.png').exists()
        # 校验失败时不应保存原图
        assert not (icon_dir / 'source.img').exists()

    def test_source_route_serves_saved_image(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        client.post(
            '/admin/site/icon',
            data={'icon': (io.BytesIO(_png_bytes()), 'logo.png')},
            content_type='multipart/form-data',
        )
        response = client.get('/admin/site/icon/source')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'image/png'
        assert response.headers['Cache-Control'] == 'no-store'
        assert response.data == _png_bytes()

    def test_source_route_404_without_source(self, client, test_admin_user, icon_dir):
        _login(client, test_admin_user)
        assert client.get('/admin/site/icon/source').status_code == 404

    def test_source_route_requires_admin(self, client, test_user, icon_dir):
        _login(client, test_user)
        response = client.get('/admin/site/icon/source')
        assert response.status_code in (301, 302)

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
        assert not (icon_dir / 'source.img').exists()

        from backend.models import get_site_setting
        assert get_site_setting('icon_crop') is None

        # 恢复默认后仍可访问（走 fallback）
        assert client.get('/apple-touch-icon.png').status_code == 200
