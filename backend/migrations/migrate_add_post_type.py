"""
迁移脚本：添加文章类型字段（用于统一内容流）
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config


def migrate():
    """添加文章类型字段并创建索引"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查 type 字段是否已存在
        cursor.execute("PRAGMA table_info(posts)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'type' not in columns:
            print("添加 type 字段到 posts 表...")
            cursor.execute('''
                ALTER TABLE posts
                ADD COLUMN type TEXT DEFAULT 'post'
            ''')
            print("type 字段已添加")

            # 更新现有行，将 NULL 值设置为 'post'
            print("更新现有文章的 type 值为 'post'...")
            cursor.execute('''
                UPDATE posts
                SET type = 'post'
                WHERE type IS NULL
            ''')
            updated_count = cursor.rowcount
            print(f"已更新 {updated_count} 篇文章的 type 值")
        else:
            print("type 字段已存在，跳过添加")

        # 创建索引
        print("创建索引 idx_posts_type...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_posts_type
            ON posts(type)
        ''')
        print("索引 idx_posts_type 已创建")

        print("创建索引 idx_posts_type_created...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_posts_type_created
            ON posts(type, created_at DESC)
        ''')
        print("索引 idx_posts_type_created 已创建")

        conn.commit()
        print("\n文章类型字段迁移完成！")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
