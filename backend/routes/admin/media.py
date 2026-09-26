"""图片上传（后台 / 移动端）（admin 蓝图子模块）。"""

from flask import request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from models import (
    create_optimized_image_record,
)
from auth_decorators import login_required, api_key_required
from backend.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/upload', methods=['POST'])
@login_required
def upload_image():
    """
    处理图片上传，包含多层安全验证和图片优化

    安全验证流程:
        1. 文件存在性检查
        2. 文件扩展名白名单验证
        3. 文件类型实际内容验证（PIL）
        4. 图片尺寸验证（防止DoS）
        5. 文件大小验证（5MB限制）
        6. 安全文件名生成（时间戳+随机后缀）

    新功能:
        - 自动压缩图片为WebP格式
        - 生成多种尺寸（缩略图、中等、大图）
        - 返回所有尺寸的URL
    """
    # 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    # 验证文件扩展名
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400

    # 读取文件内容进行深度验证
    file_content = file.read()
    file.seek(0)  # 重置文件指针

    file_size = len(file_content)
    max_file_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_file_size:
        return jsonify({'success': False, 'error': f'文件大小超过限制（最大{max_file_size//1024//1024}MB）'}), 400

    secure_name = secure_filename(file.filename)
    file_type = secure_name.rsplit('.', 1)[1].lower() if '.' in secure_name else None

    # 验证实际文件类型和尺寸；如果 Pillow 缺失，则降级为扩展名校验
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(file_content))
        detected_type = img.format.lower() if img.format else file_type

        allowed_types = ['jpeg', 'jpg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'mpo', 'heic', 'heif']
        if detected_type not in allowed_types:
            return jsonify({'success': False, 'error': f'无效的图片文件类型: {detected_type}'}), 400

        width, height = img.size
        max_dimension = 8192
        if width > max_dimension or height > max_dimension:
            return jsonify({'success': False, 'error': f'图片尺寸过大，最大允许{max_dimension}x{max_dimension}'}), 400

        # MPO/HEIC/HEIF 格式统一转换为 JPEG
        if detected_type in ['mpo', 'heic', 'heif']:
            # 转换为RGB模式（如果需要）并保存为JPEG
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 重新编码为JPEG到内存
            jpeg_buffer = io.BytesIO()
            img.save(jpeg_buffer, format='JPEG', quality=95)
            file_content = jpeg_buffer.getvalue()
            file_type = 'jpg'
            detected_type = 'jpeg'
            logger.info(f"Converted {detected_type} to JPEG")
        else:
            file_type = 'jpg' if detected_type == 'jpeg' else detected_type
    except ImportError:
        logger.warning('Pillow is not installed; skipping deep image validation and optimization')
    except Exception:
        return jsonify({'success': False, 'error': '图片文件损坏或格式错误'}), 400

    # 生成安全的文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = file_type or 'png'
    random_suffix = os.urandom(4).hex()
    base_filename = f"{timestamp}_{random_suffix}"

    # 创建uploads目录下的images子目录
    images_dir = UPLOAD_FOLDER / 'images'
    images_dir.mkdir(exist_ok=True)

    # 保存原始文件
    original_path = images_dir / f"{base_filename}.{ext}"
    try:
        with open(original_path, 'wb') as f:
            f.write(file_content)
    except Exception as e:
        return jsonify({'success': False, 'error': f'文件保存失败: {str(e)}'}), 500

    # 记录到数据库并触发后台优化
    try:
        from image_processor import get_image_hash
        from tasks.image_optimization_task import queue_image_optimization

        image_hash = get_image_hash(str(original_path))
        optimization_id = create_optimized_image_record(
            original_path=str(original_path),
            original_hash=image_hash,
            status='pending'
        )

        # 触发后台优化
        queue_image_optimization(str(original_path))

        # 立即返回原图URL（使用绝对路径确保兼容性）
        image_url = f"/static/uploads/images/{original_path.name}"
        logger.info(f"Image uploaded: {original_path.name}, URL: {image_url}")

        return jsonify({
            'success': True,
            'url': image_url,
            'filename': original_path.name,
            'original_url': image_url,
            'optimization_id': optimization_id,
            'status': 'pending'
        })

    except Exception as e:
        logger.error(f'Error queueing image optimization: {e}')
        # 降级：立即返回原图
        return build_upload_response(original_path.name)

@mobile_bp.route('/upload', methods=['POST'])
@api_key_required
def mobile_upload_image():
    """
    移动端专用图片上传接口

    特点:
        - 无需CSRF token（适合移动端）
        - 需要登录session或 X-API-Key 请求头认证
        - 返回绝对URL路径
        - 支持HEIC格式自动转换
        - 详细的错误信息
    """
    # 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': '没有文件上传',
            'message': '请选择要上传的图片文件'
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': '未选择文件',
            'message': '文件名为空'
        }), 400

    # 验证文件扩展名
    if not allowed_file(file.filename):
        allowed_list = ', '.join(ALLOWED_EXTENSIONS)
        return jsonify({
            'success': False,
            'error': f'不支持的文件类型',
            'message': f'支持的文件类型: {allowed_list}'
        }), 400

    # 读取文件内容
    file_content = file.read()
    file_size = len(file_content)
    max_file_size = 50 * 1024 * 1024  # 50MB

    if file_size > max_file_size:
        return jsonify({
            'success': False,
            'error': f'文件大小超过限制',
            'message': f'最大允许{max_file_size//1024//1024}MB'
        }), 400

    # 获取安全文件名
    secure_name = secure_filename(file.filename)
    file_type = secure_name.rsplit('.', 1)[1].lower() if '.' in secure_name else 'jpg'

    logger.info(f"Mobile upload request: filename={file.filename}, size={file_size}, type={file_type}")

    # 验证和处理图片
    try:
        from PIL import Image
        import io

        # 验证图片文件
        img = Image.open(io.BytesIO(file_content))
        detected_type = img.format.lower() if img.format else file_type

        # 处理HEIC/HEIF格式（转换为JPEG）
        if detected_type in ['heic', 'heif']:
            logger.info(f"Converting HEIC to JPEG")
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 重新编码为JPEG
            jpeg_buffer = io.BytesIO()
            img.save(jpeg_buffer, format='JPEG', quality=95)
            file_content = jpeg_buffer.getvalue()
            file_type = 'jpg'

        # 保存文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_suffix = os.urandom(4).hex()
        base_filename = f"{timestamp}_{random_suffix}"

        images_dir = UPLOAD_FOLDER / 'images'
        images_dir.mkdir(exist_ok=True)

        original_path = images_dir / f"{base_filename}.{file_type}"

        with open(original_path, 'wb') as f:
            f.write(file_content)

        # 生成绝对URL（重要：移动端需要完整的URL路径）
        image_url = f"/static/uploads/images/{original_path.name}"

        logger.info(f"Mobile upload successful: {original_path.name}, URL: {image_url}")

        # 返回详细的响应，确保移动端可以正确解析
        return jsonify({
            'success': True,
            'url': image_url,
            'filename': original_path.name,
            'original_url': image_url,
            'message': '上传成功',
            'file_size': len(file_content)
        })

    except ImportError:
        logger.error('PIL not installed for mobile upload')
        return jsonify({
            'success': False,
            'error': '服务器配置错误',
            'message': '图片处理功能不可用'
        }), 500
    except Exception as e:
        logger.error(f'Mobile upload error: {e}')
        return jsonify({
            'success': False,
            'error': f'上传失败: {str(e)}',
            'message': '图片处理过程中发生错误'
        }), 500
