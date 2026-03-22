
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

class TestAuthRoutesEdgeCases:
    """认证路由边界测试"""
    
    def test_login_with_empty_credentials(self, client):
        """测试空凭据登录"""
        response = client.post('/login', data={
            'username': '',
            'password': ''
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_login_with_special_characters(self, client):
        """测试特殊字符用户名"""
        response = client.post('/login', data={
            'username': "<script>alert('xss')</script>",
            'password': 'test'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_register_with_existing_username(self, client, admin_user):
        """测试重复用户名注册"""
        response = client.post('/register', data={
            'username': 'admin',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200

class TestBlogRoutesEdgeCases:
    """博客路由边界测试"""
    
    def test_view_nonexistent_post(self, client):
        """测试访问不存在的文章"""
        response = client.get('/post/99999')
        assert response.status_code == 404
    
    def test_view_post_with_invalid_id(self, client):
        """测试访问无效ID的文章"""
        response = client.get('/post/abc')
        assert response.status_code == 404
    
    def test_search_with_empty_query(self, client):
        """测试空搜索查询"""
        response = client.get('/search?q=')
        assert response.status_code == 200
    
    def test_search_with_special_chars(self, client):
        """测试特殊字符搜索"""
        response = client.get('/search?q=<script>alert(1)</script>')
        assert response.status_code == 200
    
    def test_search_with_very_long_query(self, client):
        """测试超长搜索查询"""
        long_query = 'a' * 1000
        response = client.get(f'/search?q={long_query}')
        assert response.status_code == 200

class TestAPIRoutesEdgeCases:
    """API路由边界测试"""
    
    def test_api_posts_with_invalid_limit(self, client):
        """测试无效的limit参数"""
        response = client.get('/api/posts?limit=-1')
        assert response.status_code in [200, 400]
    
    def test_api_posts_with_invalid_cursor(self, client):
        """测试无效的cursor参数"""
        response = client.get('/api/posts?cursor=invalid_cursor')
        data = json.loads(response.data)
        assert response.status_code == 200
    
    def test_api_posts_with_large_limit(self, client):
        """测试超大的limit参数"""
        response = client.get('/api/posts?limit=10000')
        assert response.status_code == 200

class TestAdminRoutesEdgeCases:
    """管理员路由边界测试"""
    
    def test_admin_access_without_login(self, client):
        """测试未登录访问管理后台"""
        response = client.get('/admin/')
        assert response.status_code == 302
        assert '/login' in response.headers.get('Location', '')
    
    def test_admin_delete_nonexistent_post(self, client, admin_user):
        """测试删除不存在的文章"""
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
        
        response = client.post('/admin/post/99999/delete')
        assert response.status_code in [404, 302]
