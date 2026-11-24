"""管理后台子模块共用的小工具。

原先这些助手直接堆在 ``backend/routes/admin/__init__.py``，8 个子模块各自用一行
``from . import ...`` 把全部助手隐式拉进来（并附 ``noqa: F401``），既看不出谁用了
什么，也让签名变更难以评估影响。现在集中在这里，子模块按需显式导入。

注意：本模块不能导入 ``admin_bp`` / ``mobile_bp`` 等蓝图，避免与包 ``__init__``
形成循环依赖。
"""

import logging

from flask import jsonify, request

from backend.auth_decorators import get_current_user
from backend.config import ALLOWED_EXTENSIONS
from backend.models import get_db_context
from backend.utils.password import validate_password_strength
from backend.utils.text import auto_title

logger = logging.getLogger(__name__)


def get_request_data():
    """同时兼容 JSON 和表单提交。"""
    data = request.get_json(silent=True)
    if data is not None:
        return data

    form = request.form
    if not form:
        return {}

    normalized = {}
    for key in form.keys():
        values = form.getlist(key)
        normalized[key] = values if len(values) > 1 else form.get(key)
    return normalized


def normalize_post_ids(raw_value):
    """把单值/列表形式的文章ID统一转为整型列表。"""
    if raw_value is None:
        return []
    values = raw_value if isinstance(raw_value, list) else [raw_value]
    result = []
    for value in values:
        if value in (None, ''):
            continue
        result.append(int(value))
    return result


def filter_operable_post_ids(post_ids):
    """
    按当前用户角色过滤批量操作的文章ID，与 can_edit_post 规则一致：
    admin/editor 可操作所有文章，author 只能操作自己的文章。
    返回 (可操作ID列表, 因无权限被跳过的数量)。
    """
    user = get_current_user()
    if user and user.get('role') in ('admin', 'editor'):
        return post_ids, 0
    if not post_ids:
        return [], 0
    author_id = user.get('id') if user else None
    with get_db_context() as conn:
        placeholders = ','.join('?' * len(post_ids))
        rows = conn.execute(
            f'SELECT id FROM posts WHERE author_id = ? AND id IN ({placeholders})',
            (author_id, *post_ids)
        ).fetchall()
        allowed = {row[0] for row in rows}
    result = [pid for pid in post_ids if pid in allowed]
    return result, len(post_ids) - len(result)


def allowed_file(filename):
    """检查文件扩展名是否允许。"""
    return bool(filename) and '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def build_upload_response(image_filename):
    """上传成功后的统一响应体（移动端需要绝对路径语义）。"""
    image_url = f"/static/uploads/images/{image_filename}"
    return jsonify({
        'success': True,
        'url': image_url,
        'original_url': image_url,
        'urls': {
            'thumbnail': image_url,
            'medium': image_url,
            'large': image_url,
            'original': image_url
        },
        'filename': image_filename
    })


__all__ = [
    'logger',
    'auto_title',
    'get_request_data',
    'normalize_post_ids',
    'filter_operable_post_ids',
    'allowed_file',
    'build_upload_response',
    'validate_password_strength',
]
