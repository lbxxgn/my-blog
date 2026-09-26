"""知识库入口重定向与站点设置（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, flash

from models import (
    get_site_icon_version, set_site_setting,
)
from auth_decorators import login_required, admin_required
from backend.utils.site_icon import generate_site_icons, reset_site_icons, has_custom_icons
import time


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/knowledge')
@login_required
def knowledge_admin():
    """重定向到知识库独立空间"""
    return redirect(url_for('knowledge.index'))

@admin_bp.route('/site')
@login_required
@admin_required
def site_settings():
    """站点设置页（仅管理员）"""
    return render_template(
        'admin/site_settings.html',
        has_custom_icon=has_custom_icons(),
        icon_version=get_site_icon_version(),
    )

@admin_bp.route('/site/icon', methods=['POST'])
@login_required
@admin_required
def upload_site_icon():
    """上传并生成站点图标"""
    file = request.files.get('icon')
    if not file or file.filename == '':
        flash('请选择图片文件', 'error')
        return redirect(url_for('admin.site_settings'))

    if not allowed_file(file.filename):
        flash('不支持的图片格式，请上传 PNG/JPG/WEBP 等图片', 'error')
        return redirect(url_for('admin.site_settings'))

    file_content = file.read()
    try:
        generate_site_icons(file_content)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('admin.site_settings'))
    except Exception as e:
        logger.error(f'Site icon upload failed: {e}')
        flash('图标处理失败，请稍后重试', 'error')
        return redirect(url_for('admin.site_settings'))

    set_site_setting('icon_version', str(int(time.time())))
    flash('站点图标已更新', 'success')
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/icon/reset', methods=['POST'])
@login_required
@admin_required
def reset_site_icon():
    """恢复默认站点图标"""
    reset_site_icons()
    set_site_setting('icon_version', str(int(time.time())))
    flash('已恢复默认图标', 'success')
    return redirect(url_for('admin.site_settings'))
