"""导入导出（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, session, flash, send_file
import os
import shutil

from auth_decorators import login_required
from logger import log_operation, log_error


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/export')
@login_required
def export_page():
    """导出页面"""
    return render_template('admin/export.html')

@admin_bp.route('/export/markdown')
@login_required
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
@login_required
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

@admin_bp.route('/import')
@login_required
def import_page():
    """导入页面"""
    return render_template('admin/import.html')

@admin_bp.route('/import/json', methods=['POST'])
@login_required
def import_json():
    """从JSON文件导入文章"""
    try:
        user_id = session.get('user_id')

        if 'import_file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(url_for('admin.import_page'))

        file = request.files['import_file']

        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.import_page'))

        if not file.filename.endswith('.json'):
            flash('只支持JSON格式文件', 'error')
            return redirect(url_for('admin.import_page'))

        # 临时保存文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_file_path = tmp_file.name

        # 导入文章
        from import_posts import import_from_json
        count, skipped, messages = import_from_json(tmp_file_path, user_id)

        # 清理临时文件
        os.unlink(tmp_file_path)

        # 显示结果
        for msg in messages[1:]:
            flash(msg, 'success' if '✅' in msg else 'warning' if '⚠️' in msg else 'error')

        flash(messages[0], 'success')
        log_operation(user_id, session.get('username'), f'导入 {count} 篇文章从 JSON')

    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from JSON')

    return redirect(url_for('admin.import_page'))

@admin_bp.route('/import/markdown', methods=['POST'])
@login_required
def import_markdown():
    """从Markdown目录导入文章"""
    try:
        user_id = session.get('user_id')

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

        # 解压ZIP文件
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, 'import.zip')
            file.save(zip_path)

            # 解压
            extract_dir = os.path.join(tmp_dir, 'extracted')
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 查找posts目录或使用解压目录
            posts_dir = os.path.join(extract_dir, 'posts')
            if not os.path.exists(posts_dir):
                posts_dir = extract_dir

            # 导入文章
            from import_posts import import_from_markdown_directory
            count, skipped, messages = import_from_markdown_directory(posts_dir, user_id)

        # 显示结果
        for msg in messages[1:]:
            flash(msg, 'success' if '✅' in msg else 'warning' if '⚠️' in msg else 'error')

        flash(messages[0], 'success')
        log_operation(user_id, session.get('username'), f'导入 {count} 篇文章从 Markdown')

    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from markdown')

    return redirect(url_for('admin.import_page'))
