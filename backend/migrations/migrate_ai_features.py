"""
AI功能数据库迁移脚本
- 为users表添加AI配置字段
- 添加ai_tag_history历史记录表（可选）
"""
import sqlite3
import shutil
from pathlib import Path


def migrate_database():
    # 数据库路径
    db_path = Path(__file__).parent.parent.parent / 'db' / 'simple_blog.db'

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 启用外键约束
        cursor.execute('PRAGMA foreign_keys = ON')

        # 1. 备份当前数据库
        print("📦 创建数据库备份...")
        backup_path = str(db_path).replace('.db', '_backup_before_ai_features.db')
        shutil.copy2(str(db_path), backup_path)
        print(f"   ✅ 备份创建成功: {backup_path}")

        # 2. 为users表添加AI配置字段
        print("\n📊 迁移users表（添加AI配置字段）...")

        ai_fields = [
            ('ai_tag_generation_enabled', 'BOOLEAN DEFAULT 1'),
            ('ai_provider', 'TEXT DEFAULT "openai"'),
            ('ai_api_key', 'TEXT'),
            ('ai_model', 'TEXT DEFAULT "gpt-3.5-turbo"'),
        ]

        for field_name, field_def in ai_fields:
            try:
                # 对于时间戳字段，不使用DEFAULT
                if 'TIMESTAMP' in field_def and 'CURRENT_TIMESTAMP' in field_def:
                    sql = f'ALTER TABLE users ADD COLUMN {field_name} TIMESTAMP'
                else:
                    sql = f'ALTER TABLE users ADD COLUMN {field_name} {field_def}'
                cursor.execute(sql)
                print(f"   ✅ 添加字段: {field_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e).lower():
                    print(f"   ⏭️  字段已存在，跳过: {field_name}")
                else:
                    raise

        # 3. 创建ai_tag_history表（可选功能）
        print("\n📊 创建ai_tag_history表...")
        create_history_table = """
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
        );
        """

        try:
            cursor.execute(create_history_table)
            print("   ✅ 创建表: ai_tag_history")
        except sqlite3.OperationalError as e:
            print(f"   ⏭️  表已存在: ai_tag_history")

        # 3.5. 添加currency列到ai_tag_history表（如果不存在）
        print("\n📊 添加currency列到ai_tag_history表...")
        try:
            cursor.execute('ALTER TABLE ai_tag_history ADD COLUMN currency TEXT DEFAULT "USD"')
            print("   ✅ 添加字段: currency")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print(f"   ⏭️  字段已存在，跳过: currency")
            else:
                raise

        # 4. 创建索引
        print("\n🔍 创建索引...")
        indexes = [
            ('idx_ai_history_post', 'CREATE INDEX IF NOT EXISTS idx_ai_history_post ON ai_tag_history(post_id)'),
            ('idx_ai_history_user', 'CREATE INDEX IF NOT EXISTS idx_ai_history_user ON ai_tag_history(user_id)'),
            ('idx_ai_history_created', 'CREATE INDEX IF NOT EXISTS idx_ai_history_created ON ai_tag_history(created_at DESC)'),
        ]

        for index_name, sql in indexes:
            try:
                cursor.execute(sql)
                print(f"   ✅ 创建索引: {index_name}")
            except sqlite3.OperationalError:
                print(f"   ⏭️  索引已存在: {index_name}")

        # 5. 为现有用户设置默认AI配置
        print("\n⚙️  为现有用户设置默认AI配置...")
        cursor.execute('UPDATE users SET ai_tag_generation_enabled = 1 WHERE ai_tag_generation_enabled IS NULL')
        cursor.execute('UPDATE users SET ai_provider = "openai" WHERE ai_provider IS NULL')
        cursor.execute('UPDATE users SET ai_model = "gpt-3.5-turbo" WHERE ai_model IS NULL')
        print("   ✅ 默认AI配置已设置")

        conn.commit()
        print("\n" + "="*50)
        print("✅ AI功能迁移完成！")
        print(f"   数据库: {db_path}")
        print(f"   备份: {backup_path}")
        print("="*50)
        print("\n📝 新增字段:")
        print("   - users.ai_tag_generation_enabled: 是否启用AI标签生成")
        print("   - users.ai_provider: LLM提供商 (openai/claude/qwen)")
        print("   - users.ai_api_key: API密钥（加密存储）")
        print("   - users.ai_model: 使用的模型名称")
        print("\n📝 新增表:")
        print("   - ai_tag_history: AI标签生成历史记录")
        print("\n⚠️  下一步:")
        print("   1. 更新 requirements.txt 添加 openai 依赖")
        print("   2. 在用户设置页面配置AI功能")
        print("="*50)
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        print("   数据库已回滚到迁移前的状态")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    print("="*50)
    print("AI功能 - 数据库迁移")
    print("="*50)
    success = migrate_database()
    exit(0 if success else 1)
