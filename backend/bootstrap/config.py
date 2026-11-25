"""核心配置装配。

Flask 在 ``Flask.__init__`` 里已经预置了一批配置键（例如
``SESSION_COOKIE_SAMESITE=None``），所以默认值不能靠 ``dict.setdefault``——
会被预设的 ``None`` 挡住。这里改为"覆盖值优先，其次才是默认值"的显式写入。
"""

from backend.config import (
    AUTO_MIGRATE,
    DEBUG,
    FORCE_HTTPS,
    IS_PRODUCTION,
    MAX_CONTENT_LENGTH,
    PERMANENT_SESSION_LIFETIME,
    SECRET_KEY,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    TRUST_PROXY_HEADERS,
    WTF_CSRF_ENABLED,
    WTF_CSRF_SSL_STRICT,
    WTF_CSRF_TIME_LIMIT,
)

__all__ = ['apply_core_config', 'apply_defaults', 'enable_proxy_fix']

# 项目自身的基础配置：必须无条件写入（调用方不能靠它省略 SECRET_KEY 等）
_CORE_CONFIG = {
    'SECRET_KEY': SECRET_KEY,
    'MAX_CONTENT_LENGTH': MAX_CONTENT_LENGTH,
    'DEBUG': DEBUG,
    'IS_PRODUCTION': IS_PRODUCTION,
    'FORCE_HTTPS': FORCE_HTTPS,
    'TRUST_PROXY_HEADERS': TRUST_PROXY_HEADERS,
    'AUTO_MIGRATE': AUTO_MIGRATE,
}

# CSRF / 缓存 / 会话的默认值：``create_app(config_overrides=...)`` 显式给出的键优先
_DEFAULT_CONFIG = {
    'WTF_CSRF_ENABLED': WTF_CSRF_ENABLED,
    'WTF_CSRF_TIME_LIMIT': WTF_CSRF_TIME_LIMIT,
    'WTF_CSRF_SSL_STRICT': WTF_CSRF_SSL_STRICT,
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_THRESHOLD': 1000,
    'SESSION_COOKIE_SECURE': SESSION_COOKIE_SECURE,
    'SESSION_COOKIE_HTTPONLY': SESSION_COOKIE_HTTPONLY,
    'SESSION_COOKIE_SAMESITE': SESSION_COOKIE_SAMESITE,
    'PERMANENT_SESSION_LIFETIME': PERMANENT_SESSION_LIFETIME,
}


def apply_core_config(app, config_overrides=None):
    """写入项目基础配置，随后应用调用方的覆盖值。"""
    app.config.update(_CORE_CONFIG)
    if config_overrides:
        app.config.update(config_overrides)


def apply_defaults(app, config_overrides=None):
    """写入 CSRF / 缓存 / 会话默认值，``config_overrides`` 中的键保持不变。"""
    overrides = config_overrides or {}
    for key, value in _DEFAULT_CONFIG.items():
        if key not in overrides:
            app.config[key] = value


def enable_proxy_fix(app):
    """反向代理部署时恢复真实客户端 IP / 协议，避免限流与审计全落在代理 IP 上。"""
    if not app.config.get('TRUST_PROXY_HEADERS'):
        return

    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
