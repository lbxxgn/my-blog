#!/usr/bin/env python3
"""
图片清理工具共享模块

整合所有图片清理脚本中的通用功能
"""

import re
import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from datetime import datetime, timedelta
import json
import os

try:
    import requests
except ImportError:  # pragma: no cover - 依赖可选
    requests = None


# 从 routes/blog.py 复用的图片提取正则
IMAGE_SRC_PATTERN = re.compile(
    r'<img[^>]+src=(?:"([^"]+)"|\'([^\']+)\'|([^>\s]+))[^>]*>',
    re.IGNORECASE
)
IMG_TAG_PATTERN = re.compile(r'<img[^>]*src=(?:"[^"]+"|\'[^\']+\'|[^>\s]+)[^>]*>', re.IGNORECASE)


def get_db_connection():
    """获取数据库连接（使用models.py的现有工具）"""
    try:
        from models import get_db_connection
        return get_db_connection()
    except ImportError:
        # 回退到直接创建连接
        from config import get_db_path
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        return conn


def fetch_posts_batch(cursor, batch_size: int = 100):
    """
    分批获取文章（避免一次性加载所有文章到内存）

    Args:
        cursor: 数据库游标
        batch_size: 每批文章数量

    Yields:
        文章批次列表
    """
    while True:
        posts = cursor.fetchmany(batch_size)
        if not posts:
            break
        yield posts


def extract_images_from_content(content: str) -> List[Tuple[str, str]]:
    """
    从文章内容中提取所有图片标签

    Args:
        content: 文章HTML内容

    Returns:
        [(img_tag, url), ...] - 图片标签和URL的列表
    """
    if not content:
        return []

    matches = [
        next((value for value in match if value), '')
        for match in IMAGE_SRC_PATTERN.findall(content)
    ]
    img_tags = IMG_TAG_PATTERN.findall(content)

    return list(zip(img_tags, matches))


def remove_img_tags_by_urls(content: str, urls_to_remove: List[str]) -> str:
    """
    删除指定URL的图片标签（优化版 - 单次正则替换）

    Args:
        content: 文章HTML内容
        urls_to_remove: 要删除的URL列表

    Returns:
        清理后的内容
    """
    if not urls_to_remove:
        return content

    # 构建单一正则表达式，使用 alternation
    escaped_urls = [re.escape(url) for url in urls_to_remove]
    pattern = re.compile(
        r'<img[^>]*src=["\'](' + '|'.join(escaped_urls) + r')["\'][^>]*>',
        re.IGNORECASE
    )

    return pattern.sub('', content)


def check_image_url(url: str, timeout: int = 5,
                    check_external: bool = True) -> Tuple[bool, Optional[str]]:
    """
    统一的图片URL检查器

    Args:
        url: 图片URL
        timeout: 超时时间（秒）
        check_external: 是否检查外部URL

    Returns:
        (is_valid, error_message)
    """
    # 本地路径检查
    if url.startswith('/'):
        file_path = Path(__file__).parent.parent.parent / 'static' / url.lstrip('/')
        if file_path.exists():
            return True, None
        return False, '文件不存在'

    # 外部URL检查
    if url.startswith('http') and check_external:
        if requests is None:
            return False, 'requests 未安装，无法检查外部链接'
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if content_type.startswith('image/'):
                    return True, None
                return False, f'不是图片类型: {content_type}'
            return False, f'HTTP {response.status_code}'
        except requests.exceptions.Timeout:
            return False, '请求超时'
        except requests.exceptions.RequestException as e:
            return False, f'网络错误: {str(e)}'

    return False, '不支持的URL格式'


def check_image_urls_concurrent(urls: List[str], timeout: int = 5,
                               max_workers: int = 10) -> Dict[str, Tuple[bool, Optional[str]]]:
    """
    并发检查多个图片URL（大幅提升性能）

    Args:
        urls: 图片URL列表
        timeout: 每个请求的超时时间（秒）
        max_workers: 最大并发数

    Returns:
        {url: (is_valid, error_message)} 的字典
    """
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_url = {
            executor.submit(check_image_url, url, timeout): url
            for url in urls
        }

        # 收集结果
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results[url] = result
            except Exception as e:
                results[url] = (False, f'检查异常: {str(e)}')

    return results


def print_cleanup_report(report: Dict, title: str = "清理报告"):
    """标准化的清理报告打印器"""
    print('\n' + '='*60)
    print(f'📊 {title}')
    print('='*60)

    # 打印基础统计
    key_labels = {
        'total_posts': '总文章数',
        'posts_with_images': '包含图片的文章',
        'posts_with_external_images': '包含外部图片的文章',
        'total_images': '总图片数',
        'total_external_images': '外部图片总数',
        'valid_images': '✅ 有效图片',
        'invalid_images': '❌ 无效图片',
        'timeout_images': '⏱️  超时图片',
        'external_skipped': '⏭️  跳过的外部链接',
        'cleaned_posts': '🧹 清理的文章数',
        'total_removed': '删除图片总数',
    }

    for key, label in key_labels.items():
        if key in report:
            print(f'{label}: {report[key]}')

    # 打印错误
    if report.get('errors'):
        print(f'\n⚠️  错误: {len(report["errors"])}')
        for error in report['errors']:
            print(f'   - {error}')

    # 打印详情
    if report.get('details'):
        print(f'\n📋 详细清理列表:')
        for detail in report['details'][:10]:
            post_id = detail.get('post_id', '?')
            title = detail.get('title', '无标题')
            invalid_count = detail.get('invalid_count', 0)
            print(f'\n   文章 #{post_id}: {title}')
            print(f'   删除了 {invalid_count} 个无效图片')

            errors = detail.get('errors', [])
            for url, error in errors[:3]:
                short_url = url[:60] + '...' if len(url) > 60 else url
                print(f'      - {short_url} ({error})')

        if len(report['details']) > 10:
            print(f'\n   ... 还有 {len(report["details"]) - 10} 篇文章')

    print('='*60)


class CleanupLogger:
    """清理操作日志记录器"""

    @staticmethod
    def post(post_id: int, title: str):
        print(f'📄 文章 #{post_id}: {title}')

    @staticmethod
    def success(msg: str):
        print(f'   ✅ {msg}')

    @staticmethod
    def error(msg: str):
        print(f'   ❌ {msg}')

    @staticmethod
    def warning(msg: str):
        print(f'   ⚠️  {msg}')

    @staticmethod
    def info(msg: str):
        print(f'   ℹ️  {msg}')

    @staticmethod
    def removed(count: int, original_len: int, cleaned_len: int):
        print(f'   🧹 删除了 {count} 个无效图片标签')
        print(f'   📏 内容长度: {original_len} -> {cleaned_len}')

    @staticmethod
    def saved():
        print(f'   💾 已更新数据库')


class URLCheckCache:
    """URL检查结果缓存"""

    def __init__(self, cache_file: str = None, cache_hours: int = 24):
        """
        初始化缓存

        Args:
            cache_file: 缓存文件路径
            cache_hours: 缓存有效期（小时）
        """
        if cache_file is None:
            backend_dir = Path(__file__).parent
            cache_file = backend_dir / 'url_check_cache.json'

        self.cache_file = Path(cache_file)
        self.cache_hours = cache_hours
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    # 检查缓存是否过期
                    cache_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
                    if datetime.now() - cache_time < timedelta(hours=self.cache_hours):
                        return data.get('results', {})
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        return {}

    def _save_cache(self):
        """保存缓存"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': self.cache
                }, f, indent=2)
        except Exception as e:
            print(f'⚠️  保存缓存失败: {e}')

    def get(self, url: str) -> Optional[Tuple[bool, Optional[str]]]:
        """获取缓存的检查结果"""
        return self.cache.get(url)

    def set(self, url: str, result: Tuple[bool, Optional[str]]):
        """设置缓存"""
        self.cache[url] = result

    def save(self):
        """保存缓存到文件"""
        self._save_cache()

    def clear(self):
        """清空缓存"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()


def check_image_urls_with_cache(
    urls: List[str],
    timeout: int = 5,
    max_workers: int = 10,
    use_cache: bool = True,
    cache_hours: int = 24
) -> Dict[str, Tuple[bool, Optional[str]]]:
    """
    带缓存的并发URL检查

    Args:
        urls: 图片URL列表
        timeout: 请求超时时间
        max_workers: 最大并发数
        use_cache: 是否使用缓存
        cache_hours: 缓存有效期（小时）

    Returns:
        {url: (is_valid, error_message)} 的字典
    """
    results = {}
    urls_to_check = []

    # 使用缓存
    cache = None
    if use_cache:
        cache = URLCheckCache(cache_hours=cache_hours)

        for url in urls:
            cached_result = cache.get(url)
            if cached_result is not None:
                results[url] = cached_result
            else:
                urls_to_check.append(url)

        print(f'💾 从缓存加载了 {len(results)} 个URL的检查结果')
        print(f'🔍 需要检查 {len(urls_to_check)} 个新URL\n')
    else:
        urls_to_check = urls

    # 并发检查未缓存的URL
    if urls_to_check:
        new_results = check_image_urls_concurrent(
            urls_to_check,
            timeout=timeout,
            max_workers=max_workers
        )

        # 更新缓存
        if cache:
            for url, result in new_results.items():
                cache.set(url, result)
            cache.save()

        results.update(new_results)

    return results


def check_image_urls_with_progress(
    urls: List[str],
    timeout: int = 5,
    max_workers: int = 10,
    use_cache: bool = True,
    show_progress: bool = True
) -> Dict[str, Tuple[bool, Optional[str]]]:
    """
    带进度条的并发URL检查

    Args:
        urls: 图片URL列表
        timeout: 请求超时时间
        max_workers: 最大并发数
        use_cache: 是否使用缓存
        show_progress: 是否显示进度条

    Returns:
        {url: (is_valid, error_message)} 的字典
    """
    if not show_progress:
        return check_image_urls_with_cache(urls, timeout, max_workers, use_cache)

    # 尝试导入tqdm
    try:
        from tqdm import tqdm
    except ImportError:
        print('⚠️  未安装tqdm，不显示进度条')
        print('💡 安装: pip install tqdm\n')
        return check_image_urls_with_cache(urls, timeout, max_workers, use_cache)

    results = {}
    cache = None
    urls_to_check = []

    # 使用缓存
    if use_cache:
        cache = URLCheckCache()
        for url in urls:
            cached_result = cache.get(url)
            if cached_result is not None:
                results[url] = cached_result
            else:
                urls_to_check.append(url)

        if len(results) > 0:
            print(f'💾 从缓存加载: {len(results)}/{len(urls)} 个URL\n')
    else:
        urls_to_check = urls

    # 并发检查未缓存的URL
    if urls_to_check:
        print(f'🔍 并发检查 {len(urls_to_check)} 个URL...')

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(check_image_url, url, timeout): url
                for url in urls_to_check
            }

            # 使用tqdm显示进度
            with tqdm(total=len(urls_to_check), desc="检查进度", unit="url") as pbar:
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        results[url] = result

                        # 更新缓存
                        if cache:
                            cache.set(url, result)

                        # 更新进度条描述
                        valid, error = result
                        status = '✅' if valid else '❌'
                        pbar.set_postfix_str(f'{status} {url[:30]}...')
                    except Exception as e:
                        results[url] = (False, f'检查异常: {str(e)}')
                    finally:
                        pbar.update(1)

        # 保存缓存
        if cache:
            cache.save()

        print()  # 进度条后换行

    return results
