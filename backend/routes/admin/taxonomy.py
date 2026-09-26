"""分类与标签管理（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, flash

from models import (
    get_all_categories, create_category, delete_category,
    create_tag, get_all_tags, delete_tag,
)
from auth_decorators import login_required


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/categories')
@login_required
def category_list():
    """列出所有分类"""
    categories = get_all_categories()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/categories/new', methods=['POST'])
@login_required
def new_category():
    """创建新分类"""
    name = request.form.get('name')
    if not name:
        flash('分类名称不能为空', 'error')
        return redirect(url_for('admin.category_list'))

    category_id = create_category(name)
    if category_id:
        flash('分类创建成功', 'success')
    else:
        flash('分类名称已存在', 'error')
    return redirect(url_for('admin.category_list'))

@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category_route(category_id):
    """删除分类"""
    delete_category(category_id)
    flash('分类已删除', 'success')
    return redirect(url_for('admin.category_list'))

@admin_bp.route('/tags')
@login_required
def tag_list():
    """列出所有标签"""
    tags = get_all_tags()
    return render_template('admin/tags.html', tags=tags)

@admin_bp.route('/tags/new', methods=['POST'])
@login_required
def new_tag():
    """创建新标签"""
    name = request.form.get('name')
    if not name:
        flash('标签名称不能为空', 'error')
        return redirect(url_for('admin.tag_list'))

    tag_id = create_tag(name)
    if tag_id:
        flash('标签创建成功', 'success')
    else:
        flash('标签名称已存在', 'error')
    return redirect(url_for('admin.tag_list'))

@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag_route(tag_id):
    """删除标签"""
    delete_tag(tag_id)
    flash('标签已删除', 'success')
    return redirect(url_for('admin.tag_list'))
