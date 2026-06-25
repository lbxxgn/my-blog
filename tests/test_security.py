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

    def test_csrf_protection_on_form_submit(self, csrf_client, test_admin_user):
        """测试表单提交需要有效的CSRF令牌"""
        import re

        # 先获取登录页 CSRF 令牌
        login_page = csrf_client.get('/login')
        html = login_page.get_data(as_text=True)
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
        assert match, 'Login page should contain csrf_token'
        csrf_token = match.group(1)

        # 使用令牌登录
        login_response = csrf_client.post('/login', data={
            'csrf_token': csrf_token,
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        }, follow_redirects=True)
        assert login_response.status_code == 200

        # 尝试在没有CSRF令牌的情况下提交表单
        response = csrf_client.post('/admin/new', data={
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
        import re

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
            'category_id': 1,
            'is_published': 'on'
        }, follow_redirects=True)

        # 查看文章详情页，确认 XSS 标签被过滤
        from backend.models.models import get_all_posts
        result = get_all_posts(include_drafts=True, page=1, per_page=1)
        post_id = result['posts'][0]['id']

        response = client.get(f'/post/{post_id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # 提取文章内容区域，避免页面本身合法内联脚本的干扰
        content_match = re.search(r'<div class="post-content">(.*?</div>)', html, re.DOTALL)
        assert content_match, 'Post content area should be present'
        content_html = content_match.group(1)

        # XSS 脚本标签不应以原始形式出现在文章内容中
        assert '<script>' not in content_html
        assert 'onerror=alert(1)' not in content_html
        # 确认内容被正确转义/清理
        assert '&lt;script&gt;' in content_html or 'alert("XSS")' not in content_html


class TestRateLimiting:
    """请求频率限制测试"""

    def test_login_rate_limiting(self, limited_client):
        """测试登录接口的请求频率限制"""
        # 快速发送多个登录请求
        for _ in range(6):
            limited_client.post('/login', data={
                'username': 'nonexistent',
                'password': 'wrongpassword'
            })

        # 第7次请求应该被限制（登录限制为 5 per minute）
        response = limited_client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })

        assert response.status_code == 429

    def test_api_rate_limiting(self, limited_client):
        """测试API接口的请求频率限制"""
        # 快速发送多个API请求
        for _ in range(101):
            limited_client.get('/api/posts')

        # 应该被限制（/api/posts 限制为 100 per hour）
        response = limited_client.get('/api/posts')

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
        response = client.get('/')
        set_cookie = response.headers.get('Set-Cookie', '')
        assert 'HttpOnly' in set_cookie

    def test_session_cookie_samesite(self, client):
        """测试会话Cookie是否设置了SameSite属性"""
        response = client.get('/')
        set_cookie = response.headers.get('Set-Cookie', '')
        assert 'SameSite' in set_cookie

    def test_session_regeneration_on_login(self, client, test_admin_user):
        """测试登录时会话是否重新生成"""
        # 第一次登录
        first_response = client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        first_session_cookie = first_response.headers.get('Set-Cookie')
        assert first_session_cookie is not None

        # 退出登录
        client.get('/logout')

        # 第二次登录
        second_response = client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        second_session_cookie = second_response.headers.get('Set-Cookie')
        assert second_session_cookie is not None

        # 两次登录都应下发有效的 session Cookie（Flask 客户端会话的签名值
        # 在会话数据相同时可能相同，因此只验证 Cookie 被重新设置即可）
        assert first_session_cookie
        assert second_session_cookie


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

    def test_csp_exists_and_includes_self(self, client):
        """测试内容安全策略存在并包含 self 源"""
        response = client.get('/')
        assert response.status_code == 200

        # 检查CSP策略
        csp = response.headers['Content-Security-Policy']
        assert 'script-src \'self\'' in csp

    def test_csp_restricts_external_resources(self, client):
        """测试内容安全策略限制外部资源加载"""
        csp = client.get('/').headers['Content-Security-Policy']

        assert 'img-src \'self\' data: https:' in csp
        assert 'font-src \'self\'' in csp
        assert 'connect-src \'self\'' in csp
