"""分类与标签管理（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, flash, jsonify

from models import (
    get_all_categories, create_category, delete_category, update_category, merge_category,
    create_tag, get_all_tags, delete_tag, update_tag, merge_tag, get_db_connection,
)
from auth_decorators import role_required


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/categories')
@role_required('admin', 'editor')
def category_list():
    """列出所有分类"""
    categories = get_all_categories(space='blog')
    conn = get_db_connection()
    for category in categories:
        row = conn.execute(
            'SELECT COUNT(*) AS cnt FROM posts WHERE category_id = ? AND deleted_at IS NULL',
            (category['id'],)
        ).fetchone()
        category['total_count'] = row['cnt'] if row else 0
    conn.close()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/categories/new', methods=['POST'])
@role_required('admin', 'editor')
def new_category():
    """创建新分类"""
    name = request.form.get('name')
    if not name:
        flash('分类名称不能为空', 'error')
        return redirect(url_for('admin.category_list'))

    category_id = create_category(name)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if category_id:
            return jsonify({'success': True, 'id': category_id, 'name': name})
        return jsonify({'success': False, 'error': '分类名称已存在'}), 400
    if category_id:
        flash('分类创建成功', 'success')
    else:
        flash('分类名称已存在', 'error')
    return redirect(url_for('admin.category_list'))


@admin_bp.route('/categories/<int:category_id>/rename', methods=['POST'])
@role_required('admin', 'editor')
def rename_category_route(category_id):
    name = (request.form.get('name') or '').strip()
    if not name:
        flash('分类名称不能为空', 'error')
    elif update_category(category_id, name):
        flash('分类已重命名', 'success')
    else:
        flash('重命名失败，名称可能已存在', 'error')
    return redirect(url_for('admin.category_list'))


@admin_bp.route('/categories/<int:category_id>/merge', methods=['POST'])
@role_required('admin', 'editor')
def merge_category_route(category_id):
    target_id = request.form.get('target_id', type=int)
    if not target_id:
        flash('请选择目标分类', 'error')
    elif merge_category(category_id, target_id):
        flash('分类已合并', 'success')
    else:
        flash('合并失败', 'error')
    return redirect(url_for('admin.category_list'))

@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@role_required('admin', 'editor')
def delete_category_route(category_id):
    """删除分类"""
    delete_category(category_id)
    flash('分类已删除', 'success')
    return redirect(url_for('admin.category_list'))

@admin_bp.route('/tags')
@role_required('admin', 'editor')
def tag_list():
    """列出所有标签"""
    tags = get_all_tags()
    return render_template('admin/tags.html', tags=tags)

@admin_bp.route('/tags/new', methods=['POST'])
@role_required('admin', 'editor')
def new_tag():
    """创建新标签"""
    name = request.form.get('name')
    if not name:
        flash('标签名称不能为空', 'error')
        return redirect(url_for('admin.tag_list'))

    tag_id = create_tag(name)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if tag_id:
            return jsonify({'success': True, 'id': tag_id, 'name': name})
        return jsonify({'success': False, 'error': '标签名称已存在'}), 400
    if tag_id:
        flash('标签创建成功', 'success')
    else:
        flash('标签名称已存在', 'error')
    return redirect(url_for('admin.tag_list'))


@admin_bp.route('/tags/<int:tag_id>/rename', methods=['POST'])
@role_required('admin', 'editor')
def rename_tag_route(tag_id):
    name = (request.form.get('name') or '').strip()
    if not name:
        flash('标签名称不能为空', 'error')
    elif update_tag(tag_id, name):
        flash('标签已重命名', 'success')
    else:
        flash('重命名失败，名称可能已存在', 'error')
    return redirect(url_for('admin.tag_list'))


@admin_bp.route('/tags/<int:tag_id>/merge', methods=['POST'])
@role_required('admin', 'editor')
def merge_tag_route(tag_id):
    target_id = request.form.get('target_id', type=int)
    if not target_id:
        flash('请选择目标标签', 'error')
    elif merge_tag(tag_id, target_id):
        flash('标签已合并', 'success')
    else:
        flash('合并失败', 'error')
    return redirect(url_for('admin.tag_list'))

@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@role_required('admin', 'editor')
def delete_tag_route(tag_id):
    """删除标签"""
    delete_tag(tag_id)
    flash('标签已删除', 'success')
    return redirect(url_for('admin.tag_list'))
