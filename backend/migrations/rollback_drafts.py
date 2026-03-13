"""回滚drafts表"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import config

def rollback():
    """执行回滚"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('DROP TABLE IF EXISTS drafts')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_user_post')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_user_updated')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_post')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_device')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_unique')

        conn.commit()
        print("✅ Drafts表已回滚")

    except Exception as e:
        conn.rollback()
        print(f"❌ 回滚失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    rollback()
