"""草稿同步API路由"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from models.draft import save_draft, get_drafts, get_draft, resolve_conflict, delete_draft

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

        return jsonify({'success': True, 'draft': draft}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/resolve', methods=['POST'])
@login_required
def api_resolve_conflict():
    """解决草稿冲突"""
    try:
        data = request.get_json()
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
