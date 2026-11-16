"""App Factory：可创建多个隔离实例并接受配置覆盖。"""
from backend.app import create_app


def _make(name, **overrides):
    config = {
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SETUP_LOGGING': False,
        'REGENERATE_ASSETS': False,
        'SECRET_KEY': name,
    }
    config.update(overrides)
    return create_app(config)


def test_create_app_returns_isolated_instances():
    first = _make('first')
    second = _make('second')

    assert first is not second
    assert first.config['SECRET_KEY'] == 'first'
    assert second.config['SECRET_KEY'] == 'second'
    assert 'blog.index' in first.view_functions
    assert 'blog.index' in second.view_functions
    assert first.test_client().get('/healthz').status_code == 200
    assert second.test_client().get('/healthz').status_code == 200


def test_create_app_applies_overrides():
    app = _make('override', MAX_CONTENT_LENGTH=12345)

    assert app.config['MAX_CONTENT_LENGTH'] == 12345
    assert app.config['TESTING'] is True
    assert app.config['WTF_CSRF_ENABLED'] is False
