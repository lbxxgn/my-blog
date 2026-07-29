"""
Post Model Functions

文章 CRUD、搜索、分页与访问控制。
"""

import sqlite3

from .db import get_db_connection, _safe_replace_post_fts, _safe_delete_post_fts
from .utils import truncate_text

__all__ = [
    'create_post',
    'update_post',
    'delete_post',
    'get_all_posts',
    'get_all_posts_cursor',
    'get_post_by_id',
    'update_post_with_tags',
    'get_posts_by_author',
    'get_post_excerpt',
    'check_post_access',
    'update_post_access',
    'verify_post_password',
    'search_posts',
    'get_adjacent_posts',
]


def create_post(title, content, is_published=False, category_id=None, author_id=None, access_level='public', access_password=None, type='post', post_type='blog'):
    """
    创建新文章

    Args:
        title (str): 文章标题
        content (str): 文章内容（Markdown格式）
        is_published (bool): 是否立即发布。默认为False（草稿）
        category_id (int, optional): 分类ID。默认为None
        author_id (int, optional): 作者ID。默认为None
        access_level (str): 访问级别。默认为'public'
        access_password (str, optional): 访问密码。默认为None
        type (str): 文章类型。默认为'post'
        post_type (str): 内容空间。'blog'（博客）或 'knowledge'（知识库）

    Returns:
        int: 新创建文章的ID

    Note:
        - 自动更新FTS全文搜索索引
        - 触发器已禁用，手动维护索引
        - 包含60秒内重复内容防重保护
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 防重保护：同一作者60秒内发布相同标题+内容的文章，返回已有文章ID
    if author_id is not None:
        cursor.execute(
            """SELECT id FROM posts
               WHERE author_id = ? AND title = ? AND content = ?
                 AND created_at > datetime('now', '-60 seconds')
                ORDER BY created_at DESC LIMIT 1""",
            (author_id, title, content)
        )
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return existing['id']

    cursor.execute(
        'INSERT INTO posts (title, content, is_published, category_id, author_id, access_level, access_password, type, post_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (title, content, is_published, category_id, author_id, access_level, access_password, type, post_type)
    )
    post_id = cursor.lastrowid

    # 手动更新FTS全文搜索索引（触发器已禁用以避免SQL逻辑错误）
    _safe_replace_post_fts(cursor, post_id, title, content)

    conn.commit()
    conn.close()
    return post_id

def update_post(post_id, title, content, is_published, category_id=None, access_level=None, access_password=None, type=None):
    """
    Update an existing post

    Args:
        post_id (int): 文章ID
        title (str): 文章标题
        content (str): 文章内容
        is_published (bool): 是否发布
        category_id (int, optional): 分类ID
        access_level (str, optional): 访问级别
        access_password (str, optional): 访问密码
        type (str, optional): 文章类型
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build update SQL dynamically based on which optional fields are provided
    if access_level is not None and type is not None:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, access_level = ?, access_password = ?, type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, access_level, access_password, type, post_id)
        )
    elif access_level is not None:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, access_level = ?, access_password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, access_level, access_password, post_id)
        )
    elif type is not None:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, type, post_id)
        )
    else:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, post_id)
        )

    # Manually update FTS (triggers are disabled)
    _safe_replace_post_fts(cursor, post_id, title, content)

    conn.commit()
    conn.close()
    return True

def delete_post(post_id):
    """Delete a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))

    # Manually delete from FTS (triggers are disabled)
    _safe_delete_post_fts(cursor, post_id)

    conn.commit()
    conn.close()

def get_all_posts(include_drafts=False, page=1, per_page=20, category_id=None, type=None, post_type='blog'):
    """Get all posts with pagination, optionally including drafts and filtering by category and type"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    where_conditions = []
    params = []

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    if category_id == 'none':
        where_conditions.append('posts.category_id IS NULL')
    elif category_id is not None:
        where_conditions.append('posts.category_id = ?')
        params.append(category_id)

    if type is not None:
        where_conditions.append('posts.type = ?')
        params.append(type)

    if post_type is not None:
        where_conditions.append('posts.post_type = ?')
        params.append(post_type)

    # 构建安全的WHERE子句 - 仅使用硬编码的条件
    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

    # 验证where_clause只包含安全的条件（防止代码注入）
    allowed_patterns = ['posts.is_published = ', 'posts.category_id IS NULL', 'posts.category_id = ', 'posts.type = ', 'posts.post_type = ', '1=1']
    if not any(allowed in where_clause for allowed in allowed_patterns):
        raise ValueError(f"Invalid WHERE clause: {where_clause}")

    # Count total posts
    count_query = '''
        SELECT COUNT(*) as count
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE ''' + where_clause
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get posts for current page
    query = '''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id,
               users.id as author_id,
               users.username as author_username,
               users.display_name as author_display_name
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        LEFT JOIN users ON posts.author_id = users.id
        WHERE ''' + where_clause + '''
        ORDER BY posts.created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(query, params + [per_page, offset])

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        'posts': posts,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 1
    }

def get_all_posts_cursor(cursor_time=None, per_page=20, include_drafts=False, category_id=None, post_type='blog'):
    """
    Get all posts using cursor-based pagination for better performance

    Args:
        cursor_time: Time-based cursor (created_at of last post in previous page)
        per_page: Number of posts per page
        include_drafts: Whether to include draft posts
        category_id: Filter by category ID
        post_type: Filter by content space ('blog'/'knowledge'/None for all)

    Returns:
        dict with posts, next_cursor, has_more
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    where_conditions = []
    params = []

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    if category_id == 'none':
        where_conditions.append('posts.category_id IS NULL')
    elif category_id is not None:
        where_conditions.append('posts.category_id = ?')
        params.append(category_id)

    if post_type is not None:
        where_conditions.append('posts.post_type = ?')
        params.append(post_type)

    if cursor_time:
        where_conditions.append('posts.created_at < ?')
        params.append(cursor_time)

    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

    # Get posts
    query = '''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id,
               users.id as author_id,
               users.username as author_username,
               users.display_name as author_display_name
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        LEFT JOIN users ON posts.author_id = users.id
        WHERE ''' + where_clause + '''
        ORDER BY posts.created_at DESC
        LIMIT ?
    '''
    params.append(per_page + 1)  # Fetch one extra to check if there's more

    cursor.execute(query, params)
    rows = cursor.fetchall()
    posts = [dict(row) for row in rows[:per_page]]  # Only return requested amount
    has_more = len(rows) > per_page

    # Get next cursor (created_at of last post)
    next_cursor = None
    if posts:
        next_cursor = posts[-1]['created_at']

    conn.close()

    return {
        'posts': posts,
        'next_cursor': next_cursor,
        'has_more': has_more,
        'per_page': per_page
    }

def get_post_by_id(post_id):
    """Get a single post by ID with category and author information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id,
               users.id as author_id,
               users.username as author_username,
               users.display_name as author_display_name,
               users.avatar_url as author_avatar_url,
               users.bio as author_bio
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        LEFT JOIN users ON posts.author_id = users.id
        WHERE posts.id = ?
    ''', (post_id,))
    post = cursor.fetchone()
    conn.close()
    return dict(post) if post else None

def get_adjacent_posts(post_id):
    """
    获取相邻的上一篇/下一篇文章（仅已发布的公开博客文章，按 id 排序）

    Returns:
        dict: {'prev': {'id', 'title'} | None, 'next': {'id', 'title'} | None}
        prev 为较早一篇（id 更小），next 为较新一篇（id 更大）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    base_where = "is_published = 1 AND post_type = 'blog' AND access_level = 'public'"
    cursor.execute(f'''
        SELECT id, title FROM posts
        WHERE id < ? AND {base_where}
        ORDER BY id DESC LIMIT 1
    ''', (post_id,))
    prev_post = cursor.fetchone()
    cursor.execute(f'''
        SELECT id, title FROM posts
        WHERE id > ? AND {base_where}
        ORDER BY id ASC LIMIT 1
    ''', (post_id,))
    next_post = cursor.fetchone()
    conn.close()
    return {
        'prev': dict(prev_post) if prev_post else None,
        'next': dict(next_post) if next_post else None,
    }

def search_posts(query, include_drafts=False, page=1, per_page=20, post_type_filter='all'):
    """
    使用LIKE进行文章搜索（对中文支持更好）

    Args:
        query (str): 搜索关键词
        include_drafts (bool): 是否包含草稿。默认为False
        page (int): 页码。默认为1
        per_page (int): 每页数量。默认为20
        post_type_filter (str): 内容来源过滤。'all'（全部）/ 'blog'（博客）/ 'knowledge'（知识库）

    Returns:
        dict: 包含以下键：
            - 'posts': 文章列表（含 post_type 字段，用于标注来源）
            - 'total': 总结果数
            - 'page': 当前页码
            - 'per_page': 每页数量
            - 'total_pages': 总页数

    Note:
        - 使用LIKE而不是MATCH以获得更好的中文分词支持
        - 搜索范围包括标题和内容
        - 返回按创建时间倒序排列
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建LIKE搜索模式（对中文支持更好）
    search_pattern = f'%{query}%'
    where_conditions = ['(posts.title LIKE ? OR posts.content LIKE ?)']
    params = [search_pattern, search_pattern]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    # 内容来源过滤
    if post_type_filter in ('blog', 'knowledge'):
        where_conditions.append('posts.post_type = ?')
        params.append(post_type_filter)

    where_clause = ' AND '.join(where_conditions)

    # 计算总结果数
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # 计算偏移量
    offset = (page - 1) * per_page

    # 获取当前页结果
    search_query = f'''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
        ORDER BY posts.created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(search_query, params + [per_page, offset])

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        'posts': posts,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 1
    }

def update_post_with_tags(post_id, title, content, is_published, category_id=None, tag_names=None):
    """Update post and its tags in a single transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update post
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, post_id)
        )

        # Manually update FTS (triggers are disabled)
        cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))
        cursor.execute('INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
                      (post_id, title, content))

        # Delete existing tag associations
        cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))

        # Add new tag associations if provided
        if tag_names:
            for tag_name in tag_names:
                if not tag_name.strip():
                    continue

                name = tag_name.strip()

                # Check if tag exists
                cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
                result = cursor.fetchone()

                if result:
                    tag_id = result[0]
                else:
                    # Create tag inline
                    try:
                        cursor.execute('INSERT INTO tags (name) VALUES (?)', (name,))
                        tag_id = cursor.lastrowid
                    except sqlite3.IntegrityError:
                        # Tag was created, get it again
                        cursor.execute('SELECT id FROM tags WHERE name = ?', (name,))
                        result = cursor.fetchone()
                        if result:
                            tag_id = result[0]
                        else:
                            tag_id = None

                if tag_id:
                    cursor.execute(
                        'INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                        (post_id, tag_id)
                    )

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_posts_by_author(author_id, include_drafts=False, page=1, per_page=20):
    """获取指定作者的文章"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建WHERE条件
    where_conditions = ['posts.author_id = ?']
    params = [author_id]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    where_clause = ' AND '.join(where_conditions)

    # 统计总数
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # 分页查询
    offset = (page - 1) * per_page
    query = f'''
        SELECT posts.*,
               categories.name as category_name,
               categories.id as category_id
        FROM posts
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
        ORDER BY posts.created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(query, params + [per_page, offset])

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        'posts': posts,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 1
    }

def get_post_excerpt(post_content, max_length=200):
    """
    获取文章摘要（清理HTML并截断）

    Args:
        post_content: 文章内容
        max_length: 摘要最大长度

    Returns:
        str: 文章摘要
    """
    return truncate_text(post_content, max_length)

def check_post_access(post_id, user_id=None, session_passwords=None):
    """
    检查用户是否有权限访问文章

    Args:
        post_id: 文章ID
        user_id: 用户ID（可选）
        session_passwords: session中已解锁的密码列表（可选）

    Returns:
        dict: {'allowed': bool, 'reason': str}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT access_level, access_password, author_id
        FROM posts
        WHERE id = ?
    ''', (post_id,))

    post = cursor.fetchone()
    conn.close()

    if not post:
        return {'allowed': False, 'reason': '文章不存在'}

    access_level = post['access_level'] or 'public'
    access_password = post['access_password']
    author_id = post['author_id']

    # 公开文章
    if access_level == 'public':
        return {'allowed': True, 'reason': 'public'}

    # 私密文章：只有作者和管理员可见
    if access_level == 'private':
        if user_id:
            # 检查是否是作者或管理员
            cursor = get_db_connection().cursor()
            cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()

            if user and (user_id == author_id or user['role'] == 'admin'):
                cursor.connection.close()
                return {'allowed': True, 'reason': 'author_or_admin'}

            cursor.connection.close()

        return {'allowed': False, 'reason': 'private'}

    # 登录用户可见
    if access_level == 'login':
        if user_id:
            return {'allowed': True, 'reason': 'logged_in'}
        return {'allowed': False, 'reason': 'login_required'}

    # 密码保护
    if access_level == 'password':
        # 只有作者可以直接访问（管理员也需要输入密码）
        if user_id and user_id == author_id:
            cursor = get_db_connection().cursor()
            cursor.connection.close()
            return {'allowed': True, 'reason': 'author'}

        # 检查session中是否有正确的密码
        if session_passwords and str(post_id) in session_passwords:
            return {'allowed': True, 'reason': 'password_verified'}

        return {'allowed': False, 'reason': 'password_required', 'has_password': bool(access_password)}

    return {'allowed': True, 'reason': 'unknown'}

def update_post_access(post_id, access_level, access_password=None):
    """
    更新文章访问权限

    Args:
        post_id: 文章ID
        access_level: 访问级别
        access_password: 密码（可选）

    Returns:
        bool: 是否成功
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE posts
            SET access_level = ?, access_password = ?
            WHERE id = ?
        ''', (access_level, access_password, post_id))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating post access: {e}")
        return False
    finally:
        conn.close()

def verify_post_password(post_id, password):
    """
    验证文章访问密码

    Args:
        post_id: 文章ID
        password: 输入的密码

    Returns:
        bool: 密码是否正确
    """
    import logging
    logger = logging.getLogger(__name__)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT access_password FROM posts
        WHERE id = ? AND access_level = 'password'
    ''', (post_id,))

    post = cursor.fetchone()
    conn.close()

    if not post:
        logger.warning(f"[Password Verify] Post {post_id} not found or not password protected")
        return False

    if not post['access_password']:
        logger.warning(f"[Password Verify] Post {post_id} is password protected but has no password set")
        return False

    logger.info(f"[Password Verify] Post {post_id} checking password")
    result = password == post['access_password']
    logger.info(f"[Password Verify] Password match: {result}")

    return result
