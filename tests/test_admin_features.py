"""
批量操作功能测试
测试批量更新分类、删除、发布等管理功能
"""

import pytest


@pytest.mark.usefixtures("client", "test_admin_user")
class TestBatchOperations:
    """批量操作测试"""

    def test_batch_update_category(self, client, test_admin_user, temp_db):
        """测试批量更新分类"""
        from backend.models import create_user, create_post, create_category
        from werkzeug.security import generate_password_hash

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建测试文章
        user_id = test_admin_user['id']
        for i in range(3):
            create_post(
                title=f'Post {i}',
                content=f'Content {i}',
                is_published=True,
                category_id=None,
                author_id=user_id
            )

        # 创建新分类
        category_id = create_category('Test Category', 'test-category')

        # 批量更新分类
        response = client.post('/admin/batch-update-category',
            data={
                'post_ids': [1, 2, 3],
                'category_id': category_id
            })

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    def test_batch_delete_posts(self, client, test_admin_user, temp_db):
        """测试批量删除文章"""
        from backend.models import create_user, create_post

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建测试文章
        user_id = test_admin_user['id']
        post_ids = []
        for i in range(3):
            post_id = create_post(
                title=f'Delete Me {i}',
                content=f'Content {i}',
                is_published=True,
                category_id=None,
                author_id=user_id
            )
            post_ids.append(post_id)

        # 批量删除
        response = client.post('/admin/batch-delete',
            data={'post_ids': post_ids})

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    def test_batch_publish_posts(self, client, test_admin_user, temp_db):
        """测试批量发布文章"""
        from backend.models import create_user, create_post

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建未发布文章
        user_id = test_admin_user['id']
        post_ids = []
        for i in range(2):
            post_id = create_post(
                title=f'Draft {i}',
                content=f'Draft content {i}',
                is_published=False,
                category_id=None,
                author_id=user_id
            )
            post_ids.append(post_id)

        # 批量发布
        response = client.post('/admin/batch-publish',
            data={
                'post_ids': post_ids,
                'action': 'publish'
            })

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    def test_batch_add_tags(self, client, test_admin_user, temp_db):
        """测试批量添加标签"""
        from backend.models import create_user, create_post, create_tag

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建文章
        user_id = test_admin_user['id']
        post_ids = []
        for i in range(2):
            post_id = create_post(
                title=f'Post {i}',
                content=f'Content {i}',
                is_published=True,
                category_id=None,
                author_id=user_id
            )
            post_ids.append(post_id)

        # 创建标签
        tag1_id = create_tag('Python')
        tag2_id = create_tag('Flask')

        # 批量添加标签
        response = client.post('/admin/batch-add-tags',
            data={
                'post_ids': post_ids,
                'tag_ids': [tag1_id, tag2_id]
            })

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    def test_batch_update_access(self, client, test_admin_user, temp_db):
        """测试批量更新访问权限"""
        from backend.models import create_user, create_post

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建文章
        user_id = test_admin_user['id']
        post_ids = []
        for i in range(2):
            post_id = create_post(
                title=f'Public Post {i}',
                content=f'Content {i}',
                is_published=True,
                category_id=None,
                author_id=user_id
            )
            post_ids.append(post_id)

        # 批量更新为需要密码
        response = client.post('/admin/batch-update-access',
            data={
                'post_ids': post_ids,
                'access': 'password',
                'password': 'test123'
            })

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True


@pytest.mark.usefixtures("client", "test_admin_user")
class TestImageOptimization:
    """图片优化功能测试"""

    def test_check_optimization_status(self, client, test_admin_user, temp_db):
        """测试检查图片优化状态"""
        from backend.models import create_optimized_image_record
        import json

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建优化记录
        opt_id = create_optimized_image_record(
            original_path='/static/uploads/test.jpg',
            status='pending'
        )

        response = client.get(f'/admin/image-status/{opt_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data or 'optimization_id' in data

    def test_optimization_status_completed(self, client, test_admin_user, temp_db):
        """测试已完成的优化状态"""
        from backend.models import create_optimized_image_record

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建已完成的优化记录
        opt_id = create_optimized_image_record(
            original_path='/static/uploads/test2.jpg',
            status='completed'
        )

        response = client.get(f'/admin/image-status/{opt_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('status') == 'completed'


@pytest.mark.usefixtures("client", "test_admin_user")
class TestImportExport:
    """导入导出功能测试"""

    def test_export_json(self, client, test_admin_user):
        """测试导出JSON格式"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/admin/export/json')
        assert response.status_code == 200
        assert 'application/json' in response.content_type

    def test_export_markdown(self, client, test_admin_user):
        """测试导出Markdown格式"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/admin/export/markdown')
        assert response.status_code == 200

    def test_import_json(self, client, test_admin_user):
        """测试导入JSON格式"""
        import json
        import io

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 准备测试数据
        import_data = {
            'posts': [
                {
                    'title': 'Imported Post',
                    'content': 'Imported content',
                    'created_at': '2026-03-16T10:00:00'
                }
            ]
        }

        data_file = (io.BytesIO(json.dumps(import_data).encode()), 'import.json')

        response = client.post('/admin/import/json',
            data={'file': data_file},
            content_type='multipart/form-data')

        assert response.status_code in [200, 302]


@pytest.mark.usefixtures("client", "test_admin_user")
class TestUserManagement:
    """用户管理功能测试"""

    def test_create_user(self, client, test_admin_user):
        """测试创建用户"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123',
            'role': 'author'
        }

        response = client.post('/admin/users/new', data=user_data)
        assert response.status_code in [200, 302]

    def test_edit_user(self, client, test_admin_user, temp_db):
        """测试编辑用户"""
        from backend.models import create_user

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        user_id = create_user(
            username='edituser',
            password_hash='test_hash',
            role='author'
        )

        update_data = {
            'username': 'edituser',
            'email': 'updated@example.com',
            'role': 'editor'
        }

        response = client.post(f'/admin/users/{user_id}/edit', data=update_data)
        assert response.status_code in [200, 302]

    def test_delete_user(self, client, test_admin_user, temp_db):
        """测试删除用户"""
        from backend.models import create_user

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        user_id = create_user(
            username='deleteuser',
            password_hash='test_hash',
            role='author'
        )

        response = client.post(f'/admin/users/{user_id}/delete')
        assert response.status_code in [200, 302]


@pytest.mark.usefixtures("client", "test_admin_user")
class TestCommentManagement:
    """评论管理测试"""

    def test_toggle_comment_visibility(self, client, test_admin_user, temp_db):
        """测试切换评论可见性"""
        from backend.models import create_post, create_comment
        from backend.models import create_user
        from werkzeug.security import generate_password_hash

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建评论
        user_id = create_user('commenter', generate_password_hash('pass123'), role='author')
        post_id = create_post('Test Post', 'Content', True, None, test_admin_user['id'])
        comment_id = create_comment(post_id, user_id, 'Test comment')

        response = client.post(f'/admin/comments/{comment_id}/toggle')
        assert response.status_code in [200, 302]

    def test_delete_comment(self, client, test_admin_user, temp_db):
        """测试删除评论"""
        from backend.models import create_post, create_comment
        from backend.models import create_user
        from werkzeug.security import generate_password_hash

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建评论
        user_id = create_user('commenter2', generate_password_hash('pass123'), role='author')
        post_id = create_post('Test Post', 'Content', True, None, test_admin_user['id'])
        comment_id = create_comment(post_id, user_id, 'Delete me')

        response = client.post(f'/admin/comments/{comment_id}/delete')
        assert response.status_code in [200, 302]
