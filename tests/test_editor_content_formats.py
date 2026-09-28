"""编辑器内容格式（富文本 HTML / Markdown）与统一草稿契约测试。"""

import pytest


def _login(client, user):
    client.post('/login', data={
        'username': user['username'],
        'password': user['password']
    })


@pytest.mark.usefixtures("client", "test_admin_user")
class TestContentFormatPersistence:
    """正文格式字段的读写。"""

    def test_default_format_is_html(self, test_admin_user, temp_db):
        from backend.models import create_post, get_post_by_id

        post_id = create_post('T', '<p>hi</p>', True, None, test_admin_user['id'])
        assert get_post_by_id(post_id)['content_format'] == 'html'

    def test_update_post_content_format(self, test_admin_user, temp_db):
        from backend.models import create_post, update_post, get_post_by_id

        post_id = create_post('T', 'x', True, None, test_admin_user['id'])
        update_post(post_id, 'T', '# 标题', True, content_format='markdown')
        assert get_post_by_id(post_id)['content_format'] == 'markdown'

    def test_admin_new_post_markdown(self, client, test_admin_user, temp_db):
        from backend.models import get_all_posts

        _login(client, test_admin_user)
        resp = client.post('/admin/new', data={
            'title': 'MD Post',
            'content': '# 标题\n\n**粗体**',
            'content_format': 'markdown',
            'is_published': 'on',
        })
        assert resp.status_code in (200, 302)

        result = get_all_posts(include_drafts=True, page=1, per_page=1)
        assert result['posts'][0]['content_format'] == 'markdown'

    def test_admin_new_post_invalid_format_falls_back_html(self, client, test_admin_user, temp_db):
        from backend.models import get_all_posts

        _login(client, test_admin_user)
        client.post('/admin/new', data={
            'title': 'Weird Format',
            'content': '<p>x</p>',
            'content_format': 'javascript',
            'is_published': 'on',
        })
        result = get_all_posts(include_drafts=True, page=1, per_page=1)
        assert result['posts'][0]['content_format'] == 'html'


@pytest.mark.usefixtures("client", "test_admin_user")
class TestEditorFormatEndpoints:
    """预览 / 格式转换接口。"""

    def test_preview_renders_markdown(self, client, test_admin_user):
        _login(client, test_admin_user)
        resp = client.post('/admin/preview', json={
            'content': '# Hi', 'content_format': 'markdown'
        })
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert '<h1' in data['html']

    def test_preview_strips_xss(self, client, test_admin_user):
        _login(client, test_admin_user)
        resp = client.post('/admin/preview', json={
            'content': '<img src=x onerror=alert(1)>'
        })
        assert 'onerror' not in resp.get_json()['html']

    def test_convert_html_to_markdown(self, client, test_admin_user):
        _login(client, test_admin_user)
        resp = client.post('/admin/convert-format', json={
            'content': '<h1>标题</h1><p><strong>粗</strong>体</p>',
            'to': 'markdown',
        })
        data = resp.get_json()
        assert data['success'] is True
        assert data['content_format'] == 'markdown'
        assert '# 标题' in data['content']

    def test_convert_markdown_to_html(self, client, test_admin_user):
        _login(client, test_admin_user)
        resp = client.post('/admin/convert-format', json={
            'content': '# 标题', 'to': 'html',
        })
        data = resp.get_json()
        assert data['success'] is True
        assert '<h1' in data['content']

    def test_preview_requires_login(self, client):
        resp = client.post('/admin/preview', json={'content': '# x'})
        assert resp.status_code in (302, 401)


@pytest.mark.usefixtures("client", "test_admin_user")
class TestUnifiedDraftContract:
    """草稿统一契约：content_format 可往返，知识库 autosave 复用同一路径。"""

    def test_draft_roundtrip_markdown(self, test_admin_user, temp_db):
        from backend.models.draft import create_draft, get_draft

        draft_id = create_draft(
            title='d', content='# md', user_id=test_admin_user['id'],
            content_format='markdown'
        )
        draft = get_draft(draft_id, user_id=test_admin_user['id'])
        assert draft['content_format'] == 'markdown'

    def test_ensure_drafts_table_adds_content_format(self, temp_db):
        from models import get_db_connection
        from backend.models.draft import ensure_drafts_table

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS drafts')
        cursor.execute('''
            CREATE TABLE drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category_id INTEGER,
                tags TEXT,
                is_published BOOLEAN DEFAULT 0,
                device_info TEXT DEFAULT '',
                user_agent TEXT,
                last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

        ensure_drafts_table()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(drafts)')
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        assert 'content_format' in columns

    def test_conflict_payload_includes_overwritten_content(self, test_admin_user, temp_db):
        from backend.models import create_post
        from backend.models.draft import save_draft

        post_id = create_post(
            'Doc', 'v1', True, None, test_admin_user['id'], post_type='knowledge'
        )
        first = save_draft(
            test_admin_user['id'], post_id, 'Doc', '# deviceA',
            device_info='Device A', content_format='markdown'
        )
        assert first['status'] == 'saved'

        second = save_draft(
            test_admin_user['id'], post_id, 'Doc', '# deviceB',
            device_info='Device B', content_format='markdown'
        )
        assert second['status'] == 'conflict_detected'
        assert second['other_drafts'][0]['content'] == '# deviceA'
        assert second['other_drafts'][0]['content_format'] == 'markdown'

    def test_draft_api_accepts_content_format(self, client, test_admin_user, temp_db):
        _login(client, test_admin_user)
        resp = client.post('/api/drafts', json={
            'title': 'D', 'content': '# md', 'content_format': 'markdown'
        })
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True

        draft_resp = client.get(f"/api/drafts/{data['draft_id']}")
        assert draft_resp.get_json()['draft']['content_format'] == 'markdown'
