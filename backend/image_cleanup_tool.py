#!/usr/bin/env python3
"""
统一的图片清理工具

整合了之前分散的多个清理脚本功能：
- clean_invalid_images.py (完整版，支持本地和外部检查)
- clean_invalid_images_simple.py (简化版，只检查本地)
- fast_clean_invalid_images.py (快速清理已知失效域名)
- check_external_images.py (检查外部图片)
- check_external_images_advanced.py (高级检查)
- check_external_images_optimized.py (优化检查)

使用方法：
    python backend/image_cleanup_tool.py --help
"""

import sys
import argparse
from pathlib import Path

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from utils.image_cleanup import (
    extract_images_from_content,
    remove_img_tags_by_urls,
    check_image_url,
    check_image_urls_with_progress,
    get_db_connection,
    print_cleanup_report,
    CleanupLogger
)
from backend.config import get_backup_path


def clean_local_images(dry_run=True):
    """
    只检查本地图片文件（简化版）

    扫描文章中的本地图片URL，删除指向不存在文件的图片标签
    """
    report = {
        'total_posts': 0,
        'posts_with_images': 0,
        'total_images': 0,
        'valid_images': 0,
        'invalid_images': 0,
        'cleaned_posts': 0,
        'errors': [],
        'details': []
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

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

            images = extract_images_from_content(content)

            if not images:
                continue

            report['posts_with_images'] += 1
            report['total_images'] += len(images)

            CleanupLogger.post(post_id, title)
            print(f'   发现 {len(images)} 张图片')

            invalid_urls = []
            post_errors = []

            for img_tag, url in images:
                # 只检查本地路径
                if not url.startswith('/'):
                    report['valid_images'] += 1
                    continue

                is_valid, error = check_image_url(url, check_external=False)

                if is_valid:
                    CleanupLogger.success(url)
                    report['valid_images'] += 1
                else:
                    CleanupLogger.error(f'{url} - {error}')
                    report['invalid_images'] += 1
                    invalid_urls.append(url)
                    post_errors.append((url, error))

            if invalid_urls:
                original_length = len(content)
                cleaned_content = remove_img_tags_by_urls(content, invalid_urls)
                cleaned_length = len(cleaned_content)

                CleanupLogger.removed(len(invalid_urls), original_length, cleaned_length)

                report['details'].append({
                    'post_id': post_id,
                    'title': title,
                    'invalid_count': len(invalid_urls),
                    'invalid_urls': invalid_urls,
                    'errors': post_errors
                })

                if not dry_run:
                    try:
                        cursor.execute(
                            'UPDATE posts SET content = ? WHERE id = ?',
                            (cleaned_content, post_id)
                        )
                        conn.commit()
                        report['cleaned_posts'] += 1
                        CleanupLogger.saved()
                    except Exception as e:
                        error_msg = f'更新失败: {str(e)}'
                        CleanupLogger.error(error_msg)
                        report['errors'].append({'post_id': post_id, 'error': error_msg})

            print()

        conn.close()

    except Exception as e:
        error_msg = f'数据库错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


def clean_all_images(dry_run=True, check_external=True):
    """
    完整清理（支持本地和外部图片检查）

    扫描文章中的所有图片URL，检查每个URL是否可访问，
    删除无效的图片标签
    """
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
        conn = get_db_connection()
        cursor = conn.cursor()

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

            images = extract_images_from_content(content)

            if not images:
                continue

            report['posts_with_images'] += 1
            report['total_images'] += len(images)

            CleanupLogger.post(post_id, title)
            print(f'   发现 {len(images)} 张图片')

            invalid_urls = []
            post_errors = []

            for img_tag, url in images:
                is_external = url.startswith('http') and not url.startswith(('http://localhost', 'http://127.0.0.1'))

                if is_external and not check_external:
                    print(f'   ⏭️  跳过外部链接: {url}')
                    report['external_skipped'] += 1
                    continue

                is_valid, error = check_image_url(url, check_external=check_external)

                if is_valid:
                    CleanupLogger.success(url)
                    report['valid_images'] += 1
                else:
                    CleanupLogger.error(f'{url} - {error}')
                    report['invalid_images'] += 1
                    invalid_urls.append(url)
                    post_errors.append((url, error))

            if invalid_urls:
                original_length = len(content)
                cleaned_content = remove_img_tags_by_urls(content, invalid_urls)
                cleaned_length = len(cleaned_content)

                CleanupLogger.removed(len(invalid_urls), original_length, cleaned_length)

                report['details'].append({
                    'post_id': post_id,
                    'title': title,
                    'invalid_count': len(invalid_urls),
                    'invalid_urls': invalid_urls,
                    'errors': post_errors
                })

                if not dry_run:
                    try:
                        cursor.execute(
                            'UPDATE posts SET content = ? WHERE id = ?',
                            (cleaned_content, post_id)
                        )
                        conn.commit()
                        report['cleaned_posts'] += 1
                        CleanupLogger.saved()
                    except Exception as e:
                        error_msg = f'更新失败: {str(e)}'
                        CleanupLogger.error(error_msg)
                        report['errors'].append({'post_id': post_id, 'error': error_msg})

            print()

        conn.close()

    except Exception as e:
        error_msg = f'数据库错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


def fast_clean_invalid_domains():
    """
    快速清理已知失效的域名图片

    不检查URL有效性，直接删除已知的失效域名图片：
    - 126.net (网易博客，基本都失效)
    - blog.163.com (也经常失效)
    """
    import re
    report = {
        'total_posts': 0,
        'cleaned_posts': 0,
        'total_removed': 0,
        'errors': []
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, content
            FROM posts
            WHERE content IS NOT NULL AND content != ''
            ORDER BY id
        ''')

        posts = cursor.fetchall()
        report['total_posts'] = len(posts)

        print(f'📊 开始快速清理 {len(posts)} 篇文章中的失效外部图片...\n')
        print('🎯 目标域名: 126.net, blog.163.com\n')

        for post in posts:
            post_id = post['id']
            title = post['title'] or '无标题'
            content = post['content']

            original_length = len(content)
            has_invalid_images = False

            # 删除 126.net 的图片
            if '126.net' in content:
                pattern_126 = r'<img[^>]*src=["\'][^"\']*126\.net[^"\']*["\'][^>]*>'
                matches_126 = re.findall(pattern_126, content, re.IGNORECASE)
                if matches_126:
                    content = re.sub(pattern_126, '', content, flags=re.IGNORECASE)
                    has_invalid_images = True
                    CleanupLogger.info(f'删除了 {len(matches_126)} 个 126.net 失效图片')

            # 删除 blog.163.com 的图片
            if 'blog.163.com' in content:
                pattern_163 = r'<img[^>]*src=["\'][^"\']*blog\.163\.com[^"\']*["\'][^>]*>'
                matches_163 = re.findall(pattern_163, content, flags=re.IGNORECASE)
                if matches_163:
                    content = re.sub(pattern_163, '', content, flags=re.IGNORECASE)
                    if not has_invalid_images:
                        CleanupLogger.info(f'删除了 {len(matches_163)} 个 blog.163.com 失效图片')
                    has_invalid_images = True

            if has_invalid_images:
                cleaned_length = len(content)
                removed_count = original_length - cleaned_length

                if removed_count > 0:
                    try:
                        cursor.execute('UPDATE posts SET content = ? WHERE id = ?',
                                     (content, post_id))
                        conn.commit()
                        report['cleaned_posts'] += 1
                        report['total_removed'] += len(matches_126) if matches_126 else 0
                        report['total_removed'] += len(matches_163) if matches_163 else 0
                        CleanupLogger.saved()
                        print(f'   (减少了 {removed_count} 字符)\n')
                    except Exception as e:
                        error_msg = f'更新失败: {str(e)}'
                        CleanupLogger.error(error_msg)
                        report['errors'].append({'post_id': post_id, 'error': error_msg})

        conn.close()

    except Exception as e:
        error_msg = f'数据库错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


def check_external_images(show_progress=True):
    """
    检查所有外部图片URL的可访问性

    使用并发检查和缓存，大幅提升性能
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, title, content
        FROM posts
        WHERE content IS NOT NULL AND content != ''
        ORDER BY id
    ''')

    posts = cursor.fetchall()
    conn.close()

    # 收集所有外部图片URL
    external_urls = []
    for post in posts:
        images = extract_images_from_content(post['content'])
        for img_tag, url in images:
            if url.startswith('http') and not url.startswith(('http://localhost', 'http://127.0.0.1')):
                external_urls.append(url)

    if not external_urls:
        print('✅ 没有找到外部图片URL')
        return

    # 去重
    external_urls = list(set(external_urls))

    print(f'📊 找到 {len(external_urls)} 个唯一的外部图片URL')
    print(f'🔍 开始检查可访问性...\n')

    # 并发检查
    results = check_image_urls_with_progress(
        external_urls,
        show_progress=show_progress
    )

    # 统计结果
    valid_count = sum(1 for valid, _ in results.values() if valid)
    invalid_count = len(results) - valid_count

    print(f'\n{"="*60}')
    print(f'📊 外部图片检查报告')
    print(f'{"="*60}')
    print(f'总URL数: {len(results)}')
    print(f'✅ 有效: {valid_count}')
    print(f'❌ 无效: {invalid_count}')
    print(f'{"="*60}\n')

    # 显示无效URL
    invalid_urls = [(url, error) for url, (valid, error) in results.items() if not valid]
    if invalid_urls:
        print(f'❌ 无效URL列表（前20个）:')
        for url, error in invalid_urls[:20]:
            short_url = url[:60] + '...' if len(url) > 60 else url
            print(f'   - {short_url} ({error})')

        if len(invalid_urls) > 20:
            print(f'\n   ... 还有 {len(invalid_urls) - 20} 个无效URL')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='统一的图片清理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法：
  # 只检查本地图片（快速）
  python backend/image_cleanup_tool.py local --dry-run

  # 完整检查（包括外部URL）
  python backend/image_cleanup_tool.py all --dry-run

  # 快速清理已知失效域名
  python backend/image_cleanup_tool.py fast-clean

  # 检查外部图片可访问性
  python backend/image_cleanup_tool.py check-external

  # 执行清理（不试运行）
  python backend/image_cleanup_tool.py local --force
        '''
    )

    parser.add_argument(
        'mode',
        choices=['local', 'all', 'fast-clean', 'check-external'],
        help='操作模式'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='试运行模式（不实际修改数据库）'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='执行实际修改（取消试运行）'
    )

    parser.add_argument(
        '--check-external',
        action='store_true',
        help='检查外部URL（仅all模式有效）'
    )

    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='不显示进度条'
    )

    args = parser.parse_args()

    # 确定dry_run
    dry_run = args.dry_run and not args.force

    # 执行对应的模式
    if args.mode == 'local':
        print('🖼️  本地图片清理工具\n')
        print(f'{"="*60}')
        print(f'模式: 只检查本地图片文件')
        print(f'试运行: {"是 (使用 --force 执行实际修改)" if dry_run else "否"}')
        print(f'{"="*60}\n')

        report = clean_local_images(dry_run=dry_run)
        print_cleanup_report(report, "本地图片清理报告")

        if dry_run and report['invalid_images'] > 0:
            print('\n💡 提示：使用 --force 参数执行实际清理')

    elif args.mode == 'all':
        print('🖼️  完整图片清理工具\n')
        print(f'{"="*60}')
        print(f'模式: 检查本地和外部图片')
        print(f'试运行: {"是 (使用 --force 执行实际修改)" if dry_run else "否"}')
        print(f'检查外部: {"是" if args.check_external else "否"}')
        print(f'{"="*60}\n')

        report = clean_all_images(dry_run=dry_run, check_external=args.check_external)
        print_cleanup_report(report, "完整清理报告")

        if dry_run and report['invalid_images'] > 0:
            print('\n💡 提示：使用 --force 参数执行实际清理')

    elif args.mode == 'fast-clean':
        print('⚡ 快速清理失效外部图片\n')
        print(f'{"="*60}')
        print(f'目标: 126.net, blog.163.com')
        print(f'{"="*60}\n')

        report = fast_clean_invalid_domains()
        print_cleanup_report(report, "快速清理完成报告")

    elif args.mode == 'check-external':
        check_external_images(show_progress=not args.no_progress)

    print(f'\n💡 提示：数据库备份保存在: {get_backup_path()}')


if __name__ == '__main__':
    main()
