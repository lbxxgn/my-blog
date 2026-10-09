# -*- coding: utf-8 -*-
"""011 内容格式标注纠偏迁移测试（backend/migrations/migrate_content_format.py）"""
import importlib
import os
import sqlite3
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import backend.config as config

from backend.migrations.migrate_content_format import _detect_format, migrate


@pytest.fixture()
def migration_db():
    """带完整初始 schema 的临时数据库，并让 config 指向它"""
    os.environ['TESTING'] = '1'
    db_path = tempfile.gettempdir() + f'/test_content_format_{uuid.uuid4().hex}.db'
    original_env = os.environ.get('DATABASE_URL')

    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    importlib.reload(config)

    import models
    models.init_db()

    yield db_path

    if original_env is not None:
        os.environ['DATABASE_URL'] = original_env
    else:
        os.environ.pop('DATABASE_URL', None)
    importlib.reload(config)
    if os.path.exists(db_path):
        os.remove(db_path)


class TestDetectFormat:
    def test_block_html_detected_as_html(self):
        assert _detect_format('<p>段落</p><p><img src="x"></p>') == 'html'
        assert _detect_format('<h2>标题</h2>\n<ul><li>条目</li></ul>') == 'html'
        assert _detect_format('文字<br>换行') == 'html'

    def test_plain_markdown_detected_as_markdown(self):
        assert _detect_format('# 标题\n\n正文 snake_case 和 2026_10_09') == 'markdown'
        assert _detect_format('只有一段话') == 'markdown'
        assert _detect_format('') == 'markdown'

    def test_inline_tags_do_not_flip_to_html(self):
        """Markdown 正文里偶发的行内标签（em/a/img）不应误判为 HTML 格式"""
        assert _detect_format('正文 <em>斜体</em> 和 [链接](https://example.com)') == 'markdown'
        assert _detect_format('见 <img src="/static/uploads/images/x_y.png"> 图') == 'markdown'


@pytest.mark.usefixtures('migration_db')
class TestMigrateContentFormat:
    def _seed(self, db_path, rows):
        conn = sqlite3.connect(db_path)
        try:
            conn.executemany(
                "INSERT INTO posts (title, content, content_format) VALUES (?, ?, ?)", rows
            )
            conn.commit()
        finally:
            conn.close()

    def _formats(self, db_path):
        conn = sqlite3.connect(db_path)
        try:
            return dict(conn.execute('SELECT id, content_format FROM posts').fetchall())
        finally:
            conn.close()

    def test_relabels_mislabeled_posts(self, migration_db):
        self._seed(migration_db, [
            (1, '<p>Quill 富文本</p>', 'html'),                    # 保持 html
            (2, '# Markdown 正文\n\nsnake_case', 'html'),           # 纠偏为 markdown
            (3, '纯文本随手记 2026_10_09', None),                   # NULL 纠偏为 markdown
            (4, '已是 markdown', 'markdown'),                       # 不动
        ])

        assert migrate() is True

        formats = self._formats(migration_db)
        assert formats == {1: 'html', 2: 'markdown', 3: 'markdown', 4: 'markdown'}

    def test_idempotent(self, migration_db):
        self._seed(migration_db, [
            (1, '纯文本', 'html'),
        ])

        assert migrate() is True
        first = self._formats(migration_db)
        assert migrate() is True
        assert self._formats(migration_db) == first
