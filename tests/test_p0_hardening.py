"""P0 体验/安全加固回归测试。

覆盖：草稿与知识库匿名访问、公开列表空间隔离、停用用户、密码重置、
评论展示/隐藏、知识库草稿清理、删除目录响应、访问密码哈希与 AI Key 加密。
"""

import pytest
from werkzeug.security import generate_password_hash


def _login(client, user):
    return client.post('/login', data={
        'username': user['username'],
        'password': user['password'],
    })


@pytest.mark.usefixtures('client')
class TestContentSpaceIsolation:
    def test_anonymous_cannot_view_unpublished_blog_draft(self, client, temp_db, test_user):
        from models import create_post
        post_id = create_post('Draft title', 'Draft body', False, None, test_user['id'])

        response = client.get(f'/post/{post_id}')
        assert response.status_code == 404

    def test_anonymous_cannot_view_knowledge_doc_via_post_route(self, client, temp_db, test_user):
        from models import create_kb_category, create_knowledge_doc
        cat_id = create_kb_category('KB space', space='knowledge')
        doc_id = create_knowledge_doc('KB secret', 'KB body', cat_id, author_id=test_user['id'])

        response = client.get(f'/post/{doc_id}')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_author_can_view_own_draft(self, client, temp_db, test_user):
        from models import create_post
        post_id = create_post('My draft', 'Draft body', False, None, test_user['id'])
        _login(client, test_user)

        response = client.get(f'/post/{post_id}')
        assert response.status_code == 200

    def test_archive_and_public_search_exclude_knowledge(self, client, temp_db, test_user):
        from models import create_kb_category, create_knowledge_doc
        cat_id = create_kb_category('KB hidden cat', space='knowledge')
        create_knowledge_doc('KB hidden doc', 'only in knowledge', cat_id, author_id=test_user['id'])

        archive = client.get('/archive').get_data(as_text=True)
        assert 'KB hidden doc' not in archive

        search = client.get('/search?q=KB%20hidden%20doc&source=all').get_data(as_text=True)
        assert '/knowledge/doc/' not in search


@pytest.mark.usefixtures('client')
class TestAccountSafety:
    def test_inactive_user_cannot_login(self, client, temp_db, test_user):
        from models import update_user
        update_user(test_user['id'], is_active=0)

        response = client.post('/login', data={
            'username': test_user['username'],
            'password': test_user['password'],
        }, follow_redirects=True)
        assert '已被停用' in response.get_data(as_text=True)

    def test_existing_session_invalid_after_deactivation(self, client, temp_db, test_user):
        from models import update_user
        _login(client, test_user)
        assert client.get('/').status_code == 200

        update_user(test_user['id'], is_active=0)
        response = client.get('/admin')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_admin_can_reset_user_password(self, client, temp_db, test_admin_user):
        from models import create_user
        user_id = create_user(
            'resetme',
            generate_password_hash('OldPassword123!', method='pbkdf2:sha256'),
            role='author',
        )
        _login(client, test_admin_user)

        response = client.post(f'/admin/users/{user_id}/edit', data={
            'role': 'author',
            'display_name': '',
            'bio': '',
            'is_active': '1',
            'new_password': 'NewPassword123!',
        })
        assert response.status_code == 302

        client.get('/logout')
        response = client.post('/login', data={
            'username': 'resetme',
            'password': 'NewPassword123!',
        })
        assert response.status_code == 302
        assert '/admin' in response.headers['Location']


@pytest.mark.usefixtures('client')
class TestCommentsAndKnowledge:
    def test_new_comment_is_public_and_admin_can_hide(self, client, temp_db, test_admin_user):
        from models import create_post, get_comments_by_post
        post_id = create_post('Comment post', 'Body', True, None, test_admin_user['id'])
        response = client.post(f'/post/{post_id}/comment', data={
            'author_name': 'Reader',
            'content': 'public comment',
        })
        assert response.status_code == 302

        comments = get_comments_by_post(post_id)
        assert len(comments) == 1
        comment_id = comments[0]['id']
        assert comments[0]['is_visible'] == 1

        _login(client, test_admin_user)
        response = client.post(f'/admin/comments/{comment_id}/toggle')
        assert response.status_code == 302
        assert get_comments_by_post(post_id) == []

        response = client.post(f'/admin/comments/{comment_id}/toggle')
        assert response.status_code == 302
        assert any(c['id'] == comment_id for c in get_comments_by_post(post_id))

    def test_knowledge_save_clears_surviving_draft(self, client, temp_db, test_user):
        from models import create_kb_category, create_knowledge_doc
        from models.draft import save_draft, get_drafts

        cat_id = create_kb_category('KB draft cat', space='knowledge')
        doc_id = create_knowledge_doc('Draft doc', 'old', cat_id, author_id=test_user['id'])
        save_draft(test_user['id'], doc_id, 'Draft doc', 'old draft', cat_id)

        _login(client, test_user)
        response = client.post(f'/knowledge/doc/{doc_id}/edit', data={
            'title': 'Saved doc',
            'content': 'new body',
            'category_id': cat_id,
            'is_published': '1',
        })
        assert response.status_code == 302
        assert get_drafts(test_user['id'], doc_id) == []

    def test_delete_category_form_redirects_instead_of_json(self, client, temp_db, test_user):
        from models import create_kb_category
        _login(client, test_user)
        cat_id = create_kb_category('To delete', space='knowledge')

        response = client.post(f'/knowledge/category/{cat_id}/delete')
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/knowledge/')

    def test_access_password_is_hashed_and_verifiable(self, client, temp_db, test_user):
        from models import create_post, get_db_connection, verify_post_password

        post_id = create_post(
            'Password post', 'Body', True, None, test_user['id'],
            access_level='password', access_password='PlainPass123',
        )
        conn = get_db_connection()
        row = conn.execute('SELECT access_password FROM posts WHERE id = ?', (post_id,)).fetchone()
        conn.close()

        assert row['access_password'] != 'PlainPass123'
        assert row['access_password'].startswith(('pbkdf2:', 'scrypt:'))
        assert verify_post_password(post_id, 'PlainPass123') is True
        assert verify_post_password(post_id, 'wrong') is False

    def test_empty_password_protected_post_is_rejected(self, client, temp_db, test_user):
        _login(client, test_user)
        response = client.post('/admin/new', data={
            'title': 'Locked',
            'content': 'Body',
            'content_format': 'html',
            'access_level': 'password',
            'access_password': '',
        }, follow_redirects=True)
        assert '必须设置非空密码' in response.get_data(as_text=True)


@pytest.mark.usefixtures('client')
class TestAiSecretStorage:
    def test_ai_key_is_encrypted_at_rest_and_not_echoed(self, client, temp_db, test_admin_user):
        from models import update_user_ai_config, get_user_ai_config, get_db_connection

        update_user_ai_config(test_admin_user['id'], {'ai_api_key': 'sk-test-secret-1234'})
        conn = get_db_connection()
        row = conn.execute('SELECT ai_api_key FROM users WHERE id = ?', (test_admin_user['id'],)).fetchone()
        conn.close()

        assert row['ai_api_key'].startswith('enc:v1:')
        assert 'sk-test-secret-1234' not in row['ai_api_key']
        assert get_user_ai_config(test_admin_user['id'])['ai_api_key'] == 'sk-test-secret-1234'

        _login(client, test_admin_user)
        page = client.get('/admin/ai/configure').get_data(as_text=True)
        assert 'sk-test-secret-1234' not in page
        assert '****1234' in page
