"""
站点配置迁移
- 新建 site_settings 表（键值配置，用于自定义图标版本等）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import db_path, run_cli, transaction

CREATE_TABLE = '''
    CREATE TABLE IF NOT EXISTS site_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
'''


def migrate():
    path = db_path()
    if not path.exists():
        raise RuntimeError(f'数据库文件不存在: {path}')

    with transaction(path) as conn:
        conn.execute(CREATE_TABLE)
    print("✅ 站点配置迁移完成")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, '站点配置 - 数据库迁移'))
