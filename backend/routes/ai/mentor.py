"""AI 导师点评（ai 蓝图子模块）。"""


from flask import request, session, jsonify

from models import (
    get_user_ai_config, save_ai_tag_history
)
from auth_decorators import login_required
from logger import api_internal_error





from . import ai_bp, logger, _heuristic_title, _heuristic_summary, _heuristic_type, _heuristic_tags, _pick_category, _run_structured_prompt, _parse_json_block  # noqa: F401


@ai_bp.route('/mentor-comment', methods=['POST'])
@login_required
def mentor_comment():
    """
    人生导师式点评 API

    针对文章中表达的想法，给出真诚、具体的回应与指导。
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
                '你是一个真实的人——一位读了作者很多年博客的老朋友，阅历比作者多一些，'
                '说话直接、有温度，也有自己的脾气和偏好。'
                '你回复别人的博客时从来不用固定套路：有时只回一两句戳到点子上的话，'
                '有时讲到自己经历过的事就多写几句。你从不为了凑长度而说话。'
                '你讨厌正确的废话、空洞的鼓励和"首先其次最后"式的腔调。'
            ),
            user_prompt=f"""读下面这篇博客，像老朋友看完文章后随手写下的回应那样，给作者留一段话。

写之前先问自己：这篇文章真正触动你的具体是什么？你想跟作者说什么心里话？
然后就从那句话开始写，想到哪写到哪，让它自然结束。

几条底线：
- 每次回应的形态都要不一样：可以只抓住一个细节聊，可以提出一个不同看法，可以讲你自己的类似经历，可以只反问一个问题。不要每次都"先夸优点、再指盲区、后给建议"。
- 只说有实质内容的话。如果没那么多可说，两三句话也完全可以，短不等于敷衍。
- 必须出现文章里的具体细节或原话，让作者知道你认真读了。
- 用口语，像微信里打字那样。可以偶尔有不那么工整的句子。禁用列表、小标题、"总的来说""总而言之""希望你""加油"这类词。
- 直接输出回应正文，不要开场白、称呼或落款。

文章标题：{title or '（无标题）'}

文章内容：
{content[:4000]}
""",
            max_tokens=700,
            temperature=0.9
        )
    except Exception as e:
        logger.error(f"AI mentor comment error: {e}")
        return api_internal_error(e)

    if not result:
        return jsonify({'success': False, 'error': 'AI功能未启用，请先在 AI 设置中启用并配置密钥'}), 400

    save_ai_tag_history(
        user_id=user_id,
        post_id=data.get('post_id'),
        action='mentor_comment',
        provider=user_ai_config.get('ai_provider'),
        model_used=result.get('model'),
        tokens_used=result.get('tokens_used', 0),
        input_tokens=result.get('input_tokens', 0),
        output_tokens=result.get('output_tokens', 0),
        result_preview=result['content'][:100]
    )

    return jsonify({
        'success': True,
        'comment': result['content'],
        'tokens_used': result['tokens_used'],
        'model': result['model']
    })
