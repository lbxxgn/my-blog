# -*- coding: utf-8 -*-
"""Embedding 语义搜索基础设施测试

覆盖：
- 迁移 009 幂等性
- models/embeddings 的 upsert/get/delete/search_similar（余弦相似度）
- embedding_task 的入队跳过逻辑（未启用 no-op / 内容未变跳过）
- 保存钩子与删除钩子
- rebuild 端点权限与入队

所有 HTTP embedding API 调用均通过 mock 隔离，测试不联网。
"""

import hashlib
import sqlite3
import time
from unittest import mock

import pytest

MOCK_VECTOR = [0.25, 0.5, 0.5, 0.25]


@pytest.fixture
def embedding_db(temp_db):
    """在 temp_db 基础上应用迁移 009，并重置任务队列的全局启用缓存"""
    from backend.migrations.migrate_embeddings import migrate
    assert migrate() is True

    from tasks.embedding_task import reset_enabled_cache
    reset_enabled_cache()
    yield temp_db
    reset_enabled_cache()


@pytest.fixture
def mock_embed_text():
    """mock ai_services.embeddings.embed_text，禁止任何真实 API 调用"""
    with mock.patch('ai_services.embeddings.embed_text',
                    return_value=list(MOCK_VECTOR)) as m:
        yield m


@pytest.fixture
def embedding_user(embedding_db):
    """创建了启用 Embedding 的普通用户"""
    from models import create_user
    from ai_services.embeddings import update_embedding_config

    user_id = create_user('emb_user', 'fake-hash', role='author')
    update_embedding_config(user_id, {
        'ai_embedding_enabled': True,
        'ai_embedding_api_key': 'sk-test-key',
    })
    return user_id


def _wait_for_embedding(source_type, source_id, timeout=5.0):
    """轮询等待后台 worker 写入向量"""
    from models.embeddings import get_embedding
    deadline = time.time() + timeout
    while time.time() < deadline:
        record = get_embedding(source_type, source_id)
        if record:
            return record
        time.sleep(0.05)
    return None


class TestMigration009:
    """迁移 009：embeddings 表 + users 表 ai_embedding_* 列"""

    def test_migrate_creates_table_and_columns(self, temp_db):
        from backend.migrations.migrate_embeddings import migrate
        assert migrate() is True

        conn = sqlite3.connect(temp_db)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            assert 'embeddings' in tables

            columns = {r[1] for r in conn.execute('PRAGMA table_info(embeddings)')}
            assert {'id', 'source_type', 'source_id', 'model',
                    'vector', 'content_hash', 'updated_at'} <= columns

            user_columns = {r[1] for r in conn.execute('PRAGMA table_info(users)')}
            assert {'ai_embedding_enabled', 'ai_embedding_base_url',
                    'ai_embedding_api_key', 'ai_embedding_model'} <= user_columns
        finally:
            conn.close()

    def test_migrate_is_idempotent(self, temp_db):
        """连续执行两次不报错"""
        from backend.migrations.migrate_embeddings import migrate
        assert migrate() is True
        assert migrate() is True

    def test_unique_constraint(self, embedding_db):
        """(source_type, source_id) 唯一"""
        from models.embeddings import get_embedding, upsert_embedding
        upsert_embedding('post', 1, [1.0, 0.0], model='m1')
        upsert_embedding('post', 1, [0.0, 1.0], model='m2')  # 应更新而非插入

        conn = sqlite3.connect(embedding_db)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM embeddings WHERE source_type='post' AND source_id=1"
            ).fetchone()[0]
        finally:
            conn.close()
        assert count == 1
        assert get_embedding('post', 1)['model'] == 'm2'


class TestEmbeddingModel:
    """models/embeddings 的 CRUD 与相似度检索"""

    def test_upsert_and_get(self, embedding_db):
        from models.embeddings import get_embedding, upsert_embedding

        upsert_embedding('post', 1, [1.0, 0.0, 0.0], model='m1', content_hash='h1')
        record = get_embedding('post', 1)
        assert record['model'] == 'm1'
        assert record['content_hash'] == 'h1'
        assert record['vector'] == pytest.approx([1.0, 0.0, 0.0])

        # upsert 覆盖
        upsert_embedding('post', 1, [0.0, 1.0, 0.0], model='m2', content_hash='h2')
        record = get_embedding('post', 1)
        assert record['model'] == 'm2'
        assert record['vector'] == pytest.approx([0.0, 1.0, 0.0])

    def test_get_missing_returns_none(self, embedding_db):
        from models.embeddings import get_embedding
        assert get_embedding('card', 999) is None

    def test_delete(self, embedding_db):
        from models.embeddings import delete_embedding, get_embedding, upsert_embedding

        upsert_embedding('card', 5, [1.0, 0.0], model='m1')
        assert delete_embedding('card', 5) is True
        assert get_embedding('card', 5) is None
        assert delete_embedding('card', 5) is False  # 已删除，幂等

    def test_invalid_source_type_rejected(self, embedding_db):
        from models.embeddings import upsert_embedding
        with pytest.raises(ValueError):
            upsert_embedding('bogus', 1, [1.0])

    def test_search_similar_order_and_scores(self, embedding_db):
        """top-k 顺序与余弦相似度正确性"""
        from models.embeddings import search_similar, upsert_embedding

        upsert_embedding('post', 1, [1.0, 0.0, 0.0], model='m')
        upsert_embedding('post', 2, [0.9, 0.1, 0.0], model='m')
        upsert_embedding('card', 3, [0.0, 1.0, 0.0], model='m')
        upsert_embedding('doc', 4, [-1.0, 0.0, 0.0], model='m')

        results = search_similar([1.0, 0.0, 0.0], top_k=4)

        assert [(st, sid) for st, sid, _ in results] == [
            ('post', 1), ('post', 2), ('card', 3), ('doc', 4)
        ]
        # 余弦值：同向为 1，正交的为 0，反向的为 -1
        assert results[0][2] == pytest.approx(1.0)
        assert results[1][2] == pytest.approx(0.9 / (0.82 ** 0.5), rel=1e-5)
        assert results[2][2] == pytest.approx(0.0, abs=1e-6)
        assert results[3][2] == pytest.approx(-1.0)

    def test_search_similar_top_k(self, embedding_db):
        from models.embeddings import search_similar, upsert_embedding

        for i in range(5):
            upsert_embedding('post', i + 1, [1.0, i * 0.01], model='m')

        results = search_similar([1.0, 0.0], top_k=3)
        assert len(results) == 3
        # 最相似的应是 i=0（完全同向）
        assert results[0] == ('post', 1, pytest.approx(1.0))

    def test_search_similar_source_type_filter(self, embedding_db):
        from models.embeddings import search_similar, upsert_embedding

        upsert_embedding('post', 1, [1.0, 0.0], model='m')
        upsert_embedding('card', 2, [1.0, 0.0], model='m')
        upsert_embedding('doc', 3, [1.0, 0.0], model='m')

        results = search_similar([1.0, 0.0], source_types=['card', 'doc'])
        assert {(st, sid) for st, sid, _ in results} == {('card', 2), ('doc', 3)}

    def test_search_similar_empty_table(self, embedding_db):
        from models.embeddings import search_similar
        assert search_similar([1.0, 0.0]) == []


class TestEmbeddingTask:
    """embedding_task 的入队与跳过逻辑"""

    def test_enqueue_noop_when_globally_disabled(self, embedding_db, mock_embed_text, test_user):
        """无任何用户启用时，enqueue 快速返回 None（连 worker 都不启动）"""
        from models import create_post
        from tasks.embedding_task import enqueue_embedding

        post_id = create_post(title='T', content='C', author_id=test_user['id'])
        assert enqueue_embedding('post', post_id) is None
        assert mock_embed_text.call_count == 0

    def test_process_writes_vector_when_enabled(self, embedding_db, mock_embed_text, embedding_user):
        """启用后保存文章，钩子触发后台生成向量"""
        from models import create_post

        post_id = create_post(title='Hello', content='World content', author_id=embedding_user)

        record = _wait_for_embedding('post', post_id)
        assert record is not None
        assert record['vector'] == pytest.approx(MOCK_VECTOR)
        assert record['model'] == 'BAAI/bge-m3'  # 默认模型
        expected_hash = hashlib.sha256('Hello\nWorld content'.encode('utf-8')).hexdigest()
        assert record['content_hash'] == expected_hash

    def test_skip_when_content_unchanged(self, embedding_db, mock_embed_text, test_user):
        """内容未变（content_hash 与模型一致）时跳过，不重复调用 API"""
        from models import create_post
        from ai_services.embeddings import update_embedding_config
        from tasks.embedding_task import enqueue_embedding

        # 未启用时创建（钩子在快速路径返回），避免后台线程竞争
        post_id = create_post(title='T1', content='Body', author_id=test_user['id'])
        assert mock_embed_text.call_count == 0

        update_embedding_config(test_user['id'], {
            'ai_embedding_enabled': True,
            'ai_embedding_api_key': 'sk-test-key',
        })

        future = enqueue_embedding('post', post_id)
        assert future is not None
        assert future.result(timeout=10) is True
        assert mock_embed_text.call_count == 1

        # 内容未变：再次入队应跳过
        future = enqueue_embedding('post', post_id)
        assert future.result(timeout=10) is False
        assert mock_embed_text.call_count == 1

    def test_reembed_when_content_changes(self, embedding_db, mock_embed_text, embedding_user):
        """内容变化后重新生成向量"""
        from models import create_post, update_post
        from models.embeddings import get_embedding

        post_id = create_post(title='T2', content='Old body', author_id=embedding_user)
        assert _wait_for_embedding('post', post_id) is not None

        update_post(post_id, 'T2', 'Changed body', True)

        expected_hash = hashlib.sha256('T2\nChanged body'.encode('utf-8')).hexdigest()
        deadline = time.time() + 5
        record = None
        while time.time() < deadline:
            record = get_embedding('post', post_id)
            if record and record['content_hash'] == expected_hash:
                break
            time.sleep(0.05)
        assert record is not None
        assert record['content_hash'] == expected_hash

    def test_knowledge_doc_uses_doc_source_type(self, embedding_db, mock_embed_text, test_user):
        """post_type='knowledge' 的文章归入 'doc' 类型"""
        from models import create_post
        from ai_services.embeddings import update_embedding_config
        from models.embeddings import get_embedding
        from tasks.embedding_task import enqueue_embedding

        post_id = create_post(title='Doc', content='Knowledge', author_id=test_user['id'],
                              post_type='knowledge')
        update_embedding_config(test_user['id'], {
            'ai_embedding_enabled': True,
            'ai_embedding_api_key': 'sk-test-key',
        })

        # 即使以 'post' 入队，worker 也会按实际 post_type 归为 'doc'
        future = enqueue_embedding('post', post_id)
        assert future.result(timeout=10) is True
        assert get_embedding('doc', post_id) is not None
        assert get_embedding('post', post_id) is None

    def test_card_embedding_and_delete_hook(self, embedding_db, mock_embed_text, test_user):
        """卡片生成向量；删除卡片时钩子同步清理"""
        from models import create_card, delete_card
        from ai_services.embeddings import update_embedding_config
        from models.embeddings import get_embedding
        from tasks.embedding_task import enqueue_embedding

        card_id = create_card(test_user['id'], 'Card title', 'Card content')
        update_embedding_config(test_user['id'], {
            'ai_embedding_enabled': True,
            'ai_embedding_api_key': 'sk-test-key',
        })

        future = enqueue_embedding('card', card_id)
        assert future.result(timeout=10) is True
        assert get_embedding('card', card_id) is not None

        delete_card(card_id)
        assert get_embedding('card', card_id) is None

    def test_delete_post_hook_removes_embedding(self, embedding_db, mock_embed_text, test_user):
        from models import create_post, delete_post
        from ai_services.embeddings import update_embedding_config
        from models.embeddings import get_embedding
        from tasks.embedding_task import enqueue_embedding

        post_id = create_post(title='T3', content='To be deleted', author_id=test_user['id'])
        update_embedding_config(test_user['id'], {
            'ai_embedding_enabled': True,
            'ai_embedding_api_key': 'sk-test-key',
        })

        assert enqueue_embedding('post', post_id).result(timeout=10) is True
        assert get_embedding('post', post_id) is not None

        delete_post(post_id)
        assert get_embedding('post', post_id) is None
        assert get_embedding('doc', post_id) is None


class TestEmbeddingConfigService:
    """ai_services.embeddings 的配置读写"""

    def test_config_roundtrip(self, embedding_db, test_user):
        from ai_services.embeddings import get_embedding_config, update_embedding_config

        # 默认：未启用
        config = get_embedding_config(test_user['id'])
        assert config['enabled'] is False
        assert config['base_url'] == 'https://api.siliconflow.cn/v1'
        assert config['model'] == 'BAAI/bge-m3'
        assert config['api_key'] is None

        update_embedding_config(test_user['id'], {
            'ai_embedding_enabled': True,
            'ai_embedding_api_key': 'sk-abc',
            'ai_embedding_base_url': 'https://example.com/v1',
            'ai_embedding_model': 'custom-model',
        })
        config = get_embedding_config(test_user['id'])
        assert config['enabled'] is True
        assert config['api_key'] == 'sk-abc'
        assert config['base_url'] == 'https://example.com/v1'
        assert config['model'] == 'custom-model'

    def test_config_missing_user(self, embedding_db):
        from ai_services.embeddings import get_embedding_config
        assert get_embedding_config(99999) is None

    def test_test_connection_without_key(self, embedding_db):
        from ai_services.embeddings import test_embedding_connection
        result = test_embedding_connection({'api_key': None})
        assert result['success'] is False


class TestRebuildEndpoint:
    """POST /admin/ai/embeddings/rebuild 权限与入队"""

    def test_rebuild_requires_login(self, client, embedding_db):
        response = client.post('/admin/ai/embeddings/rebuild')
        assert response.status_code in (302, 401)

    def test_rebuild_forbidden_for_author(self, client, embedding_db, test_user):
        client.post('/login', data={
            'username': test_user['username'],
            'password': test_user['password']
        })
        response = client.post('/admin/ai/embeddings/rebuild')
        # 非管理员被重定向
        assert response.status_code in (302, 401, 403)

    def test_rebuild_enqueues_all_content(self, client, embedding_db, mock_embed_text, test_admin_user):
        from models import create_card, create_post
        from ai_services.embeddings import update_embedding_config

        admin_id = test_admin_user['id']
        # 启用前先创建内容，避免钩子触发后台线程竞争
        create_post(title='P1', content='c1', author_id=admin_id)
        create_post(title='D1', content='c2', author_id=admin_id, post_type='knowledge')
        create_card(admin_id, 'Card1', 'c3')

        update_embedding_config(admin_id, {
            'ai_embedding_enabled': True,
            'ai_embedding_api_key': 'sk-test-key',
        })

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        response = client.post('/admin/ai/embeddings/rebuild')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['enqueued'] == 3

    def test_rebuild_reports_zero_when_nobody_enabled(self, client, embedding_db, mock_embed_text, test_admin_user):
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })
        response = client.post('/admin/ai/embeddings/rebuild')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['enqueued'] == 0
