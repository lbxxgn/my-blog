"""图片上传（后台 / 移动端）（admin 蓝图子模块）。"""

from flask import request, jsonify
import os

from backend.models import create_optimized_image_record
from backend.auth_decorators import login_required, role_required, api_key_required
from backend.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_IMAGE_BYTES
from backend.utils.image_upload import ImageUploadError, store_image_upload


from . import admin_bp, mobile_bp, logger
from ._shared import build_upload_response

# 移动端把校验错误映射成更直白的提示（保持历史文案）
_MOBILE_ERROR_HINTS = {
    'missing_file': '请选择要上传的图片文件',
    'empty_filename': '文件名为空',
    'unsupported_type': f"支持的文件类型: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
    'too_large': f'最大允许{MAX_IMAGE_BYTES // 1024 // 1024}MB',
}


@admin_bp.route('/upload', methods=['POST'])
@login_required
def upload_image():
    """处理图片上传：校验 + 保存原图 + 触发后台 WebP/多尺寸优化。

    校验细节（扩展名、PIL 深度校验、HEIC 转 JPEG、尺寸与大小上限、命名规则）
    统一由 ``backend.utils.image_upload`` 提供，本视图只负责鉴权与响应。
    """
    try:
        stored = store_image_upload(request.files.get('file'))
    except ImageUploadError as exc:
        return jsonify({'success': False, 'error': str(exc)}), exc.status

    try:
        from backend.image_processor import get_image_hash
        from backend.tasks.image_optimization_task import queue_image_optimization

        image_hash = get_image_hash(str(stored.path))
        optimization_id = create_optimized_image_record(
            original_path=str(stored.path),
            original_hash=image_hash,
            status='pending'
        )

        # 触发后台优化
        queue_image_optimization(str(stored.path))

        logger.info(f"Image uploaded: {stored.filename}, URL: {stored.url}")
        return jsonify({
            'success': True,
            'url': stored.url,
            'filename': stored.filename,
            'original_url': stored.url,
            'optimization_id': optimization_id,
            'status': 'pending'
        })
    except Exception as e:
        logger.error(f'Error queueing image optimization: {e}')
        # 降级：立即返回原图
        return build_upload_response(stored.filename)


@mobile_bp.route('/upload', methods=['POST'])
@api_key_required
def mobile_upload_image():
    """移动端图片上传：session 或 X-API-Key 认证，跳过 CSRF，返回绝对 URL。"""
    try:
        stored = store_image_upload(request.files.get('file'))
    except ImageUploadError as exc:
        return jsonify({
            'success': False,
            'error': str(exc),
            'message': _MOBILE_ERROR_HINTS.get(exc.code, str(exc)),
        }), exc.status

    try:
        file_size = stored.path.stat().st_size
    except OSError:
        file_size = 0

    logger.info(f"Mobile upload successful: {stored.filename}, URL: {stored.url}")
    return jsonify({
        'success': True,
        'url': stored.url,
        'filename': stored.filename,
        'original_url': stored.url,
        'message': '上传成功',
        'file_size': file_size,
    })


@admin_bp.route('/media/library', methods=['GET'])
@login_required
def media_library():
    """最近上传图片列表，供编辑器媒体库复用。"""
    from backend.models import get_db_context
    images_dir = os.path.join(UPLOAD_FOLDER, 'images')
    query = (request.args.get('q') or '').strip().lower()
    items = []
    if os.path.isdir(images_dir):
        allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        for name in os.listdir(images_dir):
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed:
                continue
            if query and query not in name.lower():
                continue
            path = os.path.join(images_dir, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            items.append({
                'name': name,
                'url': f'/static/uploads/images/{name}',
                'mtime': stat.st_mtime,
                'size': stat.st_size,
            })
    items.sort(key=lambda item: item['mtime'], reverse=True)
    items = items[:100]
    with get_db_context() as conn:
        try:
            for item in items:
                item['references'] = conn.execute(
                    'SELECT COUNT(*) AS c FROM posts WHERE deleted_at IS NULL AND content LIKE ?',
                    (f'%{item["name"]}%',),
                ).fetchone()['c']
        finally:
            pass
        return jsonify({'success': True, 'items': items})


@admin_bp.route('/media/library/delete', methods=['POST'])
@role_required('admin', 'editor')
def media_library_delete():
    """删除未被正文引用的图片。"""
    from backend.models import get_db_context
    data = request.get_json(silent=True) or request.form
    name = os.path.basename((data.get('name') or '').strip())
    if not name:
        return jsonify({'success': False, 'error': '缺少文件名'}), 400
    with get_db_context() as conn:
        try:
            refs = conn.execute(
                'SELECT COUNT(*) AS c FROM posts WHERE deleted_at IS NULL AND content LIKE ?',
                (f'%{name}%',),
            ).fetchone()['c']
        finally:
            pass
        if refs:
            return jsonify({'success': False, 'error': f'该图片仍被 {refs} 篇文章引用，不能删除'}), 400
        path = os.path.join(UPLOAD_FOLDER, 'images', name)
        if not os.path.isfile(path):
            return jsonify({'success': False, 'error': '图片不存在'}), 404
        try:
            os.remove(path)
        except OSError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 500
        return jsonify({'success': True})
