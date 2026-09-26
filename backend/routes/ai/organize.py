"""内容整理与结构重排（ai 蓝图子模块）。"""

import json
import re

from flask import request, session, jsonify

from models import (
    get_user_ai_config, save_ai_tag_history
)
from auth_decorators import login_required
from logger import api_internal_error





from . import ai_bp, logger, _heuristic_title, _heuristic_summary, _heuristic_type, _heuristic_tags, _pick_category, _run_structured_prompt, _parse_json_block  # noqa: F401


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

@ai_bp.route('/restructure', methods=['POST'])
@login_required
def restructure_content():
    """
    AI 重组文章语言与格式 API

    保持原意不变，重新组织语言并让文章结构（HTML 格式）更合理。
    """
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()

    if not content:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    user_id = session.get('user_id')
    user_ai_config = get_user_ai_config(user_id)

    try:
        result = _run_structured_prompt(
            user_ai_config,
            system_prompt=(
                '你是一位专业的中文编辑，擅长把零散、缺乏条理的文字整理成结构清晰、'
                '读起来顺畅的文章，同时完全尊重作者的原意和个人风格。'
            ),
            user_prompt=f"""请重组下面这篇文章的语言和格式。

要求：
1. 完整保留作者的原意、事实、观点和个人口吻（第一人称不变），不要增删观点
2. 把想到哪写到哪的内容按逻辑重新分段、排序，让行文有条理
3. 合理使用 HTML 结构：<h2>/<h3> 小节标题（需要时提炼）、<p> 段落、<ul>/<ol> 列表、<strong> 重点、<blockquote> 引用
4. 原文中的所有 <img> 标签必须原样保留在合适位置，不得丢失或修改
5. 原文中的链接（<a>）保留
6. 只输出重组后的 HTML 正文，不要输出解释、不要用 ``` 代码围栏包裹、不要包含文章大标题（<h1>）

文章标题（仅供参考，不要输出）：{title or '（无标题）'}

原文：
{content[:6000]}
""",
            max_tokens=3000,
            temperature=0.4
        )
    except Exception as e:
        logger.error(f"AI restructure error: {e}")
        return api_internal_error(e)

    if not result:
        return jsonify({'success': False, 'error': 'AI功能未启用，请先在 AI 设置中启用并配置密钥'}), 400

    # 去掉模型可能残留的代码围栏
    html = result['content'].strip()
    if html.startswith('```'):
        html = re.sub(r'^```[a-zA-Z]*\s*', '', html)
        html = re.sub(r'\s*```$', '', html)

    save_ai_tag_history(
        user_id=user_id,
        post_id=data.get('post_id'),
        action='restructure',
        provider=user_ai_config.get('ai_provider'),
        model_used=result.get('model'),
        tokens_used=result.get('tokens_used', 0),
        input_tokens=result.get('input_tokens', 0),
        output_tokens=result.get('output_tokens', 0),
        result_preview=html[:100]
    )

    return jsonify({
        'success': True,
        'content': html,
        'tokens_used': result['tokens_used'],
        'model': result['model']
    })
