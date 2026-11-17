"""导出 SQLite schema 快照，供迁移回归测试使用。"""
import json
import sqlite3


def dump_schema(db_path):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%'
              AND name != 'schema_migrations'
              AND type IN ('table', 'index', 'trigger', 'view')
            ORDER BY type, name
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        {'type': row[0], 'name': row[1], 'table': row[2], 'sql': row[3]}
        for row in rows
    ]


def load_snapshot(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
