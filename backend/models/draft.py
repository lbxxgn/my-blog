"""草稿数据模型"""
from models import get_db_connection
from typing import Optional, List, Dict
import logging
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _format_iso_time(time_str):
    """将 SQLite 时间字符串转换为带 UTC 时区的 ISO 8601 格式。"""
    if not time_str:
        return None
    try:
        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (ValueError, TypeError):
        return time_str


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

        draft_id = None
        if post_id is None:
            cursor.execute('''
                INSERT INTO drafts (user_id, post_id, title, content, category_id, tags, device_info)
                VALUES (?, NULL, ?, ?, ?, ?, ?)
            ''', (user_id, title, content, category_id, tags_json, device_info))
            draft_id = cursor.lastrowid
        else:
            # 先检查是否存在，避免 ON CONFLICT 与部分索引冲突
            cursor.execute('''
                SELECT id FROM drafts WHERE user_id = ? AND post_id = ?
            ''', (user_id, post_id))
            existing = cursor.fetchone()
            if existing:
                draft_id = existing['id']
                cursor.execute('''
                    UPDATE drafts SET
                        title = ?, content = ?, category_id = ?, tags = ?,
                        device_info = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND post_id = ?
                ''', (title, content, category_id, tags_json, device_info, user_id, post_id))
            else:
                cursor.execute('''
                    INSERT INTO drafts (user_id, post_id, title, content, category_id, tags, device_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, post_id, title, content, category_id, tags_json, device_info))
                draft_id = cursor.lastrowid
        cursor.execute('''
            SELECT updated_at FROM drafts WHERE id = ?
        ''', (draft_id,))
        result = cursor.fetchone()
        updated_at = _format_iso_time(result['updated_at']) if result else None

        # 同样格式化冲突草稿的时间
        for c in conflicts:
            c['updated_at'] = _format_iso_time(c.get('updated_at'))

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
            UPDATE
            drafts SET title = ?, content = ?, category_id = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (title, content, category_id, json.dumps(tags) if tags else None, draft_id, user_id))
        cursor.execute('''
            SELECT * FROM drafts WHERE id = ? AND user_id = ?
        ''', (draft_id, user_id))
        row = cursor.fetchone()
        conn.commit()
        if row:
            draft = _row_to_draft(row)
            draft['updated_at'] = _format_iso_time(draft.get('updated_at'))
            draft['created_at'] = _format_iso_time(draft.get('created_at'))
            return draft
        return None
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

        drafts = [_row_to_draft(row) for row in cursor.fetchall()]
        for d in drafts:
            d['updated_at'] = _format_iso_time(d.get('updated_at'))
        return drafts

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
        if row:
            draft = _row_to_draft(row)
            draft['updated_at'] = _format_iso_time(draft.get('updated_at'))
            draft['created_at'] = _format_iso_time(draft.get('created_at'))
            return draft
        return None

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
