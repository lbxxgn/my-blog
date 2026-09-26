"""用户管理（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash

from models import (
    get_user_by_username, get_user_by_id, create_user, update_user, delete_user, get_all_users,
)
from auth_decorators import can_manage_users


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/users')
@can_manage_users
def user_list():
    """用户列表页面"""
    users = get_all_users()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@can_manage_users
def new_user():
    """创建新用户"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'author')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')

        # 验证
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
            return render_template('admin/user_form.html', user=None)

        # 使用统一的密码强度验证
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('admin/user_form.html', user=None)

        # 检查用户名是否已存在
        if get_user_by_username(username):
            flash('用户名已存在', 'error')
            return render_template('admin/user_form.html', user=None)

        # 创建用户
        password_hash = generate_password_hash(password)
        user_id = create_user(username, password_hash, role, display_name, bio)

        if user_id:
            flash('用户创建成功', 'success')
            return redirect(url_for('admin.user_list'))
        else:
            flash('用户创建失败', 'error')

    return render_template('admin/user_form.html', user=None)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@can_manage_users
def edit_user(user_id):
    """编辑用户"""
    user = get_user_by_id(user_id)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.user_list'))

    if request.method == 'POST':
        role = request.form.get('role')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')
        is_active = 1 if request.form.get('is_active') else 0

        # 防止管理员禁用自己的账户导致被锁出后台
        if not is_active and user_id == session.get('user_id'):
            flash('不能禁用自己的账户', 'error')
            return render_template('admin/user_form.html', user=user)

        # 如果提供新密码，验证并更新
        new_password = request.form.get('new_password')
        if new_password:
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                flash(error_msg, 'error')
                return render_template('admin/user_form.html', user=user)

            password_hash = generate_password_hash(new_password)
            update_user(user_id, role=role, display_name=display_name, bio=bio,
                        password_hash=password_hash, is_active=is_active)
        else:
            update_user(user_id, role=role, display_name=display_name, bio=bio,
                        is_active=is_active)

        flash('用户更新成功', 'success')
        return redirect(url_for('admin.user_list'))

    return render_template('admin/user_form.html', user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@can_manage_users
def delete_user_route(user_id):
    """删除用户"""
    # 不允许删除自己
    if user_id == session.get('user_id'):
        flash('不能删除自己的账号', 'error')
        return redirect(url_for('admin.user_list'))

    if delete_user(user_id):
        flash('用户已删除', 'success')
    else:
        flash('用户删除失败', 'error')

    return redirect(url_for('admin.user_list'))
