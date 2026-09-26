"""评论管理（admin 蓝图子模块）。"""

from flask import render_template, redirect, url_for, flash

from models import (
    get_all_comments,
    update_comment_visibility, delete_comment,
    get_db_connection,
)
from auth_decorators import login_required


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/comments')
@login_required
def comment_list():
    """列出所有评论"""
    comments = get_all_comments(include_hidden=True)
    return render_template('admin/comments.html', comments=comments)

@admin_bp.route('/comments/<int:comment_id>/toggle', methods=['POST'])
@login_required
def toggle_comment(comment_id):
    """切换评论可见性"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT is_visible FROM comments WHERE id = ?', (comment_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        new_visibility = not result['is_visible']
        update_comment_visibility(comment_id, new_visibility)
        flash('评论状态已更新', 'success')
    else:
        flash('评论不存在', 'error')

    return redirect(url_for('admin.comment_list'))

@admin_bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment_route(comment_id):
    """删除评论"""
    delete_comment(comment_id)
    flash('评论已删除', 'success')
    return redirect(url_for('admin.comment_list'))
