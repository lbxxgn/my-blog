"""知识库入口重定向与站点设置（admin 蓝图子模块）。"""

import json
import time

from flask import Response, abort, flash, redirect, render_template, request, url_for

from backend.models import (
    delete_site_setting,
    get_site_icon_version,
    get_site_setting,
    set_site_setting,
    get_site_identity,
)
from backend.auth_decorators import login_required, admin_required
from backend.utils.site_icon import (
    generate_site_icons,
    has_custom_icons,
    has_custom_source,
    load_source_bytes,
    reset_site_icons,
    source_mimetype,
)
from backend.config import SITE_NAME, SITE_DESCRIPTION, SITE_AUTHOR


from . import admin_bp, logger
from ._shared import allowed_file


def _parse_crop_rect(raw):
    """校验前端提交的选区（归一化到 0~1 的 x/y/w/h），无效时返回 None。"""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        rect = {key: float(data.get(key)) for key in ('x', 'y', 'w', 'h')}
    except (TypeError, ValueError):
        return None
    if not all(0 <= value <= 1 for value in rect.values()):
        return None
    if rect['w'] <= 0 or rect['h'] <= 0:
        return None
    if rect['x'] + rect['w'] > 1.0001 or rect['y'] + rect['h'] > 1.0001:
        return None
    return {key: round(value, 6) for key, value in rect.items()}


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
    identity = get_site_identity({
        'site_name': SITE_NAME,
        'site_description': SITE_DESCRIPTION,
        'site_author': SITE_AUTHOR,
    })
    return render_template(
        'admin/site_settings.html',
        has_custom_icon=has_custom_icons(),
        has_source=has_custom_source(),
        icon_crop=get_site_setting('icon_crop', ''),
        icon_version=get_site_icon_version(),
        identity=identity,
    )


@admin_bp.route('/site/icon/source')
@login_required
@admin_required
def site_icon_source():
    """返回保留的原始图片，供裁剪界面重新选择区域（仅管理员）。"""
    data = load_source_bytes()
    if not data:
        abort(404)
    response = Response(data, mimetype=source_mimetype())
    response.headers['Cache-Control'] = 'no-store'
    return response


@admin_bp.route('/site/general', methods=['POST'])
@login_required
@admin_required
def update_site_identity():
    """保存站点名称、描述与作者。"""
    site_name = (request.form.get('site_name') or '').strip()
    site_description = (request.form.get('site_description') or '').strip()
    site_author = (request.form.get('site_author') or '').strip()
    if not site_name:
        flash('站点名称不能为空', 'error')
        return redirect(url_for('admin.site_settings'))
    if len(site_name) > 80 or len(site_description) > 300 or len(site_author) > 80:
        flash('站点信息过长，请缩短后重试', 'error')
        return redirect(url_for('admin.site_settings'))
    set_site_setting('site_name', site_name)
    set_site_setting('site_description', site_description)
    set_site_setting('site_author', site_author)
    flash('站点信息已更新', 'success')
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/icon', methods=['POST'])
@login_required
@admin_required
def upload_site_icon():
    """上传/重新裁剪并生成站点图标。

    - 选择新图片时上传原图，前端同时提交裁剪后的正方形图。
    - 未选择新图片时，只提交裁剪结果，使用已保留的原图重新生成图标。
    """
    file = request.files.get('icon')
    cropped = request.files.get('cropped')
    crop_rect_raw = request.form.get('crop')

    has_file = bool(file and file.filename)
    has_cropped = bool(cropped and cropped.filename)

    if not has_file and not has_cropped and not has_custom_source():
        flash('请选择图片文件', 'error')
        return redirect(url_for('admin.site_settings'))

    if has_file and not allowed_file(file.filename):
        flash('不支持的图片格式，请上传 PNG/JPG/WEBP 等图片', 'error')
        return redirect(url_for('admin.site_settings'))

    file_content = file.read() if has_file else None
    cropped_content = cropped.read() if has_cropped else None

    try:
        generate_site_icons(file_content, cropped_content)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('admin.site_settings'))
    except Exception as e:
        logger.error(f'Site icon upload failed: {e}')
        flash('图标处理失败，请稍后重试', 'error')
        return redirect(url_for('admin.site_settings'))

    crop_rect = _parse_crop_rect(crop_rect_raw)
    if crop_rect:
        set_site_setting('icon_crop', json.dumps(crop_rect))
    else:
        delete_site_setting('icon_crop')

    set_site_setting('icon_version', str(int(time.time())))
    flash('站点图标已更新', 'success')
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/icon/reset', methods=['POST'])
@login_required
@admin_required
def reset_site_icon():
    """恢复默认站点图标"""
    reset_site_icons()
    delete_site_setting('icon_crop')
    set_site_setting('icon_version', str(int(time.time())))
    flash('已恢复默认图标', 'success')
    return redirect(url_for('admin.site_settings'))
