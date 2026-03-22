"""
API路由

提供 RESTful API 接口，支持游标分页等功能。
"""

from flask import Blueprint, request, jsonify, url_for

from models import get_all_posts_cursor
from app import cache

# 创建 API 蓝图
api_bp = Blueprint('api', __name__)


@api_bp.route('/posts')
@api_bp.route('/api/posts')  # 兼容旧版API路径
@cache.cached(timeout=300, query_string=True)
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
    cursor_time = request.args.get('cursor')
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id')

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    # 使用游标分页
    posts_data = get_all_posts_cursor(
        cursor_time=cursor_time,
        per_page=per_page,
        include_drafts=False,
        category_id=category_id
    )

    return jsonify({
        'success': True,
        'posts': posts_data['posts'],
        'next_cursor': posts_data['next_cursor'],
        'has_more': posts_data['has_more'],
        'per_page': posts_data['per_page']
    })


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
@cache.cached(timeout=300, query_string=True)
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
            return jsonify({
                'success': True,
                'original_url': original_url,
                'exists': True,
                'filename': os.path.basename(original_path)
            })
        else:
            conn.close()
            return jsonify({
                'success': True,
                'original_url': None,
                'exists': False,
                'error': '未找到对应的原图文件'
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
