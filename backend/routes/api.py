"""
API路由

提供 RESTful API 接口，支持游标分页等功能。
"""

from flask import Blueprint, request, jsonify, url_for, current_app, session

from auth_decorators import login_required
from models import get_all_posts_cursor
from logger import api_internal_error
from routes.search_helpers import (
    EmbeddingApiError,
    EmbeddingNotConfigured,
    find_related,
    semantic_search,
    unified_search,
)

# 创建 API 蓝图
api_bp = Blueprint('api', __name__)


def get_cache():
    """获取缓存对象"""
    return current_app.cache


@api_bp.route('/posts')
def api_posts_cursor():
    """
    获取文章列表的 API 端点，使用游标分页
    比传统的 OFFSET 分页在大数据集上更高效

    查询参数:
        - cursor: 基于时间的游标（created_at 时间戳）
        - per_page: 每页文章数（默认: 20）
        - category_id: 可选的分类筛选器

    返回:
        JSON 格式，包含 posts, next_cursor, has_more
    """
    # 构建缓存key
    cursor_time = request.args.get('cursor', '')
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id', '')
    cache_key = f"api_posts_{cursor_time}_{per_page}_{category_id}"

    # 尝试从缓存获取
    cache = get_cache()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify(cached_result)

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    # 使用游标分页
    posts_data = get_all_posts_cursor(
        cursor_time=cursor_time if cursor_time else None,
        per_page=per_page,
        include_drafts=False,
        category_id=category_id if category_id else None
    )

    result = {
        'success': True,
        'posts': posts_data['posts'],
        'next_cursor': posts_data['next_cursor'],
        'has_more': posts_data['has_more'],
        'per_page': posts_data['per_page']
    }

    # 存入缓存
    cache.set(cache_key, result, timeout=300)

    return jsonify(result)


@api_bp.route('/share/qrcode')
def generate_qrcode():
    """生成微信分享二维码"""
    import qrcode
    from io import BytesIO
    import base64

    url = request.args.get('url', url_for('blog.index', _external=True))

    # 生成二维码
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)

    # 创建图片
    img = qr.make_image(fill_color="black", back_color="white")

    # 转换为 base64
    buffer = BytesIO()
    img.save(buffer)
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({'qrcode': f"data:image/png;base64,{img_str}"})


@api_bp.route('/image/original-url')
def get_original_image_url():
    """
    通过优化图片hash获取原图URL

    参数:
        hash: 优化图片的hash（文件名中的hash部分）

    返回:
        {
            'success': true,
            'original_url': '/static/uploads/images/xxx.ext',
            'exists': true/false
        }
    """
    hash = request.args.get('hash')
    if not hash:
        return jsonify({'success': False, 'error': '缺少hash参数'}), 400

    # 构建缓存key
    cache_key = f"original_image_url_{hash}"

    # 尝试从缓存获取
    cache = get_cache()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify(cached_result)

    try:
        # 使用数据库查询替代目录遍历，提高性能
        from models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # 查询优化图片记录
        cursor.execute('''
            SELECT original_path
            FROM optimized_images
            WHERE original_hash = ?
        ''', (hash,))

        result = cursor.fetchone()

        if result:
            # 转换为URL格式
            original_path = result['original_path']
            # 去除可能的前缀，确保返回正确的URL
            import os
            if original_path.startswith('static/uploads/images/'):
                original_url = f"/{original_path}"
            elif original_path.startswith('uploads/images/'):
                original_url = f"/static/{original_path}"
            elif original_path.startswith('/static/uploads/images/'):
                original_url = original_path
            else:
                original_url = f"/static/uploads/images/{os.path.basename(original_path)}"

            conn.close()
            response = {
                'success': True,
                'original_url': original_url,
                'exists': True,
                'filename': os.path.basename(original_path)
            }
        else:
            conn.close()
            response = {
                'success': True,
                'original_url': None,
                'exists': False,
                'error': '未找到对应的原图文件'
            }

        # 存入缓存
        cache.set(cache_key, response, timeout=300)

        return jsonify(response)

    except Exception as e:
        return api_internal_error(e)


def _search_limit(default, maximum):
    limit = request.args.get('limit', default, type=int)
    if not limit or limit <= 0 or limit > maximum:
        limit = default
    return limit


@api_bp.route('/search/all')
@login_required
def api_search_all():
    """
    统一关键词搜索：跨文章/卡片/知识库文档/卡片批注的 LIKE 检索

    查询参数:
        - q: 关键词（空则各分组返回空数组）
        - limit: 每类最多返回条数（默认: 6，最大: 50）
    """
    q = request.args.get('q', '').strip()
    limit = _search_limit(6, 50)
    return jsonify(unified_search(session['user_id'], q, limit))


@api_bp.route('/search/semantic')
@login_required
def api_search_semantic():
    """
    语义搜索：query 向量化后在 embeddings 表中检索相似内容

    查询参数:
        - q: 查询文本
        - limit: 最多返回条数（默认: 20，最大: 50）
    """
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'posts': [], 'cards': [], 'docs': []})
    limit = _search_limit(20, 50)

    try:
        return jsonify(semantic_search(session['user_id'], q, limit))
    except EmbeddingNotConfigured:
        return jsonify({'error': 'embedding_not_configured'}), 400
    except EmbeddingApiError as e:
        return jsonify({'error': 'embedding_api_error', 'detail': str(e)[:200]}), 502


@api_bp.route('/related', methods=['POST'])
@login_required
def api_related():
    """
    相关内容推荐：为给定文本推荐相关的文章/卡片/知识库文档

    JSON body:
        - text: 基准文本（不足 20 字符返回 400）
        - exclude_type / exclude_id: 可选，排除指定实体
        - limit: 返回条数（默认: 8）
    """
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if len(text) < 20:
        return jsonify({'error': 'text_too_short'}), 400

    exclude_type = data.get('exclude_type') or None
    exclude_id = data.get('exclude_id')
    limit = data.get('limit', 8)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 8
    if limit <= 0 or limit > 50:
        limit = 8

    try:
        items = find_related(session['user_id'], text,
                             exclude_type=exclude_type, exclude_id=exclude_id,
                             limit=limit)
    except EmbeddingNotConfigured:
        return jsonify({'error': 'embedding_not_configured'}), 400
    except EmbeddingApiError as e:
        return jsonify({'error': 'embedding_api_error', 'detail': str(e)[:200]}), 502

    return jsonify({'items': items})
