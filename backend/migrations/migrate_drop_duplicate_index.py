"""移除重复的 posts(post_type) 索引。

早期 init_db 同时创建了 ``idx_posts_post_type`` 与 ``idx_post_type``，两者
定义相同、完全冗余，只增加写入成本。新库已不再创建后者，这里清理存量库。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import run_cli, transaction

__all__ = ['migrate']


def migrate():
    with transaction() as conn:
        conn.execute('DROP INDEX IF EXISTS idx_post_type')
        print('✅ 冗余索引 idx_post_type 已移除')
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '移除冗余索引 idx_post_type'))
