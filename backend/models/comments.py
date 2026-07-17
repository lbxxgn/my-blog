"""
Comment Model Functions

评论 CRUD 与图片优化追踪记录。
"""

from .db import get_db_connection, get_db_context
from .users import get_user_by_id

__all__ = [
    'create_comment',
    'get_comments_by_post',
    'get_all_comments',
    'update_comment_visibility',
    'delete_comment',
    'ensure_optimized_images_table',
    'create_optimized_image_record',
]


def create_comment(post_id, author_name, author_email=None, content=None):
    """Create a new comment"""
    if content is None:
        content = author_email
        author_email = ''

        if isinstance(author_name, int):
            author = get_user_by_id(author_name)
            author_name = author['username'] if author else f'user-{author_name}'
        else:
            author_name = str(author_name)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO comments (post_id, author_name, author_email, content) VALUES (?, ?, ?, ?)',
        (post_id, author_name, author_email, content)
    )
    conn.commit()
    comment_id = cursor.lastrowid
    conn.close()
    return comment_id

def get_comments_by_post(post_id, include_hidden=False):
    """Get all comments for a post"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if include_hidden:
        cursor.execute('''
            SELECT * FROM comments
            WHERE post_id = ?
            ORDER BY created_at DESC
        ''', (post_id,))
    else:
        cursor.execute('''
            SELECT * FROM comments
            WHERE post_id = ? AND is_visible = 1
            ORDER BY created_at DESC
        ''', (post_id,))

    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments


def ensure_optimized_images_table():
    """确保图片优化追踪表存在。"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                original_hash TEXT,
                thumbnail_path TEXT,
                medium_path TEXT,
                large_path TEXT,
                original_size INTEGER,
                optimized_size INTEGER,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_status
            ON optimized_images(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_original
            ON optimized_images(original_path)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_hash
            ON optimized_images(original_hash)
        ''')


def create_optimized_image_record(original_path, status='pending', original_hash=None):
    """创建图片优化追踪记录。"""
    ensure_optimized_images_table()

    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO optimized_images (original_path, original_hash, status)
            VALUES (?, ?, ?)
            ''',
            (original_path, original_hash, status)
        )
        return cursor.lastrowid

def get_all_comments(include_hidden=False):
    """Get all comments"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if include_hidden:
        cursor.execute('''
            SELECT comments.*, posts.title as post_title, posts.id as post_id
            FROM comments
            JOIN posts ON comments.post_id = posts.id
            ORDER BY comments.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT comments.*, posts.title as post_title, posts.id as post_id
            FROM comments
            JOIN posts ON comments.post_id = posts.id
            WHERE comments.is_visible = 1
            ORDER BY comments.created_at DESC
        ''')

    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments

def update_comment_visibility(comment_id, is_visible):
    """Update comment visibility"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE comments SET is_visible = ? WHERE id = ?',
        (is_visible, comment_id)
    )
    conn.commit()
    conn.close()

def delete_comment(comment_id):
    """Delete a comment"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    conn.commit()
    conn.close()
