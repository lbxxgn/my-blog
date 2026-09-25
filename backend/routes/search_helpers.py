"""
搜索辅助模块

统一关键词搜索（跨 posts/cards/docs/annotations）、语义搜索与相关内容
推荐的公共逻辑，供 API 蓝图（backend/routes/api.py）与搜索页路由
（backend/routes/blog.py）共用。
"""

import html
import json
import logging
import re

from flask import url_for

from ai_services.embeddings import embed_text, get_embedding_config
from models import get_db_connection
from models.embeddings import search_similar

logger = logging.getLogger(__name__)

EXCERPT_LENGTH = 120
RELATED_MIN_TEXT_LENGTH = 20


class EmbeddingNotConfigured(Exception):
    """用户未配置或未启用 Embedding"""


class EmbeddingApiError(Exception):
    """Embedding API 调用失败"""


def _make_excerpt(content, length=EXCERPT_LENGTH):
    """将 HTML/纯文本内容截为纯文本摘要"""
    text = re.sub(r'<[^>]+>', ' ', str(content or ''))
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:length]


def _parse_tags(tags_raw):
    """cards.tags 是 JSON 字符串，解析为数组；失败返回空数组"""
    if not tags_raw:
        return []
    try:
        tags = json.loads(tags_raw)
        return tags if isinstance(tags, list) else []
    except (ValueError, TypeError):
        return []


def post_url(post_id):
    return url_for('view_post', post_id=post_id)


def doc_url(doc_id):
    return url_for('knowledge.view_doc', doc_id=doc_id)


def unified_search(user_id, query, limit=6):
    """
    跨库关键词（LIKE，大小写不敏感）搜索。

    Returns:
        dict: {'posts': [...], 'cards': [...], 'docs': [...], 'annotations': [...]}
    """
    result = {'posts': [], 'cards': [], 'docs': [], 'annotations': []}
    if not query:
        return result

    pattern = f'%{query}%'
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 已发布的博客文章（公开内容）
        cursor.execute('''
            SELECT id, type, title, content, created_at
            FROM posts
            WHERE is_published = 1 AND post_type = 'blog'
              AND (title LIKE ? OR content LIKE ?)
            ORDER BY created_at DESC LIMIT ?
        ''', (pattern, pattern, limit))
        for row in cursor.fetchall():
            result['posts'].append({
                'id': row['id'],
                'type': row['type'],
                'title': row['title'],
                'url': post_url(row['id']),
                'excerpt': _make_excerpt(row['content']),
                'date': row['created_at'],
            })

        # 当前用户的卡片
        cursor.execute('''
            SELECT id, title, content, tags
            FROM cards
            WHERE user_id = ?
              AND (title LIKE ? OR content LIKE ?)
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, pattern, pattern, limit))
        for row in cursor.fetchall():
            result['cards'].append({
                'id': row['id'],
                'title': row['title'],
                'excerpt': _make_excerpt(row['content']),
                'tags': _parse_tags(row['tags']),
                'url': None,
            })

        # 当前用户的知识库文档（含未发布）
        cursor.execute('''
            SELECT id, title, content
            FROM posts
            WHERE post_type = 'knowledge' AND author_id = ?
              AND (title LIKE ? OR content LIKE ?)
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, pattern, pattern, limit))
        for row in cursor.fetchall():
            result['docs'].append({
                'id': row['id'],
                'title': row['title'],
                'url': doc_url(row['id']),
                'excerpt': _make_excerpt(row['content']),
            })

        # 当前用户的卡片批注
        cursor.execute('''
            SELECT id, card_id, annotation_text, note, source_url
            FROM card_annotations
            WHERE user_id = ?
              AND (annotation_text LIKE ? OR note LIKE ?)
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, pattern, pattern, limit))
        for row in cursor.fetchall():
            result['annotations'].append({
                'id': row['id'],
                'card_id': row['card_id'],
                'text': row['annotation_text'],
                'note': row['note'],
                'source_url': row['source_url'],
            })
    finally:
        conn.close()

    return result


def is_embedding_configured(user_id):
    """当前用户是否已配置并启用 Embedding"""
    config = get_embedding_config(user_id)
    return bool(config and config.get('enabled'))


def _load_semantic_entities(matches):
    """
    将 search_similar 的结果 [(source_type, source_id, score)] 加载为
    分组实体 dict。post 只收已发布 blog，doc 收 knowledge（含未发布），
    card 全部保留。
    """
    groups = {'posts': [], 'cards': [], 'docs': []}
    if not matches:
        return groups

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for source_type, source_id, score in matches:
            score = round(float(score), 3)
            if source_type == 'post':
                cursor.execute('''
                    SELECT id, type, title, content, created_at
                    FROM posts WHERE id = ? AND is_published = 1 AND post_type = 'blog'
                ''', (source_id,))
                row = cursor.fetchone()
                if not row:
                    continue
                groups['posts'].append({
                    'id': row['id'],
                    'type': row['type'],
                    'title': row['title'],
                    'url': post_url(row['id']),
                    'excerpt': _make_excerpt(row['content']),
                    'date': row['created_at'],
                    'score': score,
                })
            elif source_type == 'doc':
                cursor.execute('''
                    SELECT id, title, content
                    FROM posts WHERE id = ? AND post_type = 'knowledge'
                ''', (source_id,))
                row = cursor.fetchone()
                if not row:
                    continue
                groups['docs'].append({
                    'id': row['id'],
                    'title': row['title'],
                    'url': doc_url(row['id']),
                    'excerpt': _make_excerpt(row['content']),
                    'score': score,
                })
            elif source_type == 'card':
                cursor.execute(
                    'SELECT id, title, content, tags FROM cards WHERE id = ?', (source_id,))
                row = cursor.fetchone()
                if not row:
                    continue
                groups['cards'].append({
                    'id': row['id'],
                    'title': row['title'],
                    'excerpt': _make_excerpt(row['content']),
                    'tags': _parse_tags(row['tags']),
                    'url': None,
                    'score': score,
                })
    finally:
        conn.close()

    return groups


def semantic_search(user_id, query, limit=20):
    """
    语义搜索：embed query -> search_similar -> 分组组装。

    Raises:
        EmbeddingNotConfigured: 未配置或未启用
        EmbeddingApiError: Embedding API 调用失败
    """
    if not is_embedding_configured(user_id):
        raise EmbeddingNotConfigured()

    config = get_embedding_config(user_id)
    try:
        vector = embed_text(query, config)
    except Exception as e:
        logger.error(f"embed_text failed in semantic_search: {e}")
        raise EmbeddingApiError(str(e))

    matches = search_similar(vector, top_k=limit, source_types=['post', 'card', 'doc'])
    return _load_semantic_entities(matches)


def find_related(user_id, text, exclude_type=None, exclude_id=None, limit=8):
    """
    查找与给定文本相关的实体（供“相关阅读/相关卡片”使用）。

    Raises:
        EmbeddingNotConfigured: 未配置或未启用
        EmbeddingApiError: Embedding API 调用失败
    """
    if not is_embedding_configured(user_id):
        raise EmbeddingNotConfigured()

    config = get_embedding_config(user_id)
    try:
        vector = embed_text(text, config)
    except Exception as e:
        logger.error(f"embed_text failed in find_related: {e}")
        raise EmbeddingApiError(str(e))

    matches = search_similar(vector, top_k=limit + 5, source_types=['post', 'card', 'doc'])

    items = []
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for source_type, source_id, score in matches:
            if exclude_type and exclude_id and source_type == exclude_type \
                    and source_id == exclude_id:
                continue
            if source_type == 'post':
                cursor.execute('''
                    SELECT id, title, content
                    FROM posts WHERE id = ? AND is_published = 1 AND post_type = 'blog'
                ''', (source_id,))
                row = cursor.fetchone()
                url = post_url(source_id) if row else None
            elif source_type == 'doc':
                cursor.execute('''
                    SELECT id, title, content
                    FROM posts WHERE id = ? AND post_type = 'knowledge'
                ''', (source_id,))
                row = cursor.fetchone()
                url = doc_url(source_id) if row else None
            elif source_type == 'card':
                cursor.execute(
                    'SELECT id, title, content FROM cards WHERE id = ?', (source_id,))
                row = cursor.fetchone()
                url = None
            else:
                continue

            if not row:
                continue

            # 内容过短的实体没有参考价值，跳过
            full_text = f"{row['title'] or ''}{row['content'] or ''}"
            if len(full_text) < RELATED_MIN_TEXT_LENGTH:
                continue

            items.append({
                'source_type': source_type,
                'source_id': source_id,
                'title': row['title'],
                'excerpt': _make_excerpt(row['content']),
                'url': url,
                'score': round(float(score), 3),
            })
            if len(items) >= limit:
                break
    finally:
        conn.close()

    return items
