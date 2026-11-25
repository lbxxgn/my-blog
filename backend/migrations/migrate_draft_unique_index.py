"""移除 drafts 表的旧唯一索引，允许同一文章保存多设备草稿。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction
from backend.utils.sqlite_schema import table_exists


def migrate():
    with transaction() as conn:
        if table_exists(conn, 'drafts'):
            conn.execute('DROP INDEX IF EXISTS idx_drafts_unique')
            conn.execute('DROP INDEX IF EXISTS idx_drafts_unique_post')
            conn.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique_post
                ON drafts(user_id, post_id, device_token)
                WHERE post_id IS NOT NULL
            ''')
    print('✅ drafts 唯一索引已修正')
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '修正 drafts 唯一索引'))
