"""
统一搜索 API、语义搜索 API、相关内容 API 与搜索页语义模式的测试
"""

import json
import sqlite3
from array import array


import pytest


def _login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user['id']
        sess['username'] = user['username']


def _insert_embedding(db_path, source_type, source_id, vector):
    conn = sqlite3.connect(db_path)
    conn.execute('''
        INSERT INTO embeddings (source_type, source_id, model, vector)
        VALUES (?, ?, 'test-model', ?)
    ''', (source_type, source_id, array('f', vector).tobytes()))
    conn.commit()
    conn.close()


@pytest.fixture
def embeddings_table(temp_db):
    """创建 embeddings 表（与迁移 009 结构一致）"""
    conn = sqlite3.connect(temp_db)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            model TEXT,
            vector BLOB,
            content_hash TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_type, source_id)
        )
    ''')
    conn.commit()
    conn.close()
    return temp_db


@pytest.fixture
def configured_embedding(monkeypatch):
    """mock 已启用且可用的 embedding 配置"""
    config = {'enabled': True, 'base_url': 'https://example.com/v1',
              'api_key': 'test-key', 'model': 'test-model'}
    monkeypatch.setattr('routes.search_helpers.get_embedding_config',
                        lambda user_id: config)
    # 查询向量固定为 [1.0, 0.0]
    monkeypatch.setattr('routes.search_helpers.embed_text',
                        lambda text, config: [1.0, 0.0])
    return config


@pytest.fixture
def search_data(temp_db, test_user):
    """预置搜索数据：文章、知识库文档、卡片、批注"""
    from models import get_db_connection

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO posts (title, content, is_published, author_id, post_type, type)
        VALUES ('Python Flask 入门', '关于 Flask 框架的详细介绍内容', 1, ?, 'blog', 'post')
    ''', (test_user['id'],))
    blog_post_id = cur.lastrowid

    cur.execute('''
        INSERT INTO posts (title, content, is_published, author_id, post_type, type)
        VALUES ('Flask 草稿', '草稿内容 flask draft', 0, ?, 'blog', 'post')
    ''', (test_user['id'],))

    cur.execute('''
        INSERT INTO posts (title, content, is_published, author_id, post_type, type)
        VALUES ('Flask 知识笔记', '知识库中的 Flask 笔记内容', 0, ?, 'knowledge', 'post')
    ''', (test_user['id'],))
    doc_id = cur.lastrowid

    cur.execute('''
        INSERT INTO cards (user_id, title, content, tags, status, source)
        VALUES (?, 'Flask 卡片', '卡片里关于 Flask 的摘抄', '["flask","web"]', 'idea', 'web')
    ''', (test_user['id'],))
    card_id = cur.lastrowid

    cur.execute('''
        INSERT INTO cards (user_id, title, content, tags, status, source)
        VALUES (?, '无关卡片', '完全不同的主题内容', '[]', 'idea', 'web')
    ''', (test_user['id'],))

    cur.execute('''
        INSERT INTO card_annotations (user_id, card_id, source_url, annotation_text, note)
        VALUES (?, ?, 'https://example.com/a', 'Flask 的关键段落', '这是我的批注')
    ''', (test_user['id'], card_id))
    annotation_id = cur.lastrowid

    conn.commit()
    conn.close()

    return {
        'user': test_user,
        'blog_post_id': blog_post_id,
        'doc_id': doc_id,
        'card_id': card_id,
        'annotation_id': annotation_id,
    }


# ---------- 统一搜索 /api/search/all ----------


class TestUnifiedSearchApi:
    def test_unauthorized_returns_401(self, client):
        resp = client.get('/api/search/all?q=flask')
        assert resp.status_code == 401

    def test_empty_query_returns_empty_groups(self, client, test_user):
        _login(client, test_user)
        resp = client.get('/api/search/all')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == {'posts': [], 'cards': [], 'docs': [], 'annotations': []}

    def test_search_hits_all_groups(self, client, search_data):
        _login(client, search_data['user'])
        resp = client.get('/api/search/all?q=flask')
        assert resp.status_code == 200
        data = resp.get_json()

        # 只命中已发布 blog 文章
        assert len(data['posts']) == 1
        post = data['posts'][0]
        assert post['id'] == search_data['blog_post_id']
        assert post['type'] == 'post'
        assert post['url'].startswith('/post/')
        assert len(post['excerpt']) <= 120
        assert post['date']

        # 卡片命中，tags 解析为数组，url 为 null
        assert len(data['cards']) == 1
        card = data['cards'][0]
        assert card['id'] == search_data['card_id']
        assert card['tags'] == ['flask', 'web']
        assert card['url'] is None
        assert len(card['excerpt']) <= 120

        # 知识库文档命中（含未发布）
        assert len(data['docs']) == 1
        doc = data['docs'][0]
        assert doc['id'] == search_data['doc_id']
        assert doc['url'].startswith('/knowledge/doc/')

        # 批注命中
        assert len(data['annotations']) == 1
        ann = data['annotations'][0]
        assert ann['id'] == search_data['annotation_id']
        assert ann['card_id'] == search_data['card_id']
        assert ann['text'] == 'Flask 的关键段落'
        assert ann['source_url'] == 'https://example.com/a'

    def test_case_insensitive_and_no_match(self, client, search_data):
        _login(client, search_data['user'])
        resp = client.get('/api/search/all?q=FLASK')
        assert len(resp.get_json()['posts']) == 1

        resp = client.get('/api/search/all?q=不存在的词xyz')
        data = resp.get_json()
        assert data['posts'] == [] and data['cards'] == [] \
            and data['docs'] == [] and data['annotations'] == []

    def test_limit_applies_per_group(self, client, test_user):
        from models import get_db_connection
        _login(client, test_user)
        conn = get_db_connection()
        for i in range(8):
            conn.execute('''
                INSERT INTO posts (title, content, is_published, author_id, post_type)
                VALUES (?, 'limit test content', 1, ?, 'blog')
            ''', (f'limit post {i}', test_user['id']))
        conn.commit()
        conn.close()

        resp = client.get('/api/search/all?q=limit&limit=3')
        assert len(resp.get_json()['posts']) == 3
        resp = client.get('/api/search/all?q=limit')
        assert len(resp.get_json()['posts']) == 6  # 默认 limit


# ---------- 语义搜索 /api/search/semantic ----------


class TestSemanticSearchApi:
    def test_unauthorized_returns_401(self, client):
        resp = client.get('/api/search/semantic?q=flask')
        assert resp.status_code == 401

    def test_not_configured_returns_400(self, client, test_user):
        _login(client, test_user)
        resp = client.get('/api/search/semantic?q=flask')
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'embedding_not_configured'

    def test_semantic_groups_and_filters(self, client, search_data,
                                         embeddings_table, configured_embedding):
        _login(client, search_data['user'])

        # post 向量与查询 [1,0] 同向；doc 垂直（score 0）；短内容卡片应被加载
        _insert_embedding(embeddings_table, 'post', search_data['blog_post_id'], [1.0, 0.0])
        _insert_embedding(embeddings_table, 'post',
                          search_data['blog_post_id'] + 1, [1.0, 0.0])  # 草稿，应被过滤
        _insert_embedding(embeddings_table, 'doc', search_data['doc_id'], [0.0, 1.0])
        _insert_embedding(embeddings_table, 'card', search_data['card_id'], [0.9, 0.1])

        resp = client.get('/api/search/semantic?q=flask 框架')
        assert resp.status_code == 200
        data = resp.get_json()

        assert len(data['posts']) == 1  # 草稿 post 被过滤
        post = data['posts'][0]
        assert post['id'] == search_data['blog_post_id']
        assert post['score'] == 1.0
        assert 'excerpt' in post and 'url' in post and 'title' in post

        assert len(data['docs']) == 1
        assert data['docs'][0]['id'] == search_data['doc_id']
        assert data['docs'][0]['score'] == 0.0

        assert len(data['cards']) == 1
        assert data['cards'][0]['id'] == search_data['card_id']
        assert 0.9 < data['cards'][0]['score'] < 1.0
        assert data['cards'][0]['url'] is None

    def test_semantic_api_error_returns_502(self, client, search_data,
                                            embeddings_table, configured_embedding,
                                            monkeypatch):
        _login(client, search_data['user'])

        def _broken(text, config):
            raise RuntimeError('connection refused by upstream')

        monkeypatch.setattr('routes.search_helpers.embed_text', _broken)
        resp = client.get('/api/search/semantic?q=flask')
        assert resp.status_code == 502
        data = resp.get_json()
        assert data['error'] == 'embedding_api_error'
        assert 'connection refused' in data['detail']

    def test_semantic_empty_query(self, client, test_user, configured_embedding):
        _login(client, test_user)
        resp = client.get('/api/search/semantic')
        assert resp.status_code == 200
        assert resp.get_json() == {'posts': [], 'cards': [], 'docs': []}


# ---------- 相关内容 /api/related ----------


class TestRelatedApi:
    def _payload(self, **kwargs):
        payload = {'text': '这是一段用于查找相关内容的基准文本，长度超过二十个字符。'}
        payload.update(kwargs)
        return payload

    def test_unauthorized_returns_401(self, client):
        resp = client.post('/api/related', data=json.dumps(self._payload()),
                           content_type='application/json')
        assert resp.status_code == 401

    def test_text_too_short(self, client, test_user, configured_embedding):
        _login(client, test_user)
        resp = client.post('/api/related', data=json.dumps(self._payload(text='太短')),
                           content_type='application/json')
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'text_too_short'

    def test_not_configured(self, client, test_user):
        _login(client, test_user)
        resp = client.post('/api/related', data=json.dumps(self._payload()),
                           content_type='application/json')
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'embedding_not_configured'

    def test_related_items_exclude_and_limit(self, client, search_data,
                                             embeddings_table, configured_embedding):
        _login(client, search_data['user'])
        _insert_embedding(embeddings_table, 'post', search_data['blog_post_id'], [1.0, 0.0])
        _insert_embedding(embeddings_table, 'doc', search_data['doc_id'], [0.99, 0.01])
        _insert_embedding(embeddings_table, 'card', search_data['card_id'], [0.98, 0.02])

        resp = client.post('/api/related',
                           data=json.dumps(self._payload(
                               exclude_type='post',
                               exclude_id=search_data['blog_post_id'])),
                           content_type='application/json')
        assert resp.status_code == 200
        items = resp.get_json()['items']

        # post 被排除，只剩 doc 和 card
        assert all(i['source_type'] != 'post' for i in items)
        assert {i['source_type'] for i in items} == {'doc', 'card'}
        for item in items:
            assert set(item.keys()) == {'source_type', 'source_id', 'title',
                                        'excerpt', 'url', 'score'}
        # 按 score 降序
        scores = [i['score'] for i in items]
        assert scores == sorted(scores, reverse=True)

    def test_related_excludes_short_entities(self, client, test_user,
                                             embeddings_table, configured_embedding):
        from models import get_db_connection
        _login(client, test_user)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO posts (title, content, is_published, author_id, post_type)
            VALUES ('短', '短', 1, ?, 'blog')
        ''', (test_user['id'],))
        short_id = cur.lastrowid
        cur.execute('''
            INSERT INTO posts (title, content, is_published, author_id, post_type)
            VALUES ('足够长的文章标题', '这是一段足够长的文章内容，用来通过最短长度过滤的检查。', 1, ?, 'blog')
        ''', (test_user['id'],))
        long_id = cur.lastrowid
        conn.commit()
        conn.close()

        _insert_embedding(embeddings_table, 'post', short_id, [1.0, 0.0])
        _insert_embedding(embeddings_table, 'post', long_id, [1.0, 0.0])

        resp = client.post('/api/related', data=json.dumps(self._payload()),
                           content_type='application/json')
        items = resp.get_json()['items']
        assert all(i['source_id'] != short_id for i in items)
        assert any(i['source_id'] == long_id for i in items)

    def test_related_api_error_returns_502(self, client, test_user,
                                           configured_embedding, monkeypatch):
        _login(client, test_user)

        def _broken(text, config):
            raise ValueError('bad api key')

        monkeypatch.setattr('routes.search_helpers.embed_text', _broken)
        resp = client.post('/api/related', data=json.dumps(self._payload()),
                           content_type='application/json')
        assert resp.status_code == 502
        assert resp.get_json()['error'] == 'embedding_api_error'


# ---------- 搜索页语义模式 ----------


class TestSearchPageSemantic:
    def test_semantic_tab_renders_guide_when_not_configured(self, client, test_user):
        _login(client, test_user)
        resp = client.get('/search?q=flask&source=semantic')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert '语义' in html
        assert '启用 Embedding' in html
        assert '/admin/ai/configure' in html

    def test_semantic_results_rendered_with_badge(self, client, search_data,
                                                  embeddings_table, configured_embedding):
        _login(client, search_data['user'])
        _insert_embedding(embeddings_table, 'post', search_data['blog_post_id'], [1.0, 0.0])
        _insert_embedding(embeddings_table, 'doc', search_data['doc_id'], [0.5, 0.5])

        resp = client.get('/search?q=flask&source=semantic')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'semantic-badge' in html
        assert '100%' in html
        assert 'Flask 入门' in html or 'Flask' in html
        # 语义模式不做关键词高亮
        assert '<mark>' not in html

    def test_keyword_search_unchanged(self, client, search_data):
        _login(client, search_data['user'])
        resp = client.get('/search?q=flask&source=all')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'source-tab' in html
