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
    get_user_by_id, merge_cards_to_post
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

