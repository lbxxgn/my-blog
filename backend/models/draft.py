"""草稿数据模型"""
from models import get_db_connection
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

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
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN TRANSACTION')

        import json
        tags_json = json.dumps(tags) if tags else None

        # 检测冲突
        cursor.execute('''
            SELECT id, title, updated_at, device_info
            FROM drafts
            WHERE user_id = ? AND post_id = ?
              AND device_info != ?
              AND updated_at > datetime('now', '-5 minutes')
            ORDER BY updated_at DESC
        ''', (user_id, post_id, device_info))

        conflicts = [dict(row) for row in cursor.fetchall()]

        # 使用UPSERT（SQLite 3.24+）
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

def get_drafts(user_id: int, post_id: Optional[int] = None) -> List[Dict]:
    """获取用户的草稿列表"""
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

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()

def get_draft(draft_id: int) -> Optional[Dict]:
    """获取单个草稿详情"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM drafts WHERE id = ?
        ''', (draft_id,))

        row = cursor.fetchone()
        return dict(row) if row else None

    finally:
        conn.close()

def resolve_conflict(conflict_draft_id: int, current_draft_id: int,
                     action: str, merged_data: Optional[Dict] = None) -> Dict:
    """解决草稿冲突"""
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
            import json
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
