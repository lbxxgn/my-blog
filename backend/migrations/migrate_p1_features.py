"""迁移：P1 内容管理能力（定时发布、软删除、修订历史、多草稿设备）。"""

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
        cursor.execute("PRAGMA table_info(posts)")
        cols = {row[1] for row in cursor.fetchall()}
        for col, definition in [('publish_at', 'TIMESTAMP'), ('deleted_at', 'TIMESTAMP')]:
            if col not in cols:
                cursor.execute(f'ALTER TABLE posts ADD COLUMN {col} {definition}')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_format TEXT DEFAULT 'html',
                category_id INTEGER,
                tags_json TEXT,
                access_level TEXT DEFAULT 'public',
                access_password TEXT,
                post_type TEXT DEFAULT 'blog',
                type TEXT DEFAULT 'post',
                author_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_revisions_post ON post_revisions(post_id, created_at DESC)')

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drafts'")
        if cursor.fetchone():
            cursor.execute('PRAGMA table_info(drafts)')
            draft_cols = {row[1] for row in cursor.fetchall()}
            if 'device_token' not in draft_cols:
                cursor.execute("ALTER TABLE drafts ADD COLUMN device_token TEXT DEFAULT ''")
            cursor.execute('DROP INDEX IF EXISTS idx_drafts_unique_post')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique_post
                ON drafts(user_id, post_id, device_token)
                WHERE post_id IS NOT NULL
            ''')

        conn.commit()
        print('✅ P1 内容管理迁移完成')
    except sqlite3.Error as e:
        conn.rollback()
        print(f'❌ 迁移失败: {e}')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
