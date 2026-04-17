"""
公开博客路由

包括首页、文章详情、搜索、分类、标签、作者页面、评论等公开访问的功能。
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app, has_app_context
import markdown2
import bleach
import logging
import json
import re

logger = logging.getLogger(__name__)

from models import (
    get_all_posts, get_all_posts_cursor, get_post_by_id,
    get_all_categories, get_category_by_id, get_all_tags,
    get_tag_by_id, get_post_tags, get_comments_by_post, create_comment,
    search_posts, get_posts_by_tag, get_posts_by_author, get_user_by_id,
    check_post_access, verify_post_password, get_popular_tags, get_db_connection
)

# 创建博客蓝图
blog_bp = Blueprint('blog', __name__)

IMAGE_SRC_PATTERN = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
IMG_TAG_SRC_REWRITE_PATTERN = re.compile(r'(<img[^>]+src=["\'])([^"\']+)(["\'])', re.IGNORECASE)
IMG_LOADING_ATTR_PATTERN = re.compile(r'<img(?![^>]*\bloading=)([^>]*)>', re.IGNORECASE)
MEDIA_PARAGRAPH_PATTERN = re.compile(
    r'<p>(\s*(?:<a\b[^>]*>\s*)?<img\b[^>]*>(?:\s*</a>)?\s*)</p>',
    re.IGNORECASE
)
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
WHITESPACE_PATTERN = re.compile(r'\s+')


def get_optimized_image_url(original_url, size='medium'):
    """
    将原图URL转换为优化后的URL

    Args:
        original_url: 原图URL，例如 /static/uploads/images/xxx.jpg 或 /static/uploads/optimized/xxx_medium.webp
        size: 尺寸类型 'thumbnail' | 'medium' | 'large' | 'feed'

    Returns:
        优化后的URL，如果不存在则返回原图URL
    """
    try:
        # 验证size参数（防止SQL注入）
        valid_sizes = ['thumbnail', 'medium', 'large', 'feed']
        if size not in valid_sizes:
            logger.warning(f"Invalid size parameter: {size}, using 'medium'")
            size = 'medium'
        resolved_size = 'medium' if size == 'feed' else size

        from pathlib import Path
        import re
        # __file__ 是 /path/to/backend/routes/blog.py
        # 需要3次parent才能到达项目根目录
        project_root = Path(__file__).parent.parent.parent

        # 处理optimized路径的图片（例如 xxx_medium.webp -> xxx_feed.webp）
        if '/uploads/optimized/' in original_url:
            # 提取图片哈希值
            # 例如: /static/uploads/optimized/632da1f5f5f9291f6f5c729351b78c47_medium.webp
            match = re.search(r'/([a-f0-9]{32})_(?:thumbnail|medium|large|feed)\.webp', original_url)
            if match:
                image_hash = match.group(1)
                # 构建新的URL
                new_url = f"/static/uploads/optimized/{image_hash}_{resolved_size}.webp"

                # 检查文件是否存在
                file_path = project_root / new_url.lstrip('/')
                logger.debug(f"Checking optimized image: project_root={project_root}, new_url={new_url}, file_path={file_path}, exists={file_path.exists()}")
                if file_path.exists():
                    logger.debug(f"Converted optimized image {original_url} -> {new_url}")
                    return new_url
                else:
                    logger.debug(f"Optimized image not found: {new_url}, returning original")
                    return original_url
            return original_url

        # 处理原始图片路径
        if '/uploads/images/' not in original_url:
            return original_url

        # 从URL构建完整文件路径
        # /static/uploads/images/xxx.jpg -> /path/to/project/static/uploads/images/xxx.jpg
        full_path = project_root / original_url.lstrip('/')

        # 查询数据库获取优化后的图片路径
        conn = get_db_connection()
        cursor = conn.cursor()

        # 根据请求的尺寸选择字段（使用白名单验证过的size）
        size_field = f'{resolved_size}_path'

        cursor.execute('''
            SELECT {}, status
            FROM optimized_images
            WHERE original_path = ?
            AND status = 'completed'
        '''.format(size_field), (str(full_path),))

        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            # 将绝对路径转换为URL
            optimized_path = result[0]
            if optimized_path.startswith(project_root.as_posix()):
                url_path = optimized_path[len(project_root.as_posix()):].lstrip('/')
                optimized_url = f"/{url_path}"
                logger.debug(f"Converted {original_url} -> {optimized_url}")
                return optimized_url

        # 如果没有找到优化版本，返回原图
        logger.debug(f"No optimized version found for {original_url}")
        return original_url

    except Exception as e:
        logger.warning(f"Error converting image URL: {e}")
        return original_url


def get_optimized_image_url_cached(original_url, size='medium'):
    """
    带缓存的图片URL优化函数

    Args:
        original_url: 原图URL
        size: 优化尺寸

    Returns:
        优化后的图片URL
    """
    if not has_app_context() or not hasattr(current_app, 'cache'):
        return get_optimized_image_url(original_url, size)

    cache = current_app.cache

    # 构建缓存key
    cache_key = f"optimized_image_url_{original_url}_{size}"

    # 尝试从缓存获取
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # 计算结果
    result = get_optimized_image_url(original_url, size)

    # 存入缓存（1小时）
    cache.set(cache_key, result, timeout=3600)

    return result

def extract_post_image_urls(content, limit=9, use_optimized=True, size='medium'):
    """
    提取文章内容中的图片URL

    Args:
        content: 文章内容（HTML）
        limit: 最多提取多少张图片
        use_optimized: 是否使用优化后的图片
        size: 当use_optimized=True时，指定使用哪个尺寸 (thumbnail/medium/large/feed)

    Returns:
        图片URL列表
    """
    content_str = str(content or '')
    image_urls = IMAGE_SRC_PATTERN.findall(content_str)[:limit]

    if use_optimized:
        # 将原图URL转换为优化后的URL（使用缓存）
        image_urls = [get_optimized_image_url_cached(url, size) for url in image_urls]

    return image_urls


def extract_post_excerpt(content, limit=160):
    text_content = HTML_TAG_PATTERN.sub(' ', str(content or ''))
    normalized = WHITESPACE_PATTERN.sub(' ', text_content).strip()
    return normalized[:limit]


def rewrite_post_image_sources(content_html, size='medium'):
    """在服务端统一处理正文图片结构，避免模板和前端再做补救。"""
    html = str(content_html or '')

    def replace_src(match):
        prefix, original_url, suffix = match.groups()
        optimized_url = get_optimized_image_url(original_url, size)
        return f'{prefix}{optimized_url}{suffix}'

    html = IMG_TAG_SRC_REWRITE_PATTERN.sub(replace_src, html)
    html = IMG_LOADING_ATTR_PATTERN.sub(r'<img loading="lazy"\1>', html)
    html = MEDIA_PARAGRAPH_PATTERN.sub(r'<p class="post-media-block">\1</p>', html)
    return html


def determine_mobile_image_layout(image_count):
    if image_count <= 1:
        return 'single'
    if image_count <= 4:
        return 'grid-4'
    if image_count <= 6:
        return 'grid-6'
    return 'grid-9'


def build_post_card_payload(post):
    post_dict = serialize_post_for_json(post)
    # 首页/分类信息流优先使用较大的优化图，避免桌面端卡片放大后发糊
    image_urls = extract_post_image_urls(post_dict.get('content'), size='large')
    post_dict['image_urls'] = image_urls
    post_dict['image_count'] = len(image_urls)
    post_dict['mobile_image_layout'] = determine_mobile_image_layout(len(image_urls))
    post_dict['excerpt'] = extract_post_excerpt(post_dict.get('content'))
    return post_dict


def build_post_card_payloads(posts):
    return [build_post_card_payload(post) for post in posts]


def serialize_post_for_json(post):
    """Serialize post rows for lightweight JSON responses."""
    post_dict = dict(post) if hasattr(post, 'keys') else {}
    if not post_dict and hasattr(post, '_asdict'):
        post_dict = post._asdict()
    if not post_dict:
        post_dict = {
            'id': getattr(post, 'id', None),
            'title': getattr(post, 'title', ''),
            'content': getattr(post, 'content', ''),
            'category_name': getattr(post, 'category_name', None),
            'created_at': getattr(post, 'created_at', None),
            'is_published': getattr(post, 'is_published', True),
            'access_level': getattr(post, 'access_level', 'public')
        }

    created_at = post_dict.get('created_at')
    if created_at and hasattr(created_at, 'isoformat'):
        post_dict['created_at'] = created_at.isoformat()

    return post_dict


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


@blog_bp.route('/post/<int:post_id>')
def view_post(post_id):
    """查看单篇文章"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('blog.index'))

    # 检查访问权限
    session_passwords = session.get('unlocked_posts', {})

    # Debug logging
    logger.info(f"[Post Access] Viewing post {post_id}, access_level: {post.get('access_level')}, user_id: {session.get('user_id')}")
    logger.info(f"[Post Access] Session passwords: {list(session_passwords.keys()) if session_passwords else 'None'}")

    access_check = check_post_access(
        post_id,
        session.get('user_id'),
        session_passwords
    )

    logger.info(f"[Post Access] Access check result: allowed={access_check['allowed']}, reason={access_check.get('reason')}")

    if not access_check['allowed']:
        # 权限不足，显示相应的提示页面
        reason = access_check['reason']

        logger.info(f"[Post Access] Access denied, reason: {reason}")

        if reason == 'password_required':
            # 密码保护文章，显示密码输入页面
            return render_template('post_password.html', post=post)

        elif reason == 'login_required':
            flash('此文章需要登录后才能查看', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        elif reason == 'private':
            flash('此文章为私密文章，无权访问', 'error')
            return redirect(url_for('blog.index'))

        else:
            flash('无权访问此文章', 'error')
            return redirect(url_for('blog.index'))

    # 渲染 Markdown 内容
    post['content_html'] = markdown2.markdown(
        post['content'],
        extras=['fenced-code-blocks', 'tables']
    )

    # 清理 HTML 防止 XSS 攻击
    post['content_html'] = bleach.clean(
        post['content_html'],
        tags=['p', 'a', 'strong', 'em', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote',
              'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'table', 'thead', 'tbody',
              'tr', 'th', 'td', 'img', 'div', 'span'],
        attributes={
            'a': ['href', 'title', 'rel'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            '*': ['class']
        },
        strip_comments=False
    )
    post['content_html'] = rewrite_post_image_sources(post['content_html'], size='medium')

    # 获取文章标签
    post['tags'] = get_post_tags(post_id)

    # 获取文章评论
    comments = get_comments_by_post(post_id)

    # 生成完整的文章URL用于分享
    post_url = url_for('blog.view_post', post_id=post_id, _external=True)

    return render_template('post.html', post=post, comments=comments, post_url=post_url)


@blog_bp.route('/post/<int:post_id>/verify-password', methods=['POST'])
def verify_post_password(post_id):
    """验证密码保护文章的密码"""
    data = request.get_json()
    password = data.get('password', '')

    logger.info(f"[Password Verify] Attempting to verify password for post {post_id}")

    if not password:
        return jsonify({'success': False, 'message': '请输入密码'}), 400

    if verify_post_password(post_id, password):
        # 密码正确，保存到 session
        if 'unlocked_posts' not in session:
            session['unlocked_posts'] = {}

        session['unlocked_posts'][str(post_id)] = True
        session.modified = True

        logger.info(f"[Password Verify] Password verified successfully for post {post_id}")
        logger.info(f"[Password Verify] Session unlocked_posts: {list(session['unlocked_posts'].keys())}")

        return jsonify({
            'success': True,
            'message': '密码验证成功',
            'redirect': url_for('blog.view_post', post_id=post_id)
        })
    else:
        logger.warning(f"[Password Verify] Invalid password for post {post_id}")
        return jsonify({'success': False, 'message': '密码错误，请重试'}), 401


@blog_bp.route('/clear-session', methods=['POST'])
def clear_session():
    """临时调试：清除session中的密码记录"""
    session.pop('unlocked_posts', None)
    session.modified = True
    return jsonify({'success': True, 'message': 'Session已清除'})


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


@blog_bp.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    """添加评论"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('blog.index'))

    author_name = request.form.get('author_name', '').strip()
    author_email = request.form.get('author_email', '').strip()
    content = request.form.get('content', '').strip()

    if not author_name or not content:
        flash('姓名和评论内容不能为空', 'error')
        return redirect(url_for('blog.view_post', post_id=post_id))

    if len(author_name) > 50:
        flash('姓名过长', 'error')
        return redirect(url_for('blog.view_post', post_id=post_id))

    if len(content) > 1000:
        flash('评论内容过长', 'error')
        return redirect(url_for('blog.view_post', post_id=post_id))

    create_comment(post_id, author_name, author_email, content)
    flash('评论提交成功', 'success')
    return redirect(url_for('blog.view_post', post_id=post_id))


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


@blog_bp.route('/search')
def search():
    """搜索文章"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    if not query:
        return render_template('search.html', query='', posts=None, pagination=None)

    posts_data = search_posts(query, include_drafts=False, page=page, per_page=per_page)

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
                         show_ellipsis=show_ellipsis)


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
