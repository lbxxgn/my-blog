"""
知识库路由 - 浏览器插件API

提供浏览器插件使用的API端点：
- /api/plugin/submit - 提交内容到知识库
- /api/plugin/sync-annotations - 同步页面标注
- /api/plugin/annotations - 获取页面标注
"""

from flask import Blueprint, request, jsonify, g
from functools import wraps
from logger import log_operation

knowledge_base_bp = Blueprint('knowledge_base', __name__)

# Note: CSRF exemption is handled in app.py after blueprint registration
# with: csrf.exempt(knowledge_base_bp)


def api_key_required(f):
    """API密钥认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import validate_api_key

        api_key = request.headers.get('X-API-Key')
        user_id = validate_api_key(api_key)

        if not user_id:
            return jsonify({'success': False, 'error': 'Invalid or missing API key'}), 401

        # Store user_id in flask.g for use in the route
        g.user_id = user_id
        return f(*args, **kwargs)

    return decorated_function


@knowledge_base_bp.route('/api/plugin/submit', methods=['POST'])
@api_key_required
def plugin_submit():
    """接收浏览器插件提交的内容"""
    from models import create_card

    data = request.get_json()
    title = data.get('title', 'Untitled')
    content = data.get('content', '')
    source_url = data.get('source_url', '')
    tags = data.get('tags', [])
    annotation_type = data.get('annotation_type', 'capture')

    if not content:
        return jsonify({'success': False, 'error': 'Content is required'}), 400

    # Build full content with metadata
    full_content = f"Source: {source_url}\n\n{content}"

    # Create card
    card_id = create_card(
        user_id=g.user_id,
        title=title,
        content=full_content,
        status='idea',
        source='browser-extension',
        tags=tags
    )

    log_operation(g.user_id, 'Plugin',
                 f'Plugin submitted content', f'Source: {source_url}')

    return jsonify({
        'success': True,
        'card_id': card_id,
        'message': 'Saved successfully'
    })


@knowledge_base_bp.route('/api/plugin/sync-annotations', methods=['POST'])
@api_key_required
def sync_annotations():
    """同步页面标注数据"""
    from models import create_annotation

    data = request.get_json()
    url = data.get('url')
    annotations = data.get('annotations', [])

    if not url or not annotations:
        return jsonify({'success': False, 'error': 'URL and annotations required'}), 400

    try:
        annotation_ids = []
        for ann in annotations:
            ann_id = create_annotation(
                user_id=g.user_id,
                source_url=url,
                annotation_text=ann.get('text'),
                xpath=ann.get('xpath'),
                color=ann.get('color', 'yellow'),
                note=ann.get('note'),
                annotation_type=ann.get('annotation_type', 'highlight')
            )
            annotation_ids.append(ann_id)

        return jsonify({
            'success': True,
            'annotation_ids': annotation_ids,
            'count': len(annotation_ids)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_base_bp.route('/api/plugin/annotations', methods=['GET'])
@api_key_required
def get_annotations():
    """获取指定URL的所有标注"""
    from models import get_annotations_by_url

    url = request.args.get('url')

    if not url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400

    try:
        annotations = get_annotations_by_url(g.user_id, url)

        return jsonify({
            'success': True,
            'annotations': annotations,
            'count': len(annotations)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
