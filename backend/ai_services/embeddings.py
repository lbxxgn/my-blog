"""
Embedding 服务 - 语义搜索向量生成

通过 OpenAI 兼容的 embeddings 接口（硅基流动/阿里百炼/OpenAI 等）
为文章、卡片、知识库文档生成向量。配置按用户存储在 users 表
（ai_embedding_* 列，见迁移 009），与对话类 AI 配置相互独立。
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://api.siliconflow.cn/v1'
DEFAULT_MODEL = 'BAAI/bge-m3'

# 单次请求的输入截断（字符），避免超长内容打爆 token 上限
MAX_INPUT_CHARS = 8000


def get_embedding_config(user_id):
    """
    获取用户的 Embedding 配置

    Args:
        user_id: 用户ID

    Returns:
        dict: {'enabled', 'base_url', 'api_key', 'model'}；
              用户不存在或未运行迁移 009 时返回 None
    """
    if not user_id:
        return None

    # 延迟导入，避免 ai_services <-> models 循环依赖
    from models import get_db_connection

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT ai_embedding_enabled, ai_embedding_base_url,
                       ai_embedding_api_key, ai_embedding_model
                FROM users
                WHERE id = ?
            ''', (user_id,))
        except sqlite3.OperationalError as e:
            # 迁移 009 尚未执行：视为未配置
            logger.warning(f"Embedding config columns missing, run migrations: {e}")
            return None
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return {
        'enabled': bool(row['ai_embedding_enabled']),
        'base_url': row['ai_embedding_base_url'] or DEFAULT_BASE_URL,
        'api_key': row['ai_embedding_api_key'],
        'model': row['ai_embedding_model'] or DEFAULT_MODEL,
    }


def update_embedding_config(user_id, data):
    """
    更新用户的 Embedding 配置

    Args:
        user_id: 用户ID
        data: 可包含 ai_embedding_enabled (bool) /
              ai_embedding_base_url / ai_embedding_api_key / ai_embedding_model (str)

    Returns:
        bool: 是否有字段被更新
    """
    from models import get_db_context

    updates = []
    params = []

    if 'ai_embedding_enabled' in data:
        updates.append('ai_embedding_enabled = ?')
        params.append(1 if data['ai_embedding_enabled'] else 0)

    for key in ('ai_embedding_base_url', 'ai_embedding_api_key', 'ai_embedding_model'):
        if key in data:
            updates.append(f'{key} = ?')
            value = (data[key] or '').strip()
            params.append(value or None)

    if not updates:
        return False

    with get_db_context() as conn:
        cursor = conn.cursor()
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        success = cursor.rowcount > 0

    # 启用状态变化后，立即失效任务队列的“是否有用户启用”缓存
    try:
        from tasks.embedding_task import reset_enabled_cache
        reset_enabled_cache()
    except Exception:
        pass

    return success


def create_embedding_client(config):
    """
    按配置创建 OpenAI 兼容客户端

    Args:
        config: get_embedding_config 返回的 dict（或同结构字典）

    Returns:
        openai.OpenAI 客户端实例
    """
    from openai import OpenAI

    api_key = (config or {}).get('api_key')
    if not api_key:
        raise ValueError('Embedding API 密钥未配置')

    return OpenAI(
        api_key=api_key,
        base_url=(config or {}).get('base_url') or DEFAULT_BASE_URL,
        timeout=30.0,
        max_retries=2,
    )


def embed_text(text, config):
    """
    生成文本向量

    Args:
        text: 输入文本
        config: Embedding 配置 dict

    Returns:
        list[float]: 向量
    """
    client = create_embedding_client(config)
    model = (config or {}).get('model') or DEFAULT_MODEL
    response = client.embeddings.create(
        model=model,
        input=(text or '')[:MAX_INPUT_CHARS],
    )
    return list(response.data[0].embedding)


def test_embedding_connection(config):
    """
    连通性测试（供设置页“测试连接”按钮）

    Returns:
        dict: {'success': bool, 'message': str}
    """
    if not config or not config.get('api_key'):
        return {'success': False, 'message': '未配置 Embedding API 密钥'}

    try:
        vector = embed_text('连接测试', config)
        model = config.get('model') or DEFAULT_MODEL
        return {
            'success': True,
            'message': f'连接成功（{model}，向量维度 {len(vector)}）',
        }
    except Exception as e:
        logger.error(f"Embedding connection test failed: {e}")
        return {'success': False, 'message': f'连接失败: {e}'}
