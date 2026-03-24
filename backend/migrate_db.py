#!/usr/bin/env python3
"""
数据库增量迁移脚本

用于从旧版本数据库升级到新版本（支持多用户系统）

功能：
1. 自动检测需要添加的字段
2. 备份原有数据库
3. 添加用户系统相关字段
4. 为现有文章分配作者
5. 创建必要的索引
6. 重建全文搜索索引

使用方法：
    python3 backend/migrate_db.py
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.config import DATABASE_URL

def backup_database(db_path):
    """备份现有数据库"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.parent / f"simple_blog_backup_{timestamp}.db"

    print(f"📦 备份数据库到: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"✅ 备份完成")
    return backup_path

def check_column_exists(conn, table_name, column_name):
    """检查表中是否存在指定列"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def migrate_users_table(conn):
    """迁移 users 表，添加新字段"""
    print("\n📋 检查 users 表结构...")

    cursor = conn.cursor()

    # 需要添加的字段（分两步：添加列 + 填充数据）
    # SQLite 不支持 ALTER TABLE 时使用 CURRENT_TIMESTAMP 等函数作为默认值
    columns_to_add = [
        ('role', "TEXT NOT NULL DEFAULT 'author'", None),
        ('display_name', "TEXT", None),
        ('bio', "TEXT", None),
        ('avatar_url', "TEXT", None),
        ('is_active', "BOOLEAN DEFAULT 1", None),
        ('created_at', "TIMESTAMP", "CURRENT_TIMESTAMP"),  # 先添加，再填充
        ('updated_at', "TIMESTAMP", "CURRENT_TIMESTAMP")   # 先添加，再填充
    ]

    updates_done = []
    updates_to_fill = []

    for column, definition, default_value in columns_to_add:
        if not check_column_exists(conn, 'users', column):
            # 移除定义中的默认值（如果有非常量默认值）
            col_def = definition.split(' DEFAULT')[0] if default_value else definition

            sql = f"ALTER TABLE users ADD COLUMN {column} {col_def}"
            print(f"  + 添加字段: {column}")
            try:
                conn.execute(sql)
                updates_done.append(column)

                # 如果需要填充默认值
                if default_value:
                    updates_to_fill.append((column, default_value))

            except sqlite3.Error as e:
                print(f"  ❌ 添加 {column} 失败: {e}")
                return False
        else:
            print(f"  ✓ 字段已存在: {column}")

    if updates_done:
        # 填充需要默认值的字段
        if updates_to_fill:
            print("\n填充默认值...")
            for column, default_value in updates_to_fill:
                try:
                    if default_value == "CURRENT_TIMESTAMP":
                        conn.execute(f"UPDATE users SET {column} = datetime('now') WHERE {column} IS NULL")
                    else:
                        conn.execute(f"UPDATE users SET {column} = ? WHERE {column} IS NULL", (default_value,))
                    print(f"  ✅ 填充 {column}")
                except sqlite3.Error as e:
                    print(f"  ❌ 填充 {column} 失败: {e}")
                    return False

        conn.commit()
        print("✅ users 表迁移完成")
    else:
        print("✅ users 表已是最新版本")

    return True

def migrate_posts_table(conn):
    """迁移 posts 表，添加 author_id 字段"""
    print("\n📋 检查 posts 表结构...")

    if not check_column_exists(conn, 'posts', 'author_id'):
        print("  + 添加字段: author_id")
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN author_id INTEGER")
            conn.commit()
            print("✅ posts 表迁移完成")

            # 为现有文章分配作者
            print("\n📝 为现有文章分配作者...")
            cursor = conn.cursor()

            # 获取第一个用户（通常是管理员）
            cursor.execute("SELECT id FROM users LIMIT 1")
            user = cursor.fetchone()

            if user:
                user_id = user[0]
                print(f"  使用用户 ID: {user_id}")

                # 更新所有没有作者的文章
                cursor.execute("""
                    UPDATE posts
                    SET author_id = ?
                    WHERE author_id IS NULL
                """, (user_id,))

                affected = cursor.rowcount
                conn.commit()
                print(f"  ✅ 已更新 {affected} 篇文章")
            else:
                print("  ⚠️  警告: 数据库中没有用户，请先创建用户")

        except sqlite3.Error as e:
            print(f"  ❌ 错误: {e}")
            return False
    else:
        print("  ✓ 字段已存在: author_id")
        print("✅ posts 表已是最新版本")

    return True

def create_indexes(conn):
    """创建新索引"""
    print("\n📋 检查索引...")

    indexes = [
        ("idx_author_id", "CREATE INDEX IF NOT EXISTS idx_author_id ON posts(author_id)"),
        ("idx_author_created", "CREATE INDEX IF NOT EXISTS idx_author_created ON posts(author_id, created_at DESC)")
    ]

    for index_name, sql in indexes:
        try:
            conn.execute(sql)
            print(f"  ✅ 索引已存在/创建: {index_name}")
        except sqlite3.Error as e:
            print(f"  ⚠️  索引警告 ({index_name}): {e}")

    conn.commit()
    print("✅ 索引检查完成")
    return True

def rebuild_fts_index(conn):
    """重建全文搜索索引"""
    print("\n📋 重建全文搜索索引...")

    try:
        # 删除旧的 FTS 数据
        conn.execute("DELETE FROM posts_fts")
        print("  ✓ 清空旧索引")

        # 重新填充索引
        conn.execute("""
            INSERT INTO posts_fts(rowid, title, content)
            SELECT id, title, content FROM posts
        """)
        conn.commit()

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM posts_fts")
        count = cursor.fetchone()[0]

        print(f"  ✅ 已索引 {count} 篇文章")
        print("✅ 全文搜索索引重建完成")
        return True

    except sqlite3.Error as e:
        print(f"  ❌ FTS 索引错误: {e}")
        print("  ⚠️  全文搜索可能不可用")
        return False

def get_migration_status(conn):
    """获取数据库迁移状态"""
    print("\n📊 数据库状态:")
    print("=" * 50)

    cursor = conn.cursor()

    # 检查表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"表: {', '.join(tables)}")

    # 检查 users 表字段
    if 'users' in tables:
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        print(f"users 表字段: {', '.join(user_columns)}")

    # 检查 posts 表字段
    if 'posts' in tables:
        cursor.execute("PRAGMA table_info(posts)")
        post_columns = [col[1] for col in cursor.fetchall()]
        print(f"posts 表字段: {', '.join(post_columns)}")

    # 统计数据
    cursor.execute("SELECT COUNT(*) FROM posts")
    posts_count = cursor.fetchone()[0]
    print(f"文章总数: {posts_count}")

    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    print(f"用户总数: {users_count}")

    # 检查有多少文章没有作者（如果字段存在）
    if check_column_exists(conn, 'posts', 'author_id'):
        cursor.execute("SELECT COUNT(*) FROM posts WHERE author_id IS NULL")
        no_author = cursor.fetchone()[0]
        if no_author > 0:
            print(f"⚠️  {no_author} 篇文章没有作者")
    else:
        print("⚠️  posts 表缺少 author_id 字段（需要迁移）")

    print("=" * 50)

def main():
    """主函数"""
    print("=" * 60)
    print("  Simple Blog 数据库迁移工具")
    print("=" * 60)

    # 获取数据库路径
    db_path = DATABASE_URL.replace('sqlite:///', '')
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"\n❌ 错误: 数据库文件不存在: {db_path}")
        print("请确保数据库已初始化")
        sys.exit(1)

    print(f"\n数据库路径: {db_path}")

    # 连接数据库
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=OFF")  # 迁移时禁用外键约束
    except sqlite3.Error as e:
        print(f"\n❌ 数据库连接失败: {e}")
        sys.exit(1)

    # 显示当前状态
    get_migration_status(conn)

    # 询问是否继续
    print("\n⚠️  即将开始数据库迁移")
    response = input("是否继续? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("❌ 已取消迁移")
        conn.close()
        sys.exit(0)

    # 备份数据库
    try:
        backup_path = backup_database(db_path)
    except Exception as e:
        print(f"\n❌ 备份失败: {e}")
        print("无法继续迁移")
        conn.close()
        sys.exit(1)

    # 执行迁移
    print("\n" + "=" * 60)
    print("开始迁移...")
    print("=" * 60)

    success = True

    # 1. 迁移 users 表
    if not migrate_users_table(conn):
        success = False

    # 2. 迁移 posts 表
    if success and not migrate_posts_table(conn):
        success = False

    # 3. 创建索引
    if success and not create_indexes(conn):
        success = False

    # 4. 重建 FTS 索引
    if success:
        rebuild_fts_index(conn)

    # 恢复外键约束
    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()

    # 显示结果
    print("\n" + "=" * 60)
    if success:
        print("✅ 迁移完成!")
        print(f"📦 原数据库已备份到: {backup_path}")
        print("\n建议:")
        print("  1. 验证应用功能是否正常")
        print("  2. 检查文章作者信息")
        print("  3. 测试用户管理功能")
        print("  4. 确认无误后可删除备份文件")
    else:
        print("❌ 迁移过程中出现错误")
        print(f"📦 数据库已恢复，备份位于: {backup_path}")
        print("请检查错误信息并手动修复")

    print("=" * 60)

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
