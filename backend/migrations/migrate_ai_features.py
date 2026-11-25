"""
AI功能数据库迁移脚本
- 为users表添加AI配置字段
- 添加ai_tag_history历史记录表（可选）
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import db_path, run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing, create_indexes

AI_USER_COLUMNS = [
    ('ai_tag_generation_enabled', 'BOOLEAN DEFAULT 1'),
    ('ai_provider', 'TEXT DEFAULT "openai"'),
    ('ai_api_key', 'TEXT'),
    ('ai_model', 'TEXT DEFAULT "gpt-3.5-turbo"'),
]

CREATE_HISTORY_TABLE = '''
    CREATE TABLE IF NOT EXISTS ai_tag_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        prompt TEXT,
        generated_tags TEXT,
        model_used TEXT,
        tokens_used INTEGER,
        cost DECIMAL(10, 6),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
'''

HISTORY_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_ai_history_post ON ai_tag_history(post_id)',
    'CREATE INDEX IF NOT EXISTS idx_ai_history_user ON ai_tag_history(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_ai_history_created ON ai_tag_history(created_at DESC)',
]


def migrate_database():
    path = db_path()
    if not path.exists():
        raise RuntimeError(f'数据库文件不存在: {path}')

    # 1. 备份当前数据库
    print("📦 创建数据库备份...")
    backup_path = str(path).replace('.db', '_backup_before_ai_features.db')
    shutil.copy2(str(path), backup_path)
    print(f"   ✅ 备份创建成功: {backup_path}")

    with transaction(path) as conn:
        conn.execute('PRAGMA foreign_keys = ON')

        # 2. 为 users 表添加 AI 配置字段
        print("\n📊 迁移users表（添加AI配置字段）...")
        added = add_columns_if_missing(conn, 'users', AI_USER_COLUMNS)
        for name in added:
            print(f"   ✅ 添加字段: {name}")
        if not added:
            print("   ⏭️  AI 配置字段已齐全")

        # 3. 创建 ai_tag_history 表
        print("\n📊 创建ai_tag_history表...")
        conn.execute(CREATE_HISTORY_TABLE)
        add_columns_if_missing(conn, 'ai_tag_history', [('currency', 'TEXT DEFAULT "USD"')])

        # 4. 创建索引
        print("\n🔍 创建索引...")
        create_indexes(conn, HISTORY_INDEXES)

        # 5. 为现有用户设置默认 AI 配置
        print("\n⚙️  为现有用户设置默认AI配置...")
        conn.execute('UPDATE users SET ai_tag_generation_enabled = 1 WHERE ai_tag_generation_enabled IS NULL')
        conn.execute('UPDATE users SET ai_provider = "openai" WHERE ai_provider IS NULL')
        conn.execute('UPDATE users SET ai_model = "gpt-3.5-turbo" WHERE ai_model IS NULL')

    print("\n" + "=" * 50)
    print("✅ AI功能迁移完成！")
    print(f"   数据库: {path}")
    print(f"   备份: {backup_path}")
    print("=" * 50)
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate_database, 'AI功能 - 数据库迁移'))
