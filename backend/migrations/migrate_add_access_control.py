"""
迁移脚本：添加文章访问控制功能
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config


def migrate():
    """添加文章访问控制字段"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(posts)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'access_level' not in columns:
            print("添加 access_level 字段...")
            cursor.execute('''
                ALTER TABLE posts
                ADD COLUMN access_level TEXT DEFAULT 'public'
            ''')
            print("✓ access_level 字段已添加")

        if 'access_password' not in columns:
            print("添加 access_password 字段...")
            cursor.execute('''
                ALTER TABLE posts
                ADD COLUMN access_password TEXT
            ''')
            print("✓ access_password 字段已添加")

        conn.commit()
        print("\n✅ 文章访问控制功能迁移完成！")

        print("\n支持的访问级别：")
        print("  - public: 公开（所有人可见）")
        print("  - login: 登录用户（仅登录用户可见）")
        print("  - password: 密码保护（需输入密码）")
        print("  - private: 私密（仅作者和管理员可见）")

    except sqlite3.Error as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
