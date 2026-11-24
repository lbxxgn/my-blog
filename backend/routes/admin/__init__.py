"""
管理后台路由

包括管理仪表板、文章管理、分类管理、标签管理、评论管理、
导入导出、用户管理等功能。

公共小工具见 ``_shared.py``；本文件只保留蓝图、跨子模块使用的
异步 AI 标题任务，以及子模块导入。
"""

from flask import Blueprint

from backend.models import get_db_context, get_user_ai_config, save_ai_tag_history
from backend.routes.ai import _run_structured_prompt
from backend.logger import log_error
from backend.routes.admin._shared import (  # noqa: F401  （re-export 供子模块与外部使用）
    logger,
    auto_title as _auto_title,
    get_request_data,
    normalize_post_ids,
    filter_operable_post_ids,
    allowed_file,
    build_upload_response,
    validate_password_strength,
)


# 创建管理后台蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 移动端专用蓝图（无 CSRF 保护，使用 API Key 认证；路由见 media.py）
mobile_bp = Blueprint('mobile', __name__)


def _async_ai_title(app, post_id, content, user_id):
    """后台线程异步调用AI生成标题并更新文章。

    保留在本模块内：测试通过 monkeypatch 包级 ``_run_structured_prompt``
    替换真实调用，因此这里的引用必须时可被替换的模块全局。
    """
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
                max_tokens=300,
                temperature=0.5,
                extra_body=(
                    {'thinking': {'type': 'disabled'}}
                    if user_ai_config.get('ai_provider') == 'deepseek'
                    else None
                ),
            )

            if ai_result:
                ai_title = (ai_result.get('content') or '').strip().strip('"\'').strip()
                if ai_title:
                    with get_db_context() as conn:
                        conn.execute('UPDATE posts SET title = ? WHERE id = ?', (ai_title, post_id))

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
                else:
                    logger.warning(
                        "Async AI title generation returned empty content "
                        "(post_id=%s, provider=%s, model=%s)",
                        post_id,
                        user_ai_config.get('ai_provider'),
                        user_ai_config.get('ai_model'),
                    )
        except Exception as e:
            logger.warning(f"Async AI title generation failed: {e}")
            log_error(
                e,
                context=f'异步AI标题生成失败 | 文章ID: {post_id}',
                user_id=user_id,
            )


# 各功能子模块（在蓝图与共享助手就绪后导入，注册路由）
from . import posts, batch, media, taxonomy, comments, import_export, users, site, backup  # noqa: E402,F401
