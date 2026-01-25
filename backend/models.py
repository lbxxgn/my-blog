import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from config import DATABASE_URL

# Setup logger
logger = logging.getLogger(__name__)

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

@contextmanager
def get_db_context(db_path=None):
    """
    Database connection context manager for automatic commit/rollback

    Usage:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute('...')
            # Auto commits on success, rolls back on exception
    """
    if db_path is None:
        db_path = DATABASE_URL.replace('sqlite:///', '')

    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def paginate_query_cursor(conn, query, where_clause, params, cursor_time=None, per_page=20):
    """
    Generic cursor-based pagination function

    Args:
        conn: Database connection
        query: Base SQL query (SELECT part only)
        where_clause: WHERE clause without 'WHERE'
        params: Query parameters list
        cursor_time: Time cursor for pagination
        per_page: Items per page

    Returns:
        dict with items, next_cursor, has_more
    """
    cursor = conn.cursor()

    where_conditions = [where_clause] if where_clause else []
    query_params = params.copy()

    if cursor_time:
        where_conditions.append('created_at < ?')
        query_params.append(cursor_time)

    final_where = ' AND '.join(where_conditions) if where_conditions else '1=1'

    # Fetch one extra item to check if there's more
    final_query = f"{query} WHERE {final_where} ORDER BY created_at DESC LIMIT ?"
    query_params.append(per_page + 1)

    cursor.execute(final_query, query_params)
    rows = cursor.fetchall()
    items = [dict(row) for row in rows[:per_page]]
    has_more = len(rows) > per_page

    next_cursor = None
    if items:
        next_cursor = items[-1].get('created_at')

    return {
        'items': items,
        'next_cursor': next_cursor,
        'has_more': has_more,
        'per_page': per_page
    }

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

    # Tags index
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)')

    # Post-Tags association indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_tags_post ON post_tags(post_id)')

    # Comments index
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)')

    # Create FTS5 virtual table for full-text search
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
            title,
            content,
            content='posts',
            content_rowid='rowid'
        )
    ''')

    # Note: FTS triggers have been removed to prevent SQL logic errors.
    # FTS index is now maintained manually in CRUD operations.

    conn.commit()
    conn.close()

def create_post(title, content, is_published=False, category_id=None, author_id=None):
    """Create a new post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO posts (title, content, is_published, category_id, author_id) VALUES (?, ?, ?, ?, ?)',
        (title, content, is_published, category_id, author_id)
    )
    post_id = cursor.lastrowid

    # Manually update FTS (triggers are disabled)
    cursor.execute('INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
                  (post_id, title, content))

    conn.commit()
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

    # Manually update FTS (triggers are disabled)
    cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))
    cursor.execute('INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
                  (post_id, title, content))

    conn.commit()
    conn.close()
    return True

def delete_post(post_id):
    """Delete a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))

    # Manually delete from FTS (triggers are disabled)
    cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))

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

    # 构建安全的WHERE子句 - 仅使用硬编码的条件
    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

    # 验证where_clause只包含安全的条件（防止代码注入）
    allowed_patterns = ['posts.is_published = ', 'posts.category_id IS NULL', 'posts.category_id = ', '1=1']
    if not any(allowed in where_clause for allowed in allowed_patterns):
        raise ValueError(f"Invalid WHERE clause: {where_clause}")

    # Count total posts
    count_query = '''
        SELECT COUNT(*) as count
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE ''' + where_clause
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get posts for current page
    query = '''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id,
               users.id as author_id,
               users.username as author_username,
               users.display_name as author_display_name
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        LEFT JOIN users ON posts.author_id = users.id
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

def get_all_posts_cursor(cursor_time=None, per_page=20, include_drafts=False, category_id=None):
    """
    Get all posts using cursor-based pagination for better performance

    Args:
        cursor_time: Time-based cursor (created_at of last post in previous page)
        per_page: Number of posts per page
        include_drafts: Whether to include draft posts
        category_id: Filter by category ID

    Returns:
        dict with posts, next_cursor, has_more
    """
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

    if cursor_time:
        where_conditions.append('posts.created_at < ?')
        params.append(cursor_time)

    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

    # Get posts
    query = '''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id,
               users.id as author_id,
               users.username as author_username,
               users.display_name as author_display_name
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        LEFT JOIN users ON posts.author_id = users.id
        WHERE ''' + where_clause + '''
        ORDER BY posts.created_at DESC
        LIMIT ?
    '''
    params.append(per_page + 1)  # Fetch one extra to check if there's more

    cursor.execute(query, params)
    rows = cursor.fetchall()
    posts = [dict(row) for row in rows[:per_page]]  # Only return requested amount
    has_more = len(rows) > per_page

    # Get next cursor (created_at of last post)
    next_cursor = None
    if posts:
        next_cursor = posts[-1]['created_at']

    conn.close()

    return {
        'posts': posts,
        'next_cursor': next_cursor,
        'has_more': has_more,
        'per_page': per_page
    }

def get_post_by_id(post_id):
    """Get a single post by ID with category and author information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id,
               users.id as author_id,
               users.username as author_username,
               users.display_name as author_display_name,
               users.avatar_url as author_avatar_url,
               users.bio as author_bio
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        LEFT JOIN users ON posts.author_id = users.id
        WHERE posts.id = ?
    ''', (post_id,))
    post = cursor.fetchone()
    conn.close()
    return dict(post) if post else None

def get_user_by_username(username):
    """Get a user by username with error handling"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_user_by_username({username}): {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_user_by_username({username}): {e}")
        return None

def update_user_password(user_id, new_password_hash):
    """Update user password - refactored to use context manager"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
        return cursor.rowcount > 0

def create_category(name):
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
    """Get all categories with proper connection management"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories ORDER BY name')
        categories = [dict(row) for row in cursor.fetchall()]
        return categories

def get_category_by_id(category_id):
    """Get a category by ID with proper connection management"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
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

def update_post_with_tags(post_id, title, content, is_published, category_id=None, tag_names=None):
    """Update post and its tags in a single transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update post
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, post_id)
        )

        # Manually update FTS (triggers are disabled)
        cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))
        cursor.execute('INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
                      (post_id, title, content))

        # Delete existing tag associations
        cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))

        # Add new tag associations if provided
        if tag_names:
            for tag_name in tag_names:
                if not tag_name.strip():
                    continue

                name = tag_name.strip()

                # Check if tag exists
                cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
                result = cursor.fetchone()

                if result:
                    tag_id = result[0]
                else:
                    # Create tag inline
                    try:
                        cursor.execute('INSERT INTO tags (name) VALUES (?)', (name,))
                        tag_id = cursor.lastrowid
                    except sqlite3.IntegrityError:
                        # Tag was created, get it again
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
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def rebuild_fts_index():
    """Manually rebuild the full-text search index"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Clear existing FTS data
        cursor.execute('DELETE FROM posts_fts')
        
        # Repopulate FTS index
        cursor.execute('''
            INSERT INTO posts_fts(rowid, title, content)
            SELECT id, title, content FROM posts
        ''')
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error rebuilding FTS index: {e}")
        return False
    finally:
        conn.close()


# ==================== 用户管理函数 ====================

def get_user_by_id(user_id):
    """根据ID获取用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_all_users():
    """获取所有用户列表（包含文章数统计）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT users.*,
               (SELECT COUNT(*) FROM posts WHERE posts.author_id = users.id) as post_count
        FROM users
        ORDER BY users.created_at DESC
    ''')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def create_user(username, password_hash, role='author', display_name=None, bio=None):
    """创建新用户（扩展版，支持角色和显示名称）"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, display_name, bio)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, role, display_name, bio))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_user(user_id, username=None, display_name=None, bio=None, role=None, is_active=None):
    """更新用户信息"""
    with get_db_context() as conn:
        cursor = conn.cursor()

        updates = []
        params = []

        if username is not None:
            updates.append('username = ?')
            params.append(username)
        if display_name is not None:
            updates.append('display_name = ?')
            params.append(display_name)
        if bio is not None:
            updates.append('bio = ?')
            params.append(bio)
        if role is not None:
            updates.append('role = ?')
            params.append(role)
        if is_active is not None:
            updates.append('is_active = ?')
            params.append(is_active)

        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(user_id)

            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            return cursor.rowcount > 0
        return False


def delete_user(user_id):
    """删除用户（将其文章设为无作者）"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        # 先将该用户的文章设为无作者
        cursor.execute('UPDATE posts SET author_id = NULL WHERE author_id = ?', (user_id,))
        # 删除用户
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))


def get_posts_by_author(author_id, include_drafts=False, page=1, per_page=20):
    """获取指定作者的文章"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建WHERE条件
    where_conditions = ['posts.author_id = ?']
    params = [author_id]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    where_clause = ' AND '.join(where_conditions)

    # 统计总数
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # 分页查询
    offset = (page - 1) * per_page
    query = f'''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id
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

