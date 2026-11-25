"""模板过滤器与全局上下文注入。"""

import re
from datetime import datetime

from backend.config import REMEMBER_DEVICE_DAYS, SITE_AUTHOR, SITE_DESCRIPTION, SITE_NAME
from backend.models import get_site_icon_version, get_site_identity
from backend.utils.timezone import utc_to_local

__all__ = ['register_template_filters', 'register_context_processors']


def register_template_filters(app):
    """注册时区相关全局函数与 Jinja2 过滤器。"""
    app.jinja_env.globals.update(utc_to_local=utc_to_local)

    @app.template_filter('localtime')
    def localtime_filter(value):
        """将 UTC 时间转换为本地时间。"""
        return utc_to_local(value)

    @app.template_filter('excerpt')
    def excerpt_filter(value, max_length=200):
        """获取文章摘要（清理 HTML 并截断）。"""
        from backend.models import get_post_excerpt
        return get_post_excerpt(value, max_length)

    @app.template_filter('highlight')
    def highlight_filter(text, query):
        """转义文本后高亮搜索关键词（<mark> 包裹，大小写不敏感）。"""
        from markupsafe import Markup, escape

        if text is None:
            return ''
        escaped_text = str(escape(text))
        if not query:
            return Markup(escaped_text)
        escaped_query = str(escape(query))
        if not escaped_query:
            return Markup(escaped_text)
        pattern = re.compile(re.escape(escaped_query), re.IGNORECASE)
        return Markup(pattern.sub(lambda m: '<mark>' + m.group(0) + '</mark>', escaped_text))


def register_context_processors(app, vite_asset):
    """把站点设置与前端资源助手注入所有模板（优先使用后台保存的配置）。"""

    @app.context_processor
    def inject_site_settings():
        identity = get_site_identity({
            'site_name': SITE_NAME,
            'site_description': SITE_DESCRIPTION,
            'site_author': SITE_AUTHOR,
        })
        return dict(
            site_name=identity.get('site_name') or SITE_NAME,
            site_description=identity.get('site_description') or SITE_DESCRIPTION,
            site_author=identity.get('site_author') or SITE_AUTHOR,
            remember_device_days=REMEMBER_DEVICE_DAYS,
            site_icon_version=get_site_icon_version(),
            vite_asset=vite_asset,
            current_year=datetime.now().year,
        )
