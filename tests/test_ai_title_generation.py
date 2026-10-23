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


def test_new_post_thread_updates_title_and_history(
        client, test_admin_user, temp_db, monkeypatch):
    import time
    from routes import admin as admin_module
    from models import get_ai_tag_history, get_post_by_id, update_user_ai_config

    update_user_ai_config(test_admin_user['id'], {
        'ai_tag_generation_enabled': True,
        'ai_provider': 'dashscope',
        'ai_model': 'qwen-turbo',
        'ai_api_key': 'sk-test',
    })
    monkeypatch.setattr(
        admin_module,
        '_run_structured_prompt',
        lambda *args, **kwargs: {
            'content': '线程生成的标题',
            'model': 'qwen-turbo',
            'tokens_used': 10,
            'input_tokens': 5,
            'output_tokens': 5,
        },
    )

    client.post('/login', data={
        'username': test_admin_user['username'],
        'password': test_admin_user['password'],
    })
    response = client.post('/admin/new', data={
        'title': '',
        'content': '<p>这是一段用于测试异步线程自动标题的正文内容。</p>',
        'content_format': 'html',
    })
    assert response.status_code in (302, 200)

    deadline = time.time() + 3
    title = None
    while time.time() < deadline:
        post = get_post_by_id(1)
        if post and post['title'] == '线程生成的标题':
            title = post['title']
            break
        time.sleep(0.05)
    assert title == '线程生成的标题'

    history = get_ai_tag_history(user_id=test_admin_user['id'])
    title_records = [
        row for row in history
        if 'generate_title' in (row.get('generated_tags') or '')
    ]
    assert title_records
    assert '线程生成的标题' in title_records[0]['generated_tags']


def test_generate_title_surfaces_empty_ai_response(
        client, test_admin_user, monkeypatch):
    from routes.ai import generation as generation_module
    from models import update_user_ai_config

    update_user_ai_config(test_admin_user['id'], {
        'ai_tag_generation_enabled': True,
        'ai_provider': 'dashscope',
        'ai_model': 'qwen-turbo',
        'ai_api_key': 'sk-test',
    })
    monkeypatch.setattr(
        generation_module,
        '_run_structured_prompt',
        lambda *args, **kwargs: {
            'content': '',
            'model': 'qwen-turbo',
            'tokens_used': 10,
            'input_tokens': 10,
            'output_tokens': 0,
        },
    )

    client.post('/login', data={
        'username': test_admin_user['username'],
        'password': test_admin_user['password'],
    })
    response = client.post('/admin/ai/generate-title', json={
        'content': '这是一段用于测试标题生成的正文内容。'
    })
    data = response.get_json()
    assert data['success'] is True
    assert data['source'] == 'heuristic'
    assert '返回内容为空' in data['ai_error']


def test_generate_title_uses_more_output_tokens_for_reasoning_models(
        client, test_admin_user, monkeypatch):
    from routes.ai import generation as generation_module
    from models import update_user_ai_config

    update_user_ai_config(test_admin_user['id'], {
        'ai_tag_generation_enabled': True,
        'ai_provider': 'deepseek',
        'ai_model': 'deepseek-v4-pro',
        'ai_api_key': 'sk-test',
    })
    captured = {}

    def fake_prompt(*args, **kwargs):
        captured.update(kwargs)
        return {
            'content': 'AI 标题',
            'model': 'deepseek-v4-pro',
            'tokens_used': 10,
            'input_tokens': 10,
            'output_tokens': 0,
        }

    monkeypatch.setattr(generation_module, '_run_structured_prompt', fake_prompt)

    client.post('/login', data={
        'username': test_admin_user['username'],
        'password': test_admin_user['password'],
    })
    response = client.post('/admin/ai/generate-title', json={
        'content': '这是一段用于测试标题生成的正文内容。'
    })
    data = response.get_json()
    assert data['source'] == 'ai'
    assert data['title'] == 'AI 标题'
    assert captured['max_tokens'] == 300
    assert captured['extra_body'] == {'thinking': {'type': 'disabled'}}
