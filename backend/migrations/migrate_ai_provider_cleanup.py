"""
AI 提供商清理迁移
- 为 users 表添加 ai_base_url 字段（自定义 OpenAI 兼容提供商使用）
- 将已移除的旧提供商（openai/volcengine/volcengine_codingplan/zhipu_codingplan 等）
  重置为默认的阿里百炼（dashscope / qwen-turbo）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.migrations._utils import db_path, run_cli, transaction
from backend.utils.sqlite_schema import add_columns_if_missing

SUPPORTED_PROVIDERS = ('dashscope', 'deepseek', 'custom')


def migrate():
    path = db_path()
    if not path.exists():
        raise RuntimeError(f'数据库文件不存在: {path}')

    with transaction(path) as conn:
        # 1. 为 users 表添加 ai_base_url 字段
        if add_columns_if_missing(conn, 'users', [('ai_base_url', 'TEXT')]):
            print("   ✅ 添加字段: ai_base_url")
        else:
            print("   ⏭️  字段已存在，跳过: ai_base_url")

        # 2. 重置已移除的旧提供商配置
        placeholders = ','.join('?' * len(SUPPORTED_PROVIDERS))
        cursor = conn.execute(
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

    print("✅ AI 提供商清理迁移完成")
    return True


if __name__ == '__main__':
    sys.exit(run_cli(migrate, 'AI 提供商清理 - 数据库迁移'))
