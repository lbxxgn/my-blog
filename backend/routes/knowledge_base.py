"""
知识库路由 - 浏览器插件API

提供浏览器插件使用的API端点：
- /api/plugin/submit - 提交内容到知识库
- /api/plugin/sync-annotations - 同步页面标注
- /api/plugin/annotations - 获取页面标注
- /api/plugin/recent - 获取最近的卡片
"""

from flask import Blueprint, request, jsonify, g
from functools import wraps
from logger import log_operation

knowledge_base_bp = Blueprint('knowledge_base', __name__)

# Note: CSRF exemption is handled in app.py after blueprint registration
# with: csrf.exempt(knowledge_base_bp)

# Validation constants
VALID_ANNOTATION_COLORS = ['yellow', 'blue', 'green', 'pink', 'orange', 'purple']
VALID_ANNOTATION_TYPES = ['highlight', 'note', 'bookmark']
MAX_CONTENT_LENGTH = 1024 * 1024  # 1MB max content size


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


def validate_annotation_data(annotation):
    """验证标注数据"""
    errors = []

    # Validate color
    color = annotation.get('color', 'yellow')
    if color not in VALID_ANNOTATION_COLORS:
        errors.append(f"Invalid color '{color}'. Must be one of: {', '.join(VALID_ANNOTATION_COLORS)}")

    # Validate annotation_type
    ann_type = annotation.get('annotation_type', 'highlight')
    if ann_type not in VALID_ANNOTATION_TYPES:
        errors.append(f"Invalid annotation_type '{ann_type}'. Must be one of: {', '.join(VALID_ANNOTATION_TYPES)}")

    return errors


def validate_content_length(content):
    """验证内容长度"""
    if len(content) > MAX_CONTENT_LENGTH:
        return False, f'Content too large (max {MAX_CONTENT_LENGTH} bytes)'
    return True, None


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

    # Validate content length
    valid, error_msg = validate_content_length(content)
    if not valid:
        return jsonify({'success': False, 'error': error_msg}), 413

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

    # Validate all annotations first
    validation_errors = []
    for i, ann in enumerate(annotations):
        errors = validate_annotation_data(ann)
        if errors:
            validation_errors.append(f"Annotation {i}: {'; '.join(errors)}")

    if validation_errors:
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': validation_errors
        }), 400

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


@knowledge_base_bp.route('/api/plugin/recent', methods=['GET'])
@api_key_required
def get_recent_cards():
    """获取最近的知识库卡片"""
    from models import get_cards_by_user

    limit = request.args.get('limit', 10, type=int)
    limit = min(limit, 50)  # Cap at 50

    try:
        cards = get_cards_by_user(g.user_id, limit=limit)

        return jsonify({
            'success': True,
            'cards': cards,
            'count': len(cards)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
