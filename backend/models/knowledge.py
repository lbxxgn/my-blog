"""
Knowledge Base Model Functions

知识库：树形分类与文档管理，以及博客/卡片到知识库的沉淀。
"""

import sqlite3

from .db import get_db_context, _safe_delete_post_fts
from .posts import create_post, get_post_by_id
from .tags import set_post_tags, get_post_tags
from .cards import get_card_by_id, delete_card
from .revisions import create_post_revision

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
    'get_knowledge_docs_for_tree',
    'get_all_knowledge_docs',
    'search_knowledge_docs',
    'update_knowledge_doc',
    'reorder_knowledge_doc',
    'delete_knowledge_doc',
    'html_to_markdown',
    'precipitate_post_to_knowledge',
    'get_knowledge_doc_by_source_post_id',
    'get_blog_post_by_source_doc_id',
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


def delete_kb_category(category_id, move_to=None):
    """删除分类：子分类上移，文档迁移到 move_to 或变为未分类。"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT parent_id FROM categories WHERE id = ?', (category_id,))
        row = cursor.fetchone()
        if not row:
            return False
        old_parent = row['parent_id']
        cursor.execute('UPDATE categories SET parent_id = ? WHERE parent_id = ?', (old_parent, category_id))
        if move_to and move_to != category_id:
            cursor.execute('UPDATE posts SET category_id = ? WHERE category_id = ?', (move_to, category_id))
        else:
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
            WHERE category_id = ? AND post_type = 'knowledge' AND deleted_at IS NULL
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
            WHERE posts.id = ? AND posts.post_type = 'knowledge' AND posts.deleted_at IS NULL
        ''', (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_knowledge_docs_by_category(category_id, include_subcategories=False, include_drafts=False,
                                   viewer_id=None, viewer_role=None):
    """获取分类下的知识库文档，并按查看者过滤他人草稿。"""
    if include_subcategories:
        cat_ids = get_descendant_category_ids(category_id)
        placeholders = ','.join('?' for _ in cat_ids)
        where_cat = f'posts.category_id IN ({placeholders})'
        params = cat_ids
    else:
        where_cat = 'posts.category_id = ?'
        params = [category_id]
    visibility_sql = ''
    visibility_params = []
    if viewer_role not in ('admin', 'editor'):
        if not include_drafts:
            visibility_sql += ' AND posts.is_published = 1'
        elif viewer_id is not None:
            visibility_sql += ' AND (posts.is_published = 1 OR posts.author_id = ?)'
            visibility_params.append(viewer_id)
        else:
            visibility_sql += ' AND posts.is_published = 1'
    elif not include_drafts:
        visibility_sql += ' AND posts.is_published = 1'
    with get_db_context() as conn:
        cursor = conn.cursor()
        sql = f'''
            SELECT posts.*, categories.name as category_name
            FROM posts
            LEFT JOIN categories ON posts.category_id = categories.id
            WHERE posts.post_type = 'knowledge' AND posts.deleted_at IS NULL AND {where_cat}
            {visibility_sql}
            ORDER BY posts.sort_order, posts.created_at DESC
        '''
        cursor.execute(sql, params + visibility_params)
        return [dict(row) for row in cursor.fetchall()]


def get_recent_knowledge_docs(limit=10, include_drafts=False, viewer_id=None, viewer_role=None):
    """获取最近的知识库文档，并按查看者过滤他人草稿。"""
    visibility_sql = ''
    visibility_params = []
    if viewer_role not in ('admin', 'editor'):
        if not include_drafts:
            visibility_sql += ' AND posts.is_published = 1'
        elif viewer_id is not None:
            visibility_sql += ' AND (posts.is_published = 1 OR posts.author_id = ?)'
            visibility_params.append(viewer_id)
        else:
            visibility_sql += ' AND posts.is_published = 1'
    elif not include_drafts:
        visibility_sql += ' AND posts.is_published = 1'
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT posts.*, categories.name as category_name
            FROM posts
            LEFT JOIN categories ON posts.category_id = categories.id
            WHERE posts.post_type = 'knowledge' AND posts.deleted_at IS NULL
            {visibility_sql}
            ORDER BY COALESCE(posts.updated_at, posts.created_at) DESC
            LIMIT ?
        ''', visibility_params + [limit])
        return [dict(row) for row in cursor.fetchall()]


def _knowledge_visibility_sql(viewer_id, viewer_role, include_drafts=True):
    if viewer_role in ('admin', 'editor'):
        return '', []
    if not include_drafts:
        return ' AND posts.is_published = 1', []
    if viewer_id is not None:
        return ' AND (posts.is_published = 1 OR posts.author_id = ?)', [viewer_id]
    return ' AND posts.is_published = 1', []


def get_knowledge_docs_for_tree(viewer_id=None, viewer_role=None):
    """按目录分组返回文档，用于侧栏树展示。"""
    visibility_sql, visibility_params = _knowledge_visibility_sql(viewer_id, viewer_role, include_drafts=True)
    with get_db_context() as conn:
        rows = conn.execute(f'''
            SELECT id, title, category_id, is_published, author_id
            FROM posts
            WHERE post_type = 'knowledge' AND deleted_at IS NULL AND category_id IS NOT NULL
            {visibility_sql}
            ORDER BY sort_order, COALESCE(updated_at, created_at) DESC
        ''', visibility_params).fetchall()
    result = {}
    for row in rows:
        result.setdefault(row['category_id'], []).append(dict(row))
    return result


def get_all_knowledge_docs(viewer_id=None, viewer_role=None, scope='all', page=1, per_page=50):
    """全部文档/未分类文档分页列表。"""
    visibility_sql, visibility_params = _knowledge_visibility_sql(viewer_id, viewer_role, include_drafts=True)
    where = ["posts.post_type = 'knowledge'", 'posts.deleted_at IS NULL']
    params = list(visibility_params)
    if scope == 'uncategorized':
        where.append('posts.category_id IS NULL')
    where_clause = ' AND '.join(where) + visibility_sql
    offset = max(0, (page - 1) * per_page)
    with get_db_context() as conn:
        total = conn.execute(f'SELECT COUNT(*) AS cnt FROM posts WHERE {where_clause}', params).fetchone()['cnt']
        rows = conn.execute(f'''
            SELECT posts.*, categories.name AS category_name
            FROM posts LEFT JOIN categories ON posts.category_id = categories.id
            WHERE {where_clause}
            ORDER BY COALESCE(posts.updated_at, posts.created_at) DESC
            LIMIT ? OFFSET ?
        ''', params + [per_page, offset]).fetchall()
    return {
        'posts': [dict(row) for row in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total else 1,
    }


def search_knowledge_docs(query, viewer_id=None, viewer_role=None, page=1, per_page=20,
                          category_id=None, status=None):
    """知识库搜索：权限过滤、目录/状态筛选、分页。"""
    visibility_sql, visibility_params = _knowledge_visibility_sql(viewer_id, viewer_role, include_drafts=True)
    where = ["posts.post_type = 'knowledge'", 'posts.deleted_at IS NULL',
             '(posts.title LIKE ? OR posts.content LIKE ?)']
    like = f'%{query}%'
    params = [like, like] + visibility_params
    if category_id:
        where.append('posts.category_id = ?')
        params.append(category_id)
    if status == 'published':
        where.append('posts.is_published = 1')
    elif status == 'draft':
        where.append('posts.is_published = 0')
    where_clause = ' AND '.join(where) + visibility_sql
    offset = max(0, (page - 1) * per_page)
    with get_db_context() as conn:
        total = conn.execute(f'SELECT COUNT(*) AS cnt FROM posts WHERE {where_clause}', params).fetchone()['cnt']
        rows = conn.execute(f'''
            SELECT posts.*, categories.name AS category_name
            FROM posts LEFT JOIN categories ON posts.category_id = categories.id
            WHERE {where_clause}
            ORDER BY COALESCE(posts.updated_at, posts.created_at) DESC
            LIMIT ? OFFSET ?
        ''', params + [per_page, offset]).fetchall()
    return {
        'posts': [dict(row) for row in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if total else 1,
    }


def update_knowledge_doc(doc_id, title, content, category_id, is_published, tag_names=None, sort_order=None):
    """更新知识库文档"""
    try:
        create_post_revision(doc_id)
    except Exception:
        pass
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE posts SET title = ?, content = ?, category_id = ?, is_published = ?,
                             content_format = 'markdown',
                             sort_order = COALESCE(?, sort_order),
                             updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND post_type = 'knowledge' AND deleted_at IS NULL
        ''', (title, content, category_id, is_published, sort_order, doc_id))
        success = cursor.rowcount > 0
    if success and tag_names is not None:
        set_post_tags(doc_id, tag_names)
    if success:
        _enqueue_doc_embedding(doc_id)
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
        success = cursor.rowcount > 0
    if success:
        _remove_doc_embedding(doc_id)
    return success


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


def get_knowledge_doc_by_source_post_id(post_id):
    """查找由某篇博客沉淀出的知识库文档。"""
    with get_db_context() as conn:
        row = conn.execute('''
            SELECT * FROM posts
            WHERE source_post_id = ? AND post_type = 'knowledge' AND deleted_at IS NULL
            ORDER BY id DESC LIMIT 1
        ''', (post_id,)).fetchone()
        return dict(row) if row else None


def get_blog_post_by_source_doc_id(doc_id):
    """查找由某篇知识库文档转出的博客草稿。"""
    with get_db_context() as conn:
        row = conn.execute('''
            SELECT * FROM posts
            WHERE source_post_id = ? AND post_type = 'blog' AND deleted_at IS NULL
            ORDER BY id DESC LIMIT 1
        ''', (doc_id,)).fetchone()
        return dict(row) if row else None


def precipitate_post_to_knowledge(post_id, category_id, tag_names=None):
    """将博客文章沉淀为知识库文档（HTML→Markdown 转换，按来源幂等更新）。"""
    post = get_post_by_id(post_id)
    if not post:
        return None
    markdown_content = html_to_markdown(post['content'])
    title = post['title']
    if tag_names is None:
        original_tags = get_post_tags(post_id)
        tag_names = [t['name'] for t in original_tags]

    existing = get_knowledge_doc_by_source_post_id(post_id)
    if existing:
        with get_db_context() as conn:
            conn.execute('''
                UPDATE posts SET title = ?, content = ?, content_format = 'markdown',
                    category_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND post_type = 'knowledge'
            ''', (title, markdown_content, category_id, existing['id']))
        set_post_tags(existing['id'], tag_names)
        _enqueue_doc_embedding(existing['id'])
        return existing['id']

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


# ==================== Embedding 钩子（best-effort，绝不阻断写路径） ====================
# 注：create_knowledge_doc 经由 create_post(post_type='knowledge') 落库，
#     create_post 的钩子已按 'doc' 类型入队，此处无需重复。

def _enqueue_doc_embedding(doc_id):
    """保存后异步更新向量"""
    try:
        from tasks.embedding_task import enqueue_embedding
        enqueue_embedding('doc', doc_id)
    except Exception:
        pass

def _remove_doc_embedding(doc_id):
    """删除文档时清理向量"""
    try:
        from tasks.embedding_task import remove_embedding
        remove_embedding('doc', doc_id)
    except Exception:
        pass
