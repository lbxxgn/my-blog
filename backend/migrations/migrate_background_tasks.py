"""持久化后台任务队列。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction

CREATE_TABLE = '''
    CREATE TABLE IF NOT EXISTS background_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        dedupe_key TEXT,
        payload TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        run_after TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        locked_at TIMESTAMP,
        locked_by TEXT,
        last_error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
'''

INDEXES = [
    '''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_background_tasks_dedupe
    ON background_tasks(kind, dedupe_key)
    WHERE dedupe_key IS NOT NULL AND status IN ('pending', 'running')
    ''',
    '''
    CREATE INDEX IF NOT EXISTS idx_background_tasks_pending
    ON background_tasks(status, run_after, id)
    ''',
]


def migrate():
    with transaction() as conn:
        conn.execute(CREATE_TABLE)
        for statement in INDEXES:
            conn.execute(statement)
    print('✅ background_tasks 表已创建')
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '持久化后台任务队列 - 数据库迁移'))
