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

    # Create categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_published BOOLEAN DEFAULT 0,
            category_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
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

def create_post(title, content, is_published=False, category_id=None):
    """Create a new post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO posts (title, content, is_published, category_id) VALUES (?, ?, ?, ?)',
        (title, content, is_published, category_id)
    )
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id

def update_post(post_id, title, content, is_published, category_id=None):
    """Update an existing post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (title, content, is_published, category_id, post_id)
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

def get_all_posts(include_drafts=False, page=1, per_page=20, category_id=None):
    """Get all posts with pagination, optionally including drafts and filtering by category"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    where_conditions = []
    params = []

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    if category_id == 'none':
        where_conditions.append('posts.category_id IS NULL')
    elif category_id is not None:
        where_conditions.append('posts.category_id = ?')
        params.append(category_id)

    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

    # Count total posts
    count_query = f'SELECT COUNT(*) as count FROM posts LEFT JOIN categories ON posts.category_id = categories.id WHERE {where_clause}'
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get posts for current page
    query = f'''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts
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

def get_post_by_id(post_id):
    """Get a single post by ID with category information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE posts.id = ?
    ''', (post_id,))
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

def update_user_password(user_id, new_password_hash):
    """Update user password"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
    conn.commit()
    conn.close()

def create_category(name):
    """Create a new category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO categories (name) VALUES (?)',
            (name,)
        )
        conn.commit()
        category_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        category_id = None
    conn.close()
    return category_id

def get_all_categories():
    """Get all categories"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return categories

def get_category_by_id(category_id):
    """Get a category by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    conn.close()
    return dict(category) if category else None

def update_category(category_id, name):
    """Update a category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE categories SET name = ? WHERE id = ?',
            (name, category_id)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def delete_category(category_id):
    """Delete a category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # First, unassign all posts from this category
    cursor.execute('UPDATE posts SET category_id = NULL WHERE category_id = ?', (category_id,))
    # Then delete the category
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()

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
