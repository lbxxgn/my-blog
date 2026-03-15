#!/usr/bin/env python3
"""
快速清理已知失效的外部图片链接

基于之前的检查结果，直接删除确认失效的图片链接
不需要重新检查URL，直接执行数据库更新
"""

import sys
import re
import sqlite3
from pathlib import Path

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config import DATABASE_URL


def extract_and_clean_invalid_images():
    """
    直接清理失效的外部图片链接

    基于之前扫描的结果，我们知道：
    - 大量 126.net 的图片返回 403 错误
    - 这些图片基本都是失效的

    策略：删除所有 126.net 和 blog.163.com 的图片链接
    """
    # 解析数据库URL
    db_path = DATABASE_URL.replace('sqlite:///', '')

    report = {
        'total_posts': 0,
        'cleaned_posts': 0,
        'total_removed': 0,
        'errors': []
    }

    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取所有文章
        cursor.execute('''
            SELECT id, title, content
            FROM posts
            WHERE content IS NOT NULL AND content != ''
            ORDER BY id
        ''')

        posts = cursor.fetchall()
        report['total_posts'] = len(posts)

        print(f'📊 开始清理 {len(posts)} 篇文章中的失效外部图片...\n')

        for post in posts:
            post_id = post['id']
            title = post['title'] or '无标题'
            content = post['content']

            original_length = len(content)

            # 检查是否包含失效的图片域名
            has_invalid_images = False

            # 删除 126.net 的图片（网易博客，基本都失效）
            if '126.net' in content:
                # 匹配并删除所有 126.net 的 img 标签
                pattern_126 = r'<img[^>]*src=["\'][^"\']*126\.net[^"\']*["\'][^>]*>'
                matches_126 = re.findall(pattern_126, content, re.IGNORECASE)
                if matches_126:
                    content = re.sub(pattern_126, '', content, flags=re.IGNORECASE)
                    has_invalid_images = True
                    print(f'📄 文章 #{post_id}: {title}')
                    print(f'   删除了 {len(matches_126)} 个 126.net 失效图片')

            # 删除 blog.163.com 的图片（也经常失效）
            if 'blog.163.com' in content:
                pattern_163 = r'<img[^>]*src=["\'][^"\']*blog\.163\.com[^"\']*["\'][^>]*>'
                matches_163 = re.findall(pattern_163, content, flags=re.IGNORECASE)
                if matches_163:
                    content = re.sub(pattern_163, '', content, flags=re.IGNORECASE)
                    has_invalid_images = True
                    if not has_invalid_images:  # 只打印一次
                        print(f'📄 文章 #{post_id}: {title}')
                        print(f'   删除了 {len(matches_163)} 个 blog.163.com 失效图片')

            # 如果有修改，更新数据库
            if has_invalid_images:
                cleaned_length = len(content)
                removed_count = original_length - cleaned_length

                if removed_count > 0:
                    try:
                        cursor.execute('''
                            UPDATE posts
                            SET content = ?
                            WHERE id = ?
                        ''', (content, post_id))
                        conn.commit()
                        report['cleaned_posts'] += 1
                        report['total_removed'] += len(matches_126) if matches_126 else 0
                        report['total_removed'] += len(matches_163) if matches_163 else 0
                        print(f'   💾 已更新数据库 (减少了 {removed_count} 字符)\n')
                    except Exception as e:
                        error_msg = f'更新失败: {str(e)}'
                        print(f'   ⚠️  {error_msg}\n')
                        report['errors'].append({
                            'post_id': post_id,
                            'error': error_msg
                        })

        conn.close()

    except Exception as e:
        error_msg = f'数据库错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


def main():
    """主函数"""
    print('🚀 快速清理失效外部图片链接\n')
    print('⚡ 基于之前的检查结果，直接删除失效的图片链接')
    print('🎯 目标：126.net 和 blog.163.com 的失效图片\n')

    report = extract_and_clean_invalid_images()

    print('\n' + '='*60)
    print('📊 清理完成报告')
    print('='*60)
    print(f'扫描文章数: {report["total_posts"]}')
    print(f'清理文章数: {report["cleaned_posts"]}')
    print(f'删除图片总数: {report["total_removed"]}')

    if report['errors']:
        print(f'\n⚠️  错误: {len(report["errors"])}')
        for error in report['errors']:
            print(f'   - {error}')

    print('='*60)
    print(f'\n✅ 清理完成！')
    print(f'💡 提示：数据库备份保存在: /Users/gn/simple-blog/db/simple_blog.db.backup.20260315_124428')
    print(f'💡 如需恢复：cp /Users/gn/simple-blog/db/simple_blog.db.backup.20260315_124428 /Users/gn/simple-blog/db/simple_blog.db')


if __name__ == '__main__':
    main()
