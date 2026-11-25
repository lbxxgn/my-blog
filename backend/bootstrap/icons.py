"""站点图标与 PWA manifest 路由。

优先返回后台上传的自定义图标，否则回退到仓库默认图标。
iOS 在解析不到 <link> 时也会自动探测根路径的 /apple-touch-icon.png、/favicon.ico。
"""

from flask import abort, jsonify, send_file

from backend.config import SITE_AUTHOR, SITE_DESCRIPTION, SITE_NAME
from backend.models import get_site_icon_version, get_site_identity
from backend.utils.site_icon import site_icon_dir

__all__ = ['register_site_icon_routes']

# 7 天；版本化文件名用于自定义图标后的即时更新
_ICON_CACHE_MAX_AGE = 604800

# 可版本化访问的尺寸 -> 仓库默认图标（无自定义时回退）
_VERSIONED_ICON_FALLBACKS = {
    16: 'icons/icon-16.png',
    32: 'icons/icon-32.png',
    48: 'icons/icon-48.png',
    180: 'apple-touch-icon.png',
    192: 'icons/icon-192.png',
    512: 'icons/icon-512.png',
}


def register_site_icon_routes(app):
    """注册 favicon / apple-touch-icon / 版本化图标与 site.webmanifest。"""

    def _serve_site_icon(custom_name, fallback_static, mimetype, cache_seconds=_ICON_CACHE_MAX_AGE):
        custom = site_icon_dir() / custom_name
        if custom.exists():
            response = send_file(str(custom), mimetype=mimetype)
        else:
            response = app.send_static_file(fallback_static)
            response.headers['Content-Type'] = mimetype

        if cache_seconds:
            response.headers['Cache-Control'] = f'public, max-age={cache_seconds}'
        else:
            # iOS 主屏图标缓存极顽固，探测路径保持可重新校验
            response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.route('/favicon.ico')
    def favicon():
        return _serve_site_icon('favicon.ico', 'icons/favicon.ico', 'image/x-icon')

    @app.route('/favicon-16.png')
    def favicon_16():
        return _serve_site_icon('icon-16.png', 'icons/icon-16.png', 'image/png')

    @app.route('/favicon-32.png')
    def favicon_32():
        return _serve_site_icon('icon-32.png', 'icons/icon-32.png', 'image/png')

    @app.route('/site-icon-48.png')
    def site_icon_48():
        return _serve_site_icon('icon-48.png', 'icons/icon-48.png', 'image/png')

    # iOS 主屏图标（含旧版 precomposed 兜底）；探测路径用 no-cache
    @app.route('/apple-touch-icon-precomposed.png')
    @app.route('/apple-touch-icon.png')
    def apple_touch_icon():
        return _serve_site_icon('icon-180.png', 'apple-touch-icon.png', 'image/png', cache_seconds=0)

    @app.route('/site-icon-192.png')
    def site_icon_192():
        return _serve_site_icon('icon-192.png', 'icons/icon-192.png', 'image/png')

    @app.route('/site-icon-512.png')
    def site_icon_512():
        return _serve_site_icon('icon-512.png', 'icons/icon-512.png', 'image/png')

    @app.route('/site-icon-<int:size>-<int:version>.png')
    def site_icon_versioned(size, version):
        """版本化图标路径：文件名随版本变化，绕开 iOS 的图标缓存。"""
        fallback = _VERSIONED_ICON_FALLBACKS.get(size)
        if not fallback:
            abort(404)
        return _serve_site_icon(f'icon-{size}.png', fallback, 'image/png')

    @app.route('/site.webmanifest')
    def site_webmanifest():
        """动态 manifest：图标 URL 带版本号，自定义图标后 PWA 能及时拿到新图标。"""
        version = get_site_icon_version()
        identity = get_site_identity({
            'site_name': SITE_NAME,
            'site_description': SITE_DESCRIPTION,
            'site_author': SITE_AUTHOR,
        })
        manifest_name = identity.get('site_name') or SITE_NAME
        manifest = {
            'name': manifest_name,
            'short_name': manifest_name,
            'start_url': '/',
            'display': 'standalone',
            'background_color': '#ffffff',
            'theme_color': '#ffffff',
            'icons': [
                {'src': f'/site-icon-192-{version}.png', 'sizes': '192x192', 'type': 'image/png'},
                {'src': f'/site-icon-512-{version}.png', 'sizes': '512x512', 'type': 'image/png'},
            ],
        }
        response = jsonify(manifest)
        response.headers['Content-Type'] = 'application/manifest+json'
        response.headers['Cache-Control'] = 'no-cache'
        return response
