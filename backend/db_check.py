#!/usr/bin/env python
"""
数据库诊断和修复工具
"""
import sqlite3
import shutil
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / 'db' / 'posts.db'

def check_database():
    """检查数据库完整性"""
    print("=" * 60)
    print("数据库诊断工具")
    print("=" * 60)
    print(f"数据库路径: {DB_PATH}")
    print(f"文件大小: {DB_PATH.stat().st_size / 1024:.2f} KB")
    print()

    if not DB_PATH.exists():
        print("❌ 数据库文件不存在")
        return False

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # 检查完整性
        print("1. 检查数据库完整性...")
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] == 'ok':
            print("   ✓ 数据库结构完整")
        else:
            print(f"   ❌ 数据库损坏: {result[0]}")
            return False

        # 检查外键
        print("\n2. 检查外键约束...")
        cursor.execute("PRAGMA foreign_key_check")
        result = cursor.fetchone()
        if result is None:
            print("   ✓ 外键约束正常")
        else:
            print(f"   ❌ 外键约束错误: {result}")

        # 检查表
        print("\n3. 数据表列表...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            if not table.startswith('sqlite_'):
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   - {table}: {count} 条记录")

        # 检查索引
        print("\n4. 索引列表...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        indexes = [row[0] for row in cursor.fetchall()]
        for index in indexes:
            print(f"   - {index}")

        conn.close()
        print("\n✓ 数据库状态良好")
        return True

    except sqlite3.Error as e:
        print(f"\n❌ 数据库错误: {e}")
        return False

def backup_database():
    """备份数据库"""
    print("\n创建备份...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DB_PATH.parent / f'posts.db.backup.{timestamp}'
    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ 备份已创建: {backup_path}")

def vacuum_database():
    """优化数据库"""
    print("\n优化数据库 (VACUUM)...")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute('VACUUM')
        conn.close()
        print("✓ 数据库已优化")
    except sqlite3.Error as e:
        print(f"❌ 优化失败: {e}")

def reindex_database():
    """重建索引"""
    print("\n重建索引...")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute('REINDEX')
        conn.close()
        print("✓ 索引已重建")
    except sqlite3.Error as e:
        print(f"❌ 重建失败: {e}")

def fix_database():
    """尝试修复损坏的数据库"""
    print("\n" + "=" * 60)
    print("尝试修复数据库...")
    print("=" * 60)

    # 先备份
    backup_database()

    # 执行修复
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute('PRAGMA integrity_check')

        # 导出数据
        print("\n导出数据...")
        with open(DB_PATH.parent / 'dump.sql', 'w') as f:
            for line in conn.iterdump():
                f.write('%s\n' % line)
        conn.close()
        print("✓ 数据已导出到 dump.sql")

        # 重建数据库
        print("\n重建数据库...")
        new_db_path = DB_PATH.parent / 'posts.db.new'
        new_conn = sqlite3.connect(str(new_db_path))
        with open(DB_PATH.parent / 'dump.sql', 'r') as f:
            sql = f.read()
            new_conn.executescript(sql)
        new_conn.close()

        # 替换旧数据库
        shutil.move(DB_PATH, DB_PATH.parent / 'posts.db.old')
        shutil.move(str(new_db_path), DB_PATH)
        print("✓ 数据库已重建")

        # 清理临时文件
        os.remove(DB_PATH.parent / 'dump.sql')
        print("✓ 临时文件已清理")

        # 验证修复结果
        return check_database()

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'check':
            check_database()
        elif command == 'backup':
            backup_database()
        elif command == 'vacuum':
            backup_database()
            vacuum_database()
        elif command == 'fix':
            reindex_database()
            vacuum_database()
        elif command == 'rebuild':
            fix_database()
        else:
            print("用法: python db_check.py [check|backup|vacuum|fix|rebuild]")
    else:
        # 默认执行检查
        if check_database():
            print("\n建议:")
            print("1. 定期运行 'python db_check.py vacuum' 优化数据库")
            print("2. 如果出现错误，运行 'python db_check.py rebuild' 重建数据库")
        else:
            print("\n数据库存在问题！")
            print("运行 'python db_check.py rebuild' 尝试修复")
