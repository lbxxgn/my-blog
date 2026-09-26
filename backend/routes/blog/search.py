"""搜索（关键词 / 语义）（blog 蓝图子模块）。"""

from flask import render_template, request, session
from models import (
    search_posts,
)

from . import blog_bp, logger, get_optimized_image_url, get_optimized_image_url_cached, extract_post_image_urls, extract_post_excerpt, rewrite_post_image_sources, determine_mobile_image_layout, build_post_card_payload, build_post_card_payloads, serialize_post_for_json  # noqa: F401


@blog_bp.route('/search')
def search():
    """搜索文章（默认博客，支持 source=all/knowledge/semantic 切换来源）"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    source = request.args.get('source', 'blog')  # blog / knowledge / all / semantic

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    if source == 'semantic':
        return _search_semantic(query, source)

    if not query:
        return render_template('search.html', query='', posts=None, pagination=None, source=source,
                               embedding_configured=False, semantic_items=None)

    post_type_filter = 'blog' if source == 'blog' else ('knowledge' if source == 'knowledge' else 'all')
    posts_data = search_posts(query, include_drafts=False, page=page, per_page=per_page,
                              post_type_filter=post_type_filter)

    # 计算分页信息
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # 计算显示的页码范围
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    return render_template('search.html',
                         query=query,
                         posts=posts_data['posts'],
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis,
                         source=source,
                         embedding_configured=False,
                         semantic_items=None)

def _search_semantic(query, source):
    """语义搜索页：结果按相似度降序，不做分页与高亮"""
    from routes.search_helpers import (
        EmbeddingApiError,
        EmbeddingNotConfigured,
        is_embedding_configured,
        semantic_search,
    )

    user_id = session.get('user_id')
    embedding_configured = is_embedding_configured(user_id) if user_id else False
    semantic_items = None

    if query and embedding_configured:
        try:
            groups = semantic_search(user_id, query, limit=20)
        except (EmbeddingNotConfigured, EmbeddingApiError):
            groups = None
        if groups is not None:
            semantic_items = []
            label_map = {'post': '博客', 'doc': '知识库', 'card': '卡片'}
            for group_key, source_type in (('posts', 'post'), ('docs', 'doc'), ('cards', 'card')):
                for item in groups[group_key]:
                    semantic_items.append({
                        'title': item['title'],
                        'excerpt': item['excerpt'],
                        'url': item['url'],
                        'score': item['score'],
                        'source_label': label_map[source_type],
                    })
            semantic_items.sort(key=lambda x: x['score'], reverse=True)

    return render_template('search.html',
                           query=query,
                           posts=None,
                           pagination=None,
                           source=source,
                           embedding_configured=embedding_configured,
                           semantic_items=semantic_items)
