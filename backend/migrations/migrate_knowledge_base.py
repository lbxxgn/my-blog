#!/usr/bin/env python3
"""
迁移脚本：知识库独立空间与树形分类

功能：
1. posts 表新增 content_format / sort_order / source_post_id 字段
2. categories 表新增 parent_id / slug / sort_order / space / icon / description 字段（扁平 -> 树形）
3. 回填现有数据：现有分类归入 blog 空间、现有文章标记为 blog/html
4. 创建知识库相关索引

使用方法：
    python3 backend/migrations/migrate_knowledge_base.py
"""

import sqlite3
import sys
import shutil
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径（migrations -> backend -> project root）
PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.config import DATABASE_URL


def backup_database(db_path):
    """备份数据库"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.parent / f"simple_blog_kb_backup_{timestamp}.db"
    print(f"📦 备份数据库到: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("✅ 备份完成")
    return backup_path


def check_column_exists(cursor, table_name, column_name):
    """检查表中是否存在指定列"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns


def add_column_if_missing(cursor, table, column, definition):
    """若列不存在则添加"""
    if check_column_exists(cursor, table, column):
        print(f"  ✓ 字段已存在: {table}.{column}")
        return False
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    print(f"  + 添加字段: {table}.{column}")
    return True


def migrate_posts_table(cursor):
    """posts 表新增字段"""
    print("\n📋 检查 posts 表结构...")
    add_column_if_missing(cursor, 'posts', 'content_format', "TEXT DEFAULT 'html'")
    add_column_if_missing(cursor, 'posts', 'sort_order', "INTEGER DEFAULT 0")
    add_column_if_missing(cursor, 'posts', 'source_post_id', "INTEGER")


def migrate_categories_table(cursor):
    """categories 表新增字段（扁平 -> 树形）"""
    print("\n📋 检查 categories 表结构...")
    add_column_if_missing(cursor, 'categories', 'parent_id', "INTEGER")
    add_column_if_missing(cursor, 'categories', 'slug', "TEXT")
    add_column_if_missing(cursor, 'categories', 'sort_order', "INTEGER DEFAULT 0")
    add_column_if_missing(cursor, 'categories', 'space', "TEXT DEFAULT 'blog'")
    add_column_if_missing(cursor, 'categories', 'icon', "TEXT")
    add_column_if_missing(cursor, 'categories', 'description', "TEXT")


def backfill_data(cursor):
    """回填现有数据"""
    print("\n📝 回填现有数据...")

    # 现有分类归入 blog 空间，parent_id 置空
    cursor.execute("UPDATE categories SET space = 'blog' WHERE space IS NULL")
    cursor.execute("UPDATE categories SET parent_id = NULL WHERE parent_id IS NULL")
    print("  ✅ 现有分类标记为 blog 空间")

    # 确保 post_type 字段存在并回填（兼容旧库）
    if check_column_exists(cursor, 'posts', 'post_type'):
        # 标准化历史值：article / knowledge-article -> blog（知识库文档后续单独创建为 knowledge）
        cursor.execute("UPDATE posts SET post_type = 'blog' WHERE post_type IN ('article', 'knowledge-article') OR post_type IS NULL")
        print("  ✅ 现有文章 post_type 标准化为 blog")
    else:
        cursor.execute("ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT 'blog'")
        print("  + 添加字段: posts.post_type")

    # 现有文章内容格式标记为 html
    cursor.execute("UPDATE posts SET content_format = 'html' WHERE content_format IS NULL")
    print("  ✅ 现有文章 content_format 标记为 html")

    # 现有文章排序默认值
    cursor.execute("UPDATE posts SET sort_order = 0 WHERE sort_order IS NULL")


def create_indexes(cursor):
    """创建知识库相关索引"""
    print("\n📋 创建索引...")
    indexes = [
        ("idx_posts_post_type", "CREATE INDEX IF NOT EXISTS idx_posts_post_type ON posts(post_type)"),
        ("idx_posts_post_type_created", "CREATE INDEX IF NOT EXISTS idx_posts_post_type_created ON posts(post_type, created_at DESC)"),
        ("idx_posts_content_format", "CREATE INDEX IF NOT EXISTS idx_posts_content_format ON posts(content_format)"),
        ("idx_posts_source_post_id", "CREATE INDEX IF NOT EXISTS idx_posts_source_post_id ON posts(source_post_id)"),
        ("idx_posts_kb_order", "CREATE INDEX IF NOT EXISTS idx_posts_kb_order ON posts(category_id, sort_order)"),
        ("idx_categories_parent", "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)"),
        ("idx_categories_space", "CREATE INDEX IF NOT EXISTS idx_categories_space ON categories(space)"),
        ("idx_categories_space_parent", "CREATE INDEX IF NOT EXISTS idx_categories_space_parent ON categories(space, parent_id, sort_order)"),
    ]
    for name, sql in indexes:
        cursor.execute(sql)
        print(f"  ✅ 索引: {name}")


def migrate():
    db_path = Path(DATABASE_URL.replace('sqlite:///', ''))
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("  知识库独立空间与树形分类 迁移")
    print("=" * 60)
    print(f"数据库路径: {db_path}")

    backup_database(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=OFF")
    cursor = conn.cursor()

    try:
        migrate_posts_table(cursor)
        migrate_categories_table(cursor)
        backfill_data(cursor)
        create_indexes(cursor)
        conn.commit()
        print("\n✅ 知识库迁移完成！")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


if __name__ == '__main__':
    migrate()
