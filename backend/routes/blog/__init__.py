"""
公开博客路由

包括首页、文章详情、搜索、分类、标签、作者页面、评论等公开访问的功能。
"""

from flask import Blueprint, current_app, has_app_context
import logging
import re

from models import get_db_connection

logger = logging.getLogger(__name__)

# 创建博客蓝图
blog_bp = Blueprint('blog', __name__)

IMAGE_SRC_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
IMG_TAG_SRC_REWRITE_PATTERN = re.compile(r'(<img[^>]+src=["\'])([^"\']+)(["\'])', re.IGNORECASE)
IMG_LOADING_ATTR_PATTERN = re.compile(r'<img(?![^>]*\bloading=)([^>]*)>', re.IGNORECASE)
MEDIA_PARAGRAPH_PATTERN = re.compile(
    r'<p>(\s*(?:<a\b[^>]*>\s*)?<img\b[^>]*>(?:\s*</a>)?\s*)</p>',
    re.IGNORECASE
)
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
WHITESPACE_PATTERN = re.compile(r'\s+')


def get_optimized_image_url(original_url, size='medium'):
    """
    将原图URL转换为优化后的URL

    Args:
        original_url: 原图URL，例如 /static/uploads/images/xxx.jpg 或 /static/uploads/optimized/xxx_medium.webp
        size: 尺寸类型 'thumbnail' | 'medium' | 'large' | 'feed'

    Returns:
        优化后的URL，如果不存在则返回原图URL
    """
    try:
        # 验证size参数（防止SQL注入）
        valid_sizes = ['thumbnail', 'medium', 'large', 'feed']
        if size not in valid_sizes:
            logger.warning(f"Invalid size parameter: {size}, using 'medium'")
            size = 'medium'
        resolved_size = 'medium' if size == 'feed' else size

        from pathlib import Path
        import re
        # __file__ 是 /path/to/backend/routes/blog.py
        # 需要3次parent才能到达项目根目录
        project_root = Path(__file__).parent.parent.parent

        # 处理optimized路径的图片（例如 xxx_medium.webp -> xxx_feed.webp）
        if '/uploads/optimized/' in original_url:
            # 提取图片哈希值
            # 例如: /static/uploads/optimized/632da1f5f5f9291f6f5c729351b78c47_medium.webp
            match = re.search(r'/([a-f0-9]{32})_(?:thumbnail|medium|large|feed)\.webp', original_url)
            if match:
                image_hash = match.group(1)
                # 构建新的URL
                new_url = f"/static/uploads/optimized/{image_hash}_{resolved_size}.webp"

                # 检查文件是否存在
                file_path = project_root / new_url.lstrip('/')
                logger.debug(f"Checking optimized image: project_root={project_root}, new_url={new_url}, file_path={file_path}, exists={file_path.exists()}")
                if file_path.exists():
                    logger.debug(f"Converted optimized image {original_url} -> {new_url}")
                    return new_url
                else:
                    logger.debug(f"Optimized image not found: {new_url}, returning original")
                    return original_url
            return original_url

        # 处理原始图片路径
        if '/uploads/images/' not in original_url:
            return original_url

        # 从URL构建完整文件路径
        # /static/uploads/images/xxx.jpg -> /path/to/project/static/uploads/images/xxx.jpg
        full_path = project_root / original_url.lstrip('/')

        # 查询数据库获取优化后的图片路径
        conn = get_db_connection()
        cursor = conn.cursor()

        # 根据请求的尺寸选择字段（使用白名单验证过的size）
        size_field = f'{resolved_size}_path'

        cursor.execute('''
            SELECT {}, status
            FROM optimized_images
            WHERE original_path = ?
            AND status = 'completed'
        '''.format(size_field), (str(full_path),))

        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            # 将绝对路径转换为URL
            optimized_path = result[0]
            if optimized_path.startswith(project_root.as_posix()):
                url_path = optimized_path[len(project_root.as_posix()):].lstrip('/')
                optimized_url = f"/{url_path}"
                logger.debug(f"Converted {original_url} -> {optimized_url}")
                return optimized_url

        # 如果没有找到优化版本，返回原图
        logger.debug(f"No optimized version found for {original_url}")
        return original_url

    except Exception as e:
        logger.warning(f"Error converting image URL: {e}")
        return original_url


def get_optimized_image_url_cached(original_url, size='medium'):
    """
    带缓存的图片URL优化函数

    Args:
        original_url: 原图URL
        size: 优化尺寸

    Returns:
        优化后的图片URL
    """
    if not has_app_context() or not hasattr(current_app, 'cache'):
        return get_optimized_image_url(original_url, size)

    cache = current_app.cache

    # 构建缓存key
    cache_key = f"optimized_image_url_{original_url}_{size}"

    # 尝试从缓存获取
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # 计算结果
    result = get_optimized_image_url(original_url, size)

    # 存入缓存（1小时）
    cache.set(cache_key, result, timeout=3600)

    return result

def extract_post_image_urls(content, limit=9, use_optimized=True, size='medium'):
    """
    提取文章内容中的图片URL

    Args:
        content: 文章内容（HTML）
        limit: 最多提取多少张图片
        use_optimized: 是否使用优化后的图片
        size: 当use_optimized=True时，指定使用哪个尺寸 (thumbnail/medium/large/feed)

    Returns:
        图片URL列表
    """
    content_str = str(content or '')
    image_urls = IMAGE_SRC_PATTERN.findall(content_str)[:limit]

    if use_optimized:
        # 将原图URL转换为优化后的URL（使用缓存）
        image_urls = [get_optimized_image_url_cached(url, size) for url in image_urls]

    return image_urls


def extract_post_excerpt(content, limit=160):
    text_content = HTML_TAG_PATTERN.sub(' ', str(content or ''))
    normalized = WHITESPACE_PATTERN.sub(' ', text_content).strip()
    return normalized[:limit]


def rewrite_post_image_sources(content_html, size='medium'):
    """在服务端统一处理正文图片结构，避免模板和前端再做补救。"""
    html = str(content_html or '')

    def replace_src(match):
        prefix, original_url, suffix = match.groups()
        optimized_url = get_optimized_image_url(original_url, size)
        return f'{prefix}{optimized_url}{suffix}'

    html = IMG_TAG_SRC_REWRITE_PATTERN.sub(replace_src, html)
    html = IMG_LOADING_ATTR_PATTERN.sub(r'<img loading="lazy"\1>', html)
    html = MEDIA_PARAGRAPH_PATTERN.sub(r'<p class="post-media-block">\1</p>', html)
    return html


def determine_mobile_image_layout(image_count):
    if image_count <= 1:
        return 'single'
    if image_count <= 4:
        return 'grid-4'
    if image_count <= 6:
        return 'grid-6'
    return 'grid-9'


def build_post_card_payload(post):
    post_dict = serialize_post_for_json(post)
    # 首页/分类信息流优先使用较大的优化图，避免桌面端卡片放大后发糊
    image_urls = extract_post_image_urls(post_dict.get('content'), size='large')
    post_dict['image_urls'] = image_urls
    post_dict['image_count'] = len(image_urls)
    post_dict['mobile_image_layout'] = determine_mobile_image_layout(len(image_urls))
    post_dict['excerpt'] = extract_post_excerpt(post_dict.get('content'))
    return post_dict


def build_post_card_payloads(posts):
    return [build_post_card_payload(post) for post in posts]


def serialize_post_for_json(post):
    """Serialize post rows for lightweight JSON responses."""
    post_dict = dict(post) if hasattr(post, 'keys') else {}
    if not post_dict and hasattr(post, '_asdict'):
        post_dict = post._asdict()
    if not post_dict:
        post_dict = {
            'id': getattr(post, 'id', None),
            'title': getattr(post, 'title', ''),
            'content': getattr(post, 'content', ''),
            'category_name': getattr(post, 'category_name', None),
            'created_at': getattr(post, 'created_at', None),
            'is_published': getattr(post, 'is_published', True),
            'access_level': getattr(post, 'access_level', 'public')
        }

    created_at = post_dict.get('created_at')
    if created_at and hasattr(created_at, 'isoformat'):
        post_dict['created_at'] = created_at.isoformat()

    return post_dict

# 各功能子模块（在 __init__ 定义共享助手/蓝图之后导入，注册路由）
from . import feed, post_detail, search, mobile  # noqa: E402,F401
