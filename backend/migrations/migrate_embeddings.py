"""
Embedding 语义搜索基础设施迁移
- 新建 embeddings 表（按 source_type/source_id 唯一存储向量）
- users 表增加 Embedding 服务配置列（独立于对话类 AI 配置）
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config

NEW_USER_COLUMNS = [
    ('ai_embedding_enabled', 'INTEGER DEFAULT 0'),
    ('ai_embedding_base_url', 'TEXT'),
    ('ai_embedding_api_key', 'TEXT'),
    ('ai_embedding_model', 'TEXT'),
]


def migrate():
    db_path = Path(config.DATABASE_URL.replace('sqlite:///', ''))

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 向量存储表（source_type: post/card/doc）
        cursor.execute('''
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
        ''')
        print("   ✅ 创建表: embeddings")

        # 2. users 表增加 Embedding 配置列
        for column, definition in NEW_USER_COLUMNS:
            try:
                cursor.execute(f'ALTER TABLE users ADD COLUMN {column} {definition}')
                print(f"   ✅ 添加字段: {column}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e).lower():
                    print(f"   ⏭️  字段已存在，跳过: {column}")
                else:
                    raise

        conn.commit()
        print("✅ Embedding 基础设施迁移完成")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
