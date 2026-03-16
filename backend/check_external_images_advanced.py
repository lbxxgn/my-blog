#!/usr/bin/env python3
"""
高级外部图片检查工具

功能：
1. 带进度条的并发检查
2. URL检查结果缓存（避免重复检查）
3. 分批处理文章
4. 详细的统计信息
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
    check_image_urls_with_progress,
    print_cleanup_report,
    URLCheckCache
)
from config import get_backup_path
from models import get_db_context


def check_and_clean_advanced(
    dry_run=True,
    batch_size=100,
    max_check=None,
    check_workers=10,
    use_cache=True,
    cache_hours=24,
    show_progress=True
):
    """
    高级检查并清理文章中的外部图片

    Args:
        dry_run: 是否为试运行
        batch_size: 每批处理的文章数
        max_check: 最多检查的文章数
        check_workers: URL检查的并发数
        use_cache: 是否使用缓存
        cache_hours: 缓存有效期（小时）
        show_progress: 是否显示进度条

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
        'cached_images': 0,
        'cleaned_posts': 0,
        'errors': [],
        'details': []
    }

    try:
        # 管理缓存
        cache = URLCheckCache(cache_hours=cache_hours) if use_cache else None

        print('🚀 高级外部图片检查工具')
        print('='*60)
        print(f'设置:')
        print(f'  - 批处理大小: {batch_size} 篇/批')
        print(f'  - 并发检查: {check_workers} 个worker')
        print(f'  - 使用缓存: {"是" if use_cache else "否"}')
        if use_cache:
            print(f'  - 缓存有效期: {cache_hours} 小时')
        print(f'  - 显示进度: {"是" if show_progress else "否"}')
        print('='*60)
        print()

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

                process_post_batch_advanced(
                    posts_batch,
                    batch_num,
                    report,
                    cache,
                    check_workers,
                    show_progress,
                    dry_run,
                    cursor,
                    conn
                )

        # 保存缓存
        if cache:
            cache.save()
            print(f'\n💾 缓存已保存')

    except Exception as e:
        error_msg = f'错误: {str(e)}'
        print(f'\n❌ {error_msg}')
        report['errors'].append({'error': error_msg})

    return report


def process_post_batch_advanced(posts, batch_num, report, cache, check_workers, show_progress, dry_run, cursor, conn):
    """处理一批文章（高级版）"""
    print(f'\n📦 处理批次 {batch_num} ({len(posts)} 篇文章)')

    # 收集所有外部图片URL
    all_external_images = []
    post_image_map = {}  # {url: [(post_id, title, img_tag), ...]}

    for post in posts:
        post_id = post['id']
        title = post['title'] or '无标题'
        content = post['content']

        # 提取图片
        images = extract_images_from_content(content)

        # 筛选出外部图片
        external_images = [(tag, url) for tag, url in images if url.startswith('http')]

        if external_images:
            report['posts_with_external_images'] += 1
            report['total_external_images'] += len(external_images)

            for img_tag, url in external_images:
                all_external_images.append(url)
                if url not in post_image_map:
                    post_image_map[url] = []
                post_image_map[url].append((post_id, title, img_tag))

    if not all_external_images:
        report['total_posts'] += len(posts)
        return

    report['total_posts'] += len(posts)

    # 去重URL
    unique_urls = list(set(all_external_images))
    print(f'🔍 发现 {len(all_external_images)} 张图片（{len(unique_urls)} 个唯一URL）')

    # 检查URL
    if cache:
        # 使用缓存
        check_results = {}
        urls_to_check = []

        for url in unique_urls:
            cached_result = cache.get(url)
            if cached_result is not None:
                check_results[url] = cached_result
                report['cached_images'] += 1
            else:
                urls_to_check.append(url)

        if report['cached_images'] > 0:
            print(f'💾 从缓存加载: {report["cached_images"]} 个URL')

        # 检查新URL
        if urls_to_check:
            new_results = check_image_urls_with_progress(
                urls_to_check,
                max_workers=check_workers,
                show_progress=show_progress,
                use_cache=False  # 已经手动处理了缓存
            )

            # 更新缓存和结果
            for url, result in new_results.items():
                cache.set(url, result)
                check_results[url] = result

            check_results.update(new_results)
    else:
        # 不使用缓存
        check_results = check_image_urls_with_progress(
            unique_urls,
            max_workers=check_workers,
            show_progress=show_progress,
            use_cache=False
        )

    # 分析结果并更新数据库
    update_posts_with_results(post_image_map, check_results, report, dry_run, cursor, conn)


def update_posts_with_results(post_image_map, check_results, report, dry_run, cursor, conn):
    """根据检查结果更新文章"""
    # 按文章分组无效图片
    post_invalid_images = {}  # {post_id: [(title, url, error), ...]}

    for url, (is_valid, error) in check_results.items():
        if not is_valid:
            for post_id, title, img_tag in post_image_map.get(url, []):
                if post_id not in post_invalid_images:
                    post_invalid_images[post_id] = []
                post_invalid_images[post_id].append((title, url, error))

            # 统计
            if error and '超时' in error:
                report['timeout_images'] += post_image_map[url].__len__()
            else:
                report['invalid_images'] += post_image_map[url].__len__()
        else:
            report['valid_images'] += post_image_map[url].__len__()

    # 清理无效图片
    for post_id, invalid_list in post_invalid_images.items():
        # 获取文章内容
        cursor.execute('SELECT title, content FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()

        if not post:
            continue

        title, content = post['title'], post['content']

        # 提取无效URL
        invalid_urls = [url for _, url, _ in invalid_list]

        print(f'\n📄 文章 #{post_id}: {title}')
        print(f'   删除 {len(invalid_urls)} 个无效图片')

        for url, error in [(url, error) for _, url, error in invalid_list][:3]:
            short_url = url[:60] + '...' if len(url) > 60 else url
            print(f'   ❌ {short_url} ({error})')

        # 使用优化的删除函数
        original_length = len(content)
        cleaned_content = remove_img_tags_by_urls(content, invalid_urls)
        cleaned_length = len(cleaned_content)

        print(f'   📏 内容长度: {original_length} -> {cleaned_length}')

        # 记录详情
        report['details'].append({
            'post_id': post_id,
            'title': title,
            'invalid_count': len(invalid_urls),
            'invalid_urls': invalid_urls,
            'errors': invalid_list
        })

        # 更新数据库
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


def main():
    """主函数"""
    print('🌐 高级外部图片检查工具\n')
    print('特性:')
    print('  ⚡ 并发检查（10倍速度）')
    print('  💾 智能缓存（避免重复检查）')
    print('  📊 进度显示')
    print('  🔄 批处理（低内存）\n')

    # 先测试
    print('🧪 先检查前10篇文章...\n')
    report_test = check_and_clean_advanced(
        dry_run=True,
        max_check=10,
        check_workers=5,
        show_progress=True
    )

    print_cleanup_report(report_test, "测试报告")

    if report_test['total_external_images'] > 0:
        print('\n❓ 是否检查所有文章？')
        try:
            confirm = input('继续？(yes/no): ').strip().lower()
            if confirm in ['yes', 'y', '是']:
                print('\n🚀 开始全量检查...\n')
                report_full = check_and_clean_advanced(
                    dry_run=True,
                    show_progress=True
                )

                print_cleanup_report(report_full, "全量检查报告")

                if report_full['invalid_images'] > 0:
                    print('\n❓ 确认执行清理？')
                    confirm2 = input('确认？(yes/no): ').strip().lower()
                    if confirm2 in ['yes', 'y', '是']:
                        print('\n🚀 执行清理...\n')
                        report_final = check_and_clean_advanced(
                            dry_run=False,
                            show_progress=True
                        )
                        print_cleanup_report(report_final, "清理完成报告")
                        print('\n✅ 清理完成！')
                        print(f'\n💡 备份: {get_backup_path()}')
                    else:
                        print('\n❌ 已取消')
                else:
                    print('\n✅ 所有图片都有效！')
            else:
                print('\n❌ 已取消')
        except (EOFError, KeyboardInterrupt):
            print('\n\n❌ 已取消')
    else:
        print('\n✅ 没有发现外部图片')


if __name__ == '__main__':
    main()
