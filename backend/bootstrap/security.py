"""安全相关装配：响应头、扩展初始化、启动迁移、CSRF 豁免与速率限制。"""

import logging
import os
import sys

from backend.config import FORCE_HTTPS, IS_PRODUCTION

__all__ = [
    'init_extensions',
    'run_startup_migrations',
    'register_security_headers',
    'register_csrf_exemptions',
    'apply_rate_limits',
]

logger = logging.getLogger(__name__)

# 需要豁免 CSRF 的端点：跨端调用（浏览器扩展、移动端、备份恢复）无法携带 CSRF token
CSRF_EXEMPT_ENDPOINTS = (
    'knowledge_base.plugin_submit',
    'knowledge_base.sync_annotations',
    'knowledge_base.plugin_validate',
    'mobile.mobile_upload_image',
    'ai.test_ai_config',
    # 全量备份恢复需要接收超过全局上限的 ZIP：先豁免，视图内提高 body 上限后手动校验 CSRF
    'admin.restore_backup',
    'legacy.plugin_submit',
    'legacy.plugin_sync_annotations',
)

# 关键端点的速率限制（端点名 -> 限额）。集中成表便于审查与调整。
ROUTE_LIMITS = {
    # 文章相关 API
    'api.api_posts_cursor': '100 per hour',
    'api.generate_qrcode': '10 per minute',
    'api.get_original_image_url': '30 per hour',
    # 认证相关端点
    'auth.passkey_register_begin': '10 per minute',
    'auth.passkey_authenticate_begin': '10 per minute',
    'auth.passkey_register_finish': '10 per minute',
    'auth.passkey_authenticate_finish': '10 per minute',
    # AI 相关端点
    'ai.generate_tags': '50 per hour',
    'ai.ai_settings': '50 per hour',
    'ai.test_ai_config': '10 per minute',
    'ai.ai_history': '50 per hour',
    'ai.ai_status': '50 per hour',
    'ai.generate_summary': '30 per hour',
    'ai.recommend_posts': '30 per hour',
    'ai.continue_writing': '20 per hour',
    'ai.organize_content': '20 per hour',
    # 知识库 API
    'knowledge_base.plugin_submit': '50 per hour',
    'knowledge_base.sync_annotations': '50 per hour',
    'knowledge_base.get_annotations': '30 per hour',
    'knowledge_base.get_recent_captures': '50 per hour',
    'knowledge_base.card_list': '20 per hour',
    'knowledge_base.card_detail': '10 per minute',
    'knowledge_base.card_status': '10 per minute',
    'knowledge_base.merge_cards': '10 per minute',
    'knowledge_base.generate_card_tags': '20 per hour',
    'knowledge_base.ai_merge_cards': '10 per hour',
    'knowledge_base.convert_card_to_post': '10 per hour',
    # 回顾页 API
    'review.api_review_weekly_generate': '10 per hour',
}


def init_extensions(app, csrf, limiter, cache):
    """初始化 CSRF / 限流 / 缓存，并把实例挂到 app 上供测试与其它模块复用。"""
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)

    app.cache = cache
    app.csrf_protect = csrf
    app.limiter = limiter


def run_startup_migrations(app):
    """非测试环境下自动应用数据库迁移；失败时直接中断启动。"""
    if not app.config.get('AUTO_MIGRATE'):
        return
    if app.config.get('TESTING') or os.environ.get('TESTING') == '1' or 'pytest' in sys.modules:
        return

    import contextlib
    import io

    from backend.migrations import apply_migrations

    with contextlib.redirect_stdout(io.StringIO()):
        applied, _skipped, failed = apply_migrations(verbose=False)
    if failed:
        raise RuntimeError(f'数据库迁移失败: {failed}')
    if applied:
        logger.info('已自动应用 %s 个数据库迁移', applied)


def register_security_headers(app):
    """添加安全响应头，增强应用安全性。"""

    @app.after_request
    def add_security_headers(response):
        # 防止 MIME 类型嗅探
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')

        # 防止点击劫持
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')

        # 启用 XSS 防护
        response.headers.setdefault('X-XSS-Protection', '1; mode=block')

        # 内容安全策略（CSP）。注意：该策略比较宽松，生产环境可能需要按实际情况收紧。
        response.headers.setdefault('Content-Security-Policy',
            "default-src 'self'; "
            # Quill 已自托管，不再需要外部 CDN
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "object-src 'none'; "
            # 允许富文本正文中的视频/外链嵌入；仅限 https，仍禁止 object/embed
            "frame-src 'self' https:; "
            "base-uri 'self';"
        )

        # 严格传输安全（仅在生产环境且启用 HTTPS 时）
        if IS_PRODUCTION and FORCE_HTTPS:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

        # 防止浏览器猜测 Referer
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')

        # Permissions Policy
        response.headers.setdefault('Permissions-Policy',
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        return response


def register_csrf_exemptions(app, csrf):
    """按端点名豁免 CSRF（只豁免真正需要跨端调用的接口，而非整个蓝图）。"""
    for endpoint in CSRF_EXEMPT_ENDPOINTS:
        view = app.view_functions.get(endpoint)
        if view is None:
            logger.warning('CSRF 豁免跳过不存在的端点: %s', endpoint)
            continue
        csrf.exempt(view)


def apply_rate_limits(app, limiter):
    """把 ``ROUTE_LIMITS`` 应用到对应端点的视图函数。"""
    for endpoint, limit in ROUTE_LIMITS.items():
        view = app.view_functions.get(endpoint)
        if view is None:
            logger.warning('限流跳过不存在的端点: %s', endpoint)
            continue
        app.view_functions[endpoint] = limiter.limit(limit)(view)
