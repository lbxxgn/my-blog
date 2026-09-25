"""
每周 AI 回顾服务

汇总用户近 7 天（本地时区）的写作活动（文章 / 卡片 / 批注），
调用该用户配置的 chat provider 生成中文每周回顾（Markdown），
并沉淀为知识库「每周回顾」分类下的文档（同周幂等：已存在则跳过或更新）。

被三处复用：
- routes/review.py 的「立即生成本周回顾」（后台线程）
- app.py 的 `flask weekly-review` CLI（crontab）
- tests/test_review.py
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from models import (
    get_db_connection, get_user_ai_config,
    create_kb_category, create_knowledge_doc, update_knowledge_doc,
)

logger = logging.getLogger(__name__)

# created_at / updated_at 均存储为 UTC 字符串（SQLite CURRENT_TIMESTAMP），
# 统计口径与「那年今日」一致，按 Asia/Shanghai（UTC+8，无夏令时）换算。
LOCAL_OFFSET = timedelta(hours=8)

REVIEW_CATEGORY_NAME = '每周回顾'
REVIEW_TAG = '每周回顾'

_STATUS_LABELS = {
    'idea': '想法',
    'draft': '草稿',
    'incubating': '孵化中',
    'published': '已发布',
}


def _utc_naive_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _local_now():
    """当前本地（UTC+8）naive 时间"""
    return _utc_naive_now() + LOCAL_OFFSET


def _local_date(utc_datetime_str):
    """UTC 时间字符串 -> 本地日期 'YYYY-MM-DD'"""
    try:
        dt = datetime.strptime(str(utc_datetime_str)[:19], '%Y-%m-%d %H:%M:%S')
        return (dt + LOCAL_OFFSET).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return str(utc_datetime_str or '')[:10]


def _status_label(status):
    return _STATUS_LABELS.get(status, status or '想法')


def current_week_label(now_local=None):
    """当前（本地）ISO 周标签，如 '2026-W39'"""
    now_local = now_local or _local_now()
    iso_year, iso_week, _ = now_local.isocalendar()
    return f'{iso_year}-W{iso_week:02d}'


def weekly_review_title(now_local=None):
    return f'每周回顾 {current_week_label(now_local)}'


# =============================================================================
# 统计汇总
# =============================================================================

def collect_weekly_stats(user_id, now_local=None):
    """
    汇总指定用户近 7 天（按本地时区）的写作活动

    Returns:
        dict: week_label/week_start/week_end、新增 posts/cards/annotations、
              想法积压数、孵化中超期（14 天未更新）卡片列表
    """
    now_local = now_local or _local_now()
    today = now_local.date()
    week_start_date = today - timedelta(days=6)
    # 本地周起点换算为 UTC 字符串，与 created_at 直接比较
    week_start_utc = datetime.combine(week_start_date, datetime.min.time()) - LOCAL_OFFSET
    week_start_str = week_start_utc.strftime('%Y-%m-%d %H:%M:%S')
    stale_before = (_utc_naive_now() - timedelta(days=14)).strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, title, post_type, type, created_at FROM posts
        WHERE author_id = ? AND created_at >= ?
        ORDER BY created_at DESC
    ''', (user_id, week_start_str))
    new_posts = [dict(r) for r in cursor.fetchall()]

    cursor.execute('''
        SELECT id, title, status, created_at FROM cards
        WHERE user_id = ? AND created_at >= ?
        ORDER BY created_at DESC
    ''', (user_id, week_start_str))
    new_cards = [dict(r) for r in cursor.fetchall()]

    cursor.execute('''
        SELECT COUNT(*) AS cnt FROM card_annotations
        WHERE user_id = ? AND created_at >= ?
    ''', (user_id, week_start_str))
    new_annotations = cursor.fetchone()['cnt']

    cursor.execute('''
        SELECT COUNT(*) AS cnt FROM cards
        WHERE user_id = ? AND status = 'idea'
    ''', (user_id,))
    idea_backlog = cursor.fetchone()['cnt']

    cursor.execute('''
        SELECT id, title, updated_at FROM cards
        WHERE user_id = ? AND status = 'incubating' AND updated_at < ?
        ORDER BY updated_at ASC
    ''', (user_id, stale_before))
    stale_incubating = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        'week_label': current_week_label(now_local),
        'week_start': week_start_date.isoformat(),
        'week_end': today.isoformat(),
        'new_posts': new_posts,
        'new_cards': new_cards,
        'new_annotations': new_annotations,
        'idea_backlog': idea_backlog,
        'stale_incubating': stale_incubating,
    }


def _stats_summary(stats):
    return {
        'new_posts': len(stats['new_posts']),
        'new_cards': len(stats['new_cards']),
        'new_annotations': stats['new_annotations'],
        'idea_backlog': stats['idea_backlog'],
        'stale_incubating': len(stats['stale_incubating']),
    }


# =============================================================================
# 回顾内容生成
# =============================================================================

def build_stats_review_markdown(stats):
    """纯统计数据回顾（AI 未配置或调用失败时的降级内容）"""
    lines = [
        f"> 统计区间：{stats['week_start']} ~ {stats['week_end']}（未启用 AI，自动统计生成）",
        '',
        '## 本周概览',
        '',
        f"- 新增文章 {len(stats['new_posts'])} 篇",
        f"- 新增卡片 {len(stats['new_cards'])} 张",
        f"- 新增批注 {stats['new_annotations']} 条",
        f"- 想法积压 {stats['idea_backlog']} 张",
        f"- 孵化中超期（14 天未更新）{len(stats['stale_incubating'])} 张",
        '',
        '## 内容亮点回顾',
        '',
    ]
    if stats['new_posts']:
        lines.append('### 文章')
        lines.append('')
        for p in stats['new_posts']:
            if p.get('post_type') == 'knowledge':
                kind = '知识库文档'
            elif p.get('type') == 'note':
                kind = '笔记'
            else:
                kind = '文章'
            lines.append(f"- 《{p['title']}》（{kind}，{_local_date(p['created_at'])}）")
        lines.append('')
    if stats['new_cards']:
        lines.append('### 卡片')
        lines.append('')
        for c in stats['new_cards']:
            lines.append(f"- {c['title'] or '未命名卡片'}（{_status_label(c['status'])}，{_local_date(c['created_at'])}）")
        lines.append('')
    if not stats['new_posts'] and not stats['new_cards']:
        lines.append('本周没有新增内容。')
        lines.append('')

    lines += ['## 积压提醒', '']
    if stats['idea_backlog']:
        lines.append(f"- 有 {stats['idea_backlog']} 张卡片仍停留在「想法」状态，挑几张推进到草稿吧。")
    else:
        lines.append('- 没有积压的想法卡片，保持！')
    lines.append('')

    lines += ['## 孵化建议', '']
    if stats['stale_incubating']:
        for c in stats['stale_incubating']:
            lines.append(
                f"- 「{c['title'] or '未命名卡片'}」在孵化中已超过 14 天未更新"
                f"（最后更新 {_local_date(c['updated_at'])}），考虑继续推进或归档。")
    else:
        lines.append('- 没有长期停滞的孵化卡片。')
    lines.append('')
    return '\n'.join(lines)


def build_ai_prompt(stats):
    """组装给 LLM 的每周回顾 prompt"""
    if stats['new_posts']:
        posts_text = '\n'.join(
            f"- 《{p['title']}》（{'笔记' if p.get('type') == 'note' else ('知识库文档' if p.get('post_type') == 'knowledge' else '文章')}，{_local_date(p['created_at'])}）"
            for p in stats['new_posts'][:30])
    else:
        posts_text = '（无）'
    if stats['new_cards']:
        cards_text = '\n'.join(
            f"- {c['title'] or '未命名卡片'}（{_status_label(c['status'])}）"
            for c in stats['new_cards'][:30])
    else:
        cards_text = '（无）'
    if stats['stale_incubating']:
        stale_text = '\n'.join(
            f"- {c['title'] or '未命名卡片'}（最后更新 {_local_date(c['updated_at'])}）"
            for c in stats['stale_incubating'][:10])
    else:
        stale_text = '（无）'

    return f"""请根据以下数据，为作者写一份中文每周回顾（{stats['week_label']}，{stats['week_start']} ~ {stats['week_end']}）。

【本周数据】
- 新增文章 {len(stats['new_posts'])} 篇
{posts_text}
- 新增卡片 {len(stats['new_cards'])} 张
{cards_text}
- 新增批注 {stats['new_annotations']} 条
- 想法积压 {stats['idea_backlog']} 张（status=idea 的卡片总数）
- 孵化中超期（14 天未更新）{len(stats['stale_incubating'])} 张
{stale_text}

【输出要求】
1. Markdown 格式，包含且仅包含这四个二级小节：## 本周概览、## 内容亮点回顾、## 积压提醒、## 孵化建议
2. 「本周概览」用几句话自然概括本周的写作状态，不要罗列干巴巴的数字
3. 「内容亮点回顾」挑 2-4 条本周新增内容，说出它们之间可能的关联或值得回味的点；引用具体标题
4. 「积压提醒」针对想法积压给出一句诚恳的提醒（没有积压就给予肯定）
5. 「孵化建议」针对超期孵化卡片，每张给一条具体、可执行的下一步建议
6. 语气像一个了解作者的老朋友，温暖但不空洞；全文 300-600 字
7. 直接输出 Markdown 正文，不要用代码围栏包裹，不要输出一级标题，不要任何解释性文字
"""


def _create_user_provider(user_id):
    """按用户 AI 配置创建 chat provider；未启用/未配置密钥时返回 None"""
    ai_config = get_user_ai_config(user_id)
    if not ai_config or not ai_config.get('ai_tag_generation_enabled'):
        return None
    if not ai_config.get('ai_api_key'):
        return None
    from ai_services import TagGenerator
    return TagGenerator.create_provider(
        ai_config.get('ai_provider', 'dashscope'),
        ai_config['ai_api_key'],
        ai_config.get('ai_model'),
        base_url=ai_config.get('ai_base_url'),
    )


# =============================================================================
# 知识库文档落库
# =============================================================================

def _get_or_create_review_category():
    """获取（不存在则创建）space='knowledge' 的「每周回顾」分类，返回分类 ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM categories WHERE name = ? AND space = 'knowledge'",
        (REVIEW_CATEGORY_NAME,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['id']

    category_id = create_kb_category(
        REVIEW_CATEGORY_NAME, parent_id=None, space='knowledge',
        icon='🗓️', description='自动生成的每周回顾')
    if category_id is None:
        # categories.name 全局唯一：名称被其他空间占用时复用同名分类
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM categories WHERE name = ?', (REVIEW_CATEGORY_NAME,))
        row = cursor.fetchone()
        conn.close()
        category_id = row['id'] if row else None
        logger.warning('「每周回顾」分类名被其他空间占用，复用分类 id=%s', category_id)
    return category_id


def _find_review_doc(user_id, title):
    """按作者 + 标题查找每周回顾文档（同周幂等判断）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT posts.id, posts.title FROM posts
        JOIN categories ON posts.category_id = categories.id
        WHERE posts.post_type = 'knowledge' AND posts.author_id = ?
          AND posts.title = ?
          AND categories.name = ? AND categories.space = 'knowledge'
        ORDER BY posts.id DESC LIMIT 1
    ''', (user_id, title, REVIEW_CATEGORY_NAME))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def find_current_week_review(user_id, now_local=None):
    """查找当前用户本周的回顾文档，不存在返回 None"""
    return _find_review_doc(user_id, weekly_review_title(now_local))


def get_weekly_reviews(user_id, limit=20):
    """当前用户的历史每周回顾文档列表（新到旧）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT posts.id, posts.title, posts.created_at
        FROM posts
        JOIN categories ON posts.category_id = categories.id
        WHERE posts.post_type = 'knowledge' AND posts.author_id = ?
          AND categories.name = ? AND categories.space = 'knowledge'
        ORDER BY posts.created_at DESC, posts.id DESC
        LIMIT ?
    ''', (user_id, REVIEW_CATEGORY_NAME, limit))
    reviews = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for row in reviews:
        row['url'] = f"/knowledge/doc/{row['id']}"
        try:
            dt = datetime.strptime(str(row['created_at'])[:19], '%Y-%m-%d %H:%M:%S')
            row['created_local'] = (dt + LOCAL_OFFSET).strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            row['created_local'] = str(row.get('created_at') or '')[:16]
    return reviews


def generate_weekly_review(user_id, llm_provider=None, force=False, now_local=None):
    """
    生成指定用户的本周回顾并落库为知识库文档（同周幂等）

    Args:
        user_id: 目标用户
        llm_provider: 可选，直接指定 LLM provider（需有 generate_text 方法）；
                      None 时按用户 AI 配置自动创建，未配置则降级为纯统计版
        force: 本周文档已存在时是否重新生成（更新内容）
        now_local: 可选，覆盖「当前本地时间」（测试用）

    Returns:
        dict: success/doc_id/title/url，及 exists/created/updated/ai_used/summary
    """
    now_local = now_local or _local_now()
    title = weekly_review_title(now_local)
    stats = collect_weekly_stats(user_id, now_local=now_local)

    category_id = _get_or_create_review_category()
    if not category_id:
        return {'success': False, 'error': '无法创建「每周回顾」分类'}

    existing = _find_review_doc(user_id, title)
    if existing and not force:
        return {
            'success': True, 'exists': True,
            'doc_id': existing['id'], 'title': title,
            'url': f"/knowledge/doc/{existing['id']}",
        }

    content = None
    ai_used = False
    provider = llm_provider if llm_provider is not None else _create_user_provider(user_id)
    if provider is not None:
        try:
            result = provider.generate_text(
                build_ai_prompt(stats),
                system_prompt='你是一位熟悉作者写作习惯的中文编辑，擅长把一周的碎片记录整理成有温度的回顾。',
                temperature=0.7,
                max_tokens=2000,
            )
            content = (result.get('text') or '') if isinstance(result, dict) else str(result or '')
            content = content.strip()
            # 去掉模型可能残留的代码围栏
            if content.startswith('```'):
                content = re.sub(r'^```[a-zA-Z]*\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            ai_used = bool(content)
        except Exception as e:
            logger.warning('每周回顾 AI 生成失败，降级为统计版: %s', e)
            content = None

    if not content:
        content = build_stats_review_markdown(stats)

    if existing:
        update_knowledge_doc(existing['id'], title, content, category_id, True,
                             tag_names=[REVIEW_TAG])
        doc_id, created, updated = existing['id'], False, True
    else:
        doc_id = create_knowledge_doc(
            title, content, category_id,
            tag_names=[REVIEW_TAG], is_published=True, author_id=user_id)
        created, updated = True, False

    logger.info('每周回顾已%s: user=%s title=%s doc_id=%s ai=%s',
                '更新' if updated else '生成', user_id, title, doc_id, ai_used)

    return {
        'success': True,
        'doc_id': doc_id,
        'title': title,
        'url': f'/knowledge/doc/{doc_id}',
        'created': created,
        'updated': updated,
        'ai_used': ai_used,
        'summary': _stats_summary(stats),
    }
