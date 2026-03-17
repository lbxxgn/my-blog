"""草稿数据模型"""
from models import get_db_connection
from typing import Optional, List, Dict
import logging
import json

logger = logging.getLogger(__name__)


def ensure_drafts_table() -> None:
    """确保草稿表和索引存在。"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drafts (
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_user_post
            ON drafts(user_id, post_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_user_updated
            ON drafts(user_id, updated_at DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_post
            ON drafts(post_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_device
            ON drafts(user_id, device_info, updated_at)
        ''')
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique_post
            ON drafts(user_id, post_id)
            WHERE post_id IS NOT NULL
        ''')
        conn.commit()
    finally:
        conn.close()


def _deserialize_tags(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []


def _row_to_draft(row) -> Dict:
    draft = dict(row)
    draft['tags'] = _deserialize_tags(draft.get('tags'))
    return draft

def save_draft(user_id: int, post_id: Optional[int], title: str,
               content: str, category_id: Optional[int] = None,
               tags: Optional[List[str]] = None, device_info: str = '') -> Dict:
    """
    保存草稿（带事务管理）

    Returns: {
        'success': bool,
        'draft_id': int,
        'updated_at': str,
        'status': 'saved' | 'conflict_detected',
        'other_drafts': List[Dict]
    }
    """
    ensure_drafts_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN TRANSACTION')
        tags_json = json.dumps(tags) if tags else None

        # 检测冲突
        if post_id is None:
            conflicts = []
        else:
            cursor.execute('''
                SELECT id, title, updated_at, device_info
                FROM drafts
                WHERE user_id = ? AND post_id = ?
                  AND device_info != ?
                  AND updated_at > datetime('now', '-5 minutes')
                ORDER BY updated_at DESC
            ''', (user_id, post_id, device_info))
            conflicts = [dict(row) for row in cursor.fetchall()]

        if post_id is None:
            cursor.execute('''
                INSERT INTO drafts (user_id, post_id, title, content, category_id, tags, device_info)
                VALUES (?, NULL, ?, ?, ?, ?, ?)
                RETURNING id, updated_at
            ''', (user_id, title, content, category_id, tags_json, device_info))
        else:
            cursor.execute('''
                INSERT INTO drafts (user_id, post_id, title, content, category_id, tags, device_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, post_id)
                DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    category_id = excluded.category_id,
                    tags = excluded.tags,
                    device_info = excluded.device_info,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, updated_at
            ''', (user_id, post_id, title, content, category_id, tags_json, device_info))

        result = cursor.fetchone()
        draft_id = result['id']
        updated_at = result['updated_at']

        conn.commit()

        return {
            'success': True,
            'draft_id': draft_id,
            'updated_at': updated_at,
            'status': 'conflict_detected' if conflicts else 'saved',
            'other_drafts': conflicts
        }

    except Exception as e:
        conn.rollback()
        logger.error(f'保存草稿失败: {e}')
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        conn.close()


def create_draft(title: str, content: str, user_id: int,
                 post_id: Optional[int] = None,
                 category_id: Optional[int] = None,
                 tags: Optional[List[str]] = None,
                 device_info: str = '') -> int:
    """兼容旧调用方式，创建一条草稿并返回ID。"""
    result = save_draft(
        user_id=user_id,
        post_id=post_id,
        title=title,
        content=content,
        category_id=category_id,
        tags=tags,
        device_info=device_info
    )
    if not result.get('success'):
        raise RuntimeError(result.get('error', '创建草稿失败'))
    return result['draft_id']


def update_draft(draft_id: int, user_id: int, title: str,
                 content: str, category_id: Optional[int] = None,
                 tags: Optional[List[str]] = None) -> Optional[Dict]:
    """按草稿ID更新内容。"""
    ensure_drafts_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE drafts
            SET title = ?, content = ?, category_id = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            RETURNING *
        ''', (title, content, category_id, json.dumps(tags) if tags else None, draft_id, user_id))
        row = cursor.fetchone()
        conn.commit()
        return _row_to_draft(row) if row else None
    finally:
        conn.close()

def get_drafts(user_id: int, post_id: Optional[int] = None) -> List[Dict]:
    """获取用户的草稿列表"""
    ensure_drafts_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if post_id:
            cursor.execute('''
                SELECT id, post_id, title, updated_at, device_info
                FROM drafts
                WHERE user_id = ? AND post_id = ?
                ORDER BY updated_at DESC
            ''', (user_id, post_id))
        else:
            cursor.execute('''
                SELECT id, post_id, title, updated_at, device_info
                FROM drafts
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT 20
            ''', (user_id,))

        return [_row_to_draft(row) for row in cursor.fetchall()]

    finally:
        conn.close()

def get_draft(draft_id: int) -> Optional[Dict]:
    """获取单个草稿详情"""
    ensure_drafts_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM drafts WHERE id = ?
        ''', (draft_id,))

        row = cursor.fetchone()
        return _row_to_draft(row) if row else None

    finally:
        conn.close()

def resolve_conflict(conflict_draft_id: int, current_draft_id: int,
                     action: str, merged_data: Optional[Dict] = None) -> Dict:
    """解决草稿冲突"""
    ensure_drafts_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN TRANSACTION')

        if action == 'keep_current':
            # 删除对方草稿
            cursor.execute('DELETE FROM drafts WHERE id = ?', (conflict_draft_id,))

        elif action == 'keep_other':
            # 删除当前草稿
            cursor.execute('DELETE FROM drafts WHERE id = ?', (current_draft_id,))

        elif action == 'merge' and merged_data:
            # 更新当前草稿为合并后的内容
            cursor.execute('''
                UPDATE drafts
                SET title = ?, content = ?, category_id = ?, tags = ?
                WHERE id = ?
            ''', (merged_data['title'], merged_data['content'],
                  merged_data.get('category_id'),
                  json.dumps(merged_data.get('tags', [])),
                  current_draft_id))

            # 删除对方草稿
            cursor.execute('DELETE FROM drafts WHERE id = ?', (conflict_draft_id,))

        conn.commit()
        return {'success': True, 'message': '冲突已解决'}

    except Exception as e:
        conn.rollback()
        logger.error(f'解决冲突失败: {e}')
        return {'success': False, 'error': str(e)}

    finally:
        conn.close()

def delete_draft(draft_id: int, user_id: int) -> Dict:
    """删除草稿"""
    ensure_drafts_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM drafts WHERE id = ? AND user_id = ?
        ''', (draft_id, user_id))

        conn.commit()
        return {'success': True, 'message': '草稿已删除'}

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}

    finally:
        conn.close()
