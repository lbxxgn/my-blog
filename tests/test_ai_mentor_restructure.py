"""临时冒烟测试：mentor-comment / restructure 端点与文章页 mentor-btn"""


def _login(client, username, password):
    return client.post('/login', data={'username': username, 'password': password},
                       follow_redirects=True)


def test_endpoints_require_login(client):
    r1 = client.post('/admin/ai/mentor-comment', json={'title': 't', 'content': 'c'},
                     headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'})
    r2 = client.post('/admin/ai/restructure', json={'title': 't', 'content': 'c'},
                     headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'})
    assert r1.status_code == 401, r1.status_code
    assert r2.status_code == 401, r2.status_code


def test_endpoints_ai_disabled(client, test_admin_user):
    _login(client, 'test_admin', 'TestPassword123!')
    r1 = client.post('/admin/ai/mentor-comment', json={'title': 't', 'content': 'c'})
    r2 = client.post('/admin/ai/restructure', json={'title': 't', 'content': 'c'})
    # 测试环境未配置真实密钥：要么报"未启用"(400)，要么走统一的 500 错误响应
    assert r1.status_code in (400, 500) and r1.get_json()['success'] is False
    assert r2.status_code in (400, 500) and r2.get_json()['success'] is False


def test_post_page_has_mentor_btn(client, test_admin_user, test_post):
    _login(client, 'test_admin', 'TestPassword123!')
    resp = client.get(f"/post/{test_post['id']}")
    assert resp.status_code == 200
    assert b'mentor-btn' in resp.data
    assert b'mentor-modal' in resp.data


def test_post_page_no_mentor_btn_anonymous(client, test_post):
    resp = client.get(f"/post/{test_post['id']}")
    assert resp.status_code == 200
    # 按钮本身只在登录态渲染（JS/CSS 中的字符串不算）
    assert b'id="mentor-btn"' not in resp.data
    assert b'id="mentor-modal"' not in resp.data
