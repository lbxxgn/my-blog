#!/usr/bin/env python3
"""
添加feed_size支持到数据库
"""

import sys
import sqlite3
from pathlib import Path

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config import DATABASE_URL


def add_feed_size_column():
    """为optimized_images表添加feed_path列"""
    db_path = DATABASE_URL.replace('sqlite:///', '')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查列是否已存在
        cursor.execute('''
            SELECT count(*) FROM pragma_table_info('optimized_images')
            WHERE name='feed_path'
        ''')
        exists = cursor.fetchone()[0] > 0

        if exists:
            print('✓ feed_path 列已存在')
            return

        # 添加列
        print('添加 feed_path 列...')
        cursor.execute('''
            ALTER TABLE optimized_images
            ADD COLUMN feed_path TEXT
        ''')

        conn.commit()
        print('✓ 成功添加 feed_path 列')

    except Exception as e:
        print(f'✗ 错误: {e}')
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    print('🔄 添加feed_size支持\n')
    add_feed_size_column()
