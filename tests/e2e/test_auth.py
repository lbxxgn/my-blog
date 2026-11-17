"""端到端：登录、登出、受保护页面的跳转。"""

import pytest

from .harness import login

pytestmark = pytest.mark.e2e


def test_invalid_login_shows_error(page, seed):
    page.goto('/login')
    page.set_value('#username', seed['admin_username'])
    page.set_value('#password', 'definitely-wrong-password')
    page.click('.login-form button[type="submit"]')

    page.wait_body_contains('用户名或密码错误')
    assert page.path() == '/login'


def test_login_success_and_logout(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])

    assert page.path().startswith('/admin')
    page.wait_body_contains('文章管理')

    page.goto('/logout', expect='/')
    page.wait_for("location.pathname === '/'")
    page.wait_body_contains('已退出登录')

    page.goto('/admin/', expect='/login')
    page.wait_body_contains('登录')
    assert page.path() == '/login'


def test_protected_pages_redirect_anonymous_users(page):
    page.goto('/admin/', expect='/login')
    assert page.path() == '/login'

    page.goto('/knowledge/', expect='/login')
    assert page.path() == '/login'

    page.goto('/review', expect='/login')
    assert page.path() == '/login'
