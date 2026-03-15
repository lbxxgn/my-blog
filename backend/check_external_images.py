#!/usr/bin/env python3
"""
检查文章中的外部图片链接是否有效

功能：
1. 检查所有外部图片URL（http/https）
2. 使用HEAD请求验证链接有效性
3. 生成详细报告
4. 可选择删除无效的外部图片
"""

import sys
import os
import re
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse
import socket

# 设置超时
socket.setdefaulttimeout(5)

# 添加后端目录到路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config import DATABASE_URL


def check_external_url(url):
    """
    检查外部URL是否有效

    Args:
        url: 图片URL

    Returns:
        (is_valid, status_code, error_message)
    """
    try:
        # 创建请求
        request = urllib.request.Request(url, method='HEAD')

        # 设置User-Agent
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

        # 发送请求
        response = urllib.request.urlopen(request, timeout=5)
        status_code = response.getcode()

        if status_code == 200:
            # 检查Content-Type
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('image/'):
                return True, status_code, None
            else:
                return False, status_code, f'不是图片: {content_type}'
        else:
            return False, status_code, f'HTTP {status_code}'

    except urllib.error.HTTPError as e:
        return False, e.code, f'HTTP {e.code}'
    except urllib.error.URLError as e:
        if hasattr(e, 'reason'):
            return False, None, f'URL错误: {e.reason}'
        else:
            return False, None, 'URL错误'
    except socket.timeout:
        return False, None, '请求超时'
    except Exception as e:
        return False, None, f'错误: {str(e)}'


def extract_images_from_content(content):
    """
    从文章内容中提取所有图片标签

    Args:
        content: 文章HTML内容

    Returns:
        [(img_tag, url, is_external), ...]
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
        is_external = url.startswith('http://') or url.startswith('https://')
        results.append((img_tag, url, is_external))

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


def check_and_clean_posts(dry_run=True, max_check=None):
    """
    检查并清理文章中的外部图片

    Args:
        dry_run: 是否为试运行
        max_check: 最多检查的文章数（None表示全部）

    Returns:
        清理报告字典
    """
    # 解析数据库URL
    db_path = DATABASE_URL.replace('sqlite:///', '')

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

        if max_check:
            posts = posts[:max_check]
            print(f'📊 开始扫描前 {len(posts)} 篇文章...\n')
        else:
            print(f'📊 开始扫描 {len(posts)} 篇文章...\n')

        for idx, post in enumerate(posts, 1):
            post_id = post['id']
            title = post['title'] or '无标题'
            content = post['content']

            # 提取图片
            images = extract_images_from_content(content)

            # 筛选出外部图片
            external_images = [(tag, url) for tag, url, is_ext in images if is_ext]

            if not external_images:
                continue

            report['posts_with_external_images'] += 1
            report['total_external_images'] += len(external_images)

            print(f'📄 [{idx}/{len(posts)}] 文章 #{post_id}: {title}')
            print(f'   发现 {len(external_images)} 张外部图片')

            invalid_urls = []
            post_errors = []

            for img_tag, url in external_images:
                # 显示URL（缩短显示）
                short_url = url[:70] + '...' if len(url) > 70 else url
                print(f'   🔍 检查: {short_url}', end=' ', flush=True)

                # 检查URL
                is_valid, status_code, error = check_external_url(url)

                if is_valid:
                    print('✅ 有效')
                    report['valid_images'] += 1
                else:
                    if '超时' in error:
                        print(f'⏱️  {error}')
                        report['timeout_images'] += 1
                    else:
                        print(f'❌ {error}')
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
    print('📊 外部图片检查报告')
    print('='*60)
    print(f'总文章数: {report["total_posts"]}')
    print(f'包含外部图片的文章: {report["posts_with_external_images"]}')
    print(f'外部图片总数: {report["total_external_images"]}')
    print(f'✅ 有效图片: {report["valid_images"]}')
    print(f'❌ 无效图片: {report["invalid_images"]}')
    print(f'⏱️  超时图片: {report["timeout_images"]}')
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
            for url, error in detail['errors'][:3]:  # 每个文章只显示前3个
                short_url = url[:60] + '...' if len(url) > 60 else url
                print(f'      - {short_url} ({error})')

        if len(report['details']) > 10:
            print(f'\n   ... 还有 {len(report["details"]) - 10} 篇文章')

    print('='*60)


def main():
    """主函数"""
    print('🌐 外部图片链接检查工具\n')
    print('⚠️  注意：检查外部链接需要较长时间，请耐心等待\n')

    # 第一次试运行
    print('🔍 第一次试运行（不修改数据库）...\n')

    # 先检查前10篇文章测试
    print('🧪 先检查前10篇文章作为测试...\n')
    report_test = check_and_clean_posts(dry_run=True, max_check=10)
    print_report(report_test)

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
        print('这可能需要几分钟时间。')

        try:
            confirm = input('继续检查所有文章？(yes/no): ').strip().lower()
            if confirm in ['yes', 'y', '是']:
                print('\n🚀 开始检查所有文章...\n')
                report_full = check_and_clean_posts(dry_run=True)
                print_report(report_full)

                if report_full['invalid_images'] > 0:
                    print('\n❓ 是否确认执行清理？这将修改数据库。')
                    confirm2 = input('确认执行？(yes/no): ').strip().lower()
                    if confirm2 in ['yes', 'y', '是']:
                        print('\n🚀 开始执行清理...\n')
                        report_final = check_and_clean_posts(dry_run=False)
                        print_report(report_final)
                        print('\n✅ 清理完成！')
                        print(f'\n💡 提示：数据库备份保存在: /Users/gn/simple-blog/db/simple_blog.db.backup.20260315_124428')
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
