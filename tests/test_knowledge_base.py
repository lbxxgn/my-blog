"""
知识库功能测试
测试知识库卡片管理、浏览器扩展API、AI辅助功能
"""

import pytest
import json


@pytest.mark.usefixtures("client", "test_admin_user")
class TestKnowledgeBaseAPI:
    """知识库API测试"""

    def test_timeline_view(self, client, test_admin_user):
        """测试时间线视图"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/knowledge_base/timeline')
        assert response.status_code == 200

    def test_quick_note(self, client, test_admin_user):
        """测试快速记事"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 获取快速记事页面
        response = client.get('/knowledge_base/quick-note')
        assert response.status_code == 200

        # 提交快速记事
        note_data = {
            'content': 'Quick note content',
            'url': '',
            'title': ''
        }

        response = client.post('/knowledge_base/quick-note', data=note_data)
        assert response.status_code in [200, 302]

    def test_incubator_view(self, client, test_admin_user):
        """测试孵化器视图"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/knowledge_base/incubator')
        assert response.status_code == 200


@pytest.mark.usefixtures("client", "test_admin_user")
class TestBrowserExtensionAPI:
    """浏览器扩展API测试"""

    def test_submit_card(self, client, test_admin_user):
        """测试提交卡片"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        card_data = {
            'content': 'Card content from browser extension',
            'url': 'https://example.com/article',
            'title': 'Example Article'
        }

        response = client.post('/api/plugin/submit',
            data=json.dumps(card_data),
            content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') is True

    def test_sync_annotations(self, client, test_admin_user):
        """测试同步标注"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        annotations_data = {
            'annotations': [
                {
                    'url': 'https://example.com',
                    'selection': 'Selected text',
                    'note': 'My note'
                }
            ]
        }

        response = client.post('/api/plugin/sync-annotations',
            data=json.dumps(annotations_data),
            content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data

    def test_get_recent_annotations(self, client, test_admin_user):
        """测试获取最近标注"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/api/plugin/annotations')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list) or 'annotations' in data


@pytest.mark.usefixtures("client", "test_admin_user")
class TestCardManagement:
    """卡片管理测试"""

    def test_get_cards(self, client, test_admin_user, temp_db):
        """测试获取卡片列表"""
        from backend.models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建测试卡片
        create_card(
            content='Test card',
            url='https://example.com',
            title='Test',
            user_id=test_admin_user['id'],
            status='idea'
        )

        response = client.get('/api/cards')
        assert response.status_code == 200
        data = response.get_json()
        assert 'cards' in data or isinstance(data, list)

    def test_get_cards_supports_query_filter(self, client, test_admin_user, temp_db):
        """测试卡片列表支持关键词过滤"""
        from backend.models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        create_card(
            content='Flask blueprints and routes',
            title='Flask note',
            user_id=test_admin_user['id'],
            status='idea'
        )
        create_card(
            content='Weekend diary',
            title='Daily note',
            user_id=test_admin_user['id'],
            status='idea'
        )

        response = client.get('/api/cards?q=flask')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 1
        assert data['cards'][0]['title'] == 'Flask note'

    def test_update_card_status(self, client, test_admin_user, temp_db):
        """测试更新卡片状态"""
        from backend.models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        card_id = create_card(
            content='Test card',
            url='https://example.com',
            title='Test',
            user_id=test_admin_user['id'],
            status='idea'
        )

        # 更新状态
        update_data = {'status': 'incubating'}

        response = client.put(
            f'/api/cards/{card_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == 200

    def test_delete_card(self, client, test_admin_user, temp_db):
        """测试删除卡片"""
        from backend.models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        card_id = create_card(
            content='To delete',
            url='https://example.com',
            title='Delete Me',
            user_id=test_admin_user['id'],
            status='idea'
        )

        response = client.delete(f'/api/cards/{card_id}')
        assert response.status_code in [200, 204]


@pytest.mark.usefixtures("client", "test_admin_user")
class TestAICardFeatures:
    """AI卡片功能测试"""

    def test_generate_tags_for_card(self, client, test_admin_user, temp_db):
        """测试为卡片生成标签"""
        from backend.models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        card_id = create_card(
            content='A card about Python programming and Flask web framework',
            url='https://example.com',
            title='Python and Flask',
            user_id=test_admin_user['id'],
            status='idea'
        )

        response = client.post('/api/cards/generate-tags',
            data=json.dumps({'card_id': card_id}),
            content_type='application/json')

        # AI功能可能需要mock，这里只测试接口
        assert response.status_code in [200, 202, 503]  # 503 if AI not configured

    def test_merge_cards_with_ai(self, client, test_admin_user, temp_db):
        """测试AI合并卡片"""
        from backend.models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建多个卡片
        card1_id = create_card(
            content='Content about Flask',
            url='https://example.com/1',
            title='Flask',
            user_id=test_admin_user['id'],
            status='idea'
        )

        card2_id = create_card(
            content='Content about Python',
            url='https://example.com/2',
            title='Python',
            user_id=test_admin_user['id'],
            status='idea'
        )

        merge_data = {
            'card_ids': [card1_id, card2_id],
            'merged_content': 'Merged: Flask and Python'
        }

        response = client.post('/api/cards/merge',
            data=json.dumps(merge_data),
            content_type='application/json')

        assert response.status_code in [200, 202]

    def test_convert_card_to_post(self, client, test_admin_user, temp_db):
        """测试转换卡片为文章"""
        from backend.models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        card_id = create_card(
            content='This is a well-developed idea',
            url='https://example.com',
            title='Ready to publish',
            user_id=test_admin_user['id'],
            status='draft'
        )

        response = client.post(f'/api/card/{card_id}/convert-to-post')
        assert response.status_code in [200, 302]
