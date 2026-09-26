"""首页/归档/分类/标签/作者（blog 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, flash, jsonify
import json
from models import (
    get_all_posts, get_all_posts_cursor, get_all_categories, get_category_by_id, get_all_tags,
    get_tag_by_id, get_posts_by_tag, get_posts_by_author, get_user_by_id,
    get_popular_tags, get_db_connection,
)

from . import blog_bp, logger, get_optimized_image_url, get_optimized_image_url_cached, extract_post_image_urls, extract_post_excerpt, rewrite_post_image_sources, determine_mobile_image_layout, build_post_card_payload, build_post_card_payloads, serialize_post_for_json  # noqa: F401


@blog_bp.route('/')
def index():
    """首页 - 列出所有已发布的内容（文章和笔记）

    支持混合显示 post 和 note 类型的内容，通过 posts.type 字段区分。
    模板可通过 post.type 判断内容类型并选择不同的渲染方式。
    """
    format = request.args.get('format', 'html')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category', type=int)
    if category_id is None:
        category_id = request.args.get('category_id', type=int)

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    # 检查是否使用游标分页（更高效的分页方式）
    cursor_time = request.args.get('cursor')
    if cursor_time:
        posts_data = get_all_posts_cursor(
            cursor_time=cursor_time,
            per_page=per_page,
            include_drafts=False,
            category_id=category_id
        )
    else:
        # 保持向后兼容性，继续支持传统OFFSET分页
        posts_data = get_all_posts(
            include_drafts=False,
            page=page,
            per_page=per_page,
            category_id=category_id
        )
    categories = get_all_categories()
    popular_tags = get_popular_tags(limit=10)

    # JSON 格式支持（用于无限滚动）
    if format == 'json':
        # 处理两种分页格式
        if 'cursor' in request.args or 'next_cursor' in posts_data:
            # 游标分页格式
            return jsonify({
                'posts': build_post_card_payloads(posts_data['posts']),
                'next_cursor': posts_data.get('next_cursor'),
                'has_more': posts_data.get('has_more'),
                'per_page': posts_data.get('per_page')
            })
        else:
            # 传统OFFSET分页格式
            return jsonify({
                'posts': build_post_card_payloads(posts_data['posts']),
                'page': posts_data['page'],
                'total_pages': posts_data['total_pages'],
                'total': posts_data['total']
            })

    card_posts = build_post_card_payloads(posts_data['posts'])

    # 处理分页信息（根据使用的分页方式）
    if 'next_cursor' in posts_data:
        # 游标分页：显示"加载更多"按钮
        start_item = None
        end_item = None
        page_range = None
        show_ellipsis = False
        pagination = {
            'page': 1,
            'total_pages': None,  # 游标分页不返回总页数
            'total': None,
            'per_page': posts_data['per_page'],
            'has_more': posts_data.get('has_more'),
            'next_cursor': posts_data.get('next_cursor')
        }
    else:
        # 传统OFFSET分页：计算页码信息
        start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
        end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

        # 计算显示的页码范围
        page_start = max(1, posts_data['page'] - 2)
        page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
        page_range = list(range(page_start, page_end))
        show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2
        pagination = posts_data

    # 获取所有标签和分类供移动端使用
    all_tags = get_all_tags()
    all_tags_json = json.dumps([{'id': t.get('id', t.id if hasattr(t, 'id') else None), 'name': t.get('name', t.name if hasattr(t, 'name') else '')} for t in all_tags])
    all_categories_json = json.dumps([{'id': c.get('id', c.id if hasattr(c, 'id') else None), 'name': c.get('name', c.name if hasattr(c, 'name') else '')} for c in categories])

    return render_template('index.html',
                         posts=card_posts,
                         categories=categories,
                         popular_tags=popular_tags,
                         pagination=pagination,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis,
                         all_tags=all_tags_json,
                         all_categories=all_categories_json)

@blog_bp.route('/archive')
def archive():
    """
    文章归档 - 按时间筛选文章
    支持:
    - days: 最近N天的文章 (7/30/90/365)
    - year: 指定年份
    - month: 指定月份
    """
    from models import get_db_connection
    from flask import render_template

    days = request.args.get('days', type=int)
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建查询条件
    where_conditions = ["is_published = 1"]
    params = []

    if days:
        where_conditions.append(f"created_at >= datetime('now', '-{days} days')")

    if year:
        where_conditions.append("strftime('%Y', created_at) = ?")
        params.append(str(year))

        if month:
            where_conditions.append("strftime('%m', created_at) = ?")
            params.append(f"{month:02d}")

    where_clause = " AND ".join(where_conditions)

    query = f'''
        SELECT * FROM posts
        WHERE {where_clause}
        ORDER BY created_at DESC
    '''

    cursor.execute(query, params)
    posts = cursor.fetchall()
    conn.close()

    # 生成标题
    title = "文章归档"
    if days:
        title = f"最近{days}天"
    elif year and month:
        title = f"{year}年{month}月"
    elif year:
        title = f"{year}年"
    else:
        title = "全部归档"

    return render_template('archive.html', posts=posts, title=title)

@blog_bp.route('/category/<int:category_id>')
def view_category(category_id):
    """查看分类下的所有文章"""
    category = get_category_by_id(category_id)
    if not category:
        flash('分类不存在', 'error')
        return redirect(url_for('blog.index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    # 检查是否使用游标分页（更高效的分页方式）
    cursor_time = request.args.get('cursor')
    if cursor_time:
        posts_data = get_all_posts_cursor(
            cursor_time=cursor_time,
            per_page=per_page,
            include_drafts=False,
            category_id=category_id
        )
    else:
        # 保持向后兼容性，继续支持传统OFFSET分页
        posts_data = get_all_posts(
            include_drafts=False,
            page=page,
            per_page=per_page,
            category_id=category_id
        )

    if request.args.get('format') == 'json':
        # 处理两种分页格式
        if 'next_cursor' in posts_data:
            # 游标分页格式
            return jsonify({
                'posts': build_post_card_payloads(posts_data['posts']),
                'next_cursor': posts_data.get('next_cursor'),
                'has_more': posts_data.get('has_more'),
                'per_page': posts_data.get('per_page')
            })
        else:
            # 传统OFFSET分页格式
            return jsonify({
                'posts': build_post_card_payloads(posts_data['posts']),
                'page': posts_data['page'],
                'total_pages': posts_data['total_pages'],
                'total': posts_data['total']
            })

    card_posts = build_post_card_payloads(posts_data['posts'])

    # 处理分页信息（根据使用的分页方式）
    if 'next_cursor' in posts_data:
        # 游标分页：显示"加载更多"按钮
        start_item = None
        end_item = None
        page_range = None
        show_ellipsis = False
        pagination = {
            'page': 1,
            'total_pages': None,  # 游标分页不返回总页数
            'total': None,
            'per_page': posts_data['per_page'],
            'has_more': posts_data.get('has_more'),
            'next_cursor': posts_data.get('next_cursor')
        }
    else:
        # 传统OFFSET分页：计算页码信息
        start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
        end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

        # 计算显示的页码范围
        page_start = max(1, posts_data['page'] - 2)
        page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
        page_range = list(range(page_start, page_end))
        show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2
        pagination = posts_data

    # 获取所有分类用于筛选栏
    categories = get_all_categories()

    return render_template('index.html',
                         posts=card_posts,
                         category=category,
                         categories=categories,
                         pagination=pagination,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis)

@blog_bp.route('/tag/<int:tag_id>')
def view_tag(tag_id):
    """查看标签下的所有文章"""
    tag = get_tag_by_id(tag_id)
    if not tag:
        flash('标签不存在', 'error')
        return redirect(url_for('blog.index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_posts_by_tag(tag_id, include_drafts=False, page=page, per_page=per_page)

    # 计算分页信息
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # 计算显示的页码范围
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    # 获取所有标签用于筛选栏
    tags = get_all_tags()

    return render_template('tag_posts.html',
                         tag=tag,
                         posts=posts_data['posts'],
                         tags=tags,
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis)

@blog_bp.route('/tags')
def list_all_tags():
    """显示所有标签页面"""
    # 获取所有标签
    tags = get_all_tags()

    if not tags:
        return render_template('tags.html', tags=[])

    # 批量获取所有标签的文章数量（修复N+1查询问题）
    tag_ids = [tag['id'] for tag in tags]
    conn = get_db_connection()
    cursor = conn.cursor()

    # 使用一个查询获取所有标签的文章数量
    placeholders = ','.join(['?'] * len(tag_ids))
    cursor.execute(f'''
        SELECT tag_id, COUNT(*) as post_count
        FROM post_tags
        WHERE tag_id IN ({placeholders})
        GROUP BY tag_id
    ''', tag_ids)

    # 将结果转换为字典
    tag_counts = {row['tag_id']: row['post_count'] for row in cursor.fetchall()}
    conn.close()

    # 为每个标签添加文章数量
    for tag in tags:
        tag['post_count'] = tag_counts.get(tag['id'], 0)

    # 按文章数量降序排序，标签名升序
    tags.sort(key=lambda x: (-x['post_count'], x['name']))

    return render_template('tags.html', tags=tags)

@blog_bp.route('/author/<int:author_id>')
def view_author(author_id):
    """查看作者页面"""
    author = get_user_by_id(author_id)
    if not author:
        flash('作者不存在', 'error')
        return redirect(url_for('blog.index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_posts_by_author(author_id, include_drafts=False,
                                     page=page, per_page=per_page)

    # 计算分页信息
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    return render_template('author.html',
                         author=author,
                         posts=posts_data['posts'],
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis)
