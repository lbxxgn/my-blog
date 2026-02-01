"""
Pytest 配置和测试固件 (fixtures)
"""

import os
import sys
import tempfile
import pytest

# 将 backend 目录添加到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


@pytest.fixture(scope='function')
def temp_db():
    """
    创建临时数据库用于测试

    每个测试都会使用一个全新的临时数据库，
    测试结束后自动清理。
    """
    import importlib
    import config
    import models
    import uuid
    import sqlite3

    # 设置测试环境变量，禁用WAL模式
    os.environ['TESTING'] = '1'

    # 使用UUID确保每个测试都有唯一的数据库文件名
    db_path = tempfile.gettempdir() + f'/test_db_{uuid.uuid4().hex}.db'

    # 保存原始 DATABASE_URL
    original_db_url = getattr(config, 'DATABASE_URL', None)

    try:
        # 设置新的数据库路径并重新加载相关模块
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        importlib.reload(config)
        importlib.reload(models)

        # 初始化数据库（使用直接SQL）
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # 创建所有表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
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

        conn.execute('''
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

        # 添加新字段
        try:
            conn.execute('ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT \'blog\'')
        except:
            pass

        try:
            conn.execute('ALTER TABLE posts ADD COLUMN source_card_ids TEXT')
        except:
            pass

        try:
            conn.execute('ALTER TABLE posts ADD COLUMN excerpt TEXT')
        except:
            pass

        try:
            conn.execute('ALTER TABLE posts ADD COLUMN metadata TEXT')
        except:
            pass

        try:
            conn.execute('ALTER TABLE posts ADD COLUMN parent_note_id INTEGER')
        except:
            pass

        try:
            conn.execute('ALTER TABLE posts ADD COLUMN link_count INTEGER DEFAULT 0')
        except:
            pass

        # 创建tags表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建post_tags关联表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS post_tags (
                post_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (post_id, tag_id),
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        ''')

        # 创建comments表
        conn.execute('''
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

        # 创建indexes
        conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON posts(created_at DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_published_created ON posts(is_published, created_at DESC)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_category_id ON posts(category_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_author_id ON posts(author_id)')

        # 创建cards表
        conn.execute('''
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

        # 创建api_keys表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                api_key TEXT NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # 创建card_annotations表
        conn.execute('''
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

        # 创建AI tag history表
        conn.execute('''
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

        # 创建note_links表
        conn.execute('''
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

        # 创建全文搜索表
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(title, content, content='posts', content_rowid='id')
        ''')

        # 创建全文搜索触发器
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
                INSERT INTO posts_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END
        ''')

        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
            END
        ''')

        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
                INSERT INTO posts_fts(rowid, title, content) VALUES (new.id, new.title, new.content);
            END
        ''')

        conn.commit()
        conn.close()

        yield db_path

    finally:
        # 清理 - 总是执行
        # 强制垃圾回收以关闭所有数据库连接
        import gc
        gc.collect()

        # 清除测试环境变量
        if 'TESTING' in os.environ:
            del os.environ['TESTING']

        # 恢复原始配置
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        # 重新加载模块恢复原值
        importlib.reload(config)
        importlib.reload(models)

        # 等待一小段时间确保所有连接都关闭
        import time
        time.sleep(0.1)

        # 删除临时数据库文件
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except:
            pass


@pytest.fixture(scope='function')
def app_with_aliases(temp_db):
    """
    创建设置了endpoint别名的Flask应用
    """
    from app import app

    # 设置endpoint别名
    app.view_functions['index'] = app.view_functions['blog.index']
    app.view_functions['login'] = app.view_functions['auth.login']

    return app


@pytest.fixture
def test_admin_user(temp_db):
    """
    创建测试管理员用户
    
    Returns:
        dict: 用户信息字典
    """
    from models import create_user
    from werkzeug.security import generate_password_hash
    
    password_hash = generate_password_hash('TestPassword123!')
    user_id = create_user(
        username='test_admin',
        password_hash=password_hash,
        role='admin',
        display_name='Test Admin',
        bio='Test admin user'
    )
    
    return {
        'id': user_id,
        'username': 'test_admin',
        'password': 'TestPassword123!',
        'role': 'admin'
    }


@pytest.fixture
def test_user(temp_db):
    """
    创建测试普通用户
    
    Returns:
        dict: 用户信息字典
    """
    from models import create_user
    from werkzeug.security import generate_password_hash
    
    password_hash = generate_password_hash('UserPassword123!')
    user_id = create_user(
        username='test_user',
        password_hash=password_hash,
        role='author',
        display_name='Test User',
        bio='Test regular user'
    )
    
    return {
        'id': user_id,
        'username': 'test_user',
        'password': 'UserPassword123!',
        'role': 'author'
    }


@pytest.fixture
def test_post(temp_db, test_user):
    """
    创建测试文章

    Returns:
        dict: 文章信息字典
    """
    from models import create_post

    # Check if create_post supports access_level parameter
    import inspect
    sig = inspect.signature(create_post)
    if 'access_level' in sig.parameters:
        post_id = create_post(
            title='Test Post',
            content='This is a test post content.',
            is_published=True,
            category_id=None,
            author_id=test_user['id'],
            access_level='public'
        )
    else:
        post_id = create_post(
            title='Test Post',
            content='This is a test post content.',
            is_published=True,
            category_id=None,
            author_id=test_user['id']
        )

    return {
        'id': post_id,
        'title': 'Test Post',
        'content': 'This is a test post content.'
    }


@pytest.fixture
def client(app_with_aliases):
    """
    创建 Flask 测试客户端

    Returns:
        Flask test client
    """
    app = app_with_aliases
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    # 禁用CSRF保护以便测试
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        yield client
