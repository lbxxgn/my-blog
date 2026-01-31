"""
知识库路由

功能:
- 快速记事页面
- 时间线页面
- 卡片管理
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from auth_decorators import login_required
from models import (
    create_card, get_card_by_id, get_cards_by_user,
    update_card_status, update_card, delete_card, get_timeline_items,
    get_user_by_id, merge_cards_to_post, get_user_ai_config, ai_merge_cards_to_post
)
import json
from logger import log_operation

knowledge_base_bp = Blueprint('knowledge_base', __name__)


@knowledge_base_bp.route('/quick-note', methods=['GET', 'POST'])
@login_required
def quick_note():
    """快速记事页面"""
    if request.method == 'POST':
        # Handle both form and JSON requests
        try:
            if request.is_json:
                data = request.get_json()
                title = data.get('title', '')
                content = data.get('content', '')
            else:
                title = request.form.get('title', '')
                content = request.form.get('content', '')

            if not content:
                return jsonify({'success': False, 'error': '内容不能为空'}), 400

            # Create card with 'idea' status
            card_id = create_card(
                user_id=session['user_id'],
                title=title if title else None,
                content=content,
                status='idea',
                source='web'
            )

            log_operation(session['user_id'], session.get('username', 'Unknown'),
                          f'创建快速笔记', f'卡片ID: {card_id}')

            if request.is_json:
                return jsonify({'success': True, 'card_id': card_id})
            else:
                return redirect(url_for('knowledge_base.timeline'))
        except Exception as e:
            import traceback
            traceback.print_exc()  # 打印到控制台
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 500
            else:
                return redirect(url_for('knowledge_base.timeline'))

    return render_template('quick_note.html')


@knowledge_base_bp.route('/timeline')
@login_required
def timeline():
    """时间线页面"""
    cursor_time = request.args.get('cursor')

    result = get_timeline_items(
        user_id=session['user_id'],
        limit=20,
        cursor_time=cursor_time
    )

    # Get user info
    user = get_user_by_id(session['user_id'])

    # Get stats
    all_cards = get_cards_by_user(session['user_id'])
    stats = {
        'total': len(all_cards),
        'ideas': len([c for c in all_cards if c['status'] == 'idea']),
        'incubating': len([c for c in all_cards if c['status'] == 'incubating']),
        'drafts': len([c for c in all_cards if c['status'] == 'draft'])
    }

    return render_template('timeline.html',
                         items=result['items'],
                         next_cursor=result['next_cursor'],
                         has_more=result['has_more'],
                         stats=stats,
                         user=user)


@knowledge_base_bp.route('/api/cards/<int:card_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def card_detail(card_id):
    """卡片详情API"""
    card = get_card_by_id(card_id)

    if not card or card['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '卡片不存在'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        update_card(
            card_id,
            title=data.get('title'),
            content=data.get('content'),
            tags=data.get('tags'),
            status=data.get('status')
        )
        return jsonify({'success': True})

    elif request.method == 'DELETE':
        delete_card(card_id)
        return jsonify({'success': True})

    return jsonify({'success': True, 'card': card})


@knowledge_base_bp.route('/api/cards/<int:card_id>/status', methods=['PUT'])
@login_required
def card_status(card_id):
    """更新卡片状态"""
    card = get_card_by_id(card_id)

    if not card or card['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '卡片不存在'}), 404

    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['idea', 'draft', 'incubating', 'published']:
        return jsonify({'success': False, 'error': '无效的状态'}), 400

    update_card_status(card_id, new_status)
    log_operation(session['user_id'], session.get('username', 'Unknown'),
                  f'更新卡片状态', f'卡片ID: {card_id}, 新状态: {new_status}')

    return jsonify({'success': True})


@knowledge_base_bp.route('/api/cards/merge', methods=['POST'])
@login_required
def merge_cards():
    """合并卡片到文章"""
    data = request.get_json()
    card_ids = data.get('card_ids', [])
    action = data.get('action', 'create_post')
    post_id = data.get('post_id')

    if not card_ids:
        return jsonify({'success': False, 'error': '请选择要合并的卡片'}), 400

    try:
        if action == 'create_post':
            post_id = merge_cards_to_post(card_ids, session['user_id'])
        elif action == 'append_post':
            if not post_id:
                return jsonify({'success': False, 'error': '请指定目标文章'}), 400
            post_id = merge_cards_to_post(card_ids, session['user_id'], post_id)
        else:
            return jsonify({'success': False, 'error': '无效的操作'}), 400

        log_operation(session['user_id'], session.get('username', 'Unknown'),
                      f'合并卡片', f'卡片IDs: {card_ids} -> 文章ID: {post_id}')

        return jsonify({'success': True, 'post_id': post_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_base_bp.route('/api/cards/generate-tags', methods=['POST'])
@login_required
def generate_card_tags():
    """AI生成卡片标签"""
    from ai_services import TagGenerator

    data = request.get_json()
    card_id = data.get('card_id')

    if not card_id:
        return jsonify({'success': False, 'error': '卡片ID不能为空'}), 400

    # Get card
    card = get_card_by_id(card_id)
    if not card or card['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '卡片不存在'}), 404

    # Get user AI config
    user_ai_config = get_user_ai_config(session['user_id'])

    if not user_ai_config or not user_ai_config.get('ai_tag_generation_enabled', False):
        return jsonify({'success': False, 'error': 'AI标签生成功能未启用'}), 400

    try:
        # Generate tags using existing TagGenerator
        title = card['title'] or '无标题'
        content = card['content']

        result = TagGenerator.generate_for_post(
            title=title,
            content=content,
            user_config=user_ai_config,
            max_tags=5
        )

        if result and result.get('tags'):
            # Update card with generated tags
            update_card(card_id, tags=result['tags'])

            log_operation(session['user_id'], session.get('username', 'Unknown'),
                         f'AI生成卡片标签', f'卡片ID: {card_id}, 标签: {result["tags"]}')

            return jsonify({
                'success': True,
                'tags': result['tags'],
                'tokens_used': result.get('tokens_used', 0)
            })
        else:
            return jsonify({'success': False, 'error': '标签生成失败'}), 500

    except ValueError as e:
        # Configuration errors should return 400
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_base_bp.route('/api/cards/ai-merge', methods=['POST'])
@login_required
def ai_merge_cards():
    """AI合并卡片"""
    data = request.get_json()
    card_ids = data.get('card_ids', [])
    merge_style = data.get('merge_style', 'comprehensive')

    if not card_ids:
        return jsonify({'success': False, 'error': '请选择要合并的卡片'}), 400

    # Get user AI config
    user_ai_config = get_user_ai_config(session['user_id'])

    if not user_ai_config or not user_ai_config.get('ai_tag_generation_enabled', False):
        return jsonify({'success': False, 'error': 'AI功能未启用，请先在设置中配置'}), 400

    try:
        result = ai_merge_cards_to_post(
            card_ids=card_ids,
            user_id=session['user_id'],
            user_config=user_ai_config,
            merge_style=merge_style
        )

        log_operation(session['user_id'], session.get('username', 'Unknown'),
                     f'AI合并卡片', f'卡片IDs: {card_ids} -> 文章ID: {result["post_id"]}')

        return jsonify({
            'success': True,
            'post_id': result['post_id'],
            'title': result['title'],
            'outline': result.get('outline', ''),
            'tags': result.get('tags', []),
            'tokens_used': result.get('tokens_used', 0)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_base_bp.route('/incubator')
@login_required
def incubator():
    """孵化箱页面"""
    status = request.args.get('status', 'incubating')

    # Get cards by status
    cards = get_cards_by_user(session['user_id'], status=status)

    # Get user info
    user = get_user_by_id(session['user_id'])

    return render_template('incubator.html', cards=cards, user=user, current_status=status)

