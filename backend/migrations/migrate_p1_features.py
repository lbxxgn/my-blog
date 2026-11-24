"""迁移：P1 内容管理能力（定时发布、软删除、修订历史、多草稿设备）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing, table_exists

CREATE_REVISIONS_TABLE = '''
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
'''


def migrate():
    with transaction() as conn:
        add_columns_if_missing(conn, 'posts', [
            ('publish_at', 'TIMESTAMP'),
            ('deleted_at', 'TIMESTAMP'),
        ])

        conn.execute(CREATE_REVISIONS_TABLE)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_revisions_post ON post_revisions(post_id, created_at DESC)')

        if table_exists(conn, 'drafts'):
            add_columns_if_missing(conn, 'drafts', [('device_token', "TEXT DEFAULT ''")])
            conn.execute('DROP INDEX IF EXISTS idx_drafts_unique')
            conn.execute('DROP INDEX IF EXISTS idx_drafts_unique_post')
            conn.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique_post
                ON drafts(user_id, post_id, device_token)
                WHERE post_id IS NOT NULL
            ''')

    print('✅ P1 内容管理迁移完成')
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, 'P1 内容管理能力 - 数据库迁移'))
