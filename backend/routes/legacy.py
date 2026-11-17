"""旧客户端路径兼容入口。

这些路径与 blueprint 的 url_prefix 不同，浏览器插件/历史客户端仍在使用；
保留为独立 blueprint，避免继续堆积在 app.py，同时便于后续 301/307 废弃。
"""
from flask import Blueprint, current_app, jsonify, redirect, request, url_for

legacy_bp = Blueprint('legacy', __name__)


@legacy_bp.route('/new', methods=['GET', 'POST'])
def legacy_new_post():
    """历史新建文章入口，302 重定向到后台新建页。"""
    return redirect(url_for('admin.new_post'), code=302)


@legacy_bp.route('/api/plugin/submit', methods=['POST'])
def plugin_submit():
    return current_app.view_functions['knowledge_base.plugin_submit']()


@legacy_bp.route('/api/plugin/sync-annotations', methods=['POST'])
def plugin_sync_annotations():
    return current_app.view_functions['knowledge_base.sync_annotations']()


@legacy_bp.route('/api/plugin/annotations', methods=['GET'])
def plugin_annotations():
    if not request.args.get('url'):
        return jsonify({'success': True, 'annotations': [], 'count': 0})
    return current_app.view_functions['knowledge_base.get_annotations']()


@legacy_bp.route('/api/plugin/recent', methods=['GET'])
def plugin_recent():
    return current_app.view_functions['knowledge_base.get_recent_captures']()


@legacy_bp.route('/api/cards', methods=['GET'])
def cards_list():
    return current_app.view_functions['knowledge_base.card_list']()


@legacy_bp.route('/api/cards/<int:card_id>', methods=['GET', 'PUT', 'DELETE'])
def card_detail(card_id):
    return current_app.view_functions['knowledge_base.card_detail'](card_id)


@legacy_bp.route('/api/cards/<int:card_id>/status', methods=['PUT'])
def card_status(card_id):
    return current_app.view_functions['knowledge_base.card_status'](card_id)


@legacy_bp.route('/api/cards/merge', methods=['POST'])
def cards_merge():
    return current_app.view_functions['knowledge_base.merge_cards']()


@legacy_bp.route('/api/cards/generate-tags', methods=['POST'])
def cards_generate_tags():
    return current_app.view_functions['knowledge_base.generate_card_tags']()


@legacy_bp.route('/api/cards/ai-merge', methods=['POST'])
def cards_ai_merge():
    return current_app.view_functions['knowledge_base.ai_merge_cards']()


@legacy_bp.route('/api/card/<int:card_id>/convert-to-post', methods=['POST'])
def convert_card_to_post(card_id):
    return current_app.view_functions['knowledge_base.convert_card_to_post'](card_id)
