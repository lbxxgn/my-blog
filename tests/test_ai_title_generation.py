"""AI 标题自动生成回归测试。"""

from models import create_post, get_post_by_id, update_user_ai_config


def test_async_ai_title_updates_post(temp_db, test_admin_user, monkeypatch):
    from backend.routes import admin as admin_pkg

    update_user_ai_config(test_admin_user['id'], {
        'ai_tag_generation_enabled': True,
        'ai_provider': 'dashscope',
        'ai_model': 'qwen-turbo',
        'ai_api_key': 'sk-test',
    })
    post_id = create_post(
        '临时标题', '<p>这是一段用于测试 AI 标题生成的正文。</p>',
        False, None, test_admin_user['id'])

    monkeypatch.setattr(
        admin_pkg,
        '_run_structured_prompt',
        lambda *args, **kwargs: {
            'content': 'AI 生成的标题',
            'model': 'qwen-turbo',
            'tokens_used': 10,
            'input_tokens': 5,
            'output_tokens': 5,
        },
    )

    from app import app
    admin_pkg._async_ai_title(app, post_id, '正文内容', test_admin_user['id'])

    assert get_post_by_id(post_id)['title'] == 'AI 生成的标题'


def test_new_post_with_empty_title_starts_ai_title_task(
        client, test_admin_user, monkeypatch):
    from routes.admin import posts as posts_module

    calls = []
    monkeypatch.setattr(
        posts_module, '_async_ai_title',
        lambda *args: calls.append(args),
    )

    client.post('/login', data={
        'username': test_admin_user['username'],
        'password': test_admin_user['password'],
    })
    response = client.post('/admin/new', data={
        'title': '',
        'content': '<p>这是一段用于测试自动标题的正文内容。</p>',
        'content_format': 'html',
    })
    assert response.status_code in (302, 200)

    import time
    deadline = time.time() + 2
    while not calls and time.time() < deadline:
        time.sleep(0.02)
    assert calls


def _post_new(client, test_admin_user, title):
    client.post('/login', data={
        'username': test_admin_user['username'],
        'password': test_admin_user['password'],
    })
    return client.post('/admin/new', data={
        'title': title,
        'content': '<p>这是一段用于测试自动标题的正文内容。</p>',
        'content_format': 'html',
    })


def _wait_for_calls(calls):
    import time
    deadline = time.time() + 2
    while not calls and time.time() < deadline:
        time.sleep(0.02)


def test_whitespace_title_still_triggers_ai_title(
        client, test_admin_user, monkeypatch):
    from routes.admin import posts as posts_module

    calls = []
    monkeypatch.setattr(posts_module, '_async_ai_title', lambda *args: calls.append(args))

    response = _post_new(client, test_admin_user, '   ')
    assert response.status_code in (302, 200)
    _wait_for_calls(calls)
    assert calls


def test_user_title_does_not_trigger_ai_title(
        client, test_admin_user, monkeypatch):
    from routes.admin import posts as posts_module

    calls = []
    monkeypatch.setattr(posts_module, '_async_ai_title', lambda *args: calls.append(args))

    response = _post_new(client, test_admin_user, '我自己写的标题')
    assert response.status_code in (302, 200)
    import time
    time.sleep(0.15)
    assert not calls
