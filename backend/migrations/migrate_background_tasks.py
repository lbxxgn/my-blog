"""持久化后台任务队列。"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import backend.config as config


def migrate():
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('''
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
        ''')
        conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_background_tasks_dedupe
            ON background_tasks(kind, dedupe_key)
            WHERE dedupe_key IS NOT NULL AND status IN ('pending', 'running')
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_background_tasks_pending
            ON background_tasks(status, run_after, id)
        ''')
        conn.commit()
        print('✅ background_tasks 表已创建')
    except sqlite3.Error as e:
        conn.rollback()
        print(f'❌ 迁移失败: {e}')
        raise
    finally:
        conn.close()
