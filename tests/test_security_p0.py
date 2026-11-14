"""P0 安全修复回归测试：IDOR、角色刷新、媒体删除权限、健康检查。"""
def _login(client, user, role=None):
    with client.session_transaction() as sess:
        sess['user_id'] = user['id']
        sess['username'] = user['username']
        if role:
            sess['role'] = role


def _create_user(username, role='author'):
    from models import create_user
    from werkzeug.security import generate_password_hash

    user_id = create_user(
        username=username,
        password_hash=generate_password_hash('UserPassword123!', method='pbkdf2:sha256'),
        role=role,
    )
    return {'id': user_id, 'username': username, 'role': role}


def test_merge_cards_cannot_append_to_other_users_post(client, test_user):
    from models import create_card, create_post, get_post_by_id

    other = _create_user('other_author')
    post_id = create_post(
        title='他人文章', content='原始正文', is_published=True,
        author_id=other['id'], access_level='public',
    )
    card_id = create_card(
        content='攻击者卡片内容', url='https://example.com/evil',
        title='evil', user_id=test_user['id'], status='idea',
    )

    _login(client, test_user)
    resp = client.post('/api/cards/merge', json={
        'card_ids': [card_id],
        'action': 'append_post',
        'post_id': post_id,
    })

    assert resp.status_code == 403
    assert get_post_by_id(post_id)['content'] == '原始正文'


def test_merge_cards_can_append_to_own_post(client, test_user):
    from models import create_card, create_post, get_post_by_id

    post_id = create_post(
        title='我的文章', content='原始正文', is_published=True,
        author_id=test_user['id'], access_level='public',
    )
    card_id = create_card(
        content='我的卡片内容', url='https://example.com/own',
        title='own', user_id=test_user['id'], status='idea',
    )

    _login(client, test_user)
    resp = client.post('/api/cards/merge', json={
        'card_ids': [card_id],
        'action': 'append_post',
        'post_id': post_id,
    })

    assert resp.status_code == 200
    assert '我的卡片内容' in get_post_by_id(post_id)['content']


def test_stale_admin_role_in_session_is_refreshed(client, test_user):
    _login(client, test_user, role='admin')

    resp = client.post('/knowledge/category/new', data={'name': '越权目录'})

    assert resp.status_code == 403


def test_author_cannot_delete_media_library_file(client, test_user, monkeypatch, tmp_path):
    import routes.admin.media as media_module

    images_dir = tmp_path / 'images'
    images_dir.mkdir()
    target = images_dir / 'owned-by-someone.png'
    target.write_bytes(b'fake-image')
    monkeypatch.setattr(media_module, 'UPLOAD_FOLDER', str(tmp_path))

    _login(client, test_user)
    resp = client.post('/admin/media/library/delete', json={'name': target.name})

    assert resp.status_code == 302
    assert target.exists()


def test_health_endpoints(client):
    assert client.get('/healthz').status_code == 200
    resp = client.get('/readyz')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ready'
