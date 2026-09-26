"""
管理后台路由

包括管理仪表板、文章管理、分类管理、标签管理、评论管理、
导入导出、用户管理等功能。
"""

from flask import Blueprint, request, jsonify
import logging
import re

from models import get_db_connection, get_user_ai_config, save_ai_tag_history
from backend.routes.ai import _run_structured_prompt
from auth_decorators import get_current_user
from backend.config import ALLOWED_EXTENSIONS

def _auto_title(content: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', content or '')
    # 正文中的 &nbsp;（首行缩进）不应出现在标题里
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return '未命名记录'
    sentence = re.split(r'[。！？.!?\n]', text)[0].strip()
    return sentence[:24] if sentence else text[:24]

def _async_ai_title(app, post_id, content, user_id):
    """后台线程异步调用AI生成标题并更新文章。"""
    with app.app_context():
        try:
            user_ai_config = get_user_ai_config(user_id)
            if not user_ai_config or not user_ai_config.get('ai_tag_generation_enabled'):
                return

            ai_result = _run_structured_prompt(
                user_ai_config,
                system_prompt='你是一个专业的文章标题生成助手。请根据文章内容生成一个简洁、准确、吸引人的标题。',
                user_prompt=f"""请为以下文章生成一个标题。

要求：
1. 标题简洁明了，18字以内
2. 准确反映文章核心内容
3. 直接返回标题文本，不要加引号或其他格式
4. 不要返回任何解释性文字，只返回标题

文章内容：
{content[:3000]}
""",
                max_tokens=50,
                temperature=0.5
            )

            if ai_result:
                ai_title = ai_result['content'].strip().strip('"\'').strip()
                if ai_title:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE posts SET title = ? WHERE id = ?', (ai_title, post_id))
                    conn.commit()
                    conn.close()

                    save_ai_tag_history(
                        user_id=user_id,
                        post_id=post_id,
                        action='generate_title',
                        provider=user_ai_config.get('ai_provider'),
                        model_used=ai_result.get('model'),
                        tokens_used=ai_result.get('tokens_used', 0),
                        input_tokens=ai_result.get('input_tokens', 0),
                        output_tokens=ai_result.get('output_tokens', 0),
                        result_preview=ai_title
                    )
        except Exception as e:
            logger.warning(f"Async AI title generation failed: {e}")

# 创建管理后台蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
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
    conn = get_db_connection()
    try:
        placeholders = ','.join('?' * len(post_ids))
        rows = conn.execute(
            f'SELECT id FROM posts WHERE author_id = ? AND id IN ({placeholders})',
            (author_id, *post_ids)
        ).fetchall()
        allowed = {row[0] for row in rows}
        result = [pid for pid in post_ids if pid in allowed]
        return result, len(post_ids) - len(result)
    finally:
        conn.close()


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def build_upload_response(image_filename):
    # 使用绝对URL确保移动端兼容性
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




def validate_password_strength(password):
    """
    验证密码强度

    要求:
        - 至少10位长度
        - 包含至少一个大写字母
        - 包含至少一个小写字母
        - 包含至少一个数字

    Args:
        password (str): 待验证的密码

    Returns:
        tuple: (is_valid, error_message)
    """
    import re
    if len(password) < 10:
        return False, '密码长度至少为10位'

    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'

    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'

    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'

    return True, None

# 移动端专用蓝图（无 CSRF 保护，使用 API Key 认证；路由见 media.py）
mobile_bp = Blueprint('mobile', __name__)

# 各功能子模块（在 __init__ 定义共享助手/蓝图之后导入，注册路由）
from . import posts, batch, media, taxonomy, comments, import_export, users, site  # noqa: E402,F401
