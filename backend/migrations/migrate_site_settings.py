"""
站点配置迁移
- 新建 site_settings 表（键值配置，用于自定义图标版本等）
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config


def migrate():
    db_path = Path(config.DATABASE_URL.replace('sqlite:///', ''))

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("   ✅ 创建表: site_settings")

        conn.commit()
        print("✅ 站点配置迁移完成")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
