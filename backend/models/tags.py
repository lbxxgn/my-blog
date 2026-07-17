"""
Tag Model Functions

标签 CRUD 与文章-标签关联维护。
"""

import sqlite3

from .db import get_db_connection, get_db_context

__all__ = [
    'create_tag',
    'get_all_tags',
    'get_tag_by_id',
    'get_popular_tags',
    'get_tag_by_name',
    'update_tag',
    'delete_tag',
    'set_post_tags',
    'get_post_tags',
    'get_posts_by_tag',
]


def create_tag(name):
    """Create a new tag - refactored to use context manager"""
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO tags (name) VALUES (?)',
                (name,)
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None

def get_all_tags():
    """Get all tags with post count"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*,
               (SELECT COUNT(*) FROM post_tags WHERE tag_id = t.id) as post_count
        FROM tags t
        ORDER BY name
    ''')
    tags = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tags

def get_tag_by_id(tag_id):
    """Get a tag by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE id = ?', (tag_id,))
    tag = cursor.fetchone()
    conn.close()
    return dict(tag) if tag else None

def get_popular_tags(limit=10):
    """Get top tags by post count (hot tags)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*,
               (SELECT COUNT(*) FROM post_tags WHERE tag_id = t.id) as post_count
        FROM tags t
        WHERE t.id IN (SELECT DISTINCT tag_id FROM post_tags)
        ORDER BY post_count DESC
        LIMIT ?
    ''', (limit,))
    tags = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tags

def get_tag_by_name(name):
    """Get a tag by name"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE name = ?', (name,))
    tag = cursor.fetchone()
    conn.close()
    return dict(tag) if tag else None

def update_tag(tag_id, name):
    """Update a tag - refactored to use context manager"""
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tags SET name = ? WHERE id = ?',
                (name, tag_id)
            )
            return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False

def delete_tag(tag_id):
    """Delete a tag - refactored to use context manager"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))

def set_post_tags(post_id, tag_names):
    """Set tags for a post (replace existing) - refactored to use context manager"""
    with get_db_context() as conn:
        cursor = conn.cursor()

        # Delete existing tag associations
        cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))

        # Add new tag associations
        for tag_name in tag_names:
            if not tag_name.strip():
                continue

            name = tag_name.strip()

            # Check if tag exists (inline query to avoid nested connection)
            cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
            result = cursor.fetchone()

            if result:
                tag_id = result[0]
            else:
                # Create tag inline (insert into tags table)
                try:
                    cursor.execute('INSERT INTO tags (name) VALUES (?)', (name,))
                    tag_id = cursor.lastrowid
                except sqlite3.IntegrityError:
                    # Tag was created by another process, get it again
                    cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
                    result = cursor.fetchone()
                    if result:
                        tag_id = result[0]
                    else:
                        tag_id = None

            if tag_id:
                cursor.execute(
                    'INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                    (post_id, tag_id)
                )

def get_post_tags(post_id):
    """Get all tags for a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT tags.* FROM tags
        JOIN post_tags ON tags.id = post_tags.tag_id
        WHERE post_tags.post_id = ?
        ORDER BY tags.name
    ''', (post_id,))
    tags = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tags

def get_posts_by_tag(tag_id, include_drafts=False, page=1, per_page=20, post_type='blog'):
    """Get all posts with a specific tag"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    where_conditions = ['post_tags.tag_id = ?']
    params = [tag_id]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    if post_type is not None:
        where_conditions.append('posts.post_type = ?')
        params.append(post_type)

    where_clause = ' AND '.join(where_conditions)

    # Count total posts
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts
        JOIN post_tags ON posts.id = post_tags.post_id
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get posts for current page
    query = f'''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts
        JOIN post_tags ON posts.id = post_tags.post_id
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
        ORDER BY posts.created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(query, params + [per_page, offset])

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        'posts': posts,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 1
    }
