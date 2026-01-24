#!/usr/bin/env python3
"""
修复数据库 FTS 触发器问题
请先停止 Flask 服务器，然后运行此脚本
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / 'db' / 'posts.db'

print("=" * 70)
print("修复数据库 FTS 触发器问题")
print("=" * 70)

if not DB_PATH.exists():
    print(f"错误: 数据库文件不存在: {DB_PATH}")
    sys.exit(1)

print(f"\n数据库路径: {DB_PATH}")
print("\n正在修复...")

try:
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    cursor = conn.cursor()

    # Drop all FTS triggers
    print("\n1. 删除 FTS 触发器...")
    cursor.execute('DROP TRIGGER IF EXISTS posts_ai')
    cursor.execute('DROP TRIGGER IF EXISTS posts_ad')
    cursor.execute('DROP TRIGGER IF EXISTS posts_au')
    print("   ✓ 已删除所有 FTS 触发器")

    # Rebuild FTS index
    print("\n2. 重建 FTS 索引...")
    cursor.execute('DELETE FROM posts_fts')
    cursor.execute('INSERT INTO posts_fts(rowid, title, content) SELECT id, title, content FROM posts')
    print("   ✓ FTS 索引已重建")

    # Verify
    cursor.execute('SELECT COUNT(*) FROM posts')
    posts_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM posts_fts')
    fts_count = cursor.fetchone()[0]
    print(f"\n   Posts: {posts_count}, FTS entries: {fts_count}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 70)
    print("✓ 修复完成！")
    print("=" * 70)
    print("\n现在可以启动 Flask 服务器：")
    print("  cd /Users/gn/simple-blog/backend")
    print("  python3 app.py")

except Exception as e:
    print(f"\n✗ 修复失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
