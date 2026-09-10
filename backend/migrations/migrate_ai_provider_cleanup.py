"""
AI 提供商清理迁移
- 为 users 表添加 ai_base_url 字段（自定义 OpenAI 兼容提供商使用）
- 将已移除的旧提供商（openai/volcengine/volcengine_codingplan/zhipu_codingplan 等）
  重置为默认的阿里百炼（dashscope / qwen-turbo）
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config

SUPPORTED_PROVIDERS = ('dashscope', 'deepseek', 'custom')


def migrate():
    db_path = Path(config.DATABASE_URL.replace('sqlite:///', ''))

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 为 users 表添加 ai_base_url 字段
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN ai_base_url TEXT')
            print("   ✅ 添加字段: ai_base_url")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("   ⏭️  字段已存在，跳过: ai_base_url")
            else:
                raise

        # 2. 重置已移除的旧提供商配置
        placeholders = ','.join('?' * len(SUPPORTED_PROVIDERS))
        cursor.execute(
            f"""UPDATE users
                SET ai_provider = 'dashscope', ai_model = 'qwen-turbo'
                WHERE ai_provider IS NOT NULL
                  AND ai_provider NOT IN ({placeholders})""",
            SUPPORTED_PROVIDERS
        )
        if cursor.rowcount > 0:
            print(f"   ✅ 已将 {cursor.rowcount} 个用户的旧提供商配置重置为阿里百炼")
        else:
            print("   ⏭️  没有使用旧提供商的用户")

        conn.commit()
        print("✅ AI 提供商清理迁移完成")
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
