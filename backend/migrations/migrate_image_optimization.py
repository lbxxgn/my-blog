"""创建optimized_images表用于图片优化追踪"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import config

def migrate():
    """执行迁移"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                original_hash TEXT,
                thumbnail_path TEXT,
                medium_path TEXT,
                large_path TEXT,
                original_size INTEGER,
                optimized_size INTEGER,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_status
            ON optimized_images(status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_original
            ON optimized_images(original_path)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_hash
            ON optimized_images(original_hash)
        ''')

        conn.commit()
        print("✅ Optimized_images表创建成功")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
