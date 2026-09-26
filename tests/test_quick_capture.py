"""快捷捕捉页 / PWA 分享目标 / 语音速记 相关测试"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _login(client, user):
    client.post('/login', data={
        'username': user['username'],
        'password': user['password']
    })


class TestQuickCapturePage:
    """GET /quick-capture 页面"""

    def test_requires_login(self, client):
        """未登录重定向到登录页"""
        response = client.get('/quick-capture')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']

    def test_renders_empty(self, client, test_user):
        """无参数时正常渲染"""
        _login(client, test_user)
        response = client.get('/quick-capture')
        assert response.status_code == 200
        assert 'qcContent' in response.get_data(as_text=True)

    def test_share_params_prefilled(self, client, test_user):
        """分享参数 title/text/url 合并预填"""
        _login(client, test_user)
        response = client.get(
            '/quick-capture?title=Hello+World&text=Some+shared+text&url=https%3A%2F%2Fexample.com%2Fpost'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        # 标题进标题框
        assert 'value="Hello World"' in html
        # text 为主、url 追加在末尾
        assert 'Some shared text' in html
        assert 'https://example.com/post' in html
        assert html.index('Some shared text') < html.index('https://example.com/post')

    def test_url_not_duplicated_when_in_text(self, client, test_user):
        """url 已在 text 中时不重复追加"""
        _login(client, test_user)
        response = client.get(
            '/quick-capture?text=check+https%3A%2F%2Fexample.com&url=https%3A%2F%2Fexample.com'
        )
        html = response.get_data(as_text=True)
        assert html.count('https://example.com') == 1


class TestApiCreateCard:
    """POST /knowledge_base/api/cards"""

    def test_requires_login(self, client):
        """未登录返回 401（JSON 请求）"""
        response = client.post('/knowledge_base/api/cards',
                               data=json.dumps({'title': 't', 'content': 'c'}),
                               content_type='application/json')
        assert response.status_code == 401

    def test_create_card_success(self, client, test_user):
        """建卡成功 201，source='share'、status='idea'、归属当前用户"""
        _login(client, test_user)
        response = client.post('/knowledge_base/api/cards',
                               data=json.dumps({
                                   'title': '分享来的灵感',
                                   'content': '一些内容',
                                   'source_url': 'https://example.com'
                               }),
                               content_type='application/json')
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'id' in data

        from models import get_card_by_id
        card = get_card_by_id(data['id'])
        assert card['source'] == 'share'
        assert card['status'] == 'idea'
        assert card['user_id'] == test_user['id']
        assert card['title'] == '分享来的灵感'

    def test_missing_content_400(self, client, test_user):
        """缺 content 返回 400"""
        _login(client, test_user)
        response = client.post('/knowledge_base/api/cards',
                               data=json.dumps({'title': 't'}),
                               content_type='application/json')
        assert response.status_code == 400


class TestPwaShareTarget:
    """PWA 分享目标契约"""

    def test_manifest_has_share_target(self):
        manifest = (PROJECT_ROOT / 'static' / 'site.webmanifest').read_text()
        assert 'share_target' in manifest
        assert '"action": "/quick-capture"' in manifest.replace("'", '"')
        assert '"title": "title"' in manifest
        assert '"text": "text"' in manifest
        assert '"url": "url"' in manifest

    def test_share_target_action_route_exists(self, client, test_user):
        """share_target action 指向存在的路由"""
        _login(client, test_user)
        response = client.get('/quick-capture?title=t&text=x&url=u')
        assert response.status_code == 200


class TestServiceWorker:
    """最小 service worker"""

    def test_sw_js_exists_and_has_fetch_listener(self):
        sw = (PROJECT_ROOT / 'static' / 'sw.js').read_text()
        assert "addEventListener('fetch'" in sw or 'addEventListener("fetch"' in sw

    def test_sw_js_served_at_root(self, client, test_user):
        """sw.js 以根路径可访问"""
        _login(client, test_user)
        response = client.get('/sw.js')
        assert response.status_code == 200
        assert 'fetch' in response.get_data(as_text=True)

    def test_base_html_registers_sw(self):
        base = (PROJECT_ROOT / 'templates' / 'base.html').read_text()
        assert 'serviceWorker' in base
        assert '/sw.js' in base
        assert 'register' in base


class TestAppleTouchIcon:
    """iOS 主屏图标根路径兜底"""

    def test_apple_touch_icon_served_at_root(self, client):
        response = client.get('/apple-touch-icon.png')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'image/png'

    def test_apple_touch_icon_precomposed_alias(self, client):
        response = client.get('/apple-touch-icon-precomposed.png')
        assert response.status_code == 200

    def test_base_html_declares_apple_touch_icon(self):
        base = (PROJECT_ROOT / 'templates' / 'base.html').read_text()
        assert 'apple-touch-icon' in base
