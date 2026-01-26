"""
多作者功能数据库迁移脚本
- 为users表添加role等字段
- 为posts表添加author_id字段
- 为现有文章分配作者（默认分配给admin用户）
"""
import sqlite3
import os
import shutil
from pathlib import Path

def migrate_database():
    # 数据库路径
    db_path = Path(__file__).parent.parent.parent / 'db' / 'simple_blog.db'

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 启用外键约束
        cursor.execute('PRAGMA foreign_keys = ON')

        # 1. 备份当前数据库
        print("📦 创建数据库备份...")
        backup_path = str(db_path).replace('.db', '_backup_before_multiauthor.db')
        shutil.copy2(str(db_path), backup_path)
        print(f"   ✅ 备份创建成功: {backup_path}")

        # 2. 为users表添加新字段（使用ALTER TABLE）
        print("\n📊 迁移users表...")

        # 添加不带默认值的字段（SQLite限制）
        users_fields = [
            ('role', 'TEXT NOT NULL DEFAULT "author"'),
            ('display_name', 'TEXT'),
            ('bio', 'TEXT'),
            ('avatar_url', 'TEXT'),
            ('is_active', 'BOOLEAN DEFAULT 1'),
            ('created_at', 'TIMESTAMP'),
            ('updated_at', 'TIMESTAMP')
        ]

        for field_name, field_def in users_fields:
            try:
                # 对于时间戳字段，不使用DEFAULT
                if 'TIMESTAMP' in field_def and 'CURRENT_TIMESTAMP' in field_def:
                    sql = f'ALTER TABLE users ADD COLUMN {field_name} TIMESTAMP'
                else:
                    sql = f'ALTER TABLE users ADD COLUMN {field_name} {field_def}'
                cursor.execute(sql)
                print(f"   ✅ 添加字段: {field_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e).lower():
                    print(f"   ⏭️  字段已存在，跳过: {field_name}")
                else:
                    raise

        # 设置role字段的默认值
        try:
            cursor.execute('UPDATE users SET role = "author" WHERE role IS NULL')
            print("   ✅ 设置role默认值")
        except:
            pass

        # 设置时间戳字段的默认值
        try:
            cursor.execute('UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL')
            cursor.execute('UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL')
            print("   ✅ 设置时间戳默认值")
        except:
            pass

        # 3. 为posts表添加author_id字段
        print("\n📊 迁移posts表...")
        try:
            cursor.execute('ALTER TABLE posts ADD COLUMN author_id INTEGER')
            print("   ✅ 添加字段: author_id")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("   ⏭️  字段已存在，跳过: author_id")
            else:
                raise

        # 4. 为现有文章分配作者（第一个用户，通常是admin）
        print("\n👤 为现有文章分配作者...")
        cursor.execute('SELECT id FROM users ORDER BY id LIMIT 1')
        first_user = cursor.fetchone()

        if first_user:
            first_user_id = first_user[0]
            cursor.execute('UPDATE posts SET author_id = ? WHERE author_id IS NULL', (first_user_id,))
            updated_posts = cursor.rowcount
            print(f"   ✅ 已为 {updated_posts} 篇文章分配作者 (用户ID: {first_user_id})")

            # 5. 将第一个用户设置为admin角色
            print("\n🔑 设置管理员角色...")
            cursor.execute('UPDATE users SET role = "admin" WHERE id = ?', (first_user_id,))
            cursor.execute('SELECT username FROM users WHERE id = ?', (first_user_id,))
            admin_user = cursor.fetchone()
            print(f"   ✅ 用户 '{admin_user[0]}' 已设置为管理员")
        else:
            print("   ⚠️  警告: 数据库中没有用户，无法分配作者")

        # 6. 创建索引
        print("\n🔍 创建索引...")
        indexes = [
            ('idx_author_id', 'CREATE INDEX IF NOT EXISTS idx_author_id ON posts(author_id)'),
            ('idx_author_created', 'CREATE INDEX IF NOT EXISTS idx_author_created ON posts(author_id, created_at DESC)')
        ]

        for index_name, sql in indexes:
            try:
                cursor.execute(sql)
                print(f"   ✅ 创建索引: {index_name}")
            except sqlite3.OperationalError:
                print(f"   ⏭️  索引已存在: {index_name}")

        conn.commit()
        print("\n" + "="*50)
        print("✅ 迁移完成！")
        print(f"   数据库: {db_path}")
        print(f"   备份: {backup_path}")
        print("="*50)
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        print("   数据库已回滚到迁移前的状态")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("="*50)
    print("多作者功能 - 数据库迁移")
    print("="*50)
    success = migrate_database()
    exit(0 if success else 1)
