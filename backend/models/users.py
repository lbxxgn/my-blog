"""
User Model Functions

用户、Passkey、AI 配置/历史与 API Key 管理。
"""

import sqlite3
import logging
import json

from .db import get_db_connection, get_db_context

# Setup logger
logger = logging.getLogger(__name__)

__all__ = [
    'get_user_by_username',
    'get_user_by_id',
    'get_user_passkeys',
    'get_passkey_by_credential_id',
    'update_user_password',
    'get_all_users',
    'create_user',
    'create_user_passkey',
    'update_user_passkey_usage',
    'delete_user_passkey',
    'update_user',
    'delete_user',
    'get_user_ai_config',
    'update_user_ai_config',
    'save_ai_tag_history',
    'get_ai_tag_history',
    'get_ai_usage_stats',
    'generate_api_key',
    'validate_api_key',
    'init_api_keys_table',
]


def get_user_by_username(username):
    """Get a user by username with error handling"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_user_by_username({username}): {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_user_by_username({username}): {e}")
        return None

def update_user_password(user_id, new_password_hash):
    """Update user password - refactored to use context manager"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
        return cursor.rowcount > 0


# ==================== 用户管理函数 ====================

def get_user_by_id(user_id):
    """根据ID获取用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_passkeys(user_id):
    """获取用户已绑定的 Passkey 列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, credential_id, sign_count, device_name, transports,
               credential_device_type, backup_eligible, backup_state,
               created_at, last_used_at
        FROM user_passkeys
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    rows = []
    for row in cursor.fetchall():
        item = dict(row)
        item['transports'] = json.loads(item['transports']) if item.get('transports') else []
        rows.append(item)
    conn.close()
    return rows


def get_passkey_by_credential_id(credential_id):
    """根据 credential_id 获取 Passkey"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT *
        FROM user_passkeys
        WHERE credential_id = ?
    ''', (credential_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    item['transports'] = json.loads(item['transports']) if item.get('transports') else []
    return item


def create_user_passkey(user_id, credential_id, public_key, sign_count=0,
                        device_name=None, transports=None, credential_device_type=None,
                        backup_eligible=False, backup_state=False):
    """为用户绑定新的 Passkey"""
    transports_json = json.dumps(transports or [], ensure_ascii=False)
    with get_db_context() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO user_passkeys (
                    user_id, credential_id, public_key, sign_count,
                    device_name, transports, credential_device_type,
                    backup_eligible, backup_state, last_used_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_id,
                credential_id,
                public_key,
                sign_count,
                device_name,
                transports_json,
                credential_device_type,
                int(bool(backup_eligible)),
                int(bool(backup_state)),
            ))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_user_passkey_usage(passkey_id, sign_count,
                              credential_device_type=None, backup_state=None):
    """更新 Passkey 的使用状态"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_passkeys
            SET sign_count = ?,
                credential_device_type = COALESCE(?, credential_device_type),
                backup_state = COALESCE(?, backup_state),
                last_used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            sign_count,
            credential_device_type,
            int(bool(backup_state)) if backup_state is not None else None,
            passkey_id,
        ))
        return cursor.rowcount > 0


def delete_user_passkey(passkey_id, user_id):
    """删除用户的 Passkey"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_passkeys WHERE id = ? AND user_id = ?', (passkey_id, user_id))
        return cursor.rowcount > 0


def get_all_users():
    """获取所有用户列表（包含文章数统计）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT users.*,
               (SELECT COUNT(*) FROM posts WHERE posts.author_id = users.id) as post_count
        FROM users
        ORDER BY users.created_at DESC
    ''')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def create_user(username, password_hash, role='author', display_name=None, bio=None):
    """创建新用户（扩展版，支持角色和显示名称）"""
    with get_db_context() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, display_name, bio)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, role, display_name, bio))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_user(user_id, username=None, display_name=None, bio=None, role=None, is_active=None):
    """更新用户信息"""
    with get_db_context() as conn:
        cursor = conn.cursor()

        updates = []
        params = []

        if username is not None:
            updates.append('username = ?')
            params.append(username)
        if display_name is not None:
            updates.append('display_name = ?')
            params.append(display_name)
        if bio is not None:
            updates.append('bio = ?')
            params.append(bio)
        if role is not None:
            updates.append('role = ?')
            params.append(role)
        if is_active is not None:
            updates.append('is_active = ?')
            params.append(is_active)

        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(user_id)

            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            return cursor.rowcount > 0
        return False


def delete_user(user_id):
    """删除用户（将其文章设为无作者）

    Returns:
        bool: 删除成功返回True，否则返回False
    """
    try:
        with get_db_context() as conn:
            cursor = conn.cursor()
            # 先将该用户的文章设为无作者
            cursor.execute('UPDATE posts SET author_id = NULL WHERE author_id = ?', (user_id,))
            # 删除用户
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            # 检查是否删除了行
            if cursor.rowcount > 0:
                return True
            return False
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False


# ==================== AI功能函数 ====================

def get_user_ai_config(user_id):
    """
    获取用户的AI配置

    Args:
        user_id: 用户ID

    Returns:
        dict: 包含AI配置的字典，如果用户不存在返回None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            ai_tag_generation_enabled,
            ai_provider,
            ai_api_key,
            ai_model
        FROM users
        WHERE id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'ai_tag_generation_enabled': bool(row['ai_tag_generation_enabled']) if row['ai_tag_generation_enabled'] is not None else True,
            'ai_provider': row['ai_provider'] or 'openai',
            'ai_api_key': row['ai_api_key'],
            'ai_model': row['ai_model'] or 'gpt-3.5-turbo'
        }
    return None


def update_user_ai_config(user_id, ai_config):
    """
    更新用户的AI配置

    Args:
        user_id: 用户ID
        ai_config: AI配置字典，包含:
            - ai_tag_generation_enabled: bool (optional)
            - ai_provider: str (optional)
            - ai_api_key: str (optional)
            - ai_model: str (optional)

    Returns:
        bool: 更新是否成功
    """
    import logging
    logger = logging.getLogger(__name__)

    with get_db_context() as conn:
        cursor = conn.cursor()

        updates = []
        params = []

        if 'ai_tag_generation_enabled' in ai_config:
            updates.append('ai_tag_generation_enabled = ?')
            params.append(1 if ai_config['ai_tag_generation_enabled'] else 0)
            logger.info(f"Update AI config: ai_tag_generation_enabled = {ai_config['ai_tag_generation_enabled']}")

        if 'ai_provider' in ai_config:
            updates.append('ai_provider = ?')
            params.append(ai_config['ai_provider'])
            logger.info(f"Update AI config: ai_provider = {ai_config['ai_provider']}")

        if 'ai_api_key' in ai_config:
            updates.append('ai_api_key = ?')
            params.append(ai_config['ai_api_key'])
            logger.info(f"Update AI config: ai_api_key = ***{ai_config['ai_api_key'][-4:] if ai_config['ai_api_key'] else '(empty)'}")

        if 'ai_model' in ai_config:
            updates.append('ai_model = ?')
            params.append(ai_config['ai_model'])
            logger.info(f"Update AI config: ai_model = {ai_config['ai_model']}")

        if updates:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            logger.info(f"Executing query: {query} with params count: {len(params)}")
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            logger.info(f"Update affected {affected_rows} rows")
            return affected_rows > 0

        logger.warning("No updates to apply")
        return False


def save_ai_tag_history(post_id=None, user_id=None, prompt=None, generated_tags=None,
                        model_used=None, tokens_used=None, cost=None, currency='USD',
                        action=None, provider=None, input_tokens=None, output_tokens=None,
                        result_preview=None, **kwargs):
    """
    保存AI功能使用历史记录（通用函数）

    支持两种调用格式：
    1. 旧格式（标签生成）：save_ai_tag_history(post_id, user_id, prompt, generated_tags, model_used, tokens_used, cost, currency)
    2. 新格式（所有AI功能）：save_ai_tag_history(user_id=..., post_id=..., action=..., provider=..., model=..., ...)

    Args:
        post_id: 文章ID (可选)
        user_id: 用户ID
        prompt: 提示词或操作类型
        generated_tags: 生成的结果（标签/摘要/推荐等）
        model_used: 使用的模型
        tokens_used: 使用的token总数
        cost: 成本
        currency: 货币单位 (USD/CNY)
        action: 操作类型 (generate_tags, generate_summary, recommend_posts, continue_writing)
        provider: AI提供商 (openai, volcengine, dashscope)
        input_tokens: 输入token数
        output_tokens: 输出token数
        result_preview: 结果预览
        **kwargs: 其他参数（兼容性）

    Returns:
        int: 历史记录ID
    """
    import json

    # 处理新格式的参数
    if action is not None:
        # 新格式：将数据转换为适合存储的格式
        prompt = action  # 使用action作为prompt

        # 构建完整的结果对象
        result_data = {
            'action': action,
            'provider': provider,
            'model': model_used or kwargs.get('model'),
        }

        # 根据action添加特定字段
        if action == 'generate_tags':
            result_data['tags'] = result_preview or generated_tags
        elif action == 'generate_summary':
            result_data['summary'] = result_preview
        elif action == 'recommend_posts':
            result_data['recommendations_count'] = kwargs.get('recommendations_count', 0)
        elif action == 'continue_writing':
            result_data['continuation_length'] = kwargs.get('continuation_length', 0)
            result_data['continuation_preview'] = result_preview[:200] if result_preview else ''

        # 添加token信息
        if input_tokens is not None or output_tokens is not None:
            result_data['input_tokens'] = input_tokens
            result_data['output_tokens'] = output_tokens
            result_data['total_tokens'] = tokens_used

        generated_tags = json.dumps(result_data, ensure_ascii=False)

        # 组合provider和model
        if provider and model_used:
            model_used = f"{provider}:{model_used}"
    else:
        # 旧格式：直接使用生成的标签
        if generated_tags is not None and not isinstance(generated_tags, str):
            generated_tags = json.dumps(generated_tags, ensure_ascii=False)

    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_tag_history (post_id, user_id, prompt, generated_tags, model_used, tokens_used, cost, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_id,
            user_id,
            prompt,
            generated_tags,
            model_used,
            tokens_used,
            cost,
            currency
        ))
        return cursor.lastrowid


def get_ai_tag_history(user_id=None, post_id=None, limit=50):
    """
    获取AI标签生成历史记录

    Args:
        user_id: 用户ID (可选，用于过滤)
        post_id: 文章ID (可选，用于过滤)
        limit: 返回记录数限制

    Returns:
        list: 历史记录列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建WHERE条件
    where_conditions = []
    params = []

    if user_id:
        where_conditions.append('user_id = ?')
        params.append(user_id)

    if post_id:
        where_conditions.append('post_id = ?')
        params.append(post_id)

    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

    query = f'''
        SELECT ai_tag_history.*,
               posts.title as post_title,
               users.username as user_username
        FROM ai_tag_history
        LEFT JOIN posts ON ai_tag_history.post_id = posts.id
        LEFT JOIN users ON ai_tag_history.user_id = users.id
        WHERE {where_clause}
        ORDER BY ai_tag_history.created_at DESC
        LIMIT ?
    '''
    params.append(limit)
    cursor.execute(query, params)

    history = []
    for row in cursor.fetchall():
        record = dict(row)
        # 保留JSON字符串格式，由路由层负责解析
        history.append(record)

    conn.close()
    return history


def get_ai_usage_stats(user_id=None):
    """
    获取AI使用统计

    Args:
        user_id: 用户ID (可选)

    Returns:
        dict: 统计信息
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute('''
            SELECT
                COUNT(*) as total_generations,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                AVG(tokens_used) as avg_tokens,
                MAX(created_at) as last_used
            FROM ai_tag_history
            WHERE user_id = ?
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT
                COUNT(*) as total_generations,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                AVG(tokens_used) as avg_tokens,
                MAX(created_at) as last_used
            FROM ai_tag_history
        ''')

    stats = dict(cursor.fetchone())

    # 获取最近使用的货币单位
    if user_id:
        cursor.execute('''
            SELECT currency FROM ai_tag_history
            WHERE user_id = ? AND currency IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id,))
    else:
        cursor.execute('''
            SELECT currency FROM ai_tag_history
            WHERE currency IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
        ''')

    currency_row = cursor.fetchone()
    stats['currency'] = currency_row['currency'] if currency_row else 'USD'

    conn.close()

    # 处理NULL值
    stats['total_tokens'] = stats['total_tokens'] or 0
    stats['total_cost'] = stats['total_cost'] or 0.0
    stats['avg_tokens'] = stats['avg_tokens'] or 0

    return stats


# ==================== 浏览器插件 API 功能 ====================

def init_api_keys_table():
    """初始化API密钥表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT NOT NULL UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_api_keys_user
        ON api_keys(user_id)
    ''')

    conn.commit()
    conn.close()


def generate_api_key(user_id):
    """生成API密钥。数据库只存 SHA-256 哈希，明文密钥仅此返回值可见一次。"""
    import secrets
    api_key = secrets.token_urlsafe(32)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO api_keys (user_id, api_key, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, _hash_api_key(api_key)))

    conn.commit()
    conn.close()

    return api_key


def _hash_api_key(api_key):
    """计算 API 密钥的 SHA-256 哈希（用于安全存储）"""
    import hashlib
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def validate_api_key(api_key):
    """验证API密钥并返回user_id。兼容旧的明文存储，命中后自动升级为哈希。"""
    if not api_key:
        return None

    import hmac

    conn = get_db_connection()
    cursor = conn.cursor()

    # 新格式：按哈希查找
    cursor.execute('''
        SELECT user_id FROM api_keys
        WHERE api_key = ? AND is_active = 1
    ''', (_hash_api_key(api_key),))

    result = cursor.fetchone()
    if result:
        user_id = result['user_id']
        conn.close()
        return user_id

    # 兼容旧格式：明文比对（恒定时间），命中后升级为哈希存储
    cursor.execute('SELECT id, user_id, api_key FROM api_keys WHERE is_active = 1')
    for row in cursor.fetchall():
        stored = row['api_key'] or ''
        # 跳过已是哈希的记录（64位hex），只处理明文遗留
        if len(stored) == 64:
            continue
        if hmac.compare_digest(stored, api_key):
            cursor.execute(
                'UPDATE api_keys SET api_key = ? WHERE id = ?',
                (_hash_api_key(api_key), row['id'])
            )
            conn.commit()
            user_id = row['user_id']
            conn.close()
            return user_id

    conn.close()
    return None
