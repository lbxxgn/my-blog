"""移动端接口（blog 蓝图子模块）。"""

from flask import request, session, jsonify
from models import (
    get_posts_by_author,
)

from . import blog_bp, logger, get_optimized_image_url, get_optimized_image_url_cached, extract_post_image_urls, extract_post_excerpt, rewrite_post_image_sources, determine_mobile_image_layout, build_post_card_payload, build_post_card_payloads, serialize_post_for_json  # noqa: F401


@blog_bp.route('/mobile/my-posts')
def mobile_my_posts():
    """Return the current user's posts for the mobile tabbed view."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401

    tab = request.args.get('tab', 'published')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    if per_page not in [5, 10, 20, 40]:
        per_page = 10

    if tab == 'drafts':
        all_posts = get_posts_by_author(user_id, include_drafts=True, page=1, per_page=10000)
        draft_posts = [post for post in all_posts['posts'] if not post.get('is_published')]
        total = len(draft_posts)
        start = (page - 1) * per_page
        end = start + per_page
        posts = draft_posts[start:end]
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    else:
        posts_data = get_posts_by_author(user_id, include_drafts=False, page=page, per_page=per_page)
        posts = posts_data['posts']
        total = posts_data['total']
        total_pages = posts_data['total_pages']

    return jsonify({
        'success': True,
        'tab': tab,
        'posts': [serialize_post_for_json(post) for post in posts],
        'page': page,
        'total': total,
        'total_pages': total_pages
    })
