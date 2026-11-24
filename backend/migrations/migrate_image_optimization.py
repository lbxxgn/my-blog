"""创建optimized_images表用于图片优化追踪"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction
from backend.utils.sqlite_schema import create_indexes

CREATE_TABLE = '''
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
'''

INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_optimized_status ON optimized_images(status)',
    'CREATE INDEX IF NOT EXISTS idx_optimized_original ON optimized_images(original_path)',
    'CREATE INDEX IF NOT EXISTS idx_optimized_hash ON optimized_images(original_hash)',
]


def migrate():
    """执行迁移"""
    with transaction() as conn:
        conn.execute(CREATE_TABLE)
        create_indexes(conn, INDEXES)
    print("✅ Optimized_images表创建成功")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '图片优化记录表 - 数据库迁移'))
