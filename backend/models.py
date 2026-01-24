import sqlite3
from pathlib import Path
from config import DATABASE_URL

def get_db_connection(db_path=None):
    """Create a database connection with better error handling"""
    if db_path is None:
        db_path = DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(
        db_path,
        timeout=20.0,  # Increase timeout to 20 seconds
        check_same_thread=False  # Allow access from multiple threads
    )
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
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

    # Create tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create post_tags association table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_tags (
            post_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    ''')

    # Create comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            author_email TEXT,
            content TEXT NOT NULL,
            is_visible BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes to improve query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON posts(created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_published_created ON posts(is_published, created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_category_id ON posts(category_id)')

    # Create FTS5 virtual table for full-text search
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
            title,
            content,
            content='posts',
            content_rowid='rowid'
        )
    ''')

    # Create triggers to keep FTS index in sync
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
            INSERT INTO posts_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
            INSERT INTO posts_fts(posts_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
        END
    ''')

    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
            INSERT INTO posts_fts(posts_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
            INSERT INTO posts_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END
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
    count_query = 'SELECT COUNT(*) as count FROM posts LEFT JOIN categories ON posts.category_id = categories.id WHERE ' + where_clause
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get posts for current page
    query = '''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE ''' + where_clause + '''
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

def create_tag(name):
    """Create a new tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO tags (name) VALUES (?)',
            (name,)
        )
        conn.commit()
        tag_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        tag_id = None
    conn.close()
    return tag_id

def get_all_tags():
    """Get all tags"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags ORDER BY name')
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

def get_tag_by_name(name):
    """Get a tag by name"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE name = ?', (name,))
    tag = cursor.fetchone()
    conn.close()
    return dict(tag) if tag else None

def update_tag(tag_id, name):
    """Update a tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE tags SET name = ? WHERE id = ?',
            (name, tag_id)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def delete_tag(tag_id):
    """Delete a tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
    conn.commit()
    conn.close()

def set_post_tags(post_id, tag_names):
    """Set tags for a post (replace existing)"""
    conn = get_db_connection()
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

    conn.commit()
    conn.close()

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

def get_posts_by_tag(tag_id, include_drafts=False, page=1, per_page=20):
    """Get all posts with a specific tag"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    where_conditions = ['post_tags.tag_id = ?']
    params = [tag_id]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

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

def search_posts(query, include_drafts=False, page=1, per_page=20):
    """Search posts using LIKE for better Chinese support"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause with LIKE for better Chinese text search
    search_pattern = f'%{query}%'
    where_conditions = ['(posts.title LIKE ? OR posts.content LIKE ?)']
    params = [search_pattern, search_pattern]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    where_clause = ' AND '.join(where_conditions)

    # Count total results
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get results for current page
    search_query = f'''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
        ORDER BY posts.created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(search_query, params + [per_page, offset])

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        'posts': posts,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 1
    }

def create_comment(post_id, author_name, author_email, content):
    """Create a new comment"""
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
