"""
AI功能路由

包括AI标签生成、摘要生成、相关文章推荐、内容续写等功能。
"""

from flask import Blueprint, render_template, request, session, jsonify
import logging

from ai_services import TagGenerator
from models import (
    get_user_ai_config, update_user_ai_config,
    save_ai_tag_history, get_ai_tag_history,
    get_ai_usage_stats, get_all_posts
)
from auth_decorators import login_required
from logger import log_operation, log_error

logger = logging.getLogger(__name__)

# 创建 AI 蓝图
ai_bp = Blueprint('ai', __name__, url_prefix='/admin/ai')


@ai_bp.route('/generate-tags', methods=['POST'])
@login_required
def generate_tags():
    """
    AI生成标签API

    接收文章标题和内容，返回AI生成的标签
    """
    try:
        # 获取请求数据
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()

        # 验证输入
        if not title:
            return jsonify({
                'success': False,
                'error': '文章标题不能为空'
            }), 400

        if not content:
            return jsonify({
                'success': False,
                'error': '文章内容不能为空'
            }), 400

        # 获取当前用户的AI配置
        user_id = session.get('user_id')
        user_ai_config = get_user_ai_config(user_id)

        if not user_ai_config:
            return jsonify({
                'success': False,
                'error': '用户不存在'
            }), 404

        # 生成标签
        try:
            result = TagGenerator.generate_for_post(
                title=title,
                content=content,
                user_config=user_ai_config,
                max_tags=3
            )
        except Exception as e:
            error_msg = str(e)
            # 提供更友好的错误信息
            if 'did not match the expected pattern' in error_msg or 'pattern' in error_msg.lower():
                logger.error(f"API validation error: {error_msg}")
                logger.error(f"User config: provider={user_ai_config.get('ai_provider')}, model={user_ai_config.get('ai_model')}")
                return jsonify({
                    'success': False,
                    'error': f'API配置验证失败：模型名称或密钥格式不正确（{user_ai_config.get("ai_provider")}/{user_ai_config.get("ai_model", "default")}）'
                }), 400
            else:
                raise

        if result is None:
            return jsonify({
                'success': False,
                'error': 'AI标签生成功能未启用，请在设置中启用'
            }), 400

        # 记录生成历史（异步，不阻塞响应）
        try:
            post_id = data.get('post_id')
            # 始终保存历史记录，即使没有 post_id（新建文章的情况）
            history_id = save_ai_tag_history(
                user_id=user_id,
                post_id=int(post_id) if post_id else None,
                action='generate_tags',
                provider=user_ai_config.get('ai_provider'),
                model_used=result.get('model'),
                tokens_used=result.get('tokens_used', 0),
                input_tokens=result.get('input_tokens', 0),
                output_tokens=result.get('output_tokens', 0),
                cost=result.get('cost', 0),
                currency=result.get('currency', 'USD'),
                result_preview=result.get('tags', []),
                generated_tags=result.get('tags', [])  # 兼容旧格式
            )
            print(f"[AI History] Saved record ID: {history_id}, post_id: {post_id}")
        except Exception as e:
            # 历史记录失败不影响主流程
            print(f"[AI History] Failed to save: {str(e)}")
            import traceback
            traceback.print_exc()
            log_error(e, context='保存AI历史记录失败')

        log_operation(session.get('user_id'), session.get('username'),
                     f'AI生成标签: {", ".join(result["tags"])} ({result["tokens_used"]} tokens)')

        return jsonify({
            'success': True,
            'tags': result['tags'],
            'tokens_used': result['tokens_used'],
            'model': result['model'],
            'cost': result.get('cost', 0)
        })

    except ValueError as e:
        # 配置错误
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        log_error(e, context='AI标签生成失败')
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@ai_bp.route('/configure', methods=['GET', 'POST'])
@login_required
def ai_settings():
    """
    AI设置页面和API
    GET: 显示设置页面
    POST: 更新AI配置
    """
    user_id = session.get('user_id')

    if request.method == 'GET':
        # 获取用户当前AI配置
        ai_config = get_user_ai_config(user_id)
        supported_providers = TagGenerator.get_supported_providers()

        # 获取使用统计
        stats = get_ai_usage_stats(user_id)

        return render_template('admin/ai_settings.html',
                             ai_config=ai_config,
                             supported_providers=supported_providers,
                             stats=stats)

    else:  # POST
        try:
            # 更新AI配置
            data = request.get_json()

            # 验证数据
            ai_config = {}

            if 'ai_tag_generation_enabled' in data:
                ai_config['ai_tag_generation_enabled'] = bool(data['ai_tag_generation_enabled'])

            if 'ai_provider' in data:
                provider = data['ai_provider']
                # 验证提供商是否支持
                supported = [p['id'] for p in TagGenerator.get_supported_providers()]
                if provider not in supported:
                    return jsonify({
                        'success': False,
                        'error': f'不支持的AI提供商: {provider}'
                    }), 400
                ai_config['ai_provider'] = provider

            if 'ai_api_key' in data:
                api_key = data['ai_api_key'].strip()
                if api_key:
                    ai_config['ai_api_key'] = api_key

            if 'ai_model' in data:
                model = data['ai_model'].strip()
                if model:
                    ai_config['ai_model'] = model

            # 更新配置
            success = update_user_ai_config(user_id, ai_config)

            if success:
                log_operation(session.get('user_id'), session.get('username'),
                             '更新AI配置')
                return jsonify({
                    'success': True,
                    'message': 'AI配置已更新'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '配置更新失败'
                }), 500

        except Exception as e:
            log_error(e, context='更新AI配置失败')
            return jsonify({
                'success': False,
                'error': f'更新失败: {str(e)}'
            }), 500


@ai_bp.route('/test', methods=['POST'])
@login_required
def test_ai_config():
    """
    测试AI配置API

    支持两种模式：
    1. 测试表单中的配置（POST请求体中提供）
    2. 测试数据库中保存的配置
    """
    try:
        user_id = session.get('user_id')

        # 尝试从请求体获取配置（表单中的值）
        form_config = request.get_json()

        if form_config and form_config.get('ai_api_key'):
            # 使用表单中的配置进行测试
            ai_config = {
                'ai_tag_generation_enabled': True,
                'ai_provider': form_config.get('ai_provider', 'openai'),
                'ai_api_key': form_config.get('ai_api_key'),
                'ai_model': form_config.get('ai_model')
            }
        else:
            # 使用数据库中保存的配置
            ai_config = get_user_ai_config(user_id)

            if not ai_config:
                return jsonify({
                    'success': False,
                    'message': '未配置API密钥，请先在下方输入密钥'
                })

        # 测试配置
        result = TagGenerator.test_user_config(ai_config)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        })


@ai_bp.route('/history')
@login_required
def ai_history():
    """
    AI生成历史页面
    """
    import json

    user_id = session.get('user_id')
    history = get_ai_tag_history(user_id=user_id, limit=50)
    stats = get_ai_usage_stats(user_id)

    # Parse generated_tags JSON for each record
    for record in history:
        if record.get('generated_tags'):
            try:
                # Try to parse as JSON
                parsed = json.loads(record['generated_tags'])
                # If it's a list (old format), keep it as is
                # If it's a dict (new format), use it as parsed_data
                if isinstance(parsed, dict):
                    record['parsed_data'] = parsed
                else:
                    record['parsed_data'] = None
            except (json.JSONDecodeError, TypeError):
                record['parsed_data'] = None
        else:
            record['parsed_data'] = None

    return render_template('admin/ai_history.html',
                         history=history,
                         stats=stats)


@ai_bp.route('/status')
@login_required
def ai_status():
    """
    获取AI功能启用状态API

    返回当前用户的AI功能是否启用，用于前端控制AI功能的显示/隐藏
    """
    user_id = session.get('user_id')
    ai_config = get_user_ai_config(user_id)

    ai_enabled = False
    if ai_config:
        ai_enabled = ai_config.get('ai_tag_generation_enabled', False)

    return jsonify({
        'ai_enabled': ai_enabled
    })


@ai_bp.route('/generate-summary', methods=['POST'])
@login_required
def generate_summary():
    """
    AI生成文章摘要API
    """
    user_id = session.get('user_id')
    user_ai_config = get_user_ai_config(user_id)

    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    max_length = data.get('max_length', 200)

    if not title:
        return jsonify({'success': False, 'error': '标题不能为空'}), 400

    if not content:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    try:
        result = TagGenerator.generate_summary(
            title=title,
            content=content,
            user_config=user_ai_config,
            max_length=max_length
        )

        if not result:
            return jsonify({'success': False, 'error': 'AI功能未启用'}), 400

        # Save to AI history
        save_ai_tag_history(
            user_id=user_id,
            post_id=data.get('post_id'),
            action='generate_summary',
            provider=user_ai_config.get('ai_provider'),
            model_used=result.get('model'),
            tokens_used=result.get('tokens_used', 0),
            input_tokens=result.get('input_tokens', 0),
            output_tokens=result.get('output_tokens', 0),
            cost=result.get('cost', 0),
            result_preview=result.get('summary', '')[:100]
        )

        return jsonify({
            'success': True,
            'summary': result['summary'],
            'tokens_used': result['tokens_used'],
            'model': result['model']
        })

    except Exception as e:
        logger.error(f"AI summary generation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_bp.route('/recommend-posts', methods=['POST'])
@login_required
def recommend_posts():
    """
    AI推荐相关文章API
    """
    user_id = session.get('user_id')
    user_ai_config = get_user_ai_config(user_id)

    data = request.get_json()
    post_id = data.get('post_id')
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    max_recommendations = data.get('max_recommendations', 3)

    if not post_id:
        return jsonify({'success': False, 'error': '文章ID不能为空'}), 400

    if not title or not content:
        return jsonify({'success': False, 'error': '标题和内容不能为空'}), 400

    try:
        # Get all published posts
        all_posts_data = get_all_posts(include_drafts=False)
        all_posts = all_posts_data.get('posts', [])

        result = TagGenerator.recommend_related_posts(
            current_post_id=post_id,
            title=title,
            content=content,
            all_posts=all_posts,
            user_config=user_ai_config,
            max_recommendations=max_recommendations
        )

        if not result:
            return jsonify({'success': False, 'error': 'AI功能未启用'}), 400

        # Save to AI history
        save_ai_tag_history(
            user_id=user_id,
            post_id=post_id,
            action='recommend_posts',
            provider=user_ai_config.get('ai_provider'),
            model_used=result.get('model'),
            tokens_used=result.get('tokens_used', 0),
            input_tokens=result.get('input_tokens', 0),
            output_tokens=result.get('output_tokens', 0),
            cost=result.get('cost', 0),
            result_preview=f"Recommended {len(result.get('recommendations', []))} posts",
            recommendations_count=len(result.get('recommendations', []))
        )

        # Debug: log the recommendations data
        logger.info(f"Recommendations data type: {type(result['recommendations'])}")
        logger.info(f"Recommendations data: {result['recommendations']}")
        if result['recommendations']:
            logger.info(f"First recommendation: {result['recommendations'][0]}")
            logger.info(f"First recommendation type: {type(result['recommendations'][0])}")

        return jsonify({
            'success': True,
            'recommendations': result['recommendations'],
            'tokens_used': result['tokens_used'],
            'model': result['model']
        })

    except Exception as e:
        logger.error(f"AI recommendation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_bp.route('/continue-writing', methods=['POST'])
@login_required
def continue_writing():
    """
    AI续写内容API
    """
    user_id = session.get('user_id')
    user_ai_config = get_user_ai_config(user_id)

    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    continuation_length = data.get('continuation_length', 500)

    if not title:
        return jsonify({'success': False, 'error': '标题不能为空'}), 400

    if not content:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    try:
        result = TagGenerator.continue_writing(
            title=title,
            content=content,
            user_config=user_ai_config,
            continuation_length=continuation_length
        )

        if not result:
            return jsonify({'success': False, 'error': 'AI功能未启用'}), 400

        # Save to AI history
        save_ai_tag_history(
            user_id=user_id,
            post_id=data.get('post_id'),
            action='continue_writing',
            provider=user_ai_config.get('ai_provider'),
            model_used=result.get('model'),
            tokens_used=result.get('tokens_used', 0),
            input_tokens=result.get('input_tokens', 0),
            output_tokens=result.get('output_tokens', 0),
            cost=result.get('cost', 0),
            result_preview=result.get('continuation', '')[:100],
            continuation_length=continuation_length
        )

        return jsonify({
            'success': True,
            'continuation': result['continuation'],
            'tokens_used': result['tokens_used'],
            'model': result['model']
        })

    except Exception as e:
        logger.error(f"AI writing continuation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
