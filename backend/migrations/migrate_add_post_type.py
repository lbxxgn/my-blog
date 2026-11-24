"""
迁移脚本：添加文章类型字段（用于统一内容流）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing, create_indexes


def migrate():
    """添加文章类型字段并创建索引"""
    with transaction() as conn:
        added = add_columns_if_missing(conn, 'posts', [('type', "TEXT DEFAULT 'post'")])

        if 'type' in added:
            print("type 字段已添加")
            cursor = conn.execute("UPDATE posts SET type = 'post' WHERE type IS NULL")
            print(f"已更新 {cursor.rowcount} 篇文章的 type 值")
        else:
            print("type 字段已存在，跳过添加")

        create_indexes(conn, [
            'CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(type)',
            'CREATE INDEX IF NOT EXISTS idx_posts_type_created ON posts(type, created_at DESC)',
        ])
        print("索引 idx_posts_type / idx_posts_type_created 已就绪")

    print("\n文章类型字段迁移完成！")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '文章类型字段 - 数据库迁移'))
