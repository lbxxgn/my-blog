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

import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import db_path, run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing, create_indexes

POST_COLUMNS = [
    ('content_format', "TEXT DEFAULT 'html'"),
    ('sort_order', 'INTEGER DEFAULT 0'),
    ('source_post_id', 'INTEGER'),
]

CATEGORY_COLUMNS = [
    ('parent_id', 'INTEGER'),
    ('slug', 'TEXT'),
    ('sort_order', 'INTEGER DEFAULT 0'),
    ('space', "TEXT DEFAULT 'blog'"),
    ('icon', 'TEXT'),
    ('description', 'TEXT'),
]

INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_posts_post_type ON posts(post_type)',
    'CREATE INDEX IF NOT EXISTS idx_posts_post_type_created ON posts(post_type, created_at DESC)',
    'CREATE INDEX IF NOT EXISTS idx_posts_content_format ON posts(content_format)',
    'CREATE INDEX IF NOT EXISTS idx_posts_source_post_id ON posts(source_post_id)',
    'CREATE INDEX IF NOT EXISTS idx_posts_kb_order ON posts(category_id, sort_order)',
    'CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)',
    'CREATE INDEX IF NOT EXISTS idx_categories_space ON categories(space)',
    'CREATE INDEX IF NOT EXISTS idx_categories_space_parent ON categories(space, parent_id, sort_order)',
]


def backup_database(path):
    """备份数据库"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = path.parent / f"simple_blog_kb_backup_{timestamp}.db"
    print(f"📦 备份数据库到: {backup_path}")
    shutil.copy2(path, backup_path)
    print("✅ 备份完成")
    return backup_path


def backfill_data(conn):
    """回填现有数据"""
    print("\n📝 回填现有数据...")

    # 现有分类归入 blog 空间，parent_id 置空
    conn.execute("UPDATE categories SET space = 'blog' WHERE space IS NULL")
    conn.execute("UPDATE categories SET parent_id = NULL WHERE parent_id IS NULL")
    print("  ✅ 现有分类标记为 blog 空间")

    # 确保 post_type 字段存在并回填（兼容旧库）
    add_columns_if_missing(conn, 'posts', [('post_type', "TEXT DEFAULT 'blog'")])
    # 标准化历史值：article / knowledge-article -> blog（知识库文档后续单独创建为 knowledge）
    conn.execute(
        "UPDATE posts SET post_type = 'blog' "
        "WHERE post_type IN ('article', 'knowledge-article') OR post_type IS NULL"
    )
    print("  ✅ 现有文章 post_type 标准化为 blog")

    # 现有文章内容格式标记为 html
    conn.execute("UPDATE posts SET content_format = 'html' WHERE content_format IS NULL")
    print("  ✅ 现有文章 content_format 标记为 html")

    # 现有文章排序默认值
    conn.execute("UPDATE posts SET sort_order = 0 WHERE sort_order IS NULL")


def migrate():
    path = db_path()
    if not path.exists():
        raise RuntimeError(f'数据库文件不存在: {path}')

    print("=" * 60)
    print("  知识库独立空间与树形分类 迁移")
    print("=" * 60)
    print(f"数据库路径: {path}")

    backup_database(path)

    with transaction(path) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")

        print("\n📋 检查 posts 表结构...")
        add_columns_if_missing(conn, 'posts', POST_COLUMNS)
        print("\n📋 检查 categories 表结构...")
        add_columns_if_missing(conn, 'categories', CATEGORY_COLUMNS)

        backfill_data(conn)

        print("\n📋 创建索引...")
        create_indexes(conn, INDEXES)

    print("\n✅ 知识库迁移完成！")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '知识库独立空间 - 数据库迁移'))
