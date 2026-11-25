"""装配层回归测试：端点配置表必须与实际注册的视图一致。"""

from backend.app import app
from backend.bootstrap.security import CSRF_EXEMPT_ENDPOINTS, ROUTE_LIMITS


def test_csrf_exempt_endpoints_exist():
    missing = [ep for ep in CSRF_EXEMPT_ENDPOINTS if ep not in app.view_functions]
    assert missing == []


def test_rate_limit_endpoints_exist():
    missing = [ep for ep in ROUTE_LIMITS if ep not in app.view_functions]
    assert missing == []


def test_rate_limit_view_functions_are_wrapped():
    """限流在启动时套在视图函数上；表里漏写的端点不会被静默忽略。"""
    unwrapped = [
        endpoint for endpoint in ROUTE_LIMITS
        if not hasattr(app.view_functions[endpoint], '__wrapped__')
    ]
    assert unwrapped == []
