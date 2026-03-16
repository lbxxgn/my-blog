#!/usr/bin/env python3
"""
清理文章中的无效图片链接（优化版）

功能：
1. 扫描所有文章内容中的图片URL
2. 检查每个URL是否可访问
3. 删除无效的图片标签
4. 生成清理报告
"""

import sys
from pathlib import Path

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from utils.image_cleanup import (
    extract_images_from_content,
    remove_img_tags_by_urls,
    check_image_url,
    get_db_connection,
    print_cleanup_report
)
from config import get_backup_path
from models import get_db_context


def clean_post_images(dry_run=True, check_external=True):
    """
    清理文章中的无效图片（优化版）

    Args:
        dry_run: 是否为试运行（不实际修改数据库）
        check_external: 是否检查外部URL

    Returns:
        清理报告字典
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
        # 使用context manager自动管理连接
        with get_db_context() as conn:
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
                    # 跳过外部URL检查（如果配置不检查）
                    is_external = url.startswith('http') and not url.startswith(f'http://localhost') and not url.startswith(f'http://127.0.0.1')

                    if is_external and not check_external:
                        print(f'   ⏭️  跳过外部链接: {url}')
                        report['external_skipped'] += 1
                        continue

                    # 检查URL
                    is_valid, error = check_image_url(url)

                    if is_valid:
                        print(f'   ✅ {url}')
                        report['valid_images'] += 1
                    else:
                        print(f'   ❌ {url} - {error}')
                        report['invalid_images'] += 1
                        invalid_urls.append(url)
                        post_errors.append((url, error))

                # 如果有无效图片，使用优化的删除函数
                if invalid_urls:
                    original_length = len(content)
                    cleaned_content = remove_img_tags_by_urls(content, invalid_urls)
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
                            cursor.execute(
                                'UPDATE posts SET content = ? WHERE id = ?',
                                (cleaned_content, post_id)
                            )
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

    except Exception as e:
        error_msg = f'数据库错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


    print_cleanup_report(report1, "清理报告（试运行）")

    if report1['invalid_images'] > 0:
        print('\n❓ 是否确认执行清理？这将修改数据库。')
        try:
            confirm = input('确认执行？(yes/no): ').strip().lower()
            if confirm in ['yes', 'y', '是']:
                print('\n🚀 开始执行清理...\n')
                report2 = clean_post_images(dry_run=False, check_external=check_external)
                print_cleanup_report(report2, "清理报告（完成）")
                print('\n✅ 清理完成！')
                print(f'\n💡 提示：数据库备份保存在: {get_backup_path()}')
            else:
                print('\n❌ 已取消清理')
        except (EOFError, KeyboardInterrupt):
            print('\n\n❌ 已取消清理')
    else:
        print('\n✅ 没有发现无效图片，无需清理')


def main():
    """主函数"""
    print('🖼️  文章图片清理工具\n')

    # 询问是否检查外部链接
    print('是否检查外部图片链接？')
    print('1. 只检查本地图片（快速）')
    print('2. 检查所有图片包括外部链接（较慢）')

    try:
        choice = input('请选择 (1/2, 默认1): ').strip() or '1'
        check_external = choice == '2'
    except (EOFError, KeyboardInterrupt):
        check_external = False
        print('1')  # 默认选项

    # 第一次试运行
    print('\n🔍 第一次试运行（不修改数据库）...\n')
    report1 = clean_post_images(dry_run=True, check_external=check_external)
    print_cleanup_report(report1, "清理报告（试运行）")

    if report1['invalid_images'] > 0:
        print('\n❓ 是否确认执行清理？这将修改数据库。')
        try:
            confirm = input('确认执行？(yes/no): ').strip().lower()
            if confirm in ['yes', 'y', '是']:
                print('\n🚀 开始执行清理...\n')
                report2 = clean_post_images(dry_run=False, check_external=check_external)
                print_cleanup_report(report2, "清理报告（完成）")
                print('\n✅ 清理完成！')
                print(f'\n💡 提示：数据库备份保存在: {get_backup_path()}')
            else:
                print('\n❌ 已取消清理')
        except (EOFError, KeyboardInterrupt):
            print('\n\n❌ 已取消清理')
    else:
        print('\n✅ 没有发现无效图片，无需清理')


if __name__ == '__main__':
    main()
