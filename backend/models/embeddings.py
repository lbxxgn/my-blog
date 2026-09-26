"""
Embedding Model Functions

向量嵌入的存取与相似度检索。表结构由迁移 009 创建
（backend/migrations/migrate_embeddings.py），向量以
array('f').tobytes() 的 float32 二进制存入 BLOB 列。
"""

import logging
import sqlite3
from array import array

import numpy as np

from .db import get_db_connection

logger = logging.getLogger(__name__)

__all__ = [
    'upsert_embedding',
    'get_embedding',
    'delete_embedding',
    'search_similar',
]

SOURCE_TYPES = ('post', 'card', 'doc')


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

    conn = get_db_connection()
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
        return cursor.lastrowid
    finally:
        conn.close()


def get_embedding(source_type, source_id):
    """
    读取一条向量记录

    Returns:
        dict: {'id', 'source_type', 'source_id', 'model', 'vector', 'content_hash', 'updated_at'}
              vector 为 list[float]；不存在返回 None
    """
    _validate_source_type(source_type)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM embeddings WHERE source_type = ? AND source_id = ?',
            (source_type, source_id)
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    record = dict(row)
    record['vector'] = _deserialize_vector(record['vector']) if record['vector'] else []
    return record


def delete_embedding(source_type, source_id):
    """删除一条向量记录，返回是否有行被删除"""
    _validate_source_type(source_type)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM embeddings WHERE source_type = ? AND source_id = ?',
            (source_type, source_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if source_types:
            invalid = set(source_types) - set(SOURCE_TYPES)
            if invalid:
                raise ValueError(f"Invalid source_types: {sorted(invalid)}")
            placeholders = ','.join('?' * len(source_types))
            cursor.execute(
                f'SELECT source_type, source_id, vector FROM embeddings '
                f'WHERE vector IS NOT NULL AND source_type IN ({placeholders})',
                list(source_types)
            )
        else:
            cursor.execute('SELECT source_type, source_id, vector FROM embeddings WHERE vector IS NOT NULL')
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        # 迁移 009 尚未执行：没有表可搜
        logger.warning(f"embeddings table unavailable: {e}")
        return []
    finally:
        conn.close()

    if not rows:
        return []

    query = np.asarray(query_vector, dtype=np.float32)
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return []

    keys = []
    vectors = []
    for row in rows:
        arr = np.frombuffer(row['vector'], dtype=np.float32)
        if arr.shape != query.shape:
            # 维度不一致（可能换了模型），跳过
            continue
        keys.append((row['source_type'], row['source_id']))
        vectors.append(arr)

    if not vectors:
        return []

    matrix = np.stack(vectors)
    norms = np.linalg.norm(matrix, axis=1)
    nonzero = norms > 0
    if not nonzero.any():
        return []

    scores = np.zeros(len(vectors), dtype=np.float32)
    scores[nonzero] = (matrix[nonzero] @ query) / (norms[nonzero] * query_norm)

    order = np.argsort(-scores)[:top_k]
    return [(keys[i][0], keys[i][1], float(scores[i])) for i in order]
