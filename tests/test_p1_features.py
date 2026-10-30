"""P1 体验优化回归测试。"""

import pytest
from werkzeug.security import generate_password_hash


def _login(client, user, password=None):
    return client.post('/login', data={
        'username': user['username'],
        'password': password or user['password'],
    })


@pytest.mark.usefixtures('client')
class TestDraftsAndRevisions:
    def test_multi_device_drafts_are_kept_separately(self, temp_db, test_user):
        from models.draft import save_draft, get_drafts

        first = save_draft(test_user['id'], 10, 'A', 'content A', device_token='tab-a')
        second = save_draft(test_user['id'], 10, 'B', 'content B', device_token='tab-b')
        assert first['draft_id'] != second['draft_id']
        assert len(get_drafts(test_user['id'], 10)) == 2
        assert second['status'] == 'conflict_detected'

    def test_same_token_updates_one_draft(self, temp_db, test_user):
        from models.draft import save_draft, get_drafts

        save_draft(test_user['id'], 11, 'A', 'one', device_token='same-tab')
        save_draft(test_user['id'], 11, 'B', 'two', device_token='same-tab')
        drafts = get_drafts(test_user['id'], 11)
        assert len(drafts) == 1
        assert drafts[0]['title'] == 'B'

    def test_update_creates_revision_and_restore_works(self, temp_db, test_user):
        from models import create_post, update_post, get_post_by_id, get_post_revisions, restore_post_revision

        post_id = create_post('Original', 'body one', True, None, test_user['id'])
        update_post(post_id, 'Changed', 'body two', True)
        revisions = get_post_revisions(post_id)
        assert revisions
        assert restore_post_revision(revisions[0]['id']) is True
        assert get_post_by_id(post_id)['title'] == 'Original'


@pytest.mark.usefixtures('client')
class TestSoftDeleteAndScheduling:
    def test_soft_delete_and_restore(self, temp_db, test_admin_user):
        from models import create_post, get_post_by_id, soft_delete_post, restore_deleted_post, get_deleted_posts

        post_id = create_post('Trash me', 'body', True, None, test_admin_user['id'])
        assert soft_delete_post(post_id) is True
        assert get_post_by_id(post_id) is None
        assert any(p['id'] == post_id for p in get_deleted_posts())
        assert restore_deleted_post(post_id) is True
        assert get_post_by_id(post_id)['title'] == 'Trash me'

    def test_trash_and_revision_pages_render(self, client, temp_db, test_admin_user):
        from models import create_post, update_post
        post_id = create_post('Revision page', 'one', True, None, test_admin_user['id'])
        update_post(post_id, 'Revision page v2', 'two', True)
        _login(client, test_admin_user)
        assert client.get(f'/admin/revisions/{post_id}').status_code == 200
        assert client.get('/admin/trash').status_code == 200

    def test_publish_due_posts(self, temp_db, test_admin_user):
        from models import create_post, get_post_by_id, get_db_connection, publish_due_posts

        post_id = create_post('Scheduled', 'body', False, None, test_admin_user['id'])
        conn = get_db_connection()
        conn.execute("UPDATE posts SET publish_at = datetime('now', '-1 minute') WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()

        assert publish_due_posts() >= 1
        assert get_post_by_id(post_id)['is_published'] == 1


@pytest.mark.usefixtures('client')
class TestAdminFiltersAndTaxonomy:
    def test_admin_dashboard_search_and_status_filters(self, client, temp_db, test_admin_user):
        from models import create_post
        create_post('Unique Draft Target', 'alpha body', False, None, test_admin_user['id'])
        create_post('Published Other', 'beta body', True, None, test_admin_user['id'])
        _login(client, test_admin_user)

        page = client.get('/admin?q=Unique%20Draft%20Target&status=draft').get_data(as_text=True)
        assert 'Unique Draft Target' in page
        assert 'Published Other' not in page

    def test_dashboard_post_ids_respects_filters(self, client, temp_db, test_admin_user):
        from models import create_post
        published_id = create_post('Ids published', 'body', True, None, test_admin_user['id'])
        draft_id = create_post('Ids draft', 'body', False, None, test_admin_user['id'])
        _login(client, test_admin_user)

        data = client.get('/admin/post-ids?status=draft').get_json()
        assert data['success'] is True
        assert data['ids'] == [draft_id]
        assert published_id not in data['ids']

    def test_admin_dashboard_like_wildcards_are_literal(self, client, temp_db, test_admin_user):
        from models import create_post
        create_post('Percent post', 'discount 50% today', True, None, test_admin_user['id'])
        create_post('Plain post', 'no special characters', True, None, test_admin_user['id'])
        _login(client, test_admin_user)

        page = client.get('/admin?q=%25').get_data(as_text=True)
        assert 'Percent post' in page
        assert 'Plain post' not in page

    def test_admin_dashboard_out_of_range_page_clamps_to_last(self, client, temp_db, test_admin_user):
        from models import create_post
        for i in range(12):
            create_post(f'Page post {i}', 'body', True, None, test_admin_user['id'])
        _login(client, test_admin_user)

        page = client.get('/admin?page=99&per_page=10').get_data(as_text=True)
        assert 'Page post' in page

    def test_admin_dashboard_empty_filter_values_do_not_hide_posts(self, client, temp_db, test_admin_user):
        from models import create_post
        create_post('Visible With Empty Filters', 'body', True, None, test_admin_user['id'])
        _login(client, test_admin_user)

        page = client.get('/admin?q=&status=&access_level=&category_id=&type=&author_id=&per_page=20').get_data(as_text=True)
        assert 'Visible With Empty Filters' in page

    def test_admin_dashboard_empty_result_keeps_filter_controls(self, client, temp_db, test_admin_user):
        from models import create_post
        create_post('Some post', 'body', True, None, test_admin_user['id'])
        _login(client, test_admin_user)

        page = client.get('/admin?q=definitely-no-match').get_data(as_text=True)
        assert '没有符合筛选条件的文章' in page
        assert 'name="status"' in page
        assert 'name="q"' in page

    def test_category_rename_and_merge(self, client, temp_db, test_admin_user):
        from models import create_category, create_post, get_category_by_id
        source = create_category('OldCat')
        target = create_category('NewCat')
        post_id = create_post('Categorized', 'body', True, source, test_admin_user['id'])
        _login(client, test_admin_user)

        client.post(f'/admin/categories/{source}/rename', data={'name': 'RenamedCat'})
        assert get_category_by_id(source)['name'] == 'RenamedCat'

        client.post(f'/admin/categories/{source}/merge', data={'target_id': target})
        from models import get_post_by_id
        assert get_post_by_id(post_id)['category_id'] == target


@pytest.mark.usefixtures('client')
class TestKnowledgePermissionsAndSearch:
    def _other_user(self):
        from models import create_user
        return create_user('other', generate_password_hash('OtherPass123!', method='pbkdf2:sha256'), role='author')

    def test_other_user_cannot_view_or_edit_private_doc(self, client, temp_db, test_user):
        from models import create_kb_category, create_knowledge_doc
        self._other_user()
        cat_id = create_kb_category('Private KB', space='knowledge')
        doc_id = create_knowledge_doc('Private doc', 'secret body', cat_id, is_published=False, author_id=test_user['id'])

        client.post('/login', data={'username': 'other', 'password': 'OtherPass123!'})
        assert client.get(f'/knowledge/doc/{doc_id}').status_code == 404
        assert client.post(f'/knowledge/doc/{doc_id}/edit', data={
            'title': 'Hacked', 'content': 'x', 'category_id': cat_id,
        }).status_code == 403

    def test_knowledge_search_filters_and_pagination(self, temp_db, test_user):
        from models import create_kb_category, create_knowledge_doc, search_knowledge_docs
        cat_id = create_kb_category('Search KB', space='knowledge')
        for i in range(3):
            create_knowledge_doc(f'Alpha {i}', 'needle body', cat_id, author_id=test_user['id'])

        result = search_knowledge_docs('Alpha', viewer_id=test_user['id'], viewer_role='author',
                                       page=1, per_page=1, category_id=cat_id)
        assert result['total'] == 3
        assert result['total_pages'] == 3
        assert len(result['posts']) == 1

    def test_category_rename_and_batch_move(self, client, temp_db, test_admin_user):
        from models import create_kb_category, create_knowledge_doc, get_knowledge_doc
        source = create_kb_category('Source', space='knowledge')
        target = create_kb_category('Target', space='knowledge')
        doc_id = create_knowledge_doc('Movable', 'body', source, author_id=test_admin_user['id'])
        _login(client, test_admin_user)

        client.post(f'/knowledge/category/{source}/rename', data={'name': 'Renamed'})
        response = client.post('/knowledge/docs/move', data={'doc_ids': str(doc_id), 'category_id': target})
        assert response.get_json()['success'] is True
        assert get_knowledge_doc(doc_id)['category_id'] == target

    def test_knowledge_index_renders_tree_docs(self, client, temp_db, test_admin_user):
        from models import create_kb_category, create_knowledge_doc
        cat_id = create_kb_category('Tree cat', space='knowledge')
        create_knowledge_doc('Tree doc title', 'body', cat_id, author_id=test_admin_user['id'])
        _login(client, test_admin_user)
        page = client.get('/knowledge/').get_data(as_text=True)
        assert 'Tree doc title' in page
        assert 'kb-tree-docs collapsed' in page

    def test_uncategorized_documents_page(self, client, temp_db, test_admin_user):
        from models import create_knowledge_doc
        create_knowledge_doc('Orphan doc', 'body', None, author_id=test_admin_user['id'])
        _login(client, test_admin_user)
        page = client.get('/knowledge/documents?scope=uncategorized').get_data(as_text=True)
        assert 'Orphan doc' in page
