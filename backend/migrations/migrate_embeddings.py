"""
Embedding 语义搜索基础设施迁移
- 新建 embeddings 表（按 source_type/source_id 唯一存储向量）
- users 表增加 Embedding 服务配置列（独立于对话类 AI 配置）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import db_path, run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing

NEW_USER_COLUMNS = [
    ('ai_embedding_enabled', 'INTEGER DEFAULT 0'),
    ('ai_embedding_base_url', 'TEXT'),
    ('ai_embedding_api_key', 'TEXT'),
    ('ai_embedding_model', 'TEXT'),
]

CREATE_TABLE = '''
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY,
        source_type TEXT NOT NULL,
        source_id INTEGER NOT NULL,
        model TEXT,
        vector BLOB,
        content_hash TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source_type, source_id)
    )
'''


def migrate():
    path = db_path()
    if not path.exists():
        raise RuntimeError(f'数据库文件不存在: {path}')

    with transaction(path) as conn:
        conn.execute(CREATE_TABLE)
        print("   ✅ 创建表: embeddings")

        added = add_columns_if_missing(conn, 'users', NEW_USER_COLUMNS)
        for name in added:
            print(f"   ✅ 添加字段: {name}")
        if not added:
            print("   ⏭️  Embedding 配置字段已齐全")

    print("✅ Embedding 基础设施迁移完成")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, 'Embedding 语义搜索基础设施 - 数据库迁移'))
