"""端到端：回顾页、统一搜索、快速笔记与卡片 API。"""

import uuid

import pytest

from .harness import login

pytestmark = pytest.mark.e2e


def test_review_page_and_apis(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])

    page.goto('/review')
    page.wait_body_contains('回顾')

    today = page.fetch_json('/api/review/today')
    assert today['status'] == 200
    assert today['data']['success'] is True

    activity = page.fetch_json('/api/review/activity?days=30')
    assert activity['status'] == 200
    assert activity['data']['success'] is True
    assert 'activity' in activity['data']


def test_unified_search_api(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])
    payload = page.fetch_json('/api/search/all?q=e2e-marker')

    assert payload['status'] == 200
    titles = [post['title'] for post in payload['data'].get('posts', [])]
    assert seed['post_title'] in titles


def test_quick_note_and_card_apis(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])

    marker = uuid.uuid4().hex[:8]
    note = page.fetch_json(
        '/knowledge_base/quick-note',
        method='POST',
        payload={'title': f'E2E 快速笔记 {marker}', 'content': f'E2E 快速笔记内容 {marker}'},
    )
    assert note['status'] == 200
    assert note['data']['success'] is True

    card = page.fetch_json(
        '/knowledge_base/api/cards',
        method='POST',
        payload={'title': f'E2E 卡片 {marker}', 'content': f'E2E 卡片内容 {marker}'},
    )
    assert card['status'] == 201
    assert card['data']['success'] is True

    cards = page.fetch_json(f'/knowledge_base/api/cards?q={marker}')
    assert cards['status'] == 200
    assert cards['data']['success'] is True
    assert any(marker in (item.get('title') or '') for item in cards['data']['cards'])
