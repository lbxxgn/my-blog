#!/usr/bin/env python3
"""
为现有图片生成feed尺寸
"""

import sys
import os
from pathlib import Path

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from image_processor import generate_image_sizes
from models import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_feed_for_existing_images():
    """为所有现有图片生成feed尺寸"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取所有已优化的图片记录
    cursor.execute('''
        SELECT original_path, feed_path
        FROM optimized_images
        WHERE status = 'completed'
        ORDER BY id
    ''')

    images = cursor.fetchall()
    total = len(images)
    logger.info(f'找到 {total} 张已优化的图片')

    generated = 0
    skipped = 0
    errors = 0

    for i, (original_path, feed_path) in enumerate(images, 1):
        print(f'\n[{i}/{total}] 处理: {Path(original_path).name}')

        # 检查是否已存在feed尺寸
        if feed_path and os.path.exists(feed_path):
            print(f'   ✓ 已存在feed尺寸')
            skipped += 1
            continue

        # 检查原图是否存在
        if not os.path.exists(original_path):
            print(f'   ⚠ 原图不存在: {original_path}')
            errors += 1
            continue

        try:
            # 生成feed尺寸
            output_dir = Path(original_path).parent.parent / 'optimized'
            sizes = generate_image_sizes(original_path, str(output_dir))

            if sizes.get('feed') and os.path.exists(sizes['feed']):
                # 更新数据库
                cursor.execute('''
                    UPDATE optimized_images
                    SET feed_path = ?
                    WHERE original_path = ?
                ''', (sizes['feed'], original_path))
                conn.commit()

                file_size = os.path.getsize(sizes['feed']) / 1024  # KB
                print(f'   ✓ 已生成feed尺寸: {Path(sizes["feed"]).name} ({file_size:.1f} KB)')
                generated += 1
            else:
                print(f'   ✗ 生成失败')
                errors += 1

        except Exception as e:
            print(f'   ✗ 错误: {e}')
            errors += 1

    conn.close()

    print(f'\n{"="*60}')
    print(f'完成！')
    print(f'生成: {generated} 张')
    print(f'跳过: {skipped} 张')
    print(f'错误: {errors} 张')
    print(f'{"="*60}')


if __name__ == '__main__':
    print('🖼️  为现有图片生成feed尺寸\n')
    generate_feed_for_existing_images()
