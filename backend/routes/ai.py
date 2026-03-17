"""
AI功能路由

包括AI标签生成、摘要生成、相关文章推荐、内容续写等功能。
"""

import json
import re

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


def _heuristic_title(content: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', content or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return '未命名记录'
    sentence = re.split(r'[。！？.!?\n]', text)[0].strip()
    return sentence[:24] if sentence else text[:24]


def _heuristic_summary(content: str, max_length: int = 120) -> str:
    text = re.sub(r'<[^>]+>', ' ', content or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + '...'


def _heuristic_type(title: str, content: str) -> str:
    combined = f"{title} {content}".lower()
    daily_keywords = ['今天', '昨天', '周末', '日常', '生活', '旅行', '见闻', '心情']
    knowledge_keywords = ['原理', '教程', '知识', '总结', '学习', '方法', 'flask', 'python', 'sql', 'api']
    idea_keywords = ['想法', '点子', '构想', '计划', '灵感', '尝试']

    if any(keyword in combined for keyword in daily_keywords):
        return 'daily'
    if any(keyword in combined for keyword in knowledge_keywords):
        return 'knowledge'
    if any(keyword in combined for keyword in idea_keywords):
        return 'idea'
    return 'knowledge' if len(combined) > 180 else 'idea'


def _heuristic_tags(title: str, content: str, max_tags: int = 4):
    combined = f"{title} {content}"
    candidates = re.findall(r'[\u4e00-\u9fffA-Za-z0-9#+.-]{2,12}', combined)
    stop_words = {
        '然后', '这个', '那个', '我们', '你们', '他们', '就是', '因为',
        '所以', '如果', '但是', '关于', '可以', '进行', '需要', '一个',
        '自己', '已经', '一下', '还是', '没有', '文章', '内容', '记录'
    }
    tags = []
    for candidate in candidates:
        lowered = candidate.lower()
        if lowered in stop_words or candidate.isdigit():
            continue
        if candidate not in tags:
            tags.append(candidate)
        if len(tags) >= max_tags:
            break
    return tags or ['随记']


def _pick_category(categories, title: str, content: str, tags):
    combined = f"{title} {content} {' '.join(tags or [])}".lower()
    best_match = None
    best_score = 0
    for category in categories or []:
        name = (category.get('name') or '').strip()
        if not name:
            continue
        score = 0
        lowered = name.lower()
        if lowered in combined:
            score += 3
        for fragment in re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', lowered):
            if fragment and fragment in combined:
                score += 1
        if score > best_score:
            best_match = category
            best_score = score
    return best_match


def _run_structured_prompt(user_config, system_prompt: str, user_prompt: str, max_tokens: int = 500, temperature: float = 0.3):
    if not user_config or not user_config.get('ai_tag_generation_enabled'):
        return None

    provider = TagGenerator.create_provider(
        user_config.get('ai_provider', 'openai'),
        user_config.get('ai_api_key'),
        user_config.get('ai_model')
    )

    if not getattr(provider, 'client', None) and hasattr(provider, '_init_client'):
        provider._init_client()

    response = provider.client.chat.completions.create(
        model=provider.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )

    content = response.choices[0].message.content.strip()
    usage = response.usage
    return {
        'content': content,
        'model': provider.model,
        'tokens_used': usage.total_tokens,
        'input_tokens': usage.prompt_tokens,
        'output_tokens': usage.completion_tokens
    }


def _parse_json_block(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


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
                parsed = json.loads(record['generated_tags'])

                # If it's a list (old format), keep it as is
                # If it's a dict (new format), use it as parsed_data
                if isinstance(parsed, dict):
                    record['parsed_data'] = parsed
                else:
                    record['parsed_data'] = None
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse AI history JSON: {e}")
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


@ai_bp.route('/organize-content', methods=['POST'])
@login_required
def organize_content():
    """根据输入内容生成整理建议。"""
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    categories = data.get('categories') or []

    if not content:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    user_id = session.get('user_id')
    user_ai_config = get_user_ai_config(user_id)

    suggestion = {
        'title': title or _heuristic_title(content),
        'summary': _heuristic_summary(content),
        'tags': _heuristic_tags(title, content),
        'content_type': _heuristic_type(title, content),
        'category': None,
        'source': 'heuristic'
    }

    heuristic_category = _pick_category(categories, suggestion['title'], content, suggestion['tags'])
    if heuristic_category:
        suggestion['category'] = {
            'id': heuristic_category.get('id'),
            'name': heuristic_category.get('name')
        }

    ai_result = None
    try:
        category_names = [c.get('name') for c in categories if c.get('name')]
        ai_result = _run_structured_prompt(
            user_ai_config,
            system_prompt='你是一个擅长整理个人笔记、知识点和灵感的写作助手。请返回严格 JSON。',
            user_prompt=f"""请根据以下输入内容，返回一个 JSON 对象，包含：
- title: 更合适的标题（18字以内）
- summary: 120字以内摘要
- tags: 3到5个标签数组
- content_type: 只能是 daily、knowledge、idea 之一
- category_name: 如果分类列表里有合适项，返回最匹配的分类名称，否则返回空字符串

可选分类：{', '.join(category_names) if category_names else '无'}
当前标题：{title or '（未填写）'}
内容：
{content[:3000]}
""",
            max_tokens=450,
            temperature=0.2
        )
    except Exception as e:
        logger.warning(f"AI organize content fallback to heuristic: {e}")

    if ai_result:
        try:
            parsed = _parse_json_block(ai_result['content'])
            ai_title = (parsed.get('title') or '').strip()
            ai_summary = (parsed.get('summary') or '').strip()
            ai_tags = parsed.get('tags') or []
            ai_type = (parsed.get('content_type') or '').strip().lower()
            ai_category_name = (parsed.get('category_name') or '').strip()

            if ai_title:
                suggestion['title'] = ai_title
            if ai_summary:
                suggestion['summary'] = ai_summary
            if isinstance(ai_tags, list) and ai_tags:
                suggestion['tags'] = [str(tag).strip() for tag in ai_tags if str(tag).strip()][:5]
            if ai_type in {'daily', 'knowledge', 'idea'}:
                suggestion['content_type'] = ai_type
            if ai_category_name:
                matched = next((c for c in categories if c.get('name') == ai_category_name), None)
                if matched:
                    suggestion['category'] = {
                        'id': matched.get('id'),
                        'name': matched.get('name')
                    }

            suggestion['source'] = 'ai'
            suggestion['tokens_used'] = ai_result['tokens_used']
            suggestion['model'] = ai_result['model']

            save_ai_tag_history(
                user_id=user_id,
                post_id=data.get('post_id'),
                action='organize_content',
                provider=user_ai_config.get('ai_provider') if user_ai_config else None,
                model_used=ai_result.get('model'),
                tokens_used=ai_result.get('tokens_used', 0),
                input_tokens=ai_result.get('input_tokens', 0),
                output_tokens=ai_result.get('output_tokens', 0),
                result_preview=json.dumps({
                    'title': suggestion['title'],
                    'content_type': suggestion['content_type'],
                    'tags': suggestion['tags']
                }, ensure_ascii=False)
            )
        except Exception as e:
            logger.warning(f"Failed to parse AI organize response, using heuristics: {e}")

    return jsonify({
        'success': True,
        'suggestion': suggestion
    })
