"""导入导出（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import os
import shutil
from pathlib import Path

from auth_decorators import admin_required, role_required
from backend.config import BASE_DIR
from logger import log_operation, log_error


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


def _safe_extract_zip(zip_path, extract_dir):
    """解压 ZIP 前校验成员路径，防止目录穿越。"""
    import zipfile
    root = Path(extract_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            target = (root / info.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f'压缩包包含非法路径：{info.filename}')
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source, open(target, 'wb') as output:
                    shutil.copyfileobj(source, output)


def _copy_import_images(source_dir, dry_run=False):
    """把导入包中的图片复制到上传目录。"""
    source_dir = Path(source_dir)
    if not source_dir.exists():
        return 0
    destination = BASE_DIR / 'static' / 'uploads' / 'images'
    count = 0
    for file_path in source_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic', '.heif'}:
            if not dry_run:
                destination.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, destination / file_path.name)
            count += 1
    return count


@admin_bp.route('/export')
@admin_required
def export_page():
    """导出页面"""
    return render_template('admin/export.html')

@admin_bp.route('/export/markdown')
@admin_required
def export_markdown():
    """导出所有文章为Markdown文件"""
    try:
        from export import export_all_posts_to_markdown
        count, path = export_all_posts_to_markdown()
        log_operation(session.get('user_id'), session.get('username'), f'导出 {count} 篇文章为 Markdown')
        archive_path = shutil.make_archive(path, 'zip', root_dir=path)
        return send_file(
            archive_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{os.path.basename(path)}.zip'
        )
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export to markdown')
        return redirect(url_for('admin.export_page'))

@admin_bp.route('/export/json')
@admin_required
def export_json():
    """导出所有文章为JSON"""
    try:
        from export import export_to_json
        count, path = export_to_json()
        log_operation(session.get('user_id'), session.get('username'), f'导出 {count} 篇文章为 JSON')
        return send_file(
            path,
            mimetype='application/json',
            as_attachment=True,
            download_name=os.path.basename(path)
        )
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export to JSON')
        return redirect(url_for('admin.export_page'))

@admin_bp.route('/export/full')
@admin_required
def export_full():
    """导出完整 ZIP：JSON 全字段 + 上传图片。"""
    try:
        from export import export_full_archive
        count, path = export_full_archive()
        log_operation(session.get('user_id'), session.get('username'), f'完整导出 {count} 篇文章（含图片）')
        return send_file(path, mimetype='application/zip', as_attachment=True,
                         download_name=os.path.basename(path))
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export full archive')
        return redirect(url_for('admin.export_page'))


@admin_bp.route('/export/knowledge')
@admin_required
def export_knowledge():
    """单独导出知识库空间（JSON + 图片 ZIP）。"""
    try:
        from export import export_full_archive
        count, path = export_full_archive(post_type='knowledge')
        log_operation(session.get('user_id'), session.get('username'), f'导出知识库 {count} 篇')
        return send_file(path, mimetype='application/zip', as_attachment=True,
                         download_name=os.path.basename(path))
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export knowledge archive')
        return redirect(url_for('admin.export_page'))


@admin_bp.route('/import')
@role_required('admin', 'editor')
def import_page():
    """导入页面"""
    return render_template('admin/import.html')

@admin_bp.route('/import/json', methods=['POST'])
@role_required('admin', 'editor')
def import_json():
    """从 JSON 或完整导出 ZIP 导入文章。"""
    user_id = session.get('user_id')
    dry_run = bool(request.form.get('dry_run'))
    tmp_root = None
    try:
        if 'import_file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(url_for('admin.import_page'))
        file = request.files['import_file']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.import_page'))
        if not (file.filename.endswith('.json') or file.filename.endswith('.zip')):
            flash('只支持 JSON 或完整导出 ZIP 文件', 'error')
            return redirect(url_for('admin.import_page'))

        import tempfile
        tmp_root = tempfile.mkdtemp(prefix='import_json_')
        safe_name = secure_filename(file.filename) or 'import.json'
        upload_path = os.path.join(tmp_root, safe_name)
        file.save(upload_path)
        json_path = upload_path
        images_dir = None
        if safe_name.lower().endswith('.zip'):
            extract_dir = os.path.join(tmp_root, 'extracted')
            _safe_extract_zip(upload_path, extract_dir)
            candidates = list(Path(extract_dir).glob('**/*.json'))
            if not candidates:
                raise ValueError('压缩包中没有找到 JSON 数据文件')
            json_path = str(candidates[0])
            images_dir = Path(extract_dir) / 'images'

        from import_posts import import_from_json
        count, skipped, messages = import_from_json(json_path, user_id, dry_run=dry_run)
        if images_dir:
            image_count = _copy_import_images(images_dir, dry_run=dry_run)
            if image_count:
                messages.insert(0, f"🖼 图片：{'预检' if dry_run else '已恢复'} {image_count} 个")

        for msg in messages[1:]:
            flash(msg, 'success' if '✅' in msg or '🔎' in msg else 'warning' if '⚠️' in msg else 'error')
        flash(messages[0], 'info' if dry_run else 'success')
        log_operation(user_id, session.get('username'), f"{'预检' if dry_run else '导入'} {count} 篇文章从 JSON")
    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from JSON')
    finally:
        if tmp_root:
            shutil.rmtree(tmp_root, ignore_errors=True)
    return redirect(url_for('admin.import_page'))


@admin_bp.route('/import/markdown', methods=['POST'])
@role_required('admin', 'editor')
def import_markdown():
    """从 Markdown ZIP 导入文章。"""
    user_id = session.get('user_id')
    dry_run = bool(request.form.get('dry_run'))
    try:
        if 'import_file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(url_for('admin.import_page'))
        file = request.files['import_file']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.import_page'))
        if not file.filename.endswith('.zip'):
            flash('只支持ZIP压缩包格式', 'error')
            return redirect(url_for('admin.import_page'))

        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, 'import.zip')
            file.save(zip_path)
            extract_dir = os.path.join(tmp_dir, 'extracted')
            _safe_extract_zip(zip_path, extract_dir)
            posts_dir = os.path.join(extract_dir, 'posts')
            if not os.path.exists(posts_dir):
                posts_dir = extract_dir
            from import_posts import import_from_markdown_directory
            count, skipped, messages = import_from_markdown_directory(posts_dir, user_id, dry_run=dry_run)
            image_count = _copy_import_images(Path(extract_dir) / 'images', dry_run=dry_run)
            if image_count:
                messages.insert(0, f"🖼 图片：{'预检' if dry_run else '已恢复'} {image_count} 个")

        for msg in messages[1:]:
            flash(msg, 'success' if '✅' in msg or '🔎' in msg else 'warning' if '⚠️' in msg else 'error')
        flash(messages[0], 'info' if dry_run else 'success')
        log_operation(user_id, session.get('username'), f"{'预检' if dry_run else '导入'} {count} 篇文章从 Markdown")
    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from markdown')
    return redirect(url_for('admin.import_page'))
