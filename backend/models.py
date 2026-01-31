import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from config import DATABASE_URL

# Setup logger
logger = logging.getLogger(__name__)

def get_db_connection(db_path=None):
    """
    创建数据库连接并配置优化设置

    Args:
        db_path (str, optional): 数据库文件路径。默认为None，使用DATABASE_URL

    Returns:
        sqlite3.Connection: 配置好的数据库连接对象

    Note:
        - timeout: 20秒超时（适用于长时间查询）
        - check_same_thread=False: 允许多线程访问（SQLite要求）
        - row_factory=sqlite3.Row: 返回字典式行对象
        - WAL模式: 写前日志，提供更好的并发性能
        - synchronous=NORMAL: 平衡性能和安全性
    """
    if db_path is None:
        db_path = DATABASE_URL.replace('sqlite:///', '')

    # 连接数据库，增加超时时间以处理长时间查询
    conn = sqlite3.connect(
        db_path,
        timeout=20.0,  # 增加超时到20秒
        check_same_thread=False  # 允许多线程访问
    )

    # 设置行工厂，使结果可以像字典一样访问
    conn.row_factory = sqlite3.Row

    # 启用WAL（Write-Ahead Logging）模式，提高并发性能
    conn.execute('PRAGMA journal_mode=WAL')

    # 设置同步模式为NORMAL（在每次事务时同步，但不是每次写入）
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
            author_id INTEGER DEFAULT 1,
            access_level TEXT DEFAULT 'public',
            access_password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (author_id) REFERENCES users(id)
        )
    ''')

    # Add new columns to posts table if they don't exist
    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT \'blog\'')
    except Exception:
        pass  # Column already exists

    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN source_card_ids TEXT')
    except Exception:
        pass  # Column already exists

    # Create users table with full schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'author',
            display_name TEXT,
            bio TEXT,
            avatar_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_tag_generation_enabled BOOLEAN DEFAULT 1,
            ai_provider TEXT DEFAULT 'openai',
            ai_api_key TEXT,
            ai_model TEXT DEFAULT 'gpt-3.5-turbo'
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_author_id ON posts(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_author_created ON posts(author_id, created_at DESC)')

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

    # Create AI tag history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_tag_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            prompt TEXT,
            generated_tags TEXT,
            model_used TEXT,
            tokens_used INTEGER,
            cost DECIMAL(10, 6),
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Create AI history indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_history_post ON ai_tag_history(post_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_history_user ON ai_tag_history(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_history_created ON ai_tag_history(created_at DESC)')

    # Create cards table for knowledge base system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            tags TEXT,
            status TEXT DEFAULT 'idea',
            source TEXT DEFAULT 'web',
            linked_article_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (linked_article_id) REFERENCES posts(id)
        )
    ''')

    # Create cards indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_user_status ON cards(user_id, status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_created ON cards(created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_linked_article ON cards(linked_article_id)')

    conn.commit()
    conn.close()

def create_post(title, content, is_published=False, category_id=None, author_id=None, access_level='public', access_password=None):
    """
    创建新文章

    Args:
        title (str): 文章标题
        content (str): 文章内容（Markdown格式）
        is_published (bool): 是否立即发布。默认为False（草稿）
        category_id (int, optional): 分类ID。默认为None
        author_id (int, optional): 作者ID。默认为None
        access_level (str): 访问级别。默认为'public'
        access_password (str, optional): 访问密码。默认为None

    Returns:
        int: 新创建文章的ID

    Note:
        - 自动更新FTS全文搜索索引
        - 触发器已禁用，手动维护索引
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO posts (title, content, is_published, category_id, author_id, access_level, access_password) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (title, content, is_published, category_id, author_id, access_level, access_password)
    )
    post_id = cursor.lastrowid

    # 手动更新FTS全文搜索索引（触发器已禁用以避免SQL逻辑错误）
    cursor.execute('INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
                  (post_id, title, content))

    conn.commit()
    conn.close()
    return post_id

def update_post(post_id, title, content, is_published, category_id=None, access_level=None, access_password=None):
    """
    Update an existing post

    Args:
        post_id (int): 文章ID
        title (str): 文章标题
        content (str): 文章内容
        is_published (bool): 是否发布
        category_id (int, optional): 分类ID
        access_level (str, optional): 访问级别
        access_password (str, optional): 访问密码
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建更新SQL（动态包含访问权限字段）
    if access_level is not None:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, access_level = ?, access_password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, access_level, access_password, post_id)
        )
    else:
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
    """
    使用LIKE进行文章搜索（对中文支持更好）

    Args:
        query (str): 搜索关键词
        include_drafts (bool): 是否包含草稿。默认为False
        page (int): 页码。默认为1
        per_page (int): 每页数量。默认为20

    Returns:
        dict: 包含以下键：
            - 'posts': 文章列表
            - 'total': 总结果数
            - 'page': 当前页码
            - 'per_page': 每页数量
            - 'total_pages': 总页数

    Note:
        - 使用LIKE而不是MATCH以获得更好的中文分词支持
        - 搜索范围包括标题和内容
        - 返回按创建时间倒序排列
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建LIKE搜索模式（对中文支持更好）
    search_pattern = f'%{query}%'
    where_conditions = ['(posts.title LIKE ? OR posts.content LIKE ?)']
    params = [search_pattern, search_pattern]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    where_clause = ' AND '.join(where_conditions)

    # 计算总结果数
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # 计算偏移量
    offset = (page - 1) * per_page

    # 获取当前页结果
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

# =============================================================================
# Cards Model Functions
# =============================================================================

def create_card(user_id, title, content, tags=None, status='idea', source='web', linked_article_id=None):
    """
    创建新卡片

    Args:
        user_id (int): 用户ID
        title (str, optional): 卡片标题
        content (str): 卡片内容
        tags (list, optional): 标签列表
        status (str): 状态 (idea/draft/incubating/published)
        source (str): 来源 (web/plugin/voice/mobile)
        linked_article_id (int, optional): 关联的文章ID

    Returns:
        int: 新创建卡片的ID
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    tags_json = json.dumps(tags) if tags else None

    cursor.execute('''
        INSERT INTO cards (user_id, title, content, tags, status, source, linked_article_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, content, tags_json, status, source, linked_article_id))

    card_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return card_id


def get_card_by_id(card_id):
    """
    通过ID获取卡片

    Args:
        card_id (int): 卡片ID

    Returns:
        dict or None: 卡片数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_cards_by_user(user_id, status=None, limit=None, offset=None):
    """
    获取用户的所有卡片

    Args:
        user_id (int): 用户ID
        status (str, optional): 筛选状态
        limit (int, optional): 限制数量
        offset (int, optional): 偏移量

    Returns:
        list: 卡片列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM cards WHERE user_id = ?'
    params = [user_id]

    if status:
        query += ' AND status = ?'
        params.append(status)

    query += ' ORDER BY created_at DESC'

    if limit:
        query += ' LIMIT ?'
        params.append(limit)
        if offset:
            query += ' OFFSET ?'
            params.append(offset)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_card_status(card_id, status):
    """
    更新卡片状态

    Args:
        card_id (int): 卡片ID
        status (str): 新状态
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE cards SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, card_id))

    conn.commit()
    conn.close()


def update_card(card_id, title=None, content=None, tags=None, status=None):
    """
    更新卡片信息

    Args:
        card_id (int): 卡片ID
        title (str, optional): 新标题
        content (str, optional): 新内容
        tags (list, optional): 新标签
        status (str, optional): 新状态
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if title is not None:
        updates.append('title = ?')
        params.append(title)

    if content is not None:
        updates.append('content = ?')
        params.append(content)

    if tags is not None:
        updates.append('tags = ?')
        params.append(json.dumps(tags))

    if status is not None:
        updates.append('status = ?')
        params.append(status)

    if updates:
        updates.append('updated_at = CURRENT_TIMESTAMP')
        query = f"UPDATE cards SET {', '.join(updates)} WHERE id = ?"
        params.append(card_id)

        cursor.execute(query, params)
        conn.commit()

    conn.close()


def delete_card(card_id):
    """
    删除卡片

    Args:
        card_id (int): 卡片ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM cards WHERE id = ?', (card_id,))
    conn.commit()
    conn.close()


def get_timeline_items(user_id, limit=20, cursor_time=None):
    """
    获取时间线项目（卡片和文章的混合流）

    Args:
        user_id (int): 用户ID
        limit (int): 每页数量
        cursor_time (str, optional): 时间游标

    Returns:
        dict: 包含 items, next_cursor, has_more
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query cards
    cards_query = '''
        SELECT id, title, content, 'card' as type, status, created_at
        FROM cards
        WHERE user_id = ?
    '''
    cards_params = [user_id]

    if cursor_time:
        cards_query += ' AND created_at < ?'
        cards_params.append(cursor_time)

    cards_query += ' ORDER BY created_at DESC LIMIT ?'
    cards_params.append(limit + 1)

    cursor.execute(cards_query, cards_params)
    cards = [dict(row) for row in cursor.fetchall()]

    # Query published posts
    posts_query = '''
        SELECT id, title, content, 'post' as type,
               CASE WHEN is_published = 1 THEN 'published' ELSE 'draft' END as status,
               created_at
        FROM posts
        WHERE author_id = ?
    '''
    posts_params = [user_id]

    if cursor_time:
        posts_query += ' AND created_at < ?'
        posts_params.append(cursor_time)

    posts_query += ' ORDER BY created_at DESC LIMIT ?'
    posts_params.append(limit + 1)

    cursor.execute(posts_query, posts_params)
    posts = [dict(row) for row in cursor.fetchall()]

    # Merge and sort by created_at
    all_items = cards + posts
    all_items.sort(key=lambda x: x['created_at'], reverse=True)

    # Paginate
    items = all_items[:limit]
    has_more = len(all_items) > limit

    next_cursor = None
    if items:
        next_cursor = items[-1]['created_at']

    conn.close()

    return {
        'items': items,
        'next_cursor': next_cursor,
        'has_more': has_more
    }


def merge_cards_to_post(card_ids, user_id, post_id=None):
    """
    合并卡片到文章

    Args:
        card_ids (list): 卡片ID列表
        user_id (int): 用户ID
        post_id (int, optional): 现有文章ID。如果为None则创建新文章

    Returns:
        int: 文章ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all cards
    placeholders = ','.join(['?' for _ in card_ids])
    query = f'SELECT * FROM cards WHERE id IN ({placeholders}) AND user_id = ? ORDER BY created_at DESC'
    cursor.execute(query, card_ids + [user_id])
    cards = [dict(row) for row in cursor.fetchall()]

    if not cards:
        conn.close()
        raise ValueError('No valid cards found')

    # Merge content
    merged_content = ''
    for card in cards:
        if card['title']:
            merged_content += f"## {card['title']}\n\n"
        merged_content += card['content'] + '\n\n---\n\n'

    # Create or update post
    if post_id:
        # Append to existing post
        cursor.execute('SELECT content FROM posts WHERE id = ?', (post_id,))
        result = cursor.fetchone()
        if result:
            existing_content = result['content']
            merged_content = existing_content + '\n\n---\n\n' + merged_content

        cursor.execute('''
            UPDATE posts SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (merged_content, post_id))
    else:
        # Create new post
        # Use first card's title or generate one
        title = cards[0]['title'] if cards[0]['title'] else '未命名文章'

        cursor.execute('''
            INSERT INTO posts (title, content, is_published, author_id)
            VALUES (?, ?, 0, ?)
        ''', (title, merged_content, user_id))
        post_id = cursor.lastrowid

    # Update cards status and link
    for card_id in card_ids:
        cursor.execute('''
            UPDATE cards SET status = 'published', linked_article_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (post_id, card_id))

    conn.commit()
    conn.close()

    return post_id


def ai_merge_cards_to_post(card_ids, user_id, user_config, merge_style='comprehensive'):
    """
    使用AI合并卡片到文章

    Args:
        card_ids (list): 卡片ID列表
        user_id (int): 用户ID
        user_config (dict): 用户AI配置
        merge_style (str): 合并风格 ('comprehensive' 或 'outline')

    Returns:
        dict: 包含 post_id, title, content, outline, tags, tokens_used
    """
    from ai_services.card_merger import AICardMerger

    # Use AI to merge
    ai_result = AICardMerger.merge_cards(
        card_ids=card_ids,
        user_id=user_id,
        user_config=user_config,
        merge_style=merge_style
    )

    # Create post with AI-generated content
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO posts (title, content, is_published, author_id, post_type)
        VALUES (?, ?, 0, ?, 'knowledge-article')
    ''', (ai_result['title'], ai_result['content'], user_id))

    post_id = cursor.lastrowid

    # Update cards status and link
    placeholders = ','.join(['?' for _ in card_ids])
    cursor.execute(f'''
        UPDATE cards SET status = 'incubating', linked_article_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders})
    ''', [post_id] + card_ids)

    conn.commit()
    conn.close()

    ai_result['post_id'] = post_id
    return ai_result


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
    """删除用户（将其文章设为无作者）

    Returns:
        bool: 删除成功返回True，否则返回False
    """
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            # 先将该用户的文章设为无作者
            cursor.execute('UPDATE posts SET author_id = NULL WHERE author_id = ?', (user_id,))
            # 删除用户
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            # 检查是否删除了行
            if cursor.rowcount > 0:
                return True
            return False
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False


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


# ==================== AI功能函数 ====================

def get_user_ai_config(user_id):
    """
    获取用户的AI配置

    Args:
        user_id: 用户ID

    Returns:
        dict: 包含AI配置的字典，如果用户不存在返回None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            ai_tag_generation_enabled,
            ai_provider,
            ai_api_key,
            ai_model
        FROM users
        WHERE id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'ai_tag_generation_enabled': bool(row['ai_tag_generation_enabled']) if row['ai_tag_generation_enabled'] is not None else True,
            'ai_provider': row['ai_provider'] or 'openai',
            'ai_api_key': row['ai_api_key'],
            'ai_model': row['ai_model'] or 'gpt-3.5-turbo'
        }
    return None


def update_user_ai_config(user_id, ai_config):
    """
    更新用户的AI配置

    Args:
        user_id: 用户ID
        ai_config: AI配置字典，包含:
            - ai_tag_generation_enabled: bool (optional)
            - ai_provider: str (optional)
            - ai_api_key: str (optional)
            - ai_model: str (optional)

    Returns:
        bool: 更新是否成功
    """
    import logging
    logger = logging.getLogger(__name__)

    with get_db_context() as conn:
        cursor = conn.cursor()

        updates = []
        params = []

        if 'ai_tag_generation_enabled' in ai_config:
            updates.append('ai_tag_generation_enabled = ?')
            params.append(1 if ai_config['ai_tag_generation_enabled'] else 0)
            logger.info(f"Update AI config: ai_tag_generation_enabled = {ai_config['ai_tag_generation_enabled']}")

        if 'ai_provider' in ai_config:
            updates.append('ai_provider = ?')
            params.append(ai_config['ai_provider'])
            logger.info(f"Update AI config: ai_provider = {ai_config['ai_provider']}")

        if 'ai_api_key' in ai_config:
            updates.append('ai_api_key = ?')
            params.append(ai_config['ai_api_key'])
            logger.info(f"Update AI config: ai_api_key = ***{ai_config['ai_api_key'][-4:] if ai_config['ai_api_key'] else '(empty)'}")

        if 'ai_model' in ai_config:
            updates.append('ai_model = ?')
            params.append(ai_config['ai_model'])
            logger.info(f"Update AI config: ai_model = {ai_config['ai_model']}")

        if updates:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            logger.info(f"Executing query: {query} with params count: {len(params)}")
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            logger.info(f"Update affected {affected_rows} rows")
            return affected_rows > 0

        logger.warning("No updates to apply")
        return False


def save_ai_tag_history(post_id=None, user_id=None, prompt=None, generated_tags=None,
                        model_used=None, tokens_used=None, cost=None, currency='USD',
                        action=None, provider=None, input_tokens=None, output_tokens=None,
                        result_preview=None, **kwargs):
    """
    保存AI功能使用历史记录（通用函数）

    支持两种调用格式：
    1. 旧格式（标签生成）：save_ai_tag_history(post_id, user_id, prompt, generated_tags, model_used, tokens_used, cost, currency)
    2. 新格式（所有AI功能）：save_ai_tag_history(user_id=..., post_id=..., action=..., provider=..., model=..., ...)

    Args:
        post_id: 文章ID (可选)
        user_id: 用户ID
        prompt: 提示词或操作类型
        generated_tags: 生成的结果（标签/摘要/推荐等）
        model_used: 使用的模型
        tokens_used: 使用的token总数
        cost: 成本
        currency: 货币单位 (USD/CNY)
        action: 操作类型 (generate_tags, generate_summary, recommend_posts, continue_writing)
        provider: AI提供商 (openai, volcengine, dashscope)
        input_tokens: 输入token数
        output_tokens: 输出token数
        result_preview: 结果预览
        **kwargs: 其他参数（兼容性）

    Returns:
        int: 历史记录ID
    """
    import json

    # 处理新格式的参数
    if action is not None:
        # 新格式：将数据转换为适合存储的格式
        prompt = action  # 使用action作为prompt

        # 构建完整的结果对象
        result_data = {
            'action': action,
            'provider': provider,
            'model': model_used or kwargs.get('model'),
        }

        # 根据action添加特定字段
        if action == 'generate_tags':
            result_data['tags'] = result_preview or generated_tags
        elif action == 'generate_summary':
            result_data['summary'] = result_preview
        elif action == 'recommend_posts':
            result_data['recommendations_count'] = kwargs.get('recommendations_count', 0)
        elif action == 'continue_writing':
            result_data['continuation_length'] = kwargs.get('continuation_length', 0)
            result_data['continuation_preview'] = result_preview[:200] if result_preview else ''

        # 添加token信息
        if input_tokens is not None or output_tokens is not None:
            result_data['input_tokens'] = input_tokens
            result_data['output_tokens'] = output_tokens
            result_data['total_tokens'] = tokens_used

        generated_tags = json.dumps(result_data, ensure_ascii=False)

        # 组合provider和model
        if provider and model_used:
            model_used = f"{provider}:{model_used}"
    else:
        # 旧格式：直接使用生成的标签
        if generated_tags is not None and not isinstance(generated_tags, str):
            generated_tags = json.dumps(generated_tags, ensure_ascii=False)

    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_tag_history (post_id, user_id, prompt, generated_tags, model_used, tokens_used, cost, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_id,
            user_id,
            prompt,
            generated_tags,
            model_used,
            tokens_used,
            cost,
            currency
        ))
        return cursor.lastrowid


def get_ai_tag_history(user_id=None, post_id=None, limit=50):
    """
    获取AI标签生成历史记录

    Args:
        user_id: 用户ID (可选，用于过滤)
        post_id: 文章ID (可选，用于过滤)
        limit: 返回记录数限制

    Returns:
        list: 历史记录列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建WHERE条件
    where_conditions = []
    params = []

    if user_id:
        where_conditions.append('user_id = ?')
        params.append(user_id)

    if post_id:
        where_conditions.append('post_id = ?')
        params.append(post_id)

    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

    query = f'''
        SELECT ai_tag_history.*,
               posts.title as post_title,
               users.username as user_username
        FROM ai_tag_history
        LEFT JOIN posts ON ai_tag_history.post_id = posts.id
        LEFT JOIN users ON ai_tag_history.user_id = users.id
        WHERE {where_clause}
        ORDER BY ai_tag_history.created_at DESC
        LIMIT ?
    '''
    params.append(limit)
    cursor.execute(query, params)

    history = []
    for row in cursor.fetchall():
        record = dict(row)
        # 保留JSON字符串格式，由路由层负责解析
        history.append(record)

    conn.close()
    return history


def get_ai_usage_stats(user_id=None):
    """
    获取AI使用统计

    Args:
        user_id: 用户ID (可选)

    Returns:
        dict: 统计信息
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute('''
            SELECT
                COUNT(*) as total_generations,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                AVG(tokens_used) as avg_tokens,
                MAX(created_at) as last_used
            FROM ai_tag_history
            WHERE user_id = ?
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT
                COUNT(*) as total_generations,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                AVG(tokens_used) as avg_tokens,
                MAX(created_at) as last_used
            FROM ai_tag_history
        ''')

    stats = dict(cursor.fetchone())

    # 获取最近使用的货币单位
    if user_id:
        cursor.execute('''
            SELECT currency FROM ai_tag_history
            WHERE user_id = ? AND currency IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT currency FROM ai_tag_history
            WHERE currency IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
        ''')

    currency_row = cursor.fetchone()
    stats['currency'] = currency_row['currency'] if currency_row else 'USD'

    conn.close()

    # 处理NULL值
    stats['total_tokens'] = stats['total_tokens'] or 0
    stats['total_cost'] = stats['total_cost'] or 0.0
    stats['avg_tokens'] = stats['avg_tokens'] or 0

    return stats


def strip_html_tags(html_content):
    """
    移除HTML标签，保留纯文本

    Args:
        html_content: 包含HTML的文本

    Returns:
        str: 纯文本内容
    """
    import re

    if not html_content:
        return ""

    # 移除script和style标签及其内容
    html_content = re.sub(r'<script[^>]*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*?>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # 替换HTML标签
    html_content = re.sub(r'<[^>]+>', '', html_content)

    # 替换HTML实体
    html_entities = {
        '&nbsp;': ' ',
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'",
        '&copy;': '©',
        '&reg;': '®',
        '&mdash;': '—',
        '&ndash;': '–',
        '&hellip;': '…',
        '&#39;': "'",
        '&#34;': '"',
    }

    for entity, char in html_entities.items():
        html_content = html_content.replace(entity, char)

    # 清理多余的空白
    html_content = re.sub(r'\s+', ' ', html_content)
    html_content = html_content.strip()

    return html_content


def truncate_text(text, max_length=200, suffix='...'):
    """
    截断文本到指定长度，避免在单词中间截断

    Args:
        text: 要截断的文本
        max_length: 最大长度
        suffix: 截断后添加的后缀

    Returns:
        str: 截断后的文本
    """
    if not text:
        return ""

    # 先移除HTML标签
    text = strip_html_tags(text)

    # 如果文本已经足够短，直接返回
    if len(text) <= max_length:
        return text

    # 截断到最大长度
    truncated = text[:max_length]

    # 尝试在最后一个空格处截断，避免截断单词
    last_space = truncated.rfind(' ')

    if last_space > max_length * 0.8:  # 如果最后一个空格在80%位置之后
        truncated = truncated[:last_space]

    return truncated + suffix


def get_post_excerpt(post_content, max_length=200):
    """
    获取文章摘要（清理HTML并截断）

    Args:
        post_content: 文章内容
        max_length: 摘要最大长度

    Returns:
        str: 文章摘要
    """
    return truncate_text(post_content, max_length)


def check_post_access(post_id, user_id=None, session_passwords=None):
    """
    检查用户是否有权限访问文章

    Args:
        post_id: 文章ID
        user_id: 用户ID（可选）
        session_passwords: session中已解锁的密码列表（可选）

    Returns:
        dict: {'allowed': bool, 'reason': str}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT access_level, access_password, author_id
        FROM posts
        WHERE id = ?
    ''', (post_id,))

    post = cursor.fetchone()
    conn.close()

    if not post:
        return {'allowed': False, 'reason': '文章不存在'}

    access_level = post['access_level'] or 'public'
    access_password = post['access_password']
    author_id = post['author_id']

    # 公开文章
    if access_level == 'public':
        return {'allowed': True, 'reason': 'public'}

    # 私密文章：只有作者和管理员可见
    if access_level == 'private':
        if user_id:
            # 检查是否是作者或管理员
            cursor = get_db_connection().cursor()
            cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()

            if user and (user_id == author_id or user['role'] == 'admin'):
                cursor.connection.close()
                return {'allowed': True, 'reason': 'author_or_admin'}

            cursor.connection.close()

        return {'allowed': False, 'reason': 'private'}

    # 登录用户可见
    if access_level == 'login':
        if user_id:
            return {'allowed': True, 'reason': 'logged_in'}
        return {'allowed': False, 'reason': 'login_required'}

    # 密码保护
    if access_level == 'password':
        # 只有作者可以直接访问（管理员也需要输入密码）
        if user_id and user_id == author_id:
            cursor = get_db_connection().cursor()
            cursor.connection.close()
            return {'allowed': True, 'reason': 'author'}

        # 检查session中是否有正确的密码
        if session_passwords and str(post_id) in session_passwords:
            return {'allowed': True, 'reason': 'password_verified'}

        return {'allowed': False, 'reason': 'password_required', 'has_password': bool(access_password)}

    return {'allowed': True, 'reason': 'unknown'}


def update_post_access(post_id, access_level, access_password=None):
    """
    更新文章访问权限

    Args:
        post_id: 文章ID
        access_level: 访问级别
        access_password: 密码（可选）

    Returns:
        bool: 是否成功
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE posts
            SET access_level = ?, access_password = ?
            WHERE id = ?
        ''', (access_level, access_password, post_id))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating post access: {e}")
        return False
    finally:
        conn.close()


def verify_post_password(post_id, password):
    """
    验证文章访问密码

    Args:
        post_id: 文章ID
        password: 输入的密码

    Returns:
        bool: 密码是否正确
    """
    import logging
    logger = logging.getLogger(__name__)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT access_password FROM posts
        WHERE id = ? AND access_level = 'password'
    ''', (post_id,))

    post = cursor.fetchone()
    conn.close()

    if not post:
        logger.warning(f"[Password Verify] Post {post_id} not found or not password protected")
        return False

    if not post['access_password']:
        logger.warning(f"[Password Verify] Post {post_id} is password protected but has no password set")
        return False

    logger.info(f"[Password Verify] Post {post_id} checking password")
    result = password == post['access_password']
    logger.info(f"[Password Verify] Password match: {result}")

    return result
