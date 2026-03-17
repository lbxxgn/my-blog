"""草稿同步API路由"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from models.draft import (
    save_draft,
    get_drafts,
    get_draft,
    update_draft,
    resolve_conflict,
    delete_draft,
)

drafts_bp = Blueprint('drafts', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

@drafts_bp.route('/api/drafts', methods=['POST'])
@login_required
def api_save_draft():
    """保存草稿"""
    try:
        data = request.get_json()
        user_id = session['user_id']

        result = save_draft(
            user_id=user_id,
            post_id=data.get('post_id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            category_id=data.get('category_id'),
            tags=data.get('tags', []),
            device_info=data.get('device_info', '')
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts', methods=['GET'])
@login_required
def api_get_drafts():
    """获取草稿列表"""
    try:
        post_id = request.args.get('post_id', type=int)
        user_id = session['user_id']

        drafts = get_drafts(user_id, post_id)
        return jsonify({'success': True, 'drafts': drafts}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/<int:draft_id>', methods=['GET'])
@login_required
def api_get_draft(draft_id):
    """获取单个草稿"""
    try:
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'success': False, 'error': '草稿不存在'}), 404

        payload = {'success': True, 'draft': draft}
        payload.update(draft)
        return jsonify(payload), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/<int:draft_id>', methods=['PUT'])
@login_required
def api_update_draft(draft_id):
    """更新草稿"""
    try:
        data = request.get_json() or {}
        user_id = session['user_id']
        current = get_draft(draft_id)

        if not current:
            return jsonify({'success': False, 'error': '草稿不存在'}), 404

        client_version = data.get('client_version')
        server_version = data.get('server_version')
        if client_version and server_version and client_version != server_version:
            return jsonify({
                'success': False,
                'error': '检测到版本冲突',
                'status': 'conflict',
                'draft': current
            }), 409

        updated = update_draft(
            draft_id=draft_id,
            user_id=user_id,
            title=data.get('title', current.get('title', '')),
            content=data.get('content', current.get('content', '')),
            category_id=data.get('category_id', current.get('category_id')),
            tags=data.get('tags', current.get('tags', []))
        )

        if not updated:
            return jsonify({'success': False, 'error': '草稿不存在'}), 404

        payload = {'success': True, 'draft': updated}
        payload.update(updated)
        return jsonify(payload), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/resolve', methods=['POST'])
@login_required
def api_resolve_conflict():
    """解决草稿冲突"""
    try:
        data = request.get_json() or {}

        if 'resolution' in data and 'draft_id' in data:
            resolution = data.get('resolution')
            draft = get_draft(data['draft_id'])
            if not draft:
                return jsonify({'success': False, 'error': '草稿不存在'}), 404

            if resolution == 'use_client':
                updated = update_draft(
                    draft_id=data['draft_id'],
                    user_id=session['user_id'],
                    title=draft.get('title', ''),
                    content=data.get('client_content', draft.get('content', '')),
                    category_id=draft.get('category_id'),
                    tags=draft.get('tags', [])
                )
                return jsonify({'success': True, 'draft': updated}), 200

            return jsonify({'success': True, 'draft': draft}), 200

        result = resolve_conflict(
            conflict_draft_id=data['conflict_draft_id'],
            current_draft_id=data['current_draft_id'],
            action=data['action'],
            merged_data=data.get('merged_data')
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/<int:draft_id>', methods=['DELETE'])
@login_required
def api_delete_draft(draft_id):
    """删除草稿"""
    try:
        user_id = session['user_id']
        result = delete_draft(draft_id, user_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
