"""文章/知识库文档修订历史与回收站辅助。

修订在更新正文前自动生成快照；回收站使用 posts.deleted_at 软删除。
"""

import json
import logging

from .db import get_db_connection, get_db_context, _safe_replace_post_fts, _safe_delete_post_fts

logger = logging.getLogger(__name__)

__all__ = [
    'ensure_revisions_table',
    'create_post_revision',
    'get_post_revisions',
    'get_post_revision',
    'restore_post_revision',
    'soft_delete_post',
    'restore_deleted_post',
    'get_deleted_posts',
    'purge_deleted_post',
    'publish_due_posts',
]


def ensure_revisions_table():
    with get_db_context() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS post_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_format TEXT DEFAULT 'html',
                category_id INTEGER,
                tags_json TEXT,
                access_level TEXT DEFAULT 'public',
                access_password TEXT,
                post_type TEXT DEFAULT 'blog',
                type TEXT DEFAULT 'post',
                author_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_revisions_post ON post_revisions(post_id, created_at DESC)')


def _load_tags(conn, post_id):
    rows = conn.execute('SELECT name FROM tags JOIN post_tags ON tags.id = post_tags.tag_id WHERE post_tags.post_id = ?', (post_id,)).fetchall()
    return [row['name'] for row in rows]


def create_post_revision(post_id):
    """保存当前文章快照。返回 revision_id，不存在时返回 None。"""
    ensure_revisions_table()
    with get_db_context() as conn:
        row = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
        if not row:
            return None
        tags = _load_tags(conn, post_id)
        cursor = conn.execute('''
            INSERT INTO post_revisions
                (post_id, title, content, content_format, category_id, tags_json,
                 access_level, access_password, post_type, type, author_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['id'], row['title'], row['content'], row['content_format'] or 'html',
            row['category_id'], json.dumps(tags, ensure_ascii=False),
            row['access_level'] or 'public', row['access_password'],
            row['post_type'] or 'blog', row['type'] or 'post', row['author_id'],
        ))
        revision_id = cursor.lastrowid
        # 每个文章保留最近 100 个版本
        conn.execute('''
            DELETE FROM post_revisions WHERE post_id = ? AND id NOT IN (
                SELECT id FROM post_revisions WHERE post_id = ? ORDER BY id DESC LIMIT 100
            )
        ''', (post_id, post_id))
        return revision_id


def get_post_revisions(post_id, limit=50):
    ensure_revisions_table()
    with get_db_context() as conn:
        rows = conn.execute('''
            SELECT * FROM post_revisions WHERE post_id = ?
            ORDER BY created_at DESC, id DESC LIMIT ?
        ''', (post_id, limit)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item['tags'] = json.loads(item.get('tags_json') or '[]')
            except (TypeError, ValueError):
                item['tags'] = []
            result.append(item)
        return result


def get_post_revision(revision_id):
    ensure_revisions_table()
    with get_db_context() as conn:
        row = conn.execute('SELECT * FROM post_revisions WHERE id = ?', (revision_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item['tags'] = json.loads(item.get('tags_json') or '[]')
        except (TypeError, ValueError):
            item['tags'] = []
        return item


def restore_post_revision(revision_id):
    """把指定版本写回文章；恢复前会把当前内容再存一份快照。"""
    revision = get_post_revision(revision_id)
    if not revision:
        return False
    post_id = revision['post_id']
    create_post_revision(post_id)
    with get_db_context() as conn:
        conn.execute('''
            UPDATE posts SET title = ?, content = ?, content_format = ?, category_id = ?,
                access_level = ?, access_password = ?, post_type = ?, type = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            revision['title'], revision['content'], revision['content_format'],
            revision['category_id'], revision['access_level'], revision['access_password'],
            revision['post_type'], revision['type'], post_id,
        ))
        conn.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))
        for name in revision.get('tags') or []:
            cursor = conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (name,))
            tag_id = cursor.lastrowid
            if not tag_id:
                tag_id = conn.execute('SELECT id FROM tags WHERE name = ?', (name,)).fetchone()['id']
            conn.execute('INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (?, ?)', (post_id, tag_id))
        _safe_replace_post_fts(conn.cursor(), post_id, revision['title'], revision['content'])
    return True


def soft_delete_post(post_id):
    with get_db_context() as conn:
        cursor = conn.execute('UPDATE posts SET deleted_at = CURRENT_TIMESTAMP WHERE id = ? AND deleted_at IS NULL', (post_id,))
        return cursor.rowcount > 0


def restore_deleted_post(post_id):
    with get_db_context() as conn:
        row = conn.execute('SELECT title, content FROM posts WHERE id = ? AND deleted_at IS NOT NULL', (post_id,)).fetchone()
        if not row:
            return False
        conn.execute('UPDATE posts SET deleted_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (post_id,))
        return True


def get_deleted_posts():
    with get_db_context() as conn:
        rows = conn.execute('''
            SELECT posts.*, users.username AS author_username, users.display_name AS author_display_name
            FROM posts
            LEFT JOIN users ON posts.author_id = users.id
            WHERE posts.deleted_at IS NOT NULL
            ORDER BY posts.deleted_at DESC
        ''').fetchall()
        return [dict(row) for row in rows]


def purge_deleted_post(post_id):
    with get_db_context() as conn:
        cursor = conn.execute('DELETE FROM posts WHERE id = ? AND deleted_at IS NOT NULL', (post_id,))
        if cursor.rowcount:
            _safe_delete_post_fts(conn.cursor(), post_id)
            return True
        return False


def publish_due_posts(limit=100):
    """把到期的定时文章置为已发布，并同步 FTS。"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, content FROM posts
            WHERE is_published = 0 AND publish_at IS NOT NULL
              AND deleted_at IS NULL AND publish_at <= CURRENT_TIMESTAMP
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        for row in rows:
            cursor.execute('UPDATE posts SET is_published = 1, publish_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (row['id'],))
            _safe_replace_post_fts(cursor, row['id'], row['title'], row['content'])
        return len(rows)
