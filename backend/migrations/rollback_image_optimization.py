"""回滚optimized_images表"""
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
        cursor.execute('DROP TABLE IF EXISTS optimized_images')
        cursor.execute('DROP INDEX IF EXISTS idx_optimized_status')
        cursor.execute('DROP INDEX IF EXISTS idx_optimized_original')
        cursor.execute('DROP INDEX IF EXISTS idx_optimized_hash')

        conn.commit()
        print("✅ Optimized_images表已回滚")

    except Exception as e:
        conn.rollback()
        print(f"❌ 回滚失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    rollback()
