"""
路由测试
"""

import pytest
from io import BytesIO
from flask import session
from types import SimpleNamespace


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

    def test_login_with_remember_device_sets_permanent_session(self, client, test_admin_user):
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password'],
            'remember_device': '1',
        })

        with client.session_transaction() as sess:
            assert sess['_permanent'] is True
            assert sess['remember_device'] is True
    
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

    def test_change_password_page_shows_passkey_section(self, client, test_admin_user):
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/change-password')
        assert response.status_code == 200
        assert '快捷登录' in response.get_data(as_text=True)

    def test_passkey_register_begin_requires_login(self, client):
        response = client.post('/passkeys/register/begin', json={})
        assert response.status_code in (302, 401)

    def test_passkey_register_begin_returns_options(self, client, test_admin_user):
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.post('/passkeys/register/begin', json={})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['options']['rp']['name']
        assert data['options']['challenge']

    def test_passkey_register_finish_stores_passkey(self, client, test_admin_user, monkeypatch):
        from models import get_user_passkeys
        import routes.auth as auth_module

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        client.post('/passkeys/register/begin', json={})

        monkeypatch.setattr(auth_module, 'verify_registration_response', lambda **kwargs: SimpleNamespace(
            credential_id=b'test-credential',
            credential_public_key=b'test-public-key',
            sign_count=1,
            credential_device_type=SimpleNamespace(value='multi_device'),
            credential_backed_up=True,
        ))

        response = client.post('/passkeys/register/finish', json={
            'credential': {
                'id': 'dGVzdC1jcmVkZW50aWFs',
                'rawId': 'dGVzdC1jcmVkZW50aWFs',
                'response': {},
                'type': 'public-key',
            },
            'device_name': 'My Mac',
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        passkeys = get_user_passkeys(test_admin_user['id'])
        assert len(passkeys) == 1
        assert passkeys[0]['device_name'] == 'My Mac'

    def test_passkey_authenticate_finish_logs_user_in(self, client, test_admin_user, monkeypatch):
        from models import create_user_passkey
        import routes.auth as auth_module

        create_user_passkey(
            user_id=test_admin_user['id'],
            credential_id=b'test-credential',
            public_key=b'test-public-key',
            sign_count=5,
            device_name='Test iPhone',
            transports=['internal'],
        )

        client.post('/passkeys/authenticate/begin', json={})

        monkeypatch.setattr(auth_module, 'verify_authentication_response', lambda **kwargs: SimpleNamespace(
            new_sign_count=6,
            credential_device_type=SimpleNamespace(value='multi_device'),
            credential_backed_up=True,
        ))

        response = client.post('/passkeys/authenticate/finish', json={
            'credential': {
                'id': 'dGVzdC1jcmVkZW50aWFs',
                'rawId': 'dGVzdC1jcmVkZW50aWFs',
                'response': {},
                'type': 'public-key',
            },
            'remember_device': True,
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        with client.session_transaction() as sess:
            assert sess['user_id'] == test_admin_user['id']
            assert sess['_permanent'] is True

    def test_passkey_delete_removes_bound_device(self, client, test_admin_user):
        from models import create_user_passkey, get_user_passkeys

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        passkey_id = create_user_passkey(
            user_id=test_admin_user['id'],
            credential_id=b'another-credential',
            public_key=b'another-public-key',
            device_name='Old Mac',
        )

        response = client.delete(f'/passkeys/{passkey_id}')
        assert response.status_code == 200
        assert get_user_passkeys(test_admin_user['id']) == []


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

    def test_index_json_respects_category_filter(self, client, temp_db):
        """测试首页 JSON 支持分类筛选"""
        from models import create_category, create_post, create_user
        from werkzeug.security import generate_password_hash

        user_id = create_user('jsonuser', generate_password_hash('TestPassword123!', method='pbkdf2:sha256'), role='author')
        category_id = create_category('Filtered')
        other_category_id = create_category('Other')

        create_post('Keep me', 'Category content', True, category_id, user_id)
        create_post('Skip me', 'Other content', True, other_category_id, user_id)

        response = client.get(f'/?format=json&category={category_id}')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['posts']) == 1
        assert data['posts'][0]['title'] == 'Keep me'
        assert data['posts'][0]['category_name'] == 'Filtered'

    def test_mobile_my_posts_requires_login(self, client):
        """测试移动端我的文章接口需要登录"""
        response = client.get('/mobile/my-posts')
        assert response.status_code == 401

    def test_mobile_my_posts_returns_published_and_drafts(self, client, test_admin_user, temp_db):
        """测试移动端我的文章接口返回已发布和草稿数据"""
        from models import create_post

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        create_post('Published mobile', 'Published content', True, None, test_admin_user['id'])
        create_post('Draft mobile', 'Draft content', False, None, test_admin_user['id'])

        published_response = client.get('/mobile/my-posts?tab=published')
        drafts_response = client.get('/mobile/my-posts?tab=drafts')

        assert published_response.status_code == 200
        assert drafts_response.status_code == 200

        published_data = published_response.get_json()
        drafts_data = drafts_response.get_json()

        assert published_data['success'] is True
        assert any(post['title'] == 'Published mobile' for post in published_data['posts'])
        assert all(post['is_published'] for post in published_data['posts'])

        assert drafts_data['success'] is True
        assert any(post['title'] == 'Draft mobile' for post in drafts_data['posts'])
        assert all(not post['is_published'] for post in drafts_data['posts'])

    def test_index_json_includes_mobile_image_metadata(self, client, temp_db):
        """测试首页 JSON 返回移动端图片布局信息"""
        from models import create_post, create_user
        from werkzeug.security import generate_password_hash

        user_id = create_user('imageuser', generate_password_hash('TestPassword123!', method='pbkdf2:sha256'), role='author')
        content = '''
            <p>图文内容</p>
            <img src="/static/uploads/1.jpg" alt="">
            <img src="/static/uploads/2.jpg" alt="">
            <img src="/static/uploads/3.jpg" alt="">
            <img src="/static/uploads/4.jpg" alt="">
        '''
        create_post('Image post', content, True, None, user_id)

        response = client.get('/?format=json')
        assert response.status_code == 200

        data = response.get_json()
        image_post = next(post for post in data['posts'] if post['title'] == 'Image post')
        assert image_post['image_count'] == 4
        assert image_post['mobile_image_layout'] == 'grid-4'
        assert image_post['image_urls'] == [
            '/static/uploads/1.jpg',
            '/static/uploads/2.jpg',
            '/static/uploads/3.jpg',
            '/static/uploads/4.jpg'
        ]
        assert image_post['excerpt'] == '图文内容'

    def test_admin_upload_accepts_png_image(self, client, test_admin_user):
        """测试上传接口接受 PNG 图片"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 1x1 transparent PNG
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f'
            b'\x00\x01\x01\x01\x00\x18\xdd\x8d\xb1\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        response = client.post(
            '/admin/upload',
            data={'file': (BytesIO(png_bytes), 'tiny.png')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['url'].startswith('/static/uploads/images/')


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
        from models import create_category, create_post, create_user, get_user_by_username
        from werkzeug.security import generate_password_hash

        # 创建测试数据
        password_hash = generate_password_hash('TestPassword123!', method='pbkdf2:sha256')
        user_id = create_user('testuser', password_hash, role='author')
        category_id = create_category('Technology')
        create_post('Test', 'Content', True, category_id, user_id)
        
        response = client.get(f'/category/{category_id}')
        assert response.status_code == 200
    
    def test_view_tag(self, client, temp_db):
        """测试查看标签"""
        from models import create_tag, create_post, create_user, set_post_tags, get_user_by_username
        from werkzeug.security import generate_password_hash

        # 创建测试数据
        password_hash = generate_password_hash('TestPassword123!', method='pbkdf2:sha256')
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


class TestKnowledgeBaseRoutes:
    """知识库API路由测试"""

    def test_plugin_submit_content(self, client, test_admin_user):
        """测试插件提交内容（默认创建文章）"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        # Create user with API key
        password_hash = generate_password_hash('TestPass123!', method='pbkdf2:sha256')
        user_id = create_user('extuser', password_hash, role='author')
        api_key = generate_api_key(user_id)

        # Submit via plugin API (default: create as post)
        response = client.post('/knowledge_base/api/plugin/submit',
            json={
                'title': 'Test Page',
                'content': 'Selected text from page',
                'source_url': 'https://example.com/test',
                'tags': ['test', 'plugin']
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'post_id' in data
        assert data['type'] == 'post'

    def test_plugin_submit_requires_api_key(self, client):
        """测试插件提交需要API密钥"""
        response = client.post('/knowledge_base/api/plugin/submit',
            json={
                'title': 'Test Page',
                'content': 'Selected text from page',
                'source_url': 'https://example.com/test',
            }
        )

        assert response.status_code == 401

    def test_plugin_sync_annotations(self, client):
        """测试插件同步标注"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser2', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        response = client.post('/knowledge_base/api/plugin/sync-annotations',
            json={
                'url': 'https://example.com/test',
                'annotations': [
                    {
                        'id': 'uuid-1',
                        'text': 'Selected text',
                        'xpath': '/html/body/p[1]',
                        'color': 'yellow',
                        'note': 'My note',
                        'annotation_type': 'highlight'
                    }
                ]
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code in [200, 201]
        data = response.get_json()
        assert data['success'] is True

    def test_plugin_get_annotations(self, client):
        """测试获取标注"""
        from models import create_user, generate_api_key, create_annotation
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser3', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        # Create a test annotation
        create_annotation(
            user_id=user_id,
            source_url='https://example.com/test',
            annotation_text='Test annotation',
            xpath='/html/body/p[1]',
            color='yellow',
            note='Test note'
        )

        # Get annotations
        response = client.get('/knowledge_base/api/plugin/annotations?url=https://example.com/test',
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['count'] >= 1
        assert len(data['annotations']) >= 1

    def test_plugin_invalid_api_key(self, client):
        """测试无效的API密钥"""
        response = client.post('/knowledge_base/api/plugin/submit',
            json={
                'title': 'Test Page',
                'content': 'Selected text from page',
                'source_url': 'https://example.com/test',
            },
            headers={'X-API-Key': 'invalid_key_12345'}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_plugin_missing_api_key(self, client):
        """测试缺少API密钥"""
        response = client.post('/knowledge_base/api/plugin/submit',
            json={
                'title': 'Test Page',
                'content': 'Selected text from page',
                'source_url': 'https://example.com/test',
            }
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_plugin_submit_missing_content(self, client):
        """测试提交时缺少必填内容"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser4', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        response = client.post('/knowledge_base/api/plugin/submit',
            json={
                'title': 'Test Page',
                'source_url': 'https://example.com/test',
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_plugin_sync_annotations_missing_params(self, client):
        """测试同步标注时缺少参数"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser5', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        # Missing URL
        response = client.post('/knowledge_base/api/plugin/sync-annotations',
            json={
                'annotations': []
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_plugin_get_annotations_missing_url(self, client):
        """测试获取标注时缺少URL参数"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser6', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        response = client.get('/knowledge_base/api/plugin/annotations',
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_plugin_recent_captures(self, client):
        """测试获取最近捕获"""
        from models import create_user, generate_api_key, create_card
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser7', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        # Create some test cards
        create_card(user_id, 'Test Card 1', 'Content 1', 'idea', 'web')
        create_card(user_id, 'Test Card 2', 'Content 2', 'idea', 'web')

        response = client.get('/knowledge_base/api/plugin/recent?limit=5',
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['count'] >= 2
        assert len(data['cards']) >= 2

    def test_plugin_content_too_large(self, client):
        """测试内容过大"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser8', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        # Create content larger than 1MB
        large_content = 'x' * (1024 * 1024 + 1)

        response = client.post('/knowledge_base/api/plugin/submit',
            json={
                'title': 'Test Page',
                'content': large_content,
                'source_url': 'https://example.com/test',
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 413
        data = response.get_json()
        assert data['success'] is False
        assert 'too large' in data['error'].lower()

    def test_plugin_invalid_annotation_color(self, client):
        """测试无效的标注颜色"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser9', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        response = client.post('/knowledge_base/api/plugin/sync-annotations',
            json={
                'url': 'https://example.com/test',
                'annotations': [
                    {
                        'text': 'Selected text',
                        'xpath': '/html/body/p[1]',
                        'color': 'invalid_color',
                        'note': 'My note'
                    }
                ]
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Validation failed' in data['error']

    def test_plugin_invalid_annotation_type(self, client):
        """测试无效的标注类型"""
        from models import create_user, generate_api_key
        from werkzeug.security import generate_password_hash

        user_id = create_user('extuser10', generate_password_hash('TestPass123!', method='pbkdf2:sha256'), role='author')
        api_key = generate_api_key(user_id)

        response = client.post('/knowledge_base/api/plugin/sync-annotations',
            json={
                'url': 'https://example.com/test',
                'annotations': [
                    {
                        'text': 'Selected text',
                        'xpath': '/html/body/p[1]',
                        'color': 'yellow',
                        'annotation_type': 'invalid_type'
                    }
                ]
            },
            headers={'X-API-Key': api_key}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Validation failed' in data['error']
