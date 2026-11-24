"""SQLite schema 的幂等结构变更助手。

``init_db`` 与版本化迁移都需要"列不存在才 ADD COLUMN"。历史实现靠
``try: ALTER ... except: pass``，会把磁盘满、表不存在、SQL 语法错误等真实故障
一起吞掉。改为先读 ``PRAGMA table_info`` 再决定是否执行。
"""

__all__ = ['table_exists', 'table_columns', 'add_columns_if_missing', 'create_indexes']


def table_exists(db, table):
    """表是否存在（``db`` 可以是连接或游标）。"""
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def table_columns(db, table):
    """返回表的列名集合；表不存在时返回空集合。"""
    return {row[1] for row in db.execute(f'PRAGMA table_info({table})').fetchall()}


def add_columns_if_missing(db, table, columns):
    """按需 ADD COLUMN。

    Args:
        db: sqlite3 连接或游标
        table (str): 表名
        columns (iterable): (列名, 列定义) 序列

    Returns:
        list: 实际新增的列名（已存在的不计入）
    """
    existing = table_columns(db, table)
    added = []
    for name, definition in columns:
        if name in existing:
            continue
        db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
        existing.add(name)
        added.append(name)
    return added


def create_indexes(db, statements):
    """执行一组 ``CREATE INDEX IF NOT EXISTS`` 语句（语句本身需幂等）。"""
    for statement in statements:
        db.execute(statement)
