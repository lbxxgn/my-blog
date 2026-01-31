"""
知识库路由

提供浏览器插件API端点和页面路由：
- /api/plugin/* - 浏览器插件API
- /quick-note - 快速记事页面
- /timeline - 时间线页面
- /incubator - 孵化箱页面
- /api/cards/* - 卡片管理API
"""

from flask import Blueprint, request, jsonify, g, session, redirect, url_for, render_template
from functools import wraps
from auth_decorators import login_required
from models import (
    create_card, get_card_by_id, get_cards_by_user,
    update_card_status, update_card, delete_card, get_timeline_items,
    get_user_by_id, merge_cards_to_post, get_user_ai_config, ai_merge_cards_to_post,
    create_annotation, get_annotations_by_url
)
import json
from logger import log_operation

knowledge_base_bp = Blueprint('knowledge_base', __name__)

# Note: CSRF exemption is handled in app.py after blueprint registration
# with: csrf.exempt(knowledge_base_bp)

# =============================================================================
# 浏览器插件 API
# =============================================================================

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

    # Validate content is not empty
    if not content or not content.strip():
        return jsonify({'success': False, 'error': 'Content is required'}), 400

    # Validate content length
    valid, error_msg = validate_content_length(content)
    if not valid:
        return jsonify({'success': False, 'error': error_msg}), 413

    # Add source URL to content if provided
    if source_url:
        content = f"{content}\n\n来源: {source_url}"

    try:
        card_id = create_card(
            user_id=g.user_id,
            title=title,
            content=content,
            tags=tags,
            status='idea',
            source='plugin'
        )

        log_operation(g.user_id, 'browser_extension',
                      f'浏览器插件提交', f'卡片ID: {card_id}, 类型: {annotation_type}')

        return jsonify({
            'success': True,
            'card_id': card_id,
            'message': 'Saved successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_base_bp.route('/api/plugin/sync-annotations', methods=['POST'])
@api_key_required
def sync_annotations():
    """同步页面标注"""
    data = request.get_json()
    url = data.get('url', '')
    annotations = data.get('annotations', [])

    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400

    if not annotations:
        return jsonify({'success': False, 'error': 'No annotations provided'}), 400

    try:
        annotation_ids = []

        for ann in annotations:
            # Validate annotation data
            errors = validate_annotation_data(ann)
            if errors:
                return jsonify({'success': False, 'error': 'Validation failed: ' + '; '.join(errors)}), 400

            # Create annotation
            ann_id = create_annotation(
                user_id=g.user_id,
                source_url=url,
                annotation_text=ann.get('text', ''),
                xpath=ann.get('xpath', ''),
                color=ann.get('color', 'yellow'),
                note=ann.get('note', ''),
                annotation_type=ann.get('annotation_type', 'highlight')
            )
            annotation_ids.append(ann_id)

        log_operation(g.user_id, 'browser_extension',
                      f'浏览器插件同步标注', f'URL: {url}, 标注数: {len(annotation_ids)}')

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
    """获取页面的标注"""
    url = request.args.get('url')

    if not url:
        return jsonify({'success': False, 'error': 'URL parameter is required'}), 400

    try:
        annotations = get_annotations_by_url(g.user_id, url)

        # Format response
        formatted_annotations = []
        for ann in annotations:
            formatted_annotations.append({
                'id': ann['id'],
                'annotation_text': ann['annotation_text'],
                'xpath': ann['xpath'],
                'color': ann['color'],
                'note': ann['note'],
                'annotation_type': ann['annotation_type'],
                'created_at': ann['created_at']
            })

        return jsonify({
            'success': True,
            'annotations': formatted_annotations,
            'count': len(formatted_annotations)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_base_bp.route('/api/plugin/recent', methods=['GET'])
@api_key_required
def get_recent_captures():
    """获取最近捕获的卡片"""
    from models import get_cards_by_user

    limit = request.args.get('limit', 10, type=int)
    limit = min(limit, 50)  # Cap at 50

    try:
        cards = get_cards_by_user(g.user_id, limit=limit)

        # Format cards for response
        formatted_cards = []
        for card in cards:
            formatted_cards.append({
                'id': card['id'],
                'title': card['title'],
                'content': card['content'],
                'tags': json.loads(card['tags']) if card['tags'] else [],
                'status': card['status'],
                'source': card['source'],
                'created_at': card['created_at']
            })

        return jsonify({
            'success': True,
            'cards': formatted_cards,
            'count': len(formatted_cards)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# 页面路由
# =============================================================================

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


# =============================================================================
# 卡片管理 API
# =============================================================================

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
