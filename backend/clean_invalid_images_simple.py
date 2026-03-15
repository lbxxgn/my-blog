#!/usr/bin/env python3
"""
清理文章中的无效图片链接（简化版）

功能：
1. 只检查本地图片文件（不检查外部URL）
2. 扫描所有文章内容中的图片链接
3. 删除指向不存在文件的图片标签
4. 生成清理报告
"""

import sys
import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config import DATABASE_URL


def check_local_image(url):
    """
    检查本地图片URL是否有效

    Args:
        url: 图片URL

    Returns:
        (is_valid, error_message)
    """
    try:
        # 处理相对路径
        if url.startswith('/'):
            # 这是本地路径，检查文件是否存在
            file_path = Path(__file__).parent.parent / 'static' / url.lstrip('/')
            if file_path.exists():
                return True, None
            else:
                return False, '文件不存在'

        # 跳过外部URL
        if url.startswith('http'):
            return False, '外部链接（跳过检查）'

        return False, '未知路径格式'

    except Exception as e:
        return False, f'检查错误: {str(e)}'


def extract_images_from_content(content):
    """
    从文章内容中提取所有图片标签

    Args:
        content: 文章HTML内容

    Returns:
        [(img_tag, url), ...] - 图片标签和URL的列表
    """
    if not content:
        return []

    # 匹配<img>标签
    pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    matches = re.findall(pattern, content, re.IGNORECASE)

    # 提取完整的img标签
    img_tags = re.findall(r'<img[^>]*src=["\'][^"\']+["\'][^>]*>', content, re.IGNORECASE)

    results = []
    for img_tag, url in zip(img_tags, matches):
        results.append((img_tag, url))

    return results


def remove_invalid_images(content, invalid_urls):
    """
    从内容中删除无效的图片标签

    Args:
        content: 文章HTML内容
        invalid_urls: 无效URL列表

    Returns:
        清理后的内容
    """
    cleaned_content = content

    for url in invalid_urls:
        # 转义正则表达式特殊字符
        escaped_url = re.escape(url)

        # 匹配并删除整个img标签
        pattern = r'<img[^>]*src=["\']' + escaped_url + r'["\'][^>]*>'
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE)

    return cleaned_content


def clean_post_images(dry_run=True):
    """
    清理文章中的无效图片

    Args:
        dry_run: 是否为试运行（不实际修改数据库）

    Returns:
        清理报告字典
    """
    # 解析数据库URL
    db_path = DATABASE_URL.replace('sqlite:///', '')

    report = {
        'total_posts': 0,
        'posts_with_images': 0,
        'total_images': 0,
        'valid_images': 0,
        'invalid_images': 0,
        'external_skipped': 0,
        'cleaned_posts': 0,
        'errors': [],
        'details': []
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

        print(f'📊 开始扫描 {len(posts)} 篇文章...\n')

        for post in posts:
            post_id = post['id']
            title = post['title'] or '无标题'
            content = post['content']

            # 提取图片
            images = extract_images_from_content(content)

            if not images:
                continue

            report['posts_with_images'] += 1
            report['total_images'] += len(images)

            print(f'📄 文章 #{post_id}: {title}')
            print(f'   发现 {len(images)} 张图片')

            invalid_urls = []
            post_errors = []

            for img_tag, url in images:
                # 检查URL
                is_valid, error = check_local_image(url)

                if is_valid:
                    print(f'   ✅ {url}')
                    report['valid_images'] += 1
                else:
                    if '外部链接' in error:
                        print(f'   ⏭️  {url} (外部链接，跳过)')
                        report['external_skipped'] += 1
                    else:
                        print(f'   ❌ {url} - {error}')
                        report['invalid_images'] += 1
                        invalid_urls.append(url)
                        post_errors.append((url, error))

            # 如果有无效图片，清理内容
            if invalid_urls:
                original_length = len(content)
                cleaned_content = remove_invalid_images(content, invalid_urls)
                cleaned_length = len(cleaned_content)

                print(f'   🧹 删除了 {len(invalid_urls)} 个无效图片标签')
                print(f'   📏 内容长度: {original_length} -> {cleaned_length}')

                # 记录详情
                report['details'].append({
                    'post_id': post_id,
                    'title': title,
                    'invalid_count': len(invalid_urls),
                    'invalid_urls': [url for url, _ in post_errors],
                    'errors': post_errors
                })

                # 如果不是试运行，更新数据库
                if not dry_run:
                    try:
                        cursor.execute('''
                            UPDATE posts
                            SET content = ?
                            WHERE id = ?
                        ''', (cleaned_content, post_id))
                        conn.commit()
                        report['cleaned_posts'] += 1
                        print(f'   💾 已更新数据库')
                    except Exception as e:
                        error_msg = f'更新失败: {str(e)}'
                        print(f'   ⚠️  {error_msg}')
                        report['errors'].append({
                            'post_id': post_id,
                            'error': error_msg
                        })

            print()  # 空行分隔

        conn.close()

    except Exception as e:
        error_msg = f'数据库错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


def print_report(report):
    """打印清理报告"""
    print('\n' + '='*60)
    print('📊 清理报告')
    print('='*60)
    print(f'总文章数: {report["total_posts"]}')
    print(f'包含图片的文章: {report["posts_with_images"]}')
    print(f'总图片数: {report["total_images"]}')
    print(f'✅ 有效图片: {report["valid_images"]}')
    print(f'❌ 无效图片: {report["invalid_images"]}')
    print(f'⏭️  跳过的外部链接: {report["external_skipped"]}')
    print(f'🧹 清理的文章数: {report["cleaned_posts"]}')

    if report['errors']:
        print(f'\n⚠️  错误: {len(report["errors"])}')
        for error in report['errors']:
            print(f'   - {error}')

    if report['details']:
        print(f'\n📋 详细清理列表:')
        for detail in report['details'][:10]:  # 只显示前10个
            print(f'\n   文章 #{detail["post_id"]}: {detail["title"]}')
            print(f'   删除了 {detail["invalid_count"]} 个无效图片')
            for url, error in detail['errors'][:3]:  # 每个文章只显示前3个错误
                print(f'      - {url[:60]}... ({error})')

        if len(report['details']) > 10:
            print(f'\n   ... 还有 {len(report["details"]) - 10} 篇文章')

    print('='*60)


def main():
    """主函数"""
    print('🖼️  文章图片清理工具（简化版 - 只检查本地图片）\n')

    # 第一次试运行
    print('🔍 第一次试运行（不修改数据库）...\n')
    report1 = clean_post_images(dry_run=True)
    print_report(report1)

    if report1['invalid_images'] > 0:
        print('\n❓ 是否确认执行清理？这将修改数据库。')
        print('无效图片将被永久删除。')

        try:
            confirm = input('确认执行？(yes/no): ').strip().lower()
            if confirm in ['yes', 'y', '是']:
                print('\n🚀 开始执行清理...\n')
                report2 = clean_post_images(dry_run=False)
                print_report(report2)
                print('\n✅ 清理完成！')
                print(f'\n💡 提示：数据库备份保存在: /Users/gn/simple-blog/db/simple_blog.db.backup.20260315_124428')
            else:
                print('\n❌ 已取消清理')
        except (EOFError, KeyboardInterrupt):
            print('\n\n❌ 已取消清理')
    else:
        print('\n✅ 没有发现无效图片，无需清理')


if __name__ == '__main__':
    main()
