"""
回顾页与每周 AI 回顾测试

覆盖：
- 那年今日 API（去年/今年过滤、本地时区月日比较、类型标注、排序、他人数据隔离）
- 随机漫步 API（≤5 张、仅当前用户）
- 写作热力 API（按本地日期聚合、窗口过滤）
- 每周回顾服务（统计汇总、mock LLM 落库、同周幂等、强制更新、无 AI 降级）
- 生成 API（202 异步流程、本周已存在防重入）
- 权限（未登录 401 / 跳转登录）
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone

import pytest

LOCAL_OFFSET = timedelta(hours=8)  # 与服务端一致：created_at 存 UTC，统计按 UTC+8


# =============================================================================
# 工具函数
# =============================================================================

def _local_now():
    """当前本地（UTC+8）naive 时间"""
    return datetime.now(timezone.utc).replace(tzinfo=None) + LOCAL_OFFSET


def _utc_str(local_dt):
    """本地 naive 时间 -> UTC 字符串（与 created_at 存储格式一致）"""
    return (local_dt - LOCAL_OFFSET).strftime('%Y-%m-%d %H:%M:%S')


def _same_day_last_year(now_local, years=1):
    try:
        return now_local.replace(year=now_local.year - years)
    except ValueError:
        # 2 月 29 日 → 2 月 28 日
        return now_local.replace(year=now_local.year - years, day=28)


def _login(client, user):
    return client.post('/login', data={
        'username': user['username'],
        'password': user['password'],
    })


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _insert_post(db_path, user_id, title, created_at,
                 post_type='blog', type_='post', content='测试内容'):
    conn = _connect(db_path)
    cur = conn.execute('''
        INSERT INTO posts (title, content, is_published, author_id, post_type, type, created_at, updated_at)
        VALUES (?, ?, 1, ?, ?, ?, ?, ?)
    ''', (title, content, user_id, post_type, type_, created_at, created_at))
    post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return post_id


def _insert_card(db_path, user_id, title, created_at,
                 status='idea', tags=None, updated_at=None):
    conn = _connect(db_path)
    cur = conn.execute('''
        INSERT INTO cards (user_id, title, content, tags, status, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'web', ?, ?)
    ''', (user_id, title, '卡片内容', json.dumps(tags) if tags else None,
          status, created_at, updated_at or created_at))
    card_id = cur.lastrowid
    conn.commit()
    conn.close()
    return card_id


def _insert_annotation(db_path, user_id, created_at):
    conn = _connect(db_path)
    cur = conn.execute('''
        INSERT INTO card_annotations (user_id, source_url, annotation_text, created_at, updated_at)
        VALUES (?, 'https://example.com/page', '批注内容', ?, ?)
    ''', (user_id, created_at, created_at))
    annotation_id = cur.lastrowid
    conn.commit()
    conn.close()
    return annotation_id


def _get_post(db_path, post_id):
    conn = _connect(db_path)
    row = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _get_category(db_path, category_id):
    conn = _connect(db_path)
    row = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _count_posts_with_title(db_path, title):
    conn = _connect(db_path)
    count = conn.execute('SELECT COUNT(*) FROM posts WHERE title = ?', (title,)).fetchone()[0]
    conn.close()
    return count


def _create_other_user(username='other_user'):
    from models import create_user
    from werkzeug.security import generate_password_hash
    return create_user(
        username,
        generate_password_hash('OtherPassword123!', method='pbkdf2:sha256'),
        role='author')


class _MockProvider:
    """模拟 chat provider（带 generate_text 公开方法）"""

    def __init__(self, text='## 本周概览\n\nAI 生成的回顾内容'):
        self.text = text
        self.calls = []

    def generate_text(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2000):
        self.calls.append(prompt)
        return {'text': self.text, 'tokens_used': 10, 'model': 'mock-model'}


# =============================================================================
# 那年今日
# =============================================================================

@pytest.mark.usefixtures('client', 'test_admin_user')
class TestTodayAPI:
    """那年今日 API"""

    def test_today_filters_year_and_user(self, client, test_admin_user, temp_db):
        """去年今天命中；今年今天与他人内容被过滤"""
        uid = test_admin_user['id']
        now = _local_now()
        last_year = _same_day_last_year(now)

        old_post_id = _insert_post(temp_db, uid, '去年今天的文章', _utc_str(last_year))
        _insert_post(temp_db, uid, '今年今天的文章', _utc_str(now))
        other_id = _create_other_user()
        _insert_post(temp_db, other_id, '别人去年今天的文章', _utc_str(last_year))

        _login(client, test_admin_user)
        data = client.get('/api/review/today').get_json()
        assert data['success'] is True

        titles = [i['title'] for i in data['items']]
        assert '去年今天的文章' in titles
        assert '今年今天的文章' not in titles
        assert '别人去年今天的文章' not in titles

        item = next(i for i in data['items'] if i['title'] == '去年今天的文章')
        assert item['year'] == last_year.year
        assert item['type'] == 'post'
        assert item['url'] == f'/post/{old_post_id}'

    def test_today_uses_local_timezone(self, client, test_admin_user, temp_db):
        """月日比较按本地时区（UTC+8），而非 UTC"""
        uid = test_admin_user['id']
        now = _local_now()
        last_year = _same_day_last_year(now)

        # 去年「本地今天 00:30」→ UTC 是昨天 16:30（UTC 月日 ≠ 今天），按本地应命中
        local_early = last_year.replace(hour=0, minute=30, second=0, microsecond=0)
        _insert_post(temp_db, uid, '去年今天凌晨', _utc_str(local_early))

        # 去年「本地明天 00:30」→ UTC 是今天 16:30（UTC 月日 == 今天），按本地不应命中
        local_next_day = local_early + timedelta(days=1)
        _insert_post(temp_db, uid, '去年明天凌晨', _utc_str(local_next_day))

        _login(client, test_admin_user)
        titles = [i['title'] for i in client.get('/api/review/today').get_json()['items']]
        assert '去年今天凌晨' in titles
        assert '去年明天凌晨' not in titles

    def test_today_item_types(self, client, test_admin_user, temp_db):
        """知识库文档 / 笔记 / 卡片的类型标注"""
        uid = test_admin_user['id']
        ts = _utc_str(_same_day_last_year(_local_now()))

        doc_id = _insert_post(temp_db, uid, '去年的知识库文档', ts, post_type='knowledge')
        note_id = _insert_post(temp_db, uid, '去年的笔记', ts, type_='note')
        _insert_card(temp_db, uid, '去年的卡片', ts)

        _login(client, test_admin_user)
        items = {i['title']: i for i in client.get('/api/review/today').get_json()['items']}

        assert items['去年的知识库文档']['type'] == 'knowledge'
        assert items['去年的知识库文档']['url'] == f'/knowledge/doc/{doc_id}'
        assert items['去年的笔记']['type'] == 'note'
        assert items['去年的笔记']['url'] == f'/post/{note_id}'
        assert items['去年的卡片']['type'] == 'card'
        assert items['去年的卡片']['url'] is None

    def test_today_sorted_by_year_desc(self, client, test_admin_user, temp_db):
        """按年份倒序返回"""
        uid = test_admin_user['id']
        now = _local_now()
        _insert_post(temp_db, uid, '三年前', _utc_str(_same_day_last_year(now, years=3)))
        _insert_post(temp_db, uid, '一年前', _utc_str(_same_day_last_year(now, years=1)))

        _login(client, test_admin_user)
        items = client.get('/api/review/today').get_json()['items']
        years = [i['year'] for i in items]
        assert years == sorted(years, reverse=True)
        assert items[0]['title'] == '一年前'

    def test_today_empty(self, client, test_admin_user):
        """无历史内容时返回空列表"""
        _login(client, test_admin_user)
        data = client.get('/api/review/today').get_json()
        assert data['success'] is True
        assert data['items'] == []


# =============================================================================
# 随机漫步
# =============================================================================

@pytest.mark.usefixtures('client', 'test_admin_user')
class TestRandomAPI:
    """随机漫步 API"""

    def test_random_returns_own_cards_up_to_5(self, client, test_admin_user, temp_db):
        """返回 ≤5 张且全部属于当前用户"""
        uid = test_admin_user['id']
        now = _utc_str(_local_now())
        my_ids = {_insert_card(temp_db, uid, f'卡片{i}', now, tags=['t1']) for i in range(7)}
        other_id = _create_other_user()
        for i in range(3):
            _insert_card(temp_db, other_id, f'别人卡片{i}', now)

        _login(client, test_admin_user)
        data = client.get('/api/review/random').get_json()
        assert data['success'] is True

        cards = data['cards']
        assert 0 < len(cards) <= 5
        assert all(c['id'] in my_ids for c in cards)

        first = cards[0]
        assert first['title'].startswith('卡片')
        assert first['tags'] == ['t1']
        assert first['status'] == 'idea'
        assert 'excerpt' in first

    def test_random_empty(self, client, test_admin_user):
        """没有卡片时返回空列表"""
        _login(client, test_admin_user)
        data = client.get('/api/review/random').get_json()
        assert data['success'] is True
        assert data['cards'] == []


# =============================================================================
# 写作热力
# =============================================================================

@pytest.mark.usefixtures('client', 'test_admin_user')
class TestActivityAPI:
    """写作热力 API"""

    def test_activity_aggregates_by_local_date(self, client, test_admin_user, temp_db):
        """posts + cards 按本地日期聚合计数"""
        uid = test_admin_user['id']
        now = _local_now()
        noon_today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        ten_days_ago = noon_today - timedelta(days=10)
        four_hundred_days_ago = noon_today - timedelta(days=400)

        _insert_post(temp_db, uid, '今天文章1', _utc_str(noon_today))
        _insert_post(temp_db, uid, '今天文章2', _utc_str(noon_today))
        _insert_card(temp_db, uid, '今天卡片', _utc_str(noon_today))
        _insert_post(temp_db, uid, '十天前文章', _utc_str(ten_days_ago))
        _insert_post(temp_db, uid, '四百天前文章', _utc_str(four_hundred_days_ago))

        _login(client, test_admin_user)
        data = client.get('/api/review/activity?days=371').get_json()
        assert data['success'] is True
        activity = data['activity']

        assert activity[noon_today.strftime('%Y-%m-%d')] == 3
        assert activity[ten_days_ago.strftime('%Y-%m-%d')] == 1
        assert four_hundred_days_ago.strftime('%Y-%m-%d') not in activity

    def test_activity_only_counts_current_user(self, client, test_admin_user, temp_db):
        """不统计其他用户的内容"""
        now = _local_now()
        other_id = _create_other_user()
        _insert_post(temp_db, other_id, '别人的文章', _utc_str(now))
        _insert_card(temp_db, other_id, '别人的卡片', _utc_str(now))

        _login(client, test_admin_user)
        activity = client.get('/api/review/activity').get_json()['activity']
        assert activity == {}


# =============================================================================
# 每周回顾服务
# =============================================================================

@pytest.mark.usefixtures('temp_db', 'test_user')
class TestWeeklyReviewService:
    """每周回顾服务（统计 + 落库 + 幂等）"""

    def test_collect_weekly_stats(self, temp_db, test_user):
        """近 7 天汇总：新增、批注、想法积压、超期孵化"""
        from services import weekly_review

        uid = test_user['id']
        now = _local_now()
        noon = now.replace(hour=12, minute=0, second=0, microsecond=0)

        # 本周内
        _insert_post(temp_db, uid, '本周文章', _utc_str(now - timedelta(days=2)))
        _insert_card(temp_db, uid, '本周卡片', _utc_str(now - timedelta(days=1)), status='draft')
        _insert_annotation(temp_db, uid, _utc_str(noon))
        # 窗口外
        _insert_post(temp_db, uid, '十天前文章', _utc_str(now - timedelta(days=10)))
        # 想法积压（一张旧、一张新）
        _insert_card(temp_db, uid, '旧想法', _utc_str(now - timedelta(days=30)), status='idea')
        _insert_card(temp_db, uid, '新想法', _utc_str(noon), status='idea')
        # 孵化中（一张 20 天未更新超期，一张活跃）
        _insert_card(temp_db, uid, '停滞孵化', _utc_str(now - timedelta(days=20)), status='incubating')
        _insert_card(temp_db, uid, '活跃孵化', _utc_str(noon), status='incubating')

        stats = weekly_review.collect_weekly_stats(uid)

        assert [p['title'] for p in stats['new_posts']] == ['本周文章']
        assert {c['title'] for c in stats['new_cards']} == {'本周卡片', '新想法', '活跃孵化'}
        assert stats['new_annotations'] == 1
        assert stats['idea_backlog'] == 2
        assert [c['title'] for c in stats['stale_incubating']] == ['停滞孵化']
        assert stats['week_label'] == weekly_review.current_week_label()

    def test_generate_with_mock_provider(self, temp_db, test_user):
        """mock LLM：回顾文档落库到「每周回顾」分类"""
        from services import weekly_review

        uid = test_user['id']
        _insert_post(temp_db, uid, '本周文章', _utc_str(_local_now()))

        provider = _MockProvider()
        result = weekly_review.generate_weekly_review(uid, llm_provider=provider)

        assert result['success'] is True
        assert result.get('created') is True
        assert result['ai_used'] is True
        assert len(provider.calls) == 1
        assert '本周文章' in provider.calls[0]  # prompt 中包含本周标题

        doc = _get_post(temp_db, result['doc_id'])
        assert doc is not None
        assert doc['post_type'] == 'knowledge'
        assert doc['title'] == weekly_review.weekly_review_title()
        assert doc['author_id'] == uid
        assert 'AI 生成的回顾内容' in doc['content']

        category = _get_category(temp_db, doc['category_id'])
        assert category['name'] == '每周回顾'
        assert category['space'] == 'knowledge'

    def test_generate_idempotent_same_week(self, temp_db, test_user):
        """同周重复生成返回已存在，不产生重复文档、不再调 LLM"""
        from services import weekly_review

        provider = _MockProvider()
        r1 = weekly_review.generate_weekly_review(test_user['id'], llm_provider=provider)
        r2 = weekly_review.generate_weekly_review(test_user['id'], llm_provider=provider)

        assert r2.get('exists') is True
        assert r2['doc_id'] == r1['doc_id']
        assert len(provider.calls) == 1
        assert _count_posts_with_title(temp_db, weekly_review.weekly_review_title()) == 1

    def test_generate_force_updates_existing(self, temp_db, test_user):
        """force=True 时更新已有文档而非新建"""
        from services import weekly_review

        provider = _MockProvider()
        r1 = weekly_review.generate_weekly_review(test_user['id'], llm_provider=provider)
        r2 = weekly_review.generate_weekly_review(test_user['id'], llm_provider=provider, force=True)

        assert r2.get('updated') is True
        assert r2['doc_id'] == r1['doc_id']
        assert len(provider.calls) == 2
        assert _count_posts_with_title(temp_db, weekly_review.weekly_review_title()) == 1

    def test_generate_fallback_without_ai(self, temp_db, test_user):
        """未配置 AI 密钥时降级为纯统计版"""
        from services import weekly_review

        uid = test_user['id']
        _insert_card(temp_db, uid, '积压想法', _utc_str(_local_now()), status='idea')

        result = weekly_review.generate_weekly_review(uid)
        assert result['success'] is True
        assert result['ai_used'] is False

        doc = _get_post(temp_db, result['doc_id'])
        assert '本周概览' in doc['content']
        assert '积压提醒' in doc['content']
        assert '孵化建议' in doc['content']
        assert '统计区间' in doc['content']

    def test_generate_fallback_on_llm_error(self, temp_db, test_user):
        """LLM 调用抛异常时同样降级为统计版"""
        from services import weekly_review

        class _BrokenProvider:
            def generate_text(self, *args, **kwargs):
                raise RuntimeError('LLM 不可用')

        result = weekly_review.generate_weekly_review(
            test_user['id'], llm_provider=_BrokenProvider())
        assert result['success'] is True
        assert result['ai_used'] is False
        doc = _get_post(temp_db, result['doc_id'])
        assert '本周概览' in doc['content']


# =============================================================================
# 每周回顾 API
# =============================================================================

@pytest.mark.usefixtures('client', 'test_admin_user')
class TestWeeklyAPI:
    """每周回顾列表 / 生成 API"""

    def test_weekly_list(self, client, test_admin_user):
        """历史列表返回已生成的回顾"""
        from services import weekly_review

        weekly_review.generate_weekly_review(
            test_admin_user['id'], llm_provider=_MockProvider())

        _login(client, test_admin_user)
        data = client.get('/api/review/weekly').get_json()
        assert data['success'] is True
        assert len(data['reviews']) == 1
        review = data['reviews'][0]
        assert review['title'].startswith('每周回顾 ')
        assert review['url'].startswith('/knowledge/doc/')
        assert review['created_local']

    def test_generate_async_flow(self, client, test_admin_user, monkeypatch):
        """POST 返回 202，后台线程完成后状态变为 done"""
        import services.weekly_review as weekly_review_service

        calls = {}

        def fake_generate(user_id, **kwargs):
            calls['user_id'] = user_id
            return {'success': True, 'doc_id': 999,
                    'title': '每周回顾 2026-W39',
                    'url': '/knowledge/doc/999', 'ai_used': True}

        monkeypatch.setattr(weekly_review_service, 'generate_weekly_review', fake_generate)

        _login(client, test_admin_user)
        resp = client.post('/api/review/weekly/generate', json={})
        assert resp.status_code == 202
        assert resp.get_json()['status'] == 'running'

        state = {}
        for _ in range(100):
            state = client.get('/api/review/weekly/status').get_json()
            if state['status'] != 'running':
                break
            time.sleep(0.05)

        assert state['status'] == 'done'
        assert state['doc_id'] == 999
        assert calls['user_id'] == test_admin_user['id']

    def test_generate_returns_exists_when_already_generated(self, client, test_admin_user):
        """本周已生成时返回 200 + exists，不再触发生成"""
        from services import weekly_review

        result = weekly_review.generate_weekly_review(
            test_admin_user['id'], llm_provider=_MockProvider())
        assert result.get('created') is True

        _login(client, test_admin_user)
        resp = client.post('/api/review/weekly/generate', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'exists'
        assert data['doc_id'] == result['doc_id']


# =============================================================================
# 页面与权限
# =============================================================================

class TestReviewPage:
    """回顾页渲染与访问控制"""

    def test_review_page_renders(self, client, test_admin_user):
        _login(client, test_admin_user)
        resp = client.get('/review')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert '写作热力' in html
        assert '那年今日' in html
        assert '随机漫步' in html
        assert '每周回顾' in html

    def test_review_page_requires_login(self, client):
        resp = client.get('/review')
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    @pytest.mark.parametrize('path', [
        '/api/review/today',
        '/api/review/random',
        '/api/review/activity',
        '/api/review/weekly',
        '/api/review/weekly/status',
    ])
    def test_get_apis_require_login(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 401

    def test_generate_api_requires_login(self, client):
        resp = client.post('/api/review/weekly/generate', json={})
        assert resp.status_code == 401
