"""
安全测试模块
包含CSRF保护、XSS防护、请求频率限制等安全功能的测试
"""

import pytest
from flask import json


class TestSecurityHeaders:
    """安全响应头测试"""

    def test_security_headers_exist(self, client):
        """测试响应中包含必要的安全头"""
        response = client.get('/')
        assert response.status_code == 200

        # 检查安全响应头
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'

        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'

        assert 'X-XSS-Protection' in response.headers
        assert response.headers['X-XSS-Protection'] == '1; mode=block'

        assert 'Content-Security-Policy' in response.headers
        assert 'default-src \'self\'' in response.headers['Content-Security-Policy']

        assert 'Referrer-Policy' in response.headers
        assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'

        assert 'Permissions-Policy' in response.headers

    def test_security_headers_on_api_endpoints(self, client):
        """测试API端点的安全响应头"""
        response = client.get('/api/posts')
        assert response.status_code == 200

        assert 'X-Content-Type-Options' in response.headers
        assert 'X-Frame-Options' in response.headers
        assert 'X-XSS-Protection' in response.headers
        assert 'Content-Security-Policy' in response.headers


class TestCSRFProtection:
    """CSRF防护测试"""

    def test_csrf_token_present(self, client):
        """测试页面响应中包含CSRF令牌"""
        response = client.get('/login')
        assert response.status_code == 200
        assert 'csrf_token' in response.get_data(as_text=True)

    def test_csrf_protection_on_form_submit(self, client, test_admin_user):
        """测试表单提交需要有效的CSRF令牌"""
        # 先登录获取会话
        login_response = client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        }, follow_redirects=True)
        assert login_response.status_code == 200

        # 尝试在没有CSRF令牌的情况下提交表单
        response = client.post('/new', data={
            'title': 'Test Post',
            'content': 'Test content'
        }, follow_redirects=True)

        # 应该返回400错误或重定向到错误页面
        assert response.status_code == 400

    def test_csrf_exempt_endpoints(self, client):
        """测试CSRF豁免端点是否正常工作"""
        # 测试插件API端点（豁免CSRF）
        response = client.post('/api/plugin/submit', json={
            'title': 'Test Plugin Submit',
            'content': 'Test content',
            'url': 'https://example.com'
        })

        # 应该返回401未授权而不是400 CSRF错误
        assert response.status_code == 401


class TestXSSProtection:
    """XSS防护测试"""

    def test_post_content_xss_protection(self, client, test_admin_user):
        """测试文章内容渲染时的XSS防护"""
        # 登录
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建包含XSS内容的文章
        xss_content = '<script>alert("XSS")</script><img src=x onerror=alert(1)>'
        client.post('/admin/new', data={
            'title': 'XSS Test Post',
            'content': xss_content,
            'category_id': 1
        }, follow_redirects=True)

        # 查看文章
        response = client.get('/admin')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # XSS内容应该被过滤
        assert '<script>' not in html
        assert 'alert("XSS")' not in html


class TestRateLimiting:
    """请求频率限制测试"""

    def test_login_rate_limiting(self, client):
        """测试登录接口的请求频率限制"""
        # 快速发送多个登录请求
        for _ in range(6):
            client.post('/login', data={
                'username': 'nonexistent',
                'password': 'wrongpassword'
            })

        # 第6次请求应该被限制
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })

        assert response.status_code == 429

    def test_api_rate_limiting(self, client):
        """测试API接口的请求频率限制"""
        # 快速发送多个API请求
        for _ in range(30):
            client.get('/api/posts')

        # 应该被限制
        response = client.get('/api/posts')
        assert response.status_code == 429


class TestPasswordSecurity:
    """密码安全性测试"""

    def test_password_validation(self, client, test_admin_user):
        """测试密码强度验证"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 测试弱密码
        response = client.post('/change-password', data={
            'current_password': test_admin_user['password'],
            'new_password': 'weak',
            'confirm_password': 'weak'
        })

        assert '密码长度至少为10位' in response.get_data(as_text=True)

        # 测试缺少数字的密码
        response = client.post('/change-password', data={
            'current_password': test_admin_user['password'],
            'new_password': 'StrongPassword',
            'confirm_password': 'StrongPassword'
        })

        assert '密码必须包含至少一个数字' in response.get_data(as_text=True)


class TestSessionSecurity:
    """会话安全测试"""

    def test_session_cookie_httponly(self, client):
        """测试会话Cookie是否设置了HttpOnly标志"""
        client.get('/')
        assert 'session' in client.cookie_jar
        cookie = client.cookie_jar['session']
        assert cookie.has_nonstandard_attr('HttpOnly')

    def test_session_cookie_samesite(self, client):
        """测试会话Cookie是否设置了SameSite属性"""
        client.get('/')
        assert 'session' in client.cookie_jar
        cookie = client.cookie_jar['session']
        assert cookie.has_nonstandard_attr('SameSite')

    def test_session_regeneration_on_login(self, client, test_admin_user):
        """测试登录时会话是否重新生成"""
        # 第一次登录
        first_response = client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        first_session_cookie = first_response.headers.get('Set-Cookie')

        # 退出登录
        client.get('/logout')

        # 第二次登录
        second_response = client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        second_session_cookie = second_response.headers.get('Set-Cookie')

        # 会话Cookie应该不同
        assert first_session_cookie != second_session_cookie


class TestAPIKeyAuthentication:
    """API密钥认证测试"""

    def test_invalid_api_key_rejected(self, client):
        """测试无效API密钥被拒绝"""
        response = client.post('/api/plugin/submit',
                             headers={'X-API-Key': 'invalid_key'},
                             json={'title': 'Test', 'content': 'Test'})

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid or missing API key' in data['error']

    def test_missing_api_key_rejected(self, client):
        """测试缺少API密钥被拒绝"""
        response = client.post('/api/plugin/submit',
                             json={'title': 'Test', 'content': 'Test'})

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid or missing API key' in data['error']


class TestContentSecurityPolicy:
    """内容安全策略测试"""

    def test_csp_block_inline_scripts(self, client):
        """测试内容安全策略阻止内联脚本"""
        response = client.get('/')
        assert response.status_code == 200

        # 检查CSP策略
        csp = response.headers['Content-Security-Policy']
        assert 'script-src \'self\'' in csp
        assert 'unsafe-inline' not in csp

    def test_csp_restricts_external_resources(self, client):
        """测试内容安全策略限制外部资源加载"""
        csp = client.get('/').headers['Content-Security-Policy']

        assert 'img-src \'self\' data: https:' in csp
        assert 'font-src \'self\'' in csp
        assert 'connect-src \'self\'' in csp
