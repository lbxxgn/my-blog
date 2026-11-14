"""移除 drafts 表的旧唯一索引，允许同一文章保存多设备草稿。"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config


def migrate():
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drafts'")
        if cursor.fetchone():
            cursor.execute('DROP INDEX IF EXISTS idx_drafts_unique')
            cursor.execute('DROP INDEX IF EXISTS idx_drafts_unique_post')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique_post
                ON drafts(user_id, post_id, device_token)
                WHERE post_id IS NOT NULL
            ''')
        conn.commit()
        print('✅ drafts 唯一索引已修正')
    except sqlite3.Error as e:
        conn.rollback()
        print(f'❌ 迁移失败: {e}')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
