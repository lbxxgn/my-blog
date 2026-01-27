"""
API路由

提供 RESTful API 接口，支持游标分页等功能。
"""

from flask import Blueprint, request, jsonify, url_for

from models import get_all_posts_cursor

# 创建 API 蓝图
api_bp = Blueprint('api', __name__)


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
