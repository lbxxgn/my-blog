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
    
    try:
        import os
        # 获取项目根目录
        from flask import current_app
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        images_dir = os.path.join(root_dir, 'static', 'uploads', 'images')

        if not os.path.exists(images_dir):
            return jsonify({'success': False, 'error': '图片目录不存在'}), 404

        # 查找包含此hash的文件
        matching_files = []
        for filename in os.listdir(images_dir):
            if hash in filename:
                file_path = os.path.join(images_dir, filename)
                if os.path.isfile(file_path):
                    matching_files.append(filename)

        if matching_files:
            # 返回第一个匹配的文件
            original_url = f"/static/uploads/images/{matching_files[0]}"
            return jsonify({
                'success': True,
                'original_url': original_url,
                'exists': True,
                'filename': matching_files[0]
            })
        else:
            return jsonify({
                'success': True,
                'original_url': None,
                'exists': False,
                'error': '未找到对应的原图文件'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
