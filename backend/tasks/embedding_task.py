"""
Embedding 后台任务

实体（文章/卡片/知识库文档）保存后异步生成或更新向量：
加载实体 -> 按归属人取 Embedding 配置 -> 未启用/未配置则跳过 ->
内容未变（content_hash 一致且模型一致）则跳过 -> 调 API -> upsert。

循环导入规避：models 的 CRUD 钩子会调用本模块，因此本模块对
models / ai_services 的导入全部放在函数内 lazy import。
"""

import hashlib
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# 正文截断长度：标题 + 正文前 N 字符参与向量化
MAX_CONTENT_CHARS = 2000

# “是否有用户启用 Embedding”的轻量缓存 TTL（秒）
_ENABLED_CACHE_TTL = 60.0


class EmbeddingTaskQueue:
    """线程安全的 Embedding 任务队列（单例）"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.executor = ThreadPoolExecutor(
                    max_workers=2, thread_name_prefix='embedding'
                )
            return cls._instance

    def submit(self, source_type, source_id):
        """提交任务，返回 Future"""
        return self.executor.submit(process_embedding, source_type, source_id)


# 全局实例
embedding_queue = EmbeddingTaskQueue()

_enabled_cache = {'value': False, 'expires_at': 0.0}


def reset_enabled_cache():
    """清空“是否有用户启用 Embedding”缓存（配置变更/测试时使用）"""
    _enabled_cache['value'] = False
    _enabled_cache['expires_at'] = 0.0


def _any_embedding_enabled():
    """快速判断是否存在启用 Embedding 的用户（带 TTL 缓存，避免每次保存都查库）"""
    now = time.monotonic()
    if now < _enabled_cache['expires_at']:
        return _enabled_cache['value']

    value = False
    try:
        from models import get_db_connection
        conn = get_db_connection()
        try:
            row = conn.execute(
                'SELECT COUNT(*) AS c FROM users WHERE ai_embedding_enabled = 1'
            ).fetchone()
            value = bool(row and row['c'] > 0)
        finally:
            conn.close()
    except Exception as e:
        # 迁移 009 未执行等情况：视为全局未启用
        logger.debug(f"Embedding enabled probe failed, treating as disabled: {e}")

    _enabled_cache['value'] = value
    _enabled_cache['expires_at'] = now + _ENABLED_CACHE_TTL
    return value


def enqueue_embedding(source_type, source_id):
    """
    入队生成/更新向量（对外接口，绝不抛异常）

    Returns:
        Future | None: 已入队返回 Future（测试可等待）；
                       全局未启用或参数非法时快速返回 None
    """
    try:
        if source_type not in ('post', 'card', 'doc') or not source_id:
            return None
        if not _any_embedding_enabled():
            return None
        return embedding_queue.submit(source_type, source_id)
    except Exception as e:
        logger.warning(f"enqueue_embedding({source_type}, {source_id}) failed: {e}")
        return None


def remove_embedding(source_type, source_id):
    """同步删除向量记录（实体删除时调用，绝不抛异常）"""
    try:
        from models.embeddings import delete_embedding
        delete_embedding(source_type, source_id)
    except Exception as e:
        logger.warning(f"remove_embedding({source_type}, {source_id}) failed: {e}")


def _load_entity(source_type, source_id):
    """
    加载实体，返回 {'title', 'content', 'owner_id', 'source_type'}。

    source_type 为规范类型：post/doc 都来自 posts 表，
    post_type='knowledge' 的归为 'doc'（与入队时的类型可能不一致，
    由调用方负责清理旧类型下的残留向量）。
    """
    from models import get_db_connection

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if source_type in ('post', 'doc'):
            cursor.execute(
                'SELECT id, title, content, author_id, post_type FROM posts WHERE id = ?',
                (source_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'title': row['title'],
                'content': row['content'],
                'owner_id': row['author_id'],
                'source_type': 'doc' if row['post_type'] == 'knowledge' else 'post',
            }
        if source_type == 'card':
            cursor.execute(
                'SELECT id, title, content, user_id FROM cards WHERE id = ?',
                (source_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'title': row['title'],
                'content': row['content'],
                'owner_id': row['user_id'],
                'source_type': 'card',
            }
        return None
    finally:
        conn.close()


def _build_text(title, content):
    return f"{title or ''}\n{(content or '')[:MAX_CONTENT_CHARS]}".strip()


def process_embedding(source_type, source_id):
    """
    Worker：为单个实体生成/更新向量

    Returns:
        bool: 实际写入向量返回 True；各种跳过/失败返回 False
    """
    try:
        from ai_services.embeddings import embed_text, get_embedding_config
        from models.embeddings import get_embedding, upsert_embedding

        entity = _load_entity(source_type, source_id)
        if not entity:
            # 实体已删除：清理残留向量
            remove_embedding(source_type, source_id)
            return False

        canonical_type = entity['source_type']
        if canonical_type != source_type:
            # 入队类型与实际类型不一致（如 post_type 变化）：清掉旧类型记录
            remove_embedding(source_type, source_id)

        config = get_embedding_config(entity['owner_id'])
        if not config or not config.get('enabled') or not config.get('api_key'):
            return False

        text = _build_text(entity['title'], entity['content'])
        content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

        existing = get_embedding(canonical_type, source_id)
        if (existing
                and existing.get('content_hash') == content_hash
                and existing.get('model') == config['model']):
            return False

        vector = embed_text(text, config)
        upsert_embedding(canonical_type, source_id, vector,
                         model=config['model'], content_hash=content_hash)
        logger.info(f"Embedding updated: {canonical_type}/{source_id} ({config['model']})")
        return True

    except Exception as e:
        logger.warning(f"process_embedding({source_type}, {source_id}) failed: {e}")
        return False
