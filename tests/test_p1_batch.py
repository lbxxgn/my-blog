"""P1 本批功能回归：桥接、统一搜索、站点设置、导入导出、移动后台、AI 状态。"""

import json
import zipfile

import pytest

from tests.test_p1_features import _login


@pytest.mark.usefixtures('client')
class TestAiStatusAndCostRemoval:
    def test_ai_status_reports_configured(self, client, temp_db, test_user):
        from models import update_user_ai_config
        _login(client, test_user)
        data = client.get('/admin/ai/status').get_json()
        assert data['ai_configured'] is False

        update_user_ai_config(test_user['id'], {'ai_api_key': 'sk-test-1234', 'ai_tag_generation_enabled': True})
        data = client.get('/admin/ai/status').get_json()
        assert data['ai_configured'] is True
        assert data['ai_enabled'] is True

    def test_ai_cost_is_not_displayed(self, client, temp_db, test_admin_user):
        _login(client, test_admin_user)
        page = client.get('/admin/ai/history').get_data(as_text=True)
        assert '总成本' not in page
        settings = client.get('/admin/ai/configure').get_data(as_text=True)
        assert '成本说明' not in settings


@pytest.mark.usefixtures('client')
class TestSiteAndEditEntry:
    def test_site_identity_can_be_updated(self, client, temp_db, test_admin_user):
        _login(client, test_admin_user)
        response = client.post('/admin/site/general', data={
            'site_name': '新站名',
            'site_description': '新的描述',
            'site_author': '新作者',
        })
        assert response.status_code == 302
        page = client.get('/').get_data(as_text=True)
        assert '新站名' in page
        manifest = client.get('/site.webmanifest').get_json()
        assert manifest['name'] == '新站名'

    def test_post_page_shows_edit_link_for_author(self, client, temp_db, test_user):
        from models import create_post
        post_id = create_post('Editable', 'body', True, None, test_user['id'])
        _login(client, test_user)
        page = client.get(f'/post/{post_id}').get_data(as_text=True)
        assert f'/admin/edit/{post_id}' in page

        client.get('/logout')
        page = client.get(f'/post/{post_id}').get_data(as_text=True)
        assert f'/admin/edit/{post_id}' not in page


@pytest.mark.usefixtures('client')
class TestBlogKnowledgeBridge:
    def test_precipitate_is_idempotent_and_backlinked(self, client, temp_db, test_user):
        from models import create_post, create_kb_category, get_db_connection
        cat_id = create_kb_category('Bridge KB', space='knowledge')
        post_id = create_post('Bridge post', '<p>hello</p>', True, None, test_user['id'])
        _login(client, test_user)

        first = client.post(f'/post/{post_id}/precipitate', json={'category_id': cat_id}).get_json()
        second = client.post(f'/post/{post_id}/precipitate', json={'category_id': cat_id}).get_json()
        assert first['success'] and second['success']
        assert first['doc_id'] == second['doc_id']

        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) AS c FROM posts WHERE source_post_id = ? AND post_type = 'knowledge'", (post_id,)).fetchone()['c']
        conn.close()
        assert count == 1

        page = client.get(f'/post/{post_id}').get_data(as_text=True)
        assert '已沉淀到知识库' in page

    def test_doc_can_be_converted_to_blog_draft_once(self, client, temp_db, test_user):
        from models import create_kb_category, create_knowledge_doc, get_db_connection
        cat_id = create_kb_category('Bridge KB 2', space='knowledge')
        doc_id = create_knowledge_doc('Doc to blog', 'markdown body', cat_id, author_id=test_user['id'])
        _login(client, test_user)

        first = client.post(f'/knowledge/doc/{doc_id}/to-blog')
        second = client.post(f'/knowledge/doc/{doc_id}/to-blog')
        assert first.status_code == 302 and second.status_code == 302

        conn = get_db_connection()
        rows = conn.execute("SELECT id, is_published FROM posts WHERE source_post_id = ? AND post_type = 'blog'", (doc_id,)).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]['is_published'] == 0


@pytest.mark.usefixtures('client')
class TestUnifiedSearch:
    def test_all_source_includes_docs_cards_annotations(self, client, temp_db, test_user):
        from models import create_post, create_kb_category, create_knowledge_doc, create_card, create_annotation
        create_post('flask blog', 'flask body', True, None, test_user['id'])
        cat_id = create_kb_category('Search KB', space='knowledge')
        create_knowledge_doc('flask doc', 'flask doc body', cat_id, author_id=test_user['id'])
        create_card(test_user['id'], 'flask card', 'card body', source='web')
        create_annotation(test_user['id'], 'https://example.com', 'flask annotation', '/p', 'yellow', 'note')

        _login(client, test_user)
        page = client.get('/search?q=flask&source=all').get_data(as_text=True)
        assert '/post/' in page
        assert '知识库' in page
        assert '卡片' in page
        assert '标注' in page
        assert 'flask' in page


@pytest.mark.usefixtures('client')
class TestExportImport:
    def test_json_export_contains_full_fields(self, temp_db, test_user, tmp_path):
        from models import create_post
        import export
        create_post('Full fields', 'body', True, None, test_user['id'], access_level='private',
                    post_type='knowledge', content_format='markdown')
        count, path = export.export_to_json(str(tmp_path))
        assert count >= 1
        data = json.loads(open(path, encoding='utf-8').read())
        item = data['posts'][0]
        for key in ('post_type', 'content_format', 'access_level', 'category_space'):
            assert key in item

    def test_dry_run_import_does_not_write(self, temp_db, test_user, tmp_path):
        from models import create_post, get_db_connection
        from import_posts import import_from_json
        create_post('Existing post', 'body', True, None, test_user['id'])
        payload = {'posts': [{
            'title': 'Preview only', 'content': 'body', 'is_published': 1,
            'created_at': '2024-01-01 00:00:00', 'content_format': 'html',
            'post_type': 'blog', 'access_level': 'public',
        }]}
        path = tmp_path / 'import.json'
        path.write_text(json.dumps(payload), encoding='utf-8')
        imported, skipped, messages = import_from_json(str(path), test_user['id'], dry_run=True)
        assert imported == 1
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) AS c FROM posts WHERE title = 'Preview only'").fetchone()['c']
        conn.close()
        assert count == 0

    def test_full_export_zip_contains_json_and_images(self, temp_db, test_user, tmp_path, monkeypatch):
        from models import create_post
        import export
        uploads = tmp_path / 'static' / 'uploads' / 'images'
        uploads.mkdir(parents=True)
        (uploads / 'demo.jpg').write_bytes(b'jpg')
        monkeypatch.setattr(export, 'BASE_DIR', tmp_path)
        create_post('Export post', 'body', True, None, test_user['id'])
        count, archive = export.export_full_archive(str(tmp_path / 'out'))
        assert count >= 1
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
        assert 'blog_export.json' in names
        assert 'images/demo.jpg' in names

    def test_safe_extract_rejects_path_traversal(self, tmp_path):
        from backend.routes.admin.import_export import _safe_extract_zip
        archive = tmp_path / 'evil.zip'
        with zipfile.ZipFile(archive, 'w') as zf:
            zf.writestr('../evil.txt', 'bad')
        with pytest.raises(ValueError):
            _safe_extract_zip(archive, tmp_path / 'out')


@pytest.mark.usefixtures('client')
class TestMobileAdminNav:
    def test_admin_pages_have_mobile_nav(self, client, temp_db, test_admin_user):
        _login(client, test_admin_user)
        page = client.get('/admin/comments').get_data(as_text=True)
        assert 'mobile-admin-nav' in page
