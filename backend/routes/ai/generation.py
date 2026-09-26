"""生成类能力（标签/摘要/标题/续写/推荐）（ai 蓝图子模块）。"""


from flask import request, session, jsonify

from ai_services import TagGenerator
from models import (
    get_user_ai_config, save_ai_tag_history, get_all_posts
)
from auth_decorators import login_required
from logger import log_operation, log_error, api_internal_error





from . import ai_bp, logger, _heuristic_title, _heuristic_summary, _heuristic_type, _heuristic_tags, _pick_category, _run_structured_prompt, _parse_json_block  # noqa: F401


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
            'error': '标签生成失败，请稍后重试'
        }), 500

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
        return api_internal_error(e)

@ai_bp.route('/generate-title', methods=['POST'])
@login_required
def generate_title():
    """
    根据内容自动生成标题
    """
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()

    if not content:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    user_id = session.get('user_id')
    user_ai_config = get_user_ai_config(user_id)

    # 启发式标题作为 fallback
    title = _heuristic_title(content)
    source = 'heuristic'

    # 尝试 AI 生成
    if user_ai_config and user_ai_config.get('ai_tag_generation_enabled'):
        try:
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
                    title = ai_title
                    source = 'ai'

                    # 记录历史
                    save_ai_tag_history(
                        user_id=user_id,
                        post_id=data.get('post_id'),
                        action='generate_title',
                        provider=user_ai_config.get('ai_provider'),
                        model_used=ai_result.get('model'),
                        tokens_used=ai_result.get('tokens_used', 0),
                        input_tokens=ai_result.get('input_tokens', 0),
                        output_tokens=ai_result.get('output_tokens', 0),
                        result_preview=title
                    )
        except Exception as e:
            logger.warning(f"AI title generation failed, using heuristic: {e}")

    return jsonify({
        'success': True,
        'title': title,
        'source': source
    })

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
        return api_internal_error(e)

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
        return api_internal_error(e)
