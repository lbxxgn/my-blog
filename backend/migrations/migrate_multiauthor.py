"""
多作者功能数据库迁移脚本
- 为users表添加role等字段
- 为posts表添加author_id字段
- 为现有文章分配作者（默认分配给admin用户）
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import db_path, run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing, create_indexes

USER_COLUMNS = [
    ('role', 'TEXT NOT NULL DEFAULT "author"'),
    ('display_name', 'TEXT'),
    ('bio', 'TEXT'),
    ('avatar_url', 'TEXT'),
    ('is_active', 'BOOLEAN DEFAULT 1'),
    ('created_at', 'TIMESTAMP'),
    ('updated_at', 'TIMESTAMP'),
]


def migrate_database():
    path = db_path()
    if not path.exists():
        raise RuntimeError(f'数据库文件不存在: {path}')

    # 1. 备份当前数据库
    print("📦 创建数据库备份...")
    backup_path = str(path).replace('.db', '_backup_before_multiauthor.db')
    shutil.copy2(str(path), backup_path)
    print(f"   ✅ 备份创建成功: {backup_path}")

    with transaction(path) as conn:
        conn.execute('PRAGMA foreign_keys = ON')

        # 2. 为 users 表添加新字段
        print("\n📊 迁移users表...")
        added = add_columns_if_missing(conn, 'users', USER_COLUMNS)
        for name in added:
            print(f"   ✅ 添加字段: {name}")
        if not added:
            print("   ⏭️  users 表字段已齐全")

        conn.execute('UPDATE users SET role = "author" WHERE role IS NULL')
        conn.execute('UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL')
        conn.execute('UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL')

        # 3. 为 posts 表添加 author_id 字段
        print("\n📊 迁移posts表...")
        if add_columns_if_missing(conn, 'posts', [('author_id', 'INTEGER')]):
            print("   ✅ 添加字段: author_id")
        else:
            print("   ⏭️  字段已存在，跳过: author_id")

        # 4. 为现有文章分配作者（第一个用户，通常是 admin）
        print("\n👤 为现有文章分配作者...")
        first_user = conn.execute('SELECT id FROM users ORDER BY id LIMIT 1').fetchone()

        if first_user:
            first_user_id = first_user[0]
            cursor = conn.execute(
                'UPDATE posts SET author_id = ? WHERE author_id IS NULL', (first_user_id,))
            print(f"   ✅ 已为 {cursor.rowcount} 篇文章分配作者 (用户ID: {first_user_id})")

            # 5. 将第一个用户设置为 admin 角色
            print("\n🔑 设置管理员角色...")
            conn.execute('UPDATE users SET role = "admin" WHERE id = ?', (first_user_id,))
            admin_name = conn.execute(
                'SELECT username FROM users WHERE id = ?', (first_user_id,)).fetchone()[0]
            print(f"   ✅ 用户 '{admin_name}' 已设置为管理员")
        else:
            print("   ⚠️  警告: 数据库中没有用户，无法分配作者")

        # 6. 创建索引
        print("\n🔍 创建索引...")
        create_indexes(conn, [
            'CREATE INDEX IF NOT EXISTS idx_author_id ON posts(author_id)',
            'CREATE INDEX IF NOT EXISTS idx_author_created ON posts(author_id, created_at DESC)',
        ])

    print("\n" + "=" * 50)
    print("✅ 迁移完成！")
    print(f"   数据库: {path}")
    print(f"   备份: {backup_path}")
    print("=" * 50)
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate_database, '多作者功能 - 数据库迁移'))
