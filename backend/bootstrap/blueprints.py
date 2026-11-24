"""蓝图注册。

注册顺序无关正确性，但保持稳定便于对照 ``flask routes`` 输出。
"""

__all__ = ['register_blueprints']


def register_blueprints(app):
    from backend.routes import (
        admin_bp, ai_bp, api_bp, auth_bp, blog_bp, knowledge_base_bp, knowledge_bp,
    )
    from backend.routes.admin import mobile_bp
    from backend.routes.drafts import drafts_bp
    from backend.routes.legacy import legacy_bp
    from backend.routes.review import review_bp

    # (蓝图, url_prefix)；空字符串表示使用蓝图自身声明的前缀
    blueprints = (
        (auth_bp, ''),
        (blog_bp, ''),
        (admin_bp, ''),
        (api_bp, '/api'),
        (ai_bp, ''),
        (knowledge_base_bp, '/knowledge_base'),
        (knowledge_bp, '/knowledge'),
        (drafts_bp, ''),
        (review_bp, ''),
        (legacy_bp, ''),
        # 移动端（无 CSRF 保护，使用 API Key 认证；路由见 admin/media.py）
        (mobile_bp, '/mobile'),
    )

    for blueprint, url_prefix in blueprints:
        if url_prefix:
            app.register_blueprint(blueprint, url_prefix=url_prefix)
        else:
            app.register_blueprint(blueprint)
