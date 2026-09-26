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
        from backend.models import create_post, create_category

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
        from backend.models import create_post

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
        from backend.models import create_post

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
        from backend.models import create_post, create_tag

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
        from backend.models import create_post

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
        user_id = create_user('commenter', generate_password_hash('pass123', method='pbkdf2:sha256'), role='author')
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
        user_id = create_user('commenter2', generate_password_hash('pass123', method='pbkdf2:sha256'), role='author')
        post_id = create_post('Test Post', 'Content', True, None, test_admin_user['id'])
        comment_id = create_comment(post_id, user_id, 'Delete me')

        response = client.post(f'/admin/comments/{comment_id}/delete')
        assert response.status_code in [200, 302]


@pytest.mark.usefixtures("client", "test_admin_user")
class TestBatchPermissions:
    """批量操作的权限校验：author 不能动他人文章，删除仅 admin"""

    def _create_author(self):
        from backend.models import create_user
        from werkzeug.security import generate_password_hash
        return create_user(
            'batch_author',
            generate_password_hash('AuthorPass123!', method='pbkdf2:sha256'),
            role='author'
        )

    def _login(self, client, username, password):
        return client.post('/login', data={'username': username, 'password': password})

    def test_batch_delete_forbidden_for_author(self, client, test_admin_user, temp_db):
        """author 调用批量删除应返回 403，文章仍在"""
        from backend.models import create_post, get_post_by_id

        post_id = create_post('Admin Post', 'Content', True, None, test_admin_user['id'])
        self._create_author()
        self._login(client, 'batch_author', 'AuthorPass123!')

        response = client.post('/admin/batch-delete', data={'post_ids': [post_id]})

        assert response.status_code == 403
        assert get_post_by_id(post_id) is not None

    def test_batch_publish_filters_other_users_posts(self, client, test_admin_user, temp_db):
        """author 批量发布时，他人文章被过滤（403），自己的文章正常处理"""
        from backend.models import create_post, get_post_by_id

        other_post = create_post('Other Post', 'Content', False, None, test_admin_user['id'])
        author_id = self._create_author()
        own_post = create_post('Own Post', 'Content', False, None, author_id)
        self._login(client, 'batch_author', 'AuthorPass123!')

        # 只选他人文章 → 403，文章保持未发布
        response = client.post('/admin/batch-publish', data={'post_ids': [other_post], 'publish': 'true'})
        assert response.status_code == 403
        assert get_post_by_id(other_post)['is_published'] in (0, False)

        # 混合选择 → 只处理自己的文章
        response = client.post('/admin/batch-publish', data={'post_ids': [other_post, own_post], 'publish': 'true'})
        assert response.status_code == 200
        assert get_post_by_id(own_post)['is_published'] in (1, True)
        assert get_post_by_id(other_post)['is_published'] in (0, False)

    def test_batch_update_category_filters_other_users_posts(self, client, test_admin_user, temp_db):
        """author 批量改分类时，他人文章不受影响"""
        from backend.models import create_post, create_category, get_post_by_id

        category_id = create_category('Perm Cat', 'perm-cat')
        other_post = create_post('Other Post', 'Content', True, None, test_admin_user['id'])
        author_id = self._create_author()
        own_post = create_post('Own Post', 'Content', True, None, author_id)
        self._login(client, 'batch_author', 'AuthorPass123!')

        response = client.post('/admin/batch-update-category',
                               data={'post_ids': [other_post, own_post], 'category_id': category_id})
        assert response.status_code == 200
        assert str(get_post_by_id(own_post)['category_id']) == str(category_id)
        assert get_post_by_id(other_post)['category_id'] is None


@pytest.mark.usefixtures("client", "test_admin_user")
class TestUserActivation:
    """账户启用开关生效测试"""

    def test_disable_and_enable_user(self, client, test_admin_user, temp_db):
        """编辑用户时不勾选/勾选 is_active 能正确禁用/启用账户"""
        from backend.models import create_user, get_user_by_id

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        user_id = create_user(
            username='toggleuser',
            password_hash='test_hash',
            role='author'
        )

        # 未勾选 is_active -> 账户被禁用
        client.post(f'/admin/users/{user_id}/edit', data={'role': 'author'})
        assert not get_user_by_id(user_id)['is_active']

        # 勾选 is_active -> 账户重新启用
        client.post(f'/admin/users/{user_id}/edit', data={'role': 'author', 'is_active': '1'})
        assert get_user_by_id(user_id)['is_active']

    def test_cannot_disable_self(self, client, test_admin_user, temp_db):
        """管理员不能禁用自己的账户"""
        from backend.models import get_user_by_id

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        client.post(f'/admin/users/{test_admin_user["id"]}/edit', data={'role': 'admin'})
        assert get_user_by_id(test_admin_user['id'])['is_active']
