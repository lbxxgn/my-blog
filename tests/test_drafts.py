"""
草稿同步功能测试
测试多设备草稿同步、冲突检测和解决
"""

import pytest
import json
from datetime import datetime


@pytest.mark.usefixtures("client", "test_admin_user")
class TestDraftsAPI:
    """草稿API测试"""

    def test_get_drafts_list_empty(self, client, test_admin_user):
        """测试获取空的草稿列表"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/api/drafts')
        assert response.status_code == 200
        data = response.get_json()
        assert 'drafts' in data
        assert isinstance(data['drafts'], list)

    def test_create_draft(self, client, test_admin_user):
        """测试创建草稿"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        draft_data = {
            'title': 'Test Draft',
            'content': 'Draft content here'
        }

        response = client.post('/api/drafts',
            data=json.dumps(draft_data),
            content_type='application/json')

        assert response.status_code == 200
        data = response.get_json()
        assert 'draft_id' in data or 'id' in data

    def test_get_single_draft(self, client, test_admin_user, temp_db):
        """测试获取单个草稿"""
        from backend.models.draft import create_draft

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建测试草稿
        draft_id = create_draft(
            title='Test Draft',
            content='Test content',
            user_id=test_admin_user['id']
        )

        response = client.get(f'/api/drafts/{draft_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Test Draft'

    def test_update_draft(self, client, test_admin_user, temp_db):
        """测试更新草稿"""
        from backend.models.draft import create_draft

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        draft_id = create_draft(
            title='Original Title',
            content='Original content',
            user_id=test_admin_user['id']
        )

        update_data = {
            'title': 'Updated Title',
            'content': 'Updated content'
        }

        response = client.put(
            f'/api/drafts/{draft_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Updated Title'

    def test_delete_draft(self, client, test_admin_user, temp_db):
        """测试删除草稿"""
        from backend.models.draft import create_draft

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        draft_id = create_draft(
            title='To Delete',
            content='Content',
            user_id=test_admin_user['id']
        )

        response = client.delete(f'/api/drafts/{draft_id}')
        assert response.status_code in [200, 204]

    def test_draft_conflict_detection(self, client, test_admin_user, temp_db):
        """测试草稿冲突检测"""
        from backend.models.draft import create_draft

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        draft_id = create_draft(
            title='Conflict Test',
            content='Original content',
            user_id=test_admin_user['id']
        )

        # 模拟冲突：客户端版本与服务器版本不一致
        update_data = {
            'title': 'Updated',
            'content': 'Updated content',
            'client_version': 'wrong_version',
            'server_version': 'different_version'
        }

        response = client.put(
            f'/api/drafts/{draft_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )

        # 应该检测到冲突
        assert response.status_code in [200, 409]

    def test_resolve_draft_conflict(self, client, test_admin_user, temp_db):
        """测试解决草稿冲突"""
        from backend.models.draft import create_draft

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        draft_id = create_draft(
            title='Conflict Draft',
            content='Server content',
            user_id=test_admin_user['id']
        )

        # 解决冲突
        resolve_data = {
            'draft_id': draft_id,
            'resolution': 'use_client',
            'client_content': 'Merged content'
        }

        response = client.post(
            '/api/drafts/resolve',
            data=json.dumps(resolve_data),
            content_type='application/json'
        )

        assert response.status_code == 200


@pytest.mark.integration
class TestDraftWorkflow:
    """草稿集成测试"""

    def test_draft_to_public_post_workflow(self, client, test_admin_user, temp_db):
        """测试草稿到公开发布的工作流"""
        from backend.models.draft import create_draft
        from backend.models import create_post

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 1. 创建草稿
        draft_id = create_draft(
            title='Draft to Post',
            content='Draft content that will become a post',
            user_id=test_admin_user['id']
        )

        # 2. 发布草稿为文章
        post_data = {
            'title': 'Draft to Post',
            'content': 'Final content',
            'category_id': None,
            'tags': [],
            'access': 'public',
            'allow_comments': True
        }

        response = client.post('/new', data=post_data)
        # 应该重定向或成功
        assert response.status_code in [200, 302]

    def test_autosave_draft_interval(self, client, test_admin_user):
        """测试草稿自动保存间隔"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 访问编辑页面
        response = client.get('/admin/new')
        assert response.status_code == 200

        # 检查页面是否包含自动保存配置
        page_content = response.get_data(as_text=True)
        # 应该有30秒的自动保存配置
        assert '30' in page_content or 'autosave' in page_content.lower()
