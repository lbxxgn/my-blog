"""
Knowledge Base Model Functions

知识库：树形分类与文档管理，以及博客/卡片到知识库的沉淀。
"""

import sqlite3

from .db import get_db_context, _safe_delete_post_fts
from .posts import create_post, get_post_by_id
from .tags import set_post_tags, get_post_tags
from .cards import get_card_by_id, delete_card

__all__ = [
    'get_kb_categories',
    'build_category_tree',
    'get_category_tree',
    'get_category_path',
    'create_kb_category',
    'update_kb_category',
    'move_kb_category',
    'delete_kb_category',
    'get_subcategories',
    'get_descendant_category_ids',
    'get_doc_count_by_category',
    'create_knowledge_doc',
    'get_knowledge_doc',
    'get_knowledge_docs_by_category',
    'get_recent_knowledge_docs',
    'update_knowledge_doc',
    'reorder_knowledge_doc',
    'delete_knowledge_doc',
    'html_to_markdown',
    'precipitate_post_to_knowledge',
    'archive_card_to_knowledge',
]


# =============================================================================
# 知识库：树形分类与文档管理（Knowledge Base）
# =============================================================================

def get_kb_categories(space='knowledge'):
    """获取指定空间的所有分类（扁平列表，供前端构建树）"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM categories
            WHERE space = ?
            ORDER BY sort_order, name
        ''', (space,))
        return [dict(row) for row in cursor.fetchall()]


def build_category_tree(categories):
    """将扁平分类列表构建为嵌套树结构"""
    by_id = {c['id']: {**c, 'children': []} for c in categories}
    roots = []
    for c in categories:
        node = by_id[c['id']]
        parent_id = c.get('parent_id')
        if parent_id and parent_id in by_id:
            by_id[parent_id]['children'].append(node)
        else:
            roots.append(node)
    return roots


def get_category_tree(space='knowledge'):
    """获取指定空间的分类树（嵌套结构）"""
    categories = get_kb_categories(space)
    return build_category_tree(categories)


def get_category_path(category_id):
    """获取分类的祖先链（从根到当前），用于面包屑导航"""
    path = []
    with get_db_context() as conn:
        cursor = conn.cursor()
        current_id = category_id
        seen = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            cursor.execute('SELECT * FROM categories WHERE id = ?', (current_id,))
            row = cursor.fetchone()
            if not row:
                break
            path.append(dict(row))
            current_id = row['parent_id']
    path.reverse()
    return path


def create_kb_category(name, parent_id=None, space='knowledge', slug=None, icon=None, description=None, sort_order=0):
    """创建知识库分类（树形）"""
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO categories (name, parent_id, space, slug, icon, description, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, parent_id, space, slug, icon, description, sort_order))
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def update_kb_category(category_id, name=None, parent_id=None, slug=None, icon=None, description=None, sort_order=None):
    """更新知识库分类"""
    updates = []
    params = []
    for field, val in [('name', name), ('parent_id', parent_id), ('slug', slug),
                       ('icon', icon), ('description', description), ('sort_order', sort_order)]:
        if val is not None:
            updates.append(f'{field} = ?')
            params.append(val)
    if not updates:
        return False
    params.append(category_id)
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(f'UPDATE categories SET {", ".join(updates)} WHERE id = ?', params)
        return cursor.rowcount > 0


def move_kb_category(category_id, new_parent_id, sort_order=0):
    """移动分类到新父级（拖拽）。禁止移动到自身子孙下。"""
    if new_parent_id is not None:
        path = get_category_path(new_parent_id)
        if any(c['id'] == category_id for c in path):
            return False
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE categories SET parent_id = ?, sort_order = ? WHERE id = ?',
                       (new_parent_id, sort_order, category_id))
        return cursor.rowcount > 0


def delete_kb_category(category_id):
    """删除分类：子分类上移到被删分类的父级，文档解绑分类"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT parent_id FROM categories WHERE id = ?', (category_id,))
        row = cursor.fetchone()
        if not row:
            return False
        old_parent = row['parent_id']
        cursor.execute('UPDATE categories SET parent_id = ? WHERE parent_id = ?', (old_parent, category_id))
        cursor.execute('UPDATE posts SET category_id = NULL WHERE category_id = ?', (category_id,))
        cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
        return True


def get_subcategories(parent_id, space='knowledge'):
    """获取直接子分类"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM categories
            WHERE parent_id IS ? AND space = ?
            ORDER BY sort_order, name
        ''', (parent_id, space))
        return [dict(row) for row in cursor.fetchall()]


def get_descendant_category_ids(category_id):
    """获取某分类的所有子孙分类ID（含自身）"""
    ids = [category_id]
    with get_db_context() as conn:
        cursor = conn.cursor()
        stack = [category_id]
        while stack:
            cid = stack.pop()
            cursor.execute('SELECT id FROM categories WHERE parent_id = ?', (cid,))
            for row in cursor.fetchall():
                ids.append(row['id'])
                stack.append(row['id'])
    return ids


def get_doc_count_by_category(category_id):
    """获取分类下知识库文档数（不含子分类）"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as cnt FROM posts
            WHERE category_id = ? AND post_type = 'knowledge'
        ''', (category_id,))
        return cursor.fetchone()['cnt']


# -----------------------------------------------------------------------------
# 知识库文档 CRUD
# -----------------------------------------------------------------------------

def create_knowledge_doc(title, content, category_id, tag_names=None, sort_order=0,
                         source_post_id=None, is_published=True, author_id=None):
    """创建知识库文档（Markdown 内容，post_type='knowledge'）"""
    post_id = create_post(
        title=title,
        content=content,
        is_published=is_published,
        category_id=category_id,
        author_id=author_id,
        type='post',
        post_type='knowledge'
    )
    if post_id and tag_names:
        set_post_tags(post_id, tag_names)
    if post_id:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE posts SET content_format = 'markdown', sort_order = ?, source_post_id = ?
                WHERE id = ?
            ''', (sort_order, source_post_id, post_id))
    return post_id


def get_knowledge_doc(doc_id):
    """获取单个知识库文档"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT posts.*, categories.name as category_name
            FROM posts
            LEFT JOIN categories ON posts.category_id = categories.id
            WHERE posts.id = ? AND posts.post_type = 'knowledge'
        ''', (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_knowledge_docs_by_category(category_id, include_subcategories=False, include_drafts=False):
    """获取分类下的知识库文档"""
    if include_subcategories:
        cat_ids = get_descendant_category_ids(category_id)
        placeholders = ','.join('?' for _ in cat_ids)
        where_cat = f'posts.category_id IN ({placeholders})'
        params = cat_ids
    else:
        where_cat = 'posts.category_id = ?'
        params = [category_id]
    with get_db_context() as conn:
        cursor = conn.cursor()
        draft_filter = '' if include_drafts else 'AND posts.is_published = 1'
        sql = f'''
            SELECT posts.*, categories.name as category_name
            FROM posts
            LEFT JOIN categories ON posts.category_id = categories.id
            WHERE posts.post_type = 'knowledge' AND {where_cat}
            {draft_filter}
            ORDER BY posts.sort_order, posts.created_at DESC
        '''
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_recent_knowledge_docs(limit=10, include_drafts=False):
    """获取最近的知识库文档"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        draft_filter = '' if include_drafts else 'AND is_published = 1'
        cursor.execute(f'''
            SELECT posts.*, categories.name as category_name
            FROM posts
            LEFT JOIN categories ON posts.category_id = categories.id
            WHERE posts.post_type = 'knowledge'
            {draft_filter}
            ORDER BY posts.created_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def update_knowledge_doc(doc_id, title, content, category_id, is_published, tag_names=None, sort_order=None):
    """更新知识库文档"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE posts SET title = ?, content = ?, category_id = ?, is_published = ?,
                             content_format = 'markdown',
                             sort_order = COALESCE(?, sort_order),
                             updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND post_type = 'knowledge'
        ''', (title, content, category_id, is_published, sort_order, doc_id))
        success = cursor.rowcount > 0
    if success and tag_names is not None:
        set_post_tags(doc_id, tag_names)
    return success


def reorder_knowledge_doc(doc_id, sort_order, category_id=None):
    """调整知识库文档排序/移动到新分类（拖拽）"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        if category_id is not None:
            cursor.execute('UPDATE posts SET sort_order = ?, category_id = ? WHERE id = ? AND post_type = ?',
                           (sort_order, category_id, doc_id, 'knowledge'))
        else:
            cursor.execute('UPDATE posts SET sort_order = ? WHERE id = ? AND post_type = ?',
                           (sort_order, doc_id, 'knowledge'))
        return cursor.rowcount > 0


def delete_knowledge_doc(doc_id):
    """删除知识库文档"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        _safe_delete_post_fts(cursor, doc_id)
        cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (doc_id,))
        cursor.execute('DELETE FROM posts WHERE id = ? AND post_type = ?', (doc_id, 'knowledge'))
        return cursor.rowcount > 0


# -----------------------------------------------------------------------------
# 博客 <-> 知识库 关联
# -----------------------------------------------------------------------------

def html_to_markdown(html_content):
    """将 HTML 转换为 Markdown（用于博客沉淀到知识库）"""
    try:
        import html2text
        h = html2text.HTML2Text()
        h.body_width = 0
        h.ignore_images = False
        h.ignore_links = False
        return h.handle(html_content or '')
    except ImportError:
        import re
        text = re.sub(r'<br\s*/?>', '\n', html_content or '')
        text = re.sub(r'</?(p|div)>', '\n', text)
        return re.sub(r'<[^>]+>', '', text)


def precipitate_post_to_knowledge(post_id, category_id, tag_names=None):
    """将博客文章沉淀为知识库文档（HTML→Markdown 转换）"""
    post = get_post_by_id(post_id)
    if not post:
        return None
    markdown_content = html_to_markdown(post['content'])
    title = post['title'] + '（沉淀自博客）'
    if tag_names is None:
        original_tags = get_post_tags(post_id)
        tag_names = [t['name'] for t in original_tags]
    new_doc_id = create_knowledge_doc(
        title=title,
        content=markdown_content,
        category_id=category_id,
        tag_names=tag_names,
        source_post_id=post_id,
        author_id=post.get('author_id')
    )
    return new_doc_id


def archive_card_to_knowledge(card_id, category_id, tag_names=None):
    """将卡片归档到知识库目录（转为知识库文档）"""
    card = get_card_by_id(card_id)
    if not card:
        return None
    content = html_to_markdown(card.get('content', ''))
    if tag_names is None:
        tag_names = card.get('tags') if isinstance(card.get('tags'), list) else []
    doc_id = create_knowledge_doc(
        title=card.get('title') or '未命名',
        content=content,
        category_id=category_id,
        tag_names=tag_names,
        author_id=card.get('user_id')
    )
    if doc_id:
        delete_card(card_id)
    return doc_id
