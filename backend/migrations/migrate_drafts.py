"""创建drafts表用于多设备草稿同步"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction
from backend.utils.sqlite_schema import create_indexes

CREATE_TABLE = '''
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
'''

INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_drafts_user_post ON drafts(user_id, post_id)',
    'CREATE INDEX IF NOT EXISTS idx_drafts_user_updated ON drafts(user_id, updated_at DESC)',
    'CREATE INDEX IF NOT EXISTS idx_drafts_post ON drafts(post_id)',
    'CREATE INDEX IF NOT EXISTS idx_drafts_device ON drafts(user_id, device_info, updated_at)',
    # 唯一约束（后续迁移 014 会替换为含 device_token 的版本）
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique ON drafts(user_id, post_id)',
]


def migrate():
    """执行迁移"""
    with transaction() as conn:
        conn.execute(CREATE_TABLE)
        create_indexes(conn, INDEXES)
    print("✅ Drafts表创建成功")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '草稿同步表 - 数据库迁移'))
