"""
Category Model Functions

博客分类 CRUD。
"""

import sqlite3

from .db import get_db_connection, get_db_context

__all__ = [
    'create_category',
    'get_all_categories',
    'get_category_by_id',
    'get_category_by_name',
    'update_category',
    'delete_category',
    'get_posts_by_category',
]


def create_category(name, slug=None):
    """Create a new category - refactored to use context manager"""
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO categories (name) VALUES (?)',
                (name,)
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None

def get_all_categories():
    """Get all categories with proper connection management and post counts"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*,
                   (SELECT COUNT(*) FROM posts WHERE category_id = c.id AND is_published = 1) as post_count
            FROM categories c
            ORDER BY c.name
        ''')
        categories = [dict(row) for row in cursor.fetchall()]
        return categories

def get_category_by_id(category_id):
    """Get a category by ID with proper connection management"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
        category = cursor.fetchone()
        return dict(category) if category else None

def get_category_by_name(category_name):
    """Get a category by name"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE name = ?', (category_name,))
        category = cursor.fetchone()
        return dict(category) if category else None

def update_category(category_id, name):
    """Update a category - refactored to use context manager"""
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE categories SET name = ? WHERE id = ?',
                (name, category_id)
            )
            return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False

def delete_category(category_id):
    """Delete a category - refactored to use context manager"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        # First, unassign all posts from this category
        cursor.execute('UPDATE posts SET category_id = NULL WHERE category_id = ?', (category_id,))
        # Then delete the category
        cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))

def get_posts_by_category(category_id, include_drafts=False):
    """Get all posts in a category"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if include_drafts:
        cursor.execute('SELECT * FROM posts WHERE category_id = ? ORDER BY created_at DESC', (category_id,))
    else:
        cursor.execute('SELECT * FROM posts WHERE category_id = ? AND is_published = 1 ORDER BY created_at DESC', (category_id,))

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return posts
