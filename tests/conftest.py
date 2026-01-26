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

    # 创建临时数据库文件
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # 保存原始 DATABASE_URL
    original_db_url = getattr(config, 'DATABASE_URL', None)

    # 设置新的数据库路径并重新加载相关模块
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    importlib.reload(config)
    importlib.reload(models)

    # 初始化数据库
    models.init_db(db_path)

    yield db_path

    # 清理
    if original_db_url:
        os.environ['DATABASE_URL'] = original_db_url
    elif 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']

    # 重新加载模块恢复原值
    importlib.reload(config)
    importlib.reload(models)

    # 删除临时数据库文件
    try:
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

    with app.test_client() as client:
        yield client
