"""
Database Model Functions

数据库连接、上下文管理、游标分页、建表初始化与 FTS 全文索引维护。
"""

import sqlite3
import logging
import os
from pathlib import Path
from contextlib import contextmanager
import sys
sys.path.append(str(Path(__file__).parent.parent))
import backend.config as config

# Setup logger
logger = logging.getLogger(__name__)

__all__ = [
    'get_db_connection',
    'get_db_context',
    'paginate_query_cursor',
    'init_db',
    'rebuild_fts_index',
]


def _safe_replace_post_fts(cursor, post_id, title, content):
    """Best-effort FTS sync that does not block the primary post write path."""
    try:
        cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))
        cursor.execute(
            'INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
            (post_id, title, content)
        )
    except sqlite3.DatabaseError as exc:
        logger.warning('Skipping posts_fts sync for post %s: %s', post_id, exc)


def _safe_delete_post_fts(cursor, post_id):
    """Best-effort FTS cleanup for environments with a damaged FTS index."""
    try:
        cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))
    except sqlite3.DatabaseError as exc:
        logger.warning('Skipping posts_fts delete for post %s: %s', post_id, exc)

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
        db_path = config.DATABASE_URL.replace('sqlite:///', '')

    # 连接数据库，增加超时时间以处理长时间查询
    conn = sqlite3.connect(
        db_path,
        timeout=20.0,  # 增加超时到20秒
        check_same_thread=False  # 允许多线程访问
    )

    # 设置行工厂，使结果可以像字典一样访问
    conn.row_factory = sqlite3.Row

    # 在测试环境中禁用WAL模式以避免锁定问题
    # 生产环境启用WAL以提高并发性能
    if os.environ.get('TESTING') != '1':
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
        db_path = config.DATABASE_URL.replace('sqlite:///', '')

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
        db_path = config.DATABASE_URL.replace('sqlite:///', '')

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

    # Add tree/space columns to categories (flat -> tree, blog/knowledge spaces)
    for _col, _def in [
        ('parent_id', 'INTEGER'),
        ('slug', 'TEXT'),
        ('sort_order', 'INTEGER DEFAULT 0'),
        ('space', "TEXT DEFAULT 'blog'"),
        ('icon', 'TEXT'),
        ('description', 'TEXT'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE categories ADD COLUMN {_col} {_def}')
        except Exception:
            pass  # Column already exists

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
        cursor.execute('ALTER TABLE posts ADD COLUMN type TEXT DEFAULT \'post\'')
    except Exception:
        pass  # Column already exists

    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN source_card_ids TEXT')
    except Exception:
        pass  # Column already exists

    # Add note-related columns
    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN excerpt TEXT')
    except Exception:
        pass  # Column already exists

    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN metadata TEXT')
    except Exception:
        pass  # Column already exists

    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN parent_note_id INTEGER')
    except Exception:
        pass  # Column already exists

    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN link_count INTEGER DEFAULT 0')
    except Exception:
        pass  # Column already exists

    # Add knowledge base columns to posts
    for _col, _def in [
        ('content_format', "TEXT DEFAULT 'html'"),
        ('sort_order', 'INTEGER DEFAULT 0'),
        ('source_post_id', 'INTEGER'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE posts ADD COLUMN {_col} {_def}')
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

    # Create passkeys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_passkeys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            credential_id BLOB NOT NULL UNIQUE,
            public_key BLOB NOT NULL,
            sign_count INTEGER DEFAULT 0,
            device_name TEXT,
            transports TEXT,
            credential_device_type TEXT,
            backup_eligible BOOLEAN DEFAULT 0,
            backup_state BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_post_created ON comments(post_id, created_at DESC)')

    # Post-Tags association composite indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_tags_tag_post ON post_tags(tag_id, post_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_tags_post_tag ON post_tags(post_id, tag_id)')

    # Posts composite indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_category_published ON posts(category_id, is_published, created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_author_published ON posts(author_id, is_published, created_at DESC)')

    # Knowledge base indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_post_type ON posts(post_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_post_type_created ON posts(post_type, created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_content_format ON posts(content_format)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_source_post_id ON posts(source_post_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_kb_order ON posts(category_id, sort_order)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_space ON categories(space)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_space_parent ON categories(space, parent_id, sort_order)')

    # Users composite indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')

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

    # Create api_keys table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id)')

    # Create card_annotations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            card_id INTEGER,
            source_url TEXT NOT NULL,
            annotation_text TEXT,
            xpath TEXT,
            color TEXT DEFAULT 'yellow',
            note TEXT,
            annotation_type TEXT DEFAULT 'highlight',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (card_id) REFERENCES cards(id)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_annotations_user_url ON card_annotations(user_id, source_url)')

    # Create note_links table for note linking feature
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS note_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_post_id INTEGER NOT NULL,
            target_post_id INTEGER NOT NULL,
            link_text TEXT,
            link_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (target_post_id) REFERENCES posts(id) ON DELETE CASCADE,
            UNIQUE(source_post_id, target_post_id)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_note_links_source ON note_links(source_post_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_note_links_target ON note_links(target_post_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_type ON posts(post_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_note ON posts(parent_note_id)')

    # 迁移版本记录表（见 backend/migrations/__init__.py）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
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
