"""
版本化数据库迁移运行器

通过 `schema_migrations` 表跟踪已应用的迁移，避免重复执行；
新迁移只需在 MIGRATIONS 注册表中追加一项。

使用方式：
    python -m backend.migrations          # 应用所有待执行迁移
    python -m backend.migrations status   # 查看迁移状态

注册新迁移：
    1. 在本目录新建 migrate_xxx.py，提供 migrate() 函数（必须幂等）
    2. 在下方 MIGRATIONS 末尾追加 (version, 描述, 模块名, 函数名)
"""
import importlib
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config

# (version, 描述, 模块名, 入口函数名) —— 只追加，勿修改已有条目
MIGRATIONS = [
    ('001_multiauthor', '用户表多作者字段', 'backend.migrations.migrate_multiauthor', 'migrate_database'),
    ('002_knowledge_base', '知识库独立空间与树形分类', 'backend.migrations.migrate_knowledge_base', 'migrate'),
    ('003_drafts', '草稿同步表', 'backend.migrations.migrate_drafts', 'migrate'),
    ('004_image_optimization', '图片优化记录表', 'backend.migrations.migrate_image_optimization', 'migrate'),
    ('005_ai_features', 'AI 配置与历史表', 'backend.migrations.migrate_ai_features', 'migrate_database'),
    ('006_access_control', '文章访问控制字段', 'backend.migrations.migrate_add_access_control', 'migrate'),
    ('007_add_post_type', '文章类型字段', 'backend.migrations.migrate_add_post_type', 'migrate'),
]


def get_db_path():
    return config.DATABASE_URL.replace('sqlite:///', '')


def ensure_migrations_table(conn):
    """创建迁移版本记录表"""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()


def get_applied_versions(conn):
    ensure_migrations_table(conn)
    rows = conn.execute('SELECT version FROM schema_migrations').fetchall()
    return {row[0] for row in rows}


def apply_migrations(verbose=True):
    """应用所有未执行的迁移，返回 (成功数, 跳过数, 失败列表)"""
    conn = sqlite3.connect(get_db_path())
    try:
        applied = get_applied_versions(conn)
        done = skipped = 0
        failed = []

        for version, description, module_name, func_name in MIGRATIONS:
            if version in applied:
                if verbose:
                    print(f"⏭️  {version} {description}（已应用，跳过）")
                skipped += 1
                continue

            if verbose:
                print(f"▶️  {version} {description}...")
            try:
                module = importlib.import_module(module_name)
                getattr(module, func_name)()
                conn.execute(
                    'INSERT INTO schema_migrations (version) VALUES (?)',
                    (version,))
                conn.commit()
                done += 1
            except Exception as e:
                conn.rollback()
                failed.append((version, str(e)))
                print(f"❌ {version} 迁移失败: {e}")
                break  # 后续迁移可能依赖前一个，失败即停止

        if verbose:
            print(f"\n迁移完成: 新应用 {done} 个，跳过 {skipped} 个" +
                  (f"，失败 {len(failed)} 个" if failed else ""))
        return done, skipped, failed
    finally:
        conn.close()


def print_status():
    """打印迁移状态"""
    conn = sqlite3.connect(get_db_path())
    try:
        applied = get_applied_versions(conn)
        for version, description, _, _ in MIGRATIONS:
            mark = '✅' if version in applied else '⬜'
            print(f"{mark} {version} {description}")
    finally:
        conn.close()
