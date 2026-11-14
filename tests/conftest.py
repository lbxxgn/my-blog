"""
Pytest 配置和测试固件 (fixtures)
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / 'backend'

# 同时保留项目根目录和 backend 目录，兼容现有测试导入风格
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(autouse=True)
def isolate_log_files(tmp_path, monkeypatch):
    """把日志重定向到临时目录，避免测试写入项目 logs/。"""
    import importlib

    log_dir = tmp_path / 'logs'
    log_dir.mkdir()
    files = {
        'LOG_DIR': log_dir,
        'APP_LOG': log_dir / 'app.log',
        'LOGIN_LOG': log_dir / 'login.log',
        'OPERATION_LOG': log_dir / 'operation.log',
        'ERROR_LOG': log_dir / 'error.log',
        'SQL_LOG': log_dir / 'sql.log',
    }
    for module_name in ('logger', 'backend.logger'):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        for attr, value in files.items():
            if hasattr(module, attr):
                monkeypatch.setattr(module, attr, value)


@pytest.fixture(scope='session')
def schema_template(tmp_path_factory):
    """用 init_db + 迁移构建一次基准 schema，避免测试与生产 schema 双份维护。"""
    import contextlib
    import importlib
    import io
    import os

    import backend.config as config
    import models

    template = tmp_path_factory.mktemp('schema') / 'template.db'
    original_testing = os.environ.get('TESTING')
    original_url = os.environ.get('DATABASE_URL')

    os.environ['TESTING'] = '1'
    os.environ['DATABASE_URL'] = f'sqlite:///{template}'
    importlib.reload(config)
    importlib.reload(models)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            models.init_db()
            from backend.migrations import apply_migrations

            _, _, failed = apply_migrations(verbose=False)
            assert not failed, f'schema template migrations failed: {failed}'
    finally:
        if original_testing is None:
            os.environ.pop('TESTING', None)
        else:
            os.environ['TESTING'] = original_testing
        if original_url is None:
            os.environ.pop('DATABASE_URL', None)
        else:
            os.environ['DATABASE_URL'] = original_url
        importlib.reload(config)
        importlib.reload(models)

    return str(template)


@pytest.fixture(scope='function')
def temp_db(schema_template):
    """
    创建临时数据库用于测试

    每个测试都会使用一个全新的临时数据库，
    测试结束后自动清理。
    """
    import importlib
    import backend.config as config
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

        # 基于 init_db + 迁移生成的基准 schema 复制，保证与生产一致
        import shutil

        shutil.copyfile(schema_template, db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # FTS 同步触发器（init_db 不创建，保留测试中直接 SQL 写入的索引行为）
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


@pytest.fixture(scope='function')
def init_database(temp_db):
    """
    兼容旧测试的临时数据库 fixture 别名

    一些历史测试使用 init_database 作为 fixture 名称；
    其功能与 temp_db 完全一致：提供一个已初始化的临时 SQLite 数据库。
    """
    return temp_db


@pytest.fixture
def test_admin_user(temp_db):
    """
    创建测试管理员用户
    
    Returns:
        dict: 用户信息字典
    """
    from models import create_user
    from werkzeug.security import generate_password_hash
    
    password_hash = generate_password_hash('TestPassword123!', method='pbkdf2:sha256')
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
def admin_user(test_admin_user):
    """Backward-compatible alias for older tests."""
    return test_admin_user


@pytest.fixture
def test_user(temp_db):
    """
    创建测试普通用户
    
    Returns:
        dict: 用户信息字典
    """
    from models import create_user
    from werkzeug.security import generate_password_hash
    
    password_hash = generate_password_hash('UserPassword123!', method='pbkdf2:sha256')
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

    # 重置限流计数，避免跨测试污染
    try:
        from app import limiter
        limiter.reset()
    except Exception:
        pass

    with app.test_client() as client:
        yield client


@pytest.fixture
def csrf_client(app_with_aliases):
    """
    创建启用 CSRF 保护的测试客户端

    Returns:
        Flask test client with CSRF enabled
    """
    app = app_with_aliases
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = True

    with app.test_client() as client:
        yield client


@pytest.fixture
def limited_client(app_with_aliases):
    """
    创建启用速率限制的测试客户端

    Returns:
        Flask test client with rate limiting enabled
    """
    app = app_with_aliases
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = True

    # 重置内存中的限流计数，避免跨测试污染
    try:
        from app import limiter
        limiter.reset()
    except Exception:
        pass

    with app.test_client() as client:
        yield client
