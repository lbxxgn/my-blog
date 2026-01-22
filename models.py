import sqlite3
from pathlib import Path
from config import DATABASE_URL

def get_db_connection(db_path=None):
    """Create a database connection"""
    if db_path is None:
        db_path = DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """Initialize the database with tables"""
    if db_path is None:
        db_path = DATABASE_URL.replace('sqlite:///', '')

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Create posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_published BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def create_post(title, content, is_published=False):
    """Create a new post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO posts (title, content, is_published) VALUES (?, ?, ?)',
        (title, content, is_published)
    )
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id

def update_post(post_id, title, content, is_published):
    """Update an existing post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE posts SET title = ?, content = ?, is_published = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (title, content, is_published, post_id)
    )
    conn.commit()
    conn.close()

def delete_post(post_id):
    """Delete a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

def get_all_posts(include_drafts=False):
    """Get all posts, optionally including drafts"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if include_drafts:
        cursor.execute('SELECT * FROM posts ORDER BY created_at DESC')
    else:
        cursor.execute('SELECT * FROM posts WHERE is_published = 1 ORDER BY created_at DESC')

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return posts

def get_post_by_id(post_id):
    """Get a single post by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    conn.close()
    return dict(post) if post else None

def create_user(username, password_hash):
    """Create a new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        user_id = None
    conn.close()
    return user_id

def get_user_by_username(username):
    """Get a user by username"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None
