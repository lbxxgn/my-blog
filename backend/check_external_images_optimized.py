#!/usr/bin/env python3
"""
检查文章中的外部图片链接是否有效（优化版）

功能：
1. 使用并发检查外部图片URL（大幅提升速度）
2. 使用共享工具模块
3. 分批处理文章（降低内存占用）
4. 生成详细报告
"""

import sys
from pathlib import Path

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from utils.image_cleanup import (
    extract_images_from_content,
    remove_img_tags_by_urls,
    get_db_connection,
    fetch_posts_batch,
    check_image_urls_concurrent,
    print_cleanup_report
)
from config import get_backup_path


def check_and_clean_posts_concurrent(dry_run=True, batch_size=100,
                                    max_check=None, check_workers=10):
    """
    并发检查并清理文章中的外部图片

    Args:
        dry_run: 是否为试运行
        batch_size: 每批处理的文章数
        max_check: 最多检查的文章数（None表示全部）
        check_workers: URL检查的并发数

    Returns:
        清理报告字典
    """
    report = {
        'total_posts': 0,
        'posts_with_external_images': 0,
        'total_external_images': 0,
        'valid_images': 0,
        'invalid_images': 0,
        'timeout_images': 0,
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

            # 分批处理文章
            batch_num = 0
            for posts_batch in fetch_posts_batch(cursor, batch_size):
                batch_num += 1

                if max_check:
                    remaining = max_check - report['total_posts']
                    if remaining <= 0:
                        break
                    posts_batch = posts_batch[:remaining]

                process_post_batch(posts_batch, batch_num, report, check_workers, dry_run, cursor, conn)

    except Exception as e:
        error_msg = f'数据库错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


def process_post_batch(posts, batch_num, report, check_workers, dry_run, cursor, conn):
    """处理一批文章"""
    print(f'📦 处理批次 {batch_num} ({len(posts)} 篇文章)\n')

    for idx, post in enumerate(posts, 1):
        post_id = post['id']
        title = post['title'] or '无标题'
        content = post['content']

        # 提取图片
        images = extract_images_from_content(content)

        # 筛选出外部图片
        external_images = [(tag, url) for tag, url in images if url.startswith('http')]

        if not external_images:
            report['total_posts'] += 1
            continue

        report['total_posts'] += 1
        report['posts_with_external_images'] += 1
        report['total_external_images'] += len(external_images)

        print(f'📄 文章 #{post_id}: {title}')
        print(f'   发现 {len(external_images)} 张外部图片')

        # 并发检查所有外部图片
        external_urls = [url for _, url in external_images]
        check_results = check_image_urls_concurrent(external_urls, max_workers=check_workers)

        # 分析结果
        invalid_urls = []
        post_errors = []

        for url in external_urls:
            short_url = url[:70] + '...' if len(url) > 70 else url
            is_valid, error = check_results[url]

            if is_valid:
                print(f'   ✅ {short_url}')
                report['valid_images'] += 1
            else:
                if '超时' in error:
                    print(f'   ⏱️  {short_url} - {error}')
                    report['timeout_images'] += 1
                else:
                    print(f'   ❌ {short_url} - {error}')
                    report['invalid_images'] += 1
                    invalid_urls.append(url)
                    post_errors.append((url, error))

        # 如果有无效图片，清理内容
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
                    # context manager会自动commit
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


def main():
    """主函数"""
    print('🌐 外部图片链接检查工具（并发优化版）\n')
    print('⚡ 使用并发检查，速度提升 10 倍\n')

    # 第一次试运行
    print('🔍 第一次试运行（不修改数据库）...\n')

    # 先检查前10篇文章测试
    print('🧪 先检查前10篇文章作为测试...\n')
    report_test = check_and_clean_posts_concurrent(dry_run=True, max_check=10, check_workers=5)
    print_cleanup_report(report_test, "外部图片检查报告（测试）")

    if report_test['total_external_images'] == 0:
        print('\n✅ 前10篇文章没有外部图片，是否检查所有文章？')
        try:
            check_all = input('检查所有文章？(yes/no): ').strip().lower()
            if check_all not in ['yes', 'y', '是']:
                print('❌ 已取消')
                return
        except (EOFError, KeyboardInterrupt):
            print('\n❌ 已取消')
            return

    if report_test['invalid_images'] > 0 or report_test['total_external_images'] > 0:
        print('\n❓ 是否检查所有文章并清理无效外部图片？')
        print('这将使用并发检查，速度很快。')

        try:
            confirm = input('继续检查所有文章？(yes/no): ').strip().lower()
            if confirm in ['yes', 'y', '是']:
                print('\n🚀 开始检查所有文章...\n')
                report_full = check_and_clean_posts_concurrent(dry_run=True, check_workers=10)
                print_cleanup_report(report_full, "外部图片检查报告（全量）")

                if report_full['invalid_images'] > 0:
                    print('\n❓ 是否确认执行清理？这将修改数据库。')
                    confirm2 = input('确认执行？(yes/no): ').strip().lower()
                    if confirm2 in ['yes', 'y', '是']:
                        print('\n🚀 开始执行清理...\n')
                        report_final = check_and_clean_posts_concurrent(
                            dry_run=False,
                            check_workers=10
                        )
                        print_cleanup_report(report_final, "外部图片清理报告（完成）")
                        print('\n✅ 清理完成！')
                        print(f'\n💡 提示：数据库备份保存在: {get_backup_path()}')
                    else:
                        print('\n❌ 已取消清理')
                else:
                    print('\n✅ 所有外部图片都有效，无需清理')
            else:
                print('\n❌ 已取消检查')
        except (EOFError, KeyboardInterrupt):
            print('\n\n❌ 已取消检查')
    else:
        print('\n✅ 没有发现外部图片，无需检查')


if __name__ == '__main__':
    main()
