"""创建drafts表用于多设备草稿同步"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config

def migrate():
    """执行迁移"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 创建drafts表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category_id INTEGER,
                tags TEXT,
                is_published BOOLEAN DEFAULT 0,
                device_info TEXT,
                user_agent TEXT,
                last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_user_post
            ON drafts(user_id, post_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_user_updated
            ON drafts(user_id, updated_at DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_post
            ON drafts(post_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_device
            ON drafts(user_id, device_info, updated_at)
        ''')

        # 唯一约束
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique
            ON drafts(user_id, post_id)
        ''')

        conn.commit()
        print("✅ Drafts表创建成功")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
