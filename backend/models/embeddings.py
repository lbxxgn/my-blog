"""
Embedding Model Functions

向量嵌入的存取与相似度检索。表结构由迁移 009 创建
（backend/migrations/migrate_embeddings.py），向量以
array('f').tobytes() 的 float32 二进制存入 BLOB 列。
"""

import logging
import sqlite3
import threading
from array import array

import numpy as np

from .db import get_db_context

logger = logging.getLogger(__name__)

__all__ = [
    'upsert_embedding',
    'get_embedding',
    'delete_embedding',
    'search_similar',
]

SOURCE_TYPES = ('post', 'card', 'doc')

# 进程内向量缓存：避免每次查询都从 SQLite 读取并反序列化全部 BLOB。
# 仍为线性扫描，但把 DB IO/反序列化从每次查询降为仅在数据变化时一次。
_vector_cache = {
    'signature': None,
    'by_dim': {},
}
_vector_cache_lock = threading.Lock()


def invalidate_vector_cache():
    with _vector_cache_lock:
        _vector_cache['signature'] = None
        _vector_cache['by_dim'] = {}


def _validate_source_type(source_type):
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Invalid source_type: {source_type!r} (expected one of {SOURCE_TYPES})")


def _serialize_vector(vector):
    """list[float] -> float32 bytes"""
    return array('f', vector).tobytes()


def _deserialize_vector(blob):
    """float32 bytes -> list[float]"""
    arr = array('f')
    arr.frombytes(blob)
    return list(arr)


def upsert_embedding(source_type, source_id, vector, model=None, content_hash=None):
    """
    写入或更新一条向量记录（按 (source_type, source_id) 唯一）

    Args:
        source_type: 'post' / 'card' / 'doc'
        source_id: 实体ID
        vector: list[float]
        model: 生成该向量的模型名
        content_hash: 内容哈希（用于变更检测）

    Returns:
        int: 记录ID
    """
    _validate_source_type(source_type)
    blob = _serialize_vector(vector)

    with get_db_context() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO embeddings (source_type, source_id, model, vector, content_hash)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_type, source_id) DO UPDATE SET
                    model = excluded.model,
                    vector = excluded.vector,
                    content_hash = excluded.content_hash,
                    updated_at = CURRENT_TIMESTAMP
            ''', (source_type, source_id, model, blob, content_hash))
            conn.commit()
            invalidate_vector_cache()
            return cursor.lastrowid
        finally:
            pass


def get_embedding(source_type, source_id):
    """
    读取一条向量记录

    Returns:
        dict: {'id', 'source_type', 'source_id', 'model', 'vector', 'content_hash', 'updated_at'}
              vector 为 list[float]；不存在返回 None
    """
    _validate_source_type(source_type)
    with get_db_context() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM embeddings WHERE source_type = ? AND source_id = ?',
                (source_type, source_id)
            )
            row = cursor.fetchone()
        finally:
            pass

        if not row:
            return None

        record = dict(row)
        record['vector'] = _deserialize_vector(record['vector']) if record['vector'] else []
        return record


def delete_embedding(source_type, source_id):
    """删除一条向量记录，返回是否有行被删除"""
    _validate_source_type(source_type)
    with get_db_context() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM embeddings WHERE source_type = ? AND source_id = ?',
                (source_type, source_id)
            )
            conn.commit()
            if cursor.rowcount:
                invalidate_vector_cache()
            return cursor.rowcount > 0
        finally:
            pass


def _load_vector_cache(conn):
    """按维度加载并缓存归一化矩阵；返回 (signature, {dim: (keys, matrix, norms)})。"""
    db_row = conn.execute('PRAGMA database_list').fetchone()
    db_file = db_row['file'] if db_row else ''
    signature = conn.execute(
        'SELECT COUNT(*) AS c, COALESCE(MAX(updated_at), \'\') AS m, COALESCE(SUM(LENGTH(vector)), 0) AS s FROM embeddings'
    ).fetchone()
    signature = (db_file, signature['c'], signature['m'], signature['s'])
    with _vector_cache_lock:
        if _vector_cache['signature'] == signature:
            return signature, _vector_cache['by_dim']

    rows = conn.execute(
        'SELECT source_type, source_id, vector FROM embeddings WHERE vector IS NOT NULL'
    ).fetchall()
    grouped = {}
    for row in rows:
        arr = np.frombuffer(row['vector'], dtype=np.float32)
        if arr.size == 0:
            continue
        grouped.setdefault(arr.size, ([], []))[0].append((row['source_type'], row['source_id']))
        grouped[arr.size][1].append(arr)

    by_dim = {}
    for dim, (keys, vectors) in grouped.items():
        matrix = np.stack(vectors)
        norms = np.linalg.norm(matrix, axis=1)
        by_dim[dim] = (keys, matrix, norms)

    with _vector_cache_lock:
        _vector_cache['signature'] = signature
        _vector_cache['by_dim'] = by_dim
    return signature, by_dim


def search_similar(query_vector, top_k=10, source_types=None):
    """
    余弦相似度检索：读全表向量，numpy 计算后返回 top-k

    Args:
        query_vector: list[float] 查询向量
        top_k: 返回数量
        source_types: 可选，限定 source_type 列表（如 ['post', 'doc']）

    Returns:
        list[tuple]: [(source_type, source_id, score)]，按相似度降序
    """
    if source_types:
        invalid = set(source_types) - set(SOURCE_TYPES)
        if invalid:
            raise ValueError(f"Invalid source_types: {sorted(invalid)}")

    query = np.asarray(query_vector, dtype=np.float32)
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return []

    try:
        with get_db_context() as conn:
            _signature, by_dim = _load_vector_cache(conn)
    except sqlite3.OperationalError as e:
        logger.warning(f"embeddings table unavailable: {e}")
        return []

    entry = by_dim.get(query.size)
    if not entry:
        return []
    keys, matrix, norms = entry

    if source_types:
        allowed = set(source_types)
        mask = np.array([key[0] in allowed for key in keys], dtype=bool)
        if not mask.any():
            return []
        keys = [key for key, keep in zip(keys, mask) if keep]
        matrix = matrix[mask]
        norms = norms[mask]

    nonzero = norms > 0
    if not nonzero.any():
        return []

    scores = np.zeros(len(keys), dtype=np.float32)
    scores[nonzero] = (matrix[nonzero] @ query) / (norms[nonzero] * query_norm)
    order = np.argsort(-scores)[:top_k]
    return [(keys[i][0], keys[i][1], float(scores[i])) for i in order]
