"""
回顾页路由

- GET  /review                        回顾页（写作热力 / 那年今日 / 随机漫步 / 每周回顾）
- GET  /api/review/today              那年今日（本地时区按月日匹配历年内容）
- GET  /api/review/random             随机漫步（随机 5 张卡片）
- GET  /api/review/activity           写作热力图数据（按本地日期聚合 posts+cards）
- GET  /api/review/weekly             历史每周回顾文档列表
- GET  /api/review/weekly/status      当前用户每周回顾生成任务状态
- POST /api/review/weekly/generate    异步触发每周回顾生成（202 + 后台线程）
"""

import json
import logging
import threading
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, render_template, request, session

from auth_decorators import login_required
from logger import log_error
from models import get_db_connection, truncate_text
from services import weekly_review as weekly_review_service

logger = logging.getLogger(__name__)

review_bp = Blueprint('review', __name__)

# created_at 为 UTC 字符串，展示/统计按 Asia/Shanghai（UTC+8，无夏令时）
LOCAL_OFFSET = timedelta(hours=8)


def _local_now():
    return datetime.now(timezone.utc).replace(tzinfo=None) + LOCAL_OFFSET


def _excerpt(content, max_length=120):
    return truncate_text(content or '', max_length)


# =============================================================================
# 页面
# =============================================================================

@review_bp.route('/review')
@login_required
def review_page():
    """回顾页"""
    return render_template('review.html')


# =============================================================================
# 那年今日
# =============================================================================

@review_bp.route('/api/review/today')
@login_required
def api_review_today():
    """那年今日：本地月日=今天且年份<今年的 posts + cards，按年份倒序"""
    user_id = session['user_id']
    now_local = _local_now()
    month_day = now_local.strftime('%m-%d')
    current_year = now_local.strftime('%Y')

    local_mmdd = "strftime('%m-%d', datetime(created_at, '+8 hours'))"
    local_year = "strftime('%Y', datetime(created_at, '+8 hours'))"

    items = []
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
        SELECT id, title, content, post_type, type, {local_year} AS year
        FROM posts
        WHERE author_id = ? AND {local_mmdd} = ? AND {local_year} < ?
    ''', (user_id, month_day, current_year))
    for row in cursor.fetchall():
        row = dict(row)
        is_knowledge = row.get('post_type') == 'knowledge'
        item_type = 'knowledge' if is_knowledge else ('note' if row.get('type') == 'note' else 'post')
        items.append({
            'id': row['id'],
            'year': int(row['year']),
            'title': row['title'],
            'type': item_type,
            'url': f"/knowledge/doc/{row['id']}" if is_knowledge else f"/post/{row['id']}",
            'excerpt': _excerpt(row.get('content')),
        })

    cursor.execute(f'''
        SELECT id, title, content, {local_year} AS year
        FROM cards
        WHERE user_id = ? AND {local_mmdd} = ? AND {local_year} < ?
    ''', (user_id, month_day, current_year))
    for row in cursor.fetchall():
        row = dict(row)
        items.append({
            'id': row['id'],
            'year': int(row['year']),
            'title': row['title'] or '未命名卡片',
            'type': 'card',
            'url': None,
            'excerpt': _excerpt(row.get('content')),
        })

    conn.close()

    items.sort(key=lambda x: (-x['year'], x['id']))
    return jsonify({'success': True, 'items': items})


# =============================================================================
# 随机漫步
# =============================================================================

@review_bp.route('/api/review/random')
@login_required
def api_review_random():
    """随机漫步：当前用户随机 5 张卡片"""
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, content, tags, status
        FROM cards
        WHERE user_id = ?
        ORDER BY RANDOM() LIMIT 5
    ''', (user_id,))

    cards = []
    for row in cursor.fetchall():
        row = dict(row)
        try:
            tags = json.loads(row['tags']) if row.get('tags') else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        cards.append({
            'id': row['id'],
            'title': row['title'] or '未命名卡片',
            'excerpt': _excerpt(row.get('content')),
            'tags': tags if isinstance(tags, list) else [],
            'status': row['status'],
        })
    conn.close()
    return jsonify({'success': True, 'cards': cards})


# =============================================================================
# 写作热力图
# =============================================================================

@review_bp.route('/api/review/activity')
@login_required
def api_review_activity():
    """写作热力：posts + cards 按本地日期聚合，返回 {date: count}"""
    user_id = session['user_id']
    days = request.args.get('days', 371, type=int) or 371
    days = max(30, min(days, 732))

    now_local = _local_now()
    start_date = now_local.date() - timedelta(days=days - 1)
    start_utc_str = (datetime.combine(start_date, datetime.min.time())
                     - LOCAL_OFFSET).strftime('%Y-%m-%d %H:%M:%S')
    local_day = "strftime('%Y-%m-%d', datetime(created_at, '+8 hours'))"

    activity = {}
    conn = get_db_connection()
    cursor = conn.cursor()
    for table, owner_col in (('posts', 'author_id'), ('cards', 'user_id')):
        cursor.execute(f'''
            SELECT {local_day} AS day, COUNT(*) AS cnt
            FROM {table}
            WHERE {owner_col} = ? AND created_at >= ?
            GROUP BY day
        ''', (user_id, start_utc_str))
        for row in cursor.fetchall():
            if row['day']:
                activity[row['day']] = activity.get(row['day'], 0) + row['cnt']
    conn.close()

    return jsonify({'success': True, 'activity': activity, 'days': days})


# =============================================================================
# 每周回顾
# =============================================================================

# 生成任务状态（单进程内存态；进程重启后以「本周文档是否已存在」兜底防重）
_weekly_tasks = {}
_weekly_tasks_lock = threading.Lock()


def _set_weekly_task(user_id, **fields):
    with _weekly_tasks_lock:
        state = _weekly_tasks.setdefault(user_id, {'status': 'idle'})
        state.update(fields)


def _get_weekly_task(user_id):
    with _weekly_tasks_lock:
        return dict(_weekly_tasks.get(user_id, {'status': 'idle'}))


def _run_weekly_review(app, user_id):
    """后台线程：生成每周回顾并回写任务状态"""
    with app.app_context():
        try:
            result = weekly_review_service.generate_weekly_review(user_id)
            if result.get('success'):
                _set_weekly_task(user_id, status='done',
                                 doc_id=result.get('doc_id'),
                                 url=result.get('url'),
                                 ai_used=result.get('ai_used', False))
            else:
                _set_weekly_task(user_id, status='error',
                                 error=result.get('error', '生成失败'))
        except Exception as e:
            logger.error('每周回顾生成失败: %s', e)
            log_error(e, context='每周回顾生成失败', user_id=user_id)
            _set_weekly_task(user_id, status='error', error='生成失败，请稍后重试')


@review_bp.route('/api/review/weekly')
@login_required
def api_review_weekly():
    """历史每周回顾文档列表"""
    reviews = weekly_review_service.get_weekly_reviews(user_id=session['user_id'])
    return jsonify({'success': True, 'reviews': reviews})


@review_bp.route('/api/review/weekly/status')
@login_required
def api_review_weekly_status():
    """当前用户的生成任务状态（前端轮询用）"""
    user_id = session['user_id']
    state = _get_weekly_task(user_id)
    if state.get('status') == 'idle':
        existing = weekly_review_service.find_current_week_review(user_id)
        if existing:
            state = {'status': 'exists', 'doc_id': existing['id'],
                     'url': f"/knowledge/doc/{existing['id']}"}
    return jsonify({'success': True, **state})


@review_bp.route('/api/review/weekly/generate', methods=['POST'])
@login_required
def api_review_weekly_generate():
    """异步触发本周回顾生成：立即返回 202，LLM 调用放后台线程"""
    user_id = session['user_id']

    if _get_weekly_task(user_id).get('status') == 'running':
        return jsonify({'success': True, 'status': 'running'}), 202

    # 防重入：本周已生成则直接返回已存在
    existing = weekly_review_service.find_current_week_review(user_id)
    if existing:
        return jsonify({'success': True, 'status': 'exists',
                        'doc_id': existing['id'],
                        'url': f"/knowledge/doc/{existing['id']}"}), 200

    app = current_app._get_current_object()
    _set_weekly_task(user_id, status='running', doc_id=None, url=None, error=None)
    t = threading.Thread(target=_run_weekly_review, args=(app, user_id))
    t.daemon = True
    t.start()

    return jsonify({'success': True, 'status': 'running'}), 202
