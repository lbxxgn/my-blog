"""
路由测试
"""

import pytest
from flask import session


class TestAuthRoutes:
    """认证路由测试"""
    
    def test_login_page(self, client):
        """测试登录页面"""
        response = client.get('/login')
        assert response.status_code == 200
    
    def test_login_success(self, client, test_admin_user):
        """测试成功登录"""
        response = client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_failure(self, client):
        """测试登录失败"""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
    
    def test_logout(self, client, test_admin_user):
        """测试退出登录"""
        # 先登录
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        
        # 再退出
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200


class TestBlogRoutes:
    """博客路由测试"""
    
    def test_index(self, client):
        """测试首页"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_view_post(self, client, test_post):
        """测试查看文章"""
        response = client.get(f'/post/{test_post["id"]}')
        assert response.status_code == 200
    
    def test_search_page(self, client):
        """测试搜索页面"""
        response = client.get('/search')
        assert response.status_code == 200
    
    def test_search_with_query(self, client, test_post):
        """测试带查询的搜索"""
        response = client.get('/search?q=Test')
        assert response.status_code == 200


class TestAdminRoutes:
    """管理后台路由测试"""
    
    def test_admin_dashboard_requires_login(self, client):
        """测试管理后台需要登录"""
        response = client.get('/admin/')
        assert response.status_code == 302  # 重定向到登录页
    
    def test_admin_dashboard_with_login(self, client, test_admin_user):
        """测试登录后访问管理后台"""
        # 先登录
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        
        # 访问管理后台
        response = client.get('/admin/')
        assert response.status_code == 200
    
    def test_new_post_page(self, client, test_admin_user):
        """测试新建文章页面"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        
        response = client.get('/admin/new')
        assert response.status_code == 200


class TestAPIRoutes:
    """API路由测试"""
    
    def test_api_posts(self, client):
        """测试文章列表API"""
        response = client.get('/api/posts')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'success' in data
        assert data['success'] is True
    
    def test_api_posts_cursor_pagination(self, client):
        """测试游标分页API"""
        response = client.get('/api/posts?per_page=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'posts' in data
        assert 'has_more' in data
        assert 'next_cursor' in data


class TestCategoryTagRoutes:
    """分类和标签路由测试"""
    
    def test_category_list(self, client):
        """测试分类列表"""
        response = client.get('/admin/categories')
        # 需要登录
        assert response.status_code in [200, 302]
    
    def test_tag_list(self, client):
        """测试标签列表"""
        response = client.get('/admin/tags')
        # 需要登录
        assert response.status_code in [200, 302]
    
    def test_view_category(self, client, temp_db):
        """测试查看分类"""
        from models import create_category, create_post, get_user_by_username
        from werkzeug.security import generate_password_hash
        
        # 创建测试数据
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('testuser', password_hash, role='author')
        category_id = create_category('Technology')
        create_post('Test', 'Content', True, category_id, user_id)
        
        response = client.get(f'/category/{category_id}')
        assert response.status_code == 200
    
    def test_view_tag(self, client, temp_db):
        """测试查看标签"""
        from models import create_tag, create_post, set_post_tags, get_user_by_username
        from werkzeug.security import generate_password_hash
        
        # 创建测试数据
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('testuser', password_hash, role='author')
        post_id = create_post('Test', 'Content', True, None, user_id)
        tag_id = create_tag('python')
        set_post_tags(post_id, ['python'])
        
        response = client.get(f'/tag/{tag_id}')
        assert response.status_code == 200


class TestCommentRoutes:
    """评论路由测试"""
    
    def test_add_comment(self, client, test_post):
        """测试添加评论"""
        response = client.post(f'/post/{test_post["id"]}/comment', data={
            'author_name': 'Test Author',
            'author_email': 'test@example.com',
            'content': 'Test comment content'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_add_comment_validation(self, client, test_post):
        """测试评论验证"""
        # 缺少必填字段
        response = client.post(f'/post/{test_post["id"]}/comment', data={
            'author_name': '',
            'content': 'Test comment'
        }, follow_redirects=True)
        
        assert response.status_code == 200
