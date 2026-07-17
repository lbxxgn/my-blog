"""
Card Model Functions

知识库卡片 CRUD、合并与时间线，以及卡片标注（annotations）。
"""

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from .db import get_db_connection

__all__ = [
    'create_card',
    'get_card_by_id',
    'get_cards_by_user',
    'update_card_status',
    'update_card',
    'delete_card',
    'get_timeline_items',
    'merge_cards_to_post',
    'ai_merge_cards_to_post',
    'init_cards_table',
    'init_card_annotations_table',
    'create_annotation',
    'get_annotations_by_url',
]


# =============================================================================
# Cards Model Functions
# =============================================================================

def create_card(user_id, title, content, tags=None, status='idea', source='web',
                linked_article_id=None, url=None, source_url=None, **kwargs):
    """
    创建新卡片

    Args:
        user_id (int): 用户ID
        title (str, optional): 卡片标题
        content (str): 卡片内容
        tags (list, optional): 标签列表
        status (str): 状态 (idea/draft/incubating/published)
        source (str): 来源 (web/plugin/voice/mobile)
        linked_article_id (int, optional): 关联的文章ID
        url/source_url: 兼容旧调用，当前仅接收不单独存储

    Returns:
        int: 新创建卡片的ID
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    tags_json = json.dumps(tags) if tags else None

    cursor.execute('''
        INSERT INTO cards (user_id, title, content, tags, status, source, linked_article_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, content, tags_json, status, source, linked_article_id))

    card_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return card_id


def get_card_by_id(card_id):
    """
    通过ID获取卡片

    Args:
        card_id (int): 卡片ID

    Returns:
        dict or None: 卡片数据
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        card = dict(row)
        # Parse JSON tags string to list
        if card.get('tags'):
            try:
                card['tags'] = json.loads(card['tags'])
            except (json.JSONDecodeError, TypeError):
                card['tags'] = []
        else:
            card['tags'] = []
        return card
    return None


def get_cards_by_user(user_id, status=None, limit=None, offset=None):
    """
    获取用户的所有卡片

    Args:
        user_id (int): 用户ID
        status (str, optional): 筛选状态
        limit (int, optional): 限制数量
        offset (int, optional): 偏移量

    Returns:
        list: 卡片列表
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM cards WHERE user_id = ?'
    params = [user_id]

    if status:
        query += ' AND status = ?'
        params.append(status)

    query += ' ORDER BY created_at DESC'

    if limit:
        query += ' LIMIT ?'
        params.append(limit)
        if offset:
            query += ' OFFSET ?'
            params.append(offset)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Parse JSON tags for each card
    cards = []
    for row in rows:
        card = dict(row)
        if card.get('tags'):
            try:
                card['tags'] = json.loads(card['tags'])
            except (json.JSONDecodeError, TypeError):
                card['tags'] = []
        else:
            card['tags'] = []
        cards.append(card)

    return cards


def update_card_status(card_id, status):
    """
    更新卡片状态

    Args:
        card_id (int): 卡片ID
        status (str): 新状态
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE cards SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, card_id))

    conn.commit()
    conn.close()


def update_card(card_id, title=None, content=None, tags=None, status=None):
    """
    更新卡片信息

    Args:
        card_id (int): 卡片ID
        title (str, optional): 新标题
        content (str, optional): 新内容
        tags (list, optional): 新标签
        status (str, optional): 新状态
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if title is not None:
        updates.append('title = ?')
        params.append(title)

    if content is not None:
        updates.append('content = ?')
        params.append(content)

    if tags is not None:
        updates.append('tags = ?')
        params.append(json.dumps(tags))

    if status is not None:
        updates.append('status = ?')
        params.append(status)

    if updates:
        updates.append('updated_at = CURRENT_TIMESTAMP')
        query = f"UPDATE cards SET {', '.join(updates)} WHERE id = ?"
        params.append(card_id)

        cursor.execute(query, params)
        conn.commit()

    conn.close()


def delete_card(card_id):
    """
    删除卡片

    Args:
        card_id (int): 卡片ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM cards WHERE id = ?', (card_id,))
    conn.commit()
    conn.close()


def get_timeline_items(user_id, limit=20, cursor_time=None):
    """
    获取时间线项目（卡片和文章的混合流）

    Args:
        user_id (int): 用户ID
        limit (int): 每页数量
        cursor_time (str, optional): 时间游标

    Returns:
        dict: 包含 items, next_cursor, has_more
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query cards
    cards_query = '''
        SELECT id, title, content, 'card' as type, status, created_at
        FROM cards
        WHERE user_id = ?
    '''
    cards_params = [user_id]

    if cursor_time:
        cards_query += ' AND created_at < ?'
        cards_params.append(cursor_time)

    cards_query += ' ORDER BY created_at DESC LIMIT ?'
    cards_params.append(limit + 1)

    cursor.execute(cards_query, cards_params)
    cards = [dict(row) for row in cursor.fetchall()]

    # Query published posts
    posts_query = '''
        SELECT id, title, content, 'post' as type,
               CASE WHEN is_published = 1 THEN 'published' ELSE 'draft' END as status,
               created_at
        FROM posts
        WHERE author_id = ?
    '''
    posts_params = [user_id]

    if cursor_time:
        posts_query += ' AND created_at < ?'
        posts_params.append(cursor_time)

    posts_query += ' ORDER BY created_at DESC LIMIT ?'
    posts_params.append(limit + 1)

    cursor.execute(posts_query, posts_params)
    posts = [dict(row) for row in cursor.fetchall()]

    # Merge and sort by created_at
    all_items = cards + posts
    all_items.sort(key=lambda x: x['created_at'], reverse=True)

    # Paginate
    items = all_items[:limit]
    has_more = len(all_items) > limit

    next_cursor = None
    if items:
        next_cursor = items[-1]['created_at']

    conn.close()

    return {
        'items': items,
        'next_cursor': next_cursor,
        'has_more': has_more
    }


def merge_cards_to_post(card_ids, user_id, post_id=None):
    """
    合并卡片到文章

    Args:
        card_ids (list): 卡片ID列表
        user_id (int): 用户ID
        post_id (int, optional): 现有文章ID。如果为None则创建新文章

    Returns:
        int: 文章ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all cards
    placeholders = ','.join(['?' for _ in card_ids])
    query = f'SELECT * FROM cards WHERE id IN ({placeholders}) AND user_id = ? ORDER BY created_at DESC'
    cursor.execute(query, card_ids + [user_id])
    cards = [dict(row) for row in cursor.fetchall()]

    if not cards:
        conn.close()
        raise ValueError('No valid cards found')

    # Merge content
    merged_content = ''
    for card in cards:
        if card['title']:
            merged_content += f"## {card['title']}\n\n"
        merged_content += card['content'] + '\n\n---\n\n'

    # Create or update post
    if post_id:
        # Append to existing post
        cursor.execute('SELECT content FROM posts WHERE id = ?', (post_id,))
        result = cursor.fetchone()
        if result:
            existing_content = result['content']
            merged_content = existing_content + '\n\n---\n\n' + merged_content

        cursor.execute('''
            UPDATE posts SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (merged_content, post_id))
    else:
        # Create new post
        # Use first card's title or generate one
        title = cards[0]['title'] if cards[0]['title'] else '未命名文章'

        cursor.execute('''
            INSERT INTO posts (title, content, is_published, author_id)
            VALUES (?, ?, 0, ?)
        ''', (title, merged_content, user_id))
        post_id = cursor.lastrowid

    # Update cards status and link
    for card_id in card_ids:
        cursor.execute('''
            UPDATE cards SET status = 'published', linked_article_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (post_id, card_id))

    conn.commit()
    conn.close()

    return post_id


def ai_merge_cards_to_post(card_ids, user_id, user_config, merge_style='comprehensive'):
    """
    使用AI合并卡片到文章

    Args:
        card_ids (list): 卡片ID列表
        user_id (int): 用户ID
        user_config (dict): 用户AI配置
        merge_style (str): 合并风格 ('comprehensive' 或 'outline')

    Returns:
        dict: 包含 post_id, title, content, outline, tags, tokens_used
    """
    from ai_services.card_merger import AICardMerger

    # Use AI to merge
    ai_result = AICardMerger.merge_cards(
        card_ids=card_ids,
        user_id=user_id,
        user_config=user_config,
        merge_style=merge_style
    )

    # Create post with AI-generated content
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO posts (title, content, is_published, author_id, post_type, content_format)
        VALUES (?, ?, 0, ?, 'knowledge', 'html')
    ''', (ai_result['title'], ai_result['content'], user_id))

    post_id = cursor.lastrowid

    # Update cards status and link
    placeholders = ','.join(['?' for _ in card_ids])
    cursor.execute(f'''
        UPDATE cards SET status = 'incubating', linked_article_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders})
    ''', [post_id] + card_ids)

    conn.commit()
    conn.close()

    ai_result['post_id'] = post_id
    return ai_result


# ==================== 浏览器插件 API 功能 ====================

def init_cards_table():
    """初始化知识库卡片表（已在init_db中创建，此函数为兼容性保留）"""
    # Cards table is already created in init_db()
    # This function exists for backward compatibility with test fixtures
    pass


def init_card_annotations_table():
    """初始化卡片标注表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            card_id INTEGER,
            source_url TEXT NOT NULL,
            annotation_text TEXT,
            xpath TEXT,
            color TEXT DEFAULT 'yellow',
            note TEXT,
            annotation_type TEXT DEFAULT 'highlight',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (card_id) REFERENCES cards(id)
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_annotations_user_url
        ON card_annotations(user_id, source_url)
    ''')

    conn.commit()
    conn.close()


def create_annotation(user_id, source_url, annotation_text, xpath, color, note, annotation_type='highlight', card_id=None):
    """创建标注"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO card_annotations
        (user_id, card_id, source_url, annotation_text, xpath, color, note, annotation_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, card_id, source_url, annotation_text, xpath, color, note, annotation_type))

    annotation_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return annotation_id


def get_annotations_by_url(user_id, source_url):
    """获取指定URL的所有标注"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM card_annotations
        WHERE user_id = ? AND source_url = ?
        ORDER BY created_at DESC
    ''', (user_id, source_url))

    annotations = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return annotations
