"""
Flask博客系统 - 主应用文件

功能:
    - 文章管理（创建、编辑、删除、发布）
    - 用户认证与授权（多角色权限系统）
    - 评论系统
    - 分类和标签管理
    - 图片上传（带安全验证）
    - 全文搜索
    - API接口（支持游标分页）

安全特性:
    - CSRF保护（Flask-WTF）
    - 速率限制（防止暴力破解）
    - 密码哈希（werkzeug.security）
    - XSS防护（bleach + markdown2）
    - SQL注入防护（参数化查询）
    - 会话安全（HttpOnly, SameSite）
    - 文件上传验证（类型+尺寸检查）

作者: Simple Blog Team
版本: 2.0
"""

# =============================================================================
# 标准库导入
# =============================================================================
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from urllib.parse import urlparse, urljoin
import markdown2
import bleach
import os
import re
import sqlite3
from pathlib import Path

# =============================================================================
# 项目配置导入
# =============================================================================
from config import (SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER, ALLOWED_EXTENSIONS,
                    MAX_CONTENT_LENGTH, BASE_DIR, DEBUG, SITE_NAME, SITE_DESCRIPTION,
                    SITE_AUTHOR, WTF_CSRF_ENABLED, WTF_CSRF_TIME_LIMIT, WTF_CSRF_SSL_STRICT)

# =============================================================================
# 安全相关导入
# =============================================================================
# CSRF保护 - 防止跨站请求伪造攻击
from flask_wtf.csrf import CSRFProtect

# 速率限制 - 防止暴力破解攻击
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# =============================================================================
# 日志系统导入
# =============================================================================
from logger import setup_logging, log_login, log_operation, log_error, log_sql

# =============================================================================
# 数据模型导入
# =============================================================================
from models import (
    # 数据库连接
    get_db_connection, init_db, get_db_context,
    # 文章相关
    get_all_posts, get_all_posts_cursor, get_post_by_id,
    create_post, update_post, delete_post, update_post_with_tags,
    # 用户相关
    get_user_by_username, get_user_by_id, create_user, update_user, delete_user, get_all_users,
    # 分类相关
    get_all_categories, create_category, update_category, delete_category,
    get_category_by_id, get_posts_by_category,
    # 标签相关
    create_tag, get_all_tags, get_popular_tags, get_tag_by_id, update_tag, delete_tag,
    get_tag_by_name, set_post_tags, get_post_tags, get_posts_by_tag,
    # 评论相关
    create_comment, get_comments_by_post, get_all_comments,
    update_comment_visibility, delete_comment,
    # 搜索和分页
    search_posts, paginate_query_cursor, get_posts_by_author,
    # AI功能相关
    get_user_ai_config, update_user_ai_config, save_ai_tag_history, get_ai_tag_history, get_ai_usage_stats
)

# =============================================================================
# 权限装饰器导入
# =============================================================================
from auth_decorators import (
    login_required, role_required, admin_required, editor_required,
    can_edit_post, can_delete_post, can_manage_users, get_current_user
)

# =============================================================================
# AI服务导入
# =============================================================================
from ai_services import TagGenerator

# =============================================================================
# Flask应用初始化
# =============================================================================
# 创建Flask应用实例，设置模板和静态文件目录
app = Flask(__name__,
            template_folder=str(BASE_DIR / 'templates'),
            static_folder=str(BASE_DIR / 'static'))

# 基础配置
app.config['SECRET_KEY'] = SECRET_KEY           # 用于会话加密的密钥
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH  # 限制上传文件大小

# =============================================================================
# CSRF保护配置
# =============================================================================
csrf = CSRFProtect(app)  # 启用CSRF保护
app.config['WTF_CSRF_ENABLED'] = WTF_CSRF_ENABLED
app.config['WTF_CSRF_TIME_LIMIT'] = WTF_CSRF_TIME_LIMIT
app.config['WTF_CSRF_SSL_STRICT'] = WTF_CSRF_SSL_STRICT

# =============================================================================
# 速率限制配置
# =============================================================================
# 防止暴力破解攻击，限制每个IP地址的请求频率
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  # 使用IP地址作为限制依据
    default_limits=["1000 per day", "200 per hour"],  # 每天最多1000次，每小时最多200次
    storage_uri="memory://",  # 使用内存存储（生产环境建议使用Redis）
    strategy="fixed-window"  # 固定时间窗口策略
)

# =============================================================================
# 会话安全配置
# =============================================================================
from config import SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE    # 仅HTTPS传输（生产环境）
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY  # 防止JavaScript访问
app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE   # CSRF防护

# =============================================================================
# 模板上下文处理器
# =============================================================================
@app.context_processor
def inject_site_settings():
    """
    将网站设置注入到所有模板中
    使所有模板都能访问站点名称、描述和作者信息
    """
    return dict(
        site_name=SITE_NAME,
        site_description=SITE_DESCRIPTION,
        site_author=SITE_AUTHOR
    )

# =============================================================================
# 辅助函数
# =============================================================================
def validate_password_strength(password):
    """
    验证密码强度

    要求:
        - 至少10位长度
        - 包含至少一个大写字母
        - 包含至少一个小写字母
        - 包含至少一个数字
        - 不能是常见弱密码

    Args:
        password (str): 待验证的密码

    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): 密码是否有效
            - error_message (str|None): 错误信息，有效时为None
    """
    if len(password) < 10:
        return False, '密码长度至少为10位'

    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'

    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'

    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'

    # 检查常见弱密码
    weak_passwords = ['password123', 'Admin123', '1234567890', 'Password123']
    if password.lower() in [wp.lower() for wp in weak_passwords]:
        return False, '密码过于常见，请使用更复杂的密码'

    return True, None

# =============================================================================
# 日志系统初始化
# =============================================================================
setup_logging(app)

# =============================================================================
# 时区处理
# =============================================================================
from datetime import datetime, timedelta, timezone
import pytz

# 定义中国时区（UTC+8）
CHINA_TZ = pytz.timezone('Asia/Shanghai')

def utc_to_local(utc_datetime_str):
    """
    将UTC时间字符串转换为中国时区（UTC+8）的本地时间

    Args:
        utc_datetime_str (str|None): UTC时间字符串，格式如 '2024-01-01 12:00:00'

    Returns:
        str: 本地时间字符串，格式如 '2024-01-01 20:00:00'
             如果转换失败则返回原字符串
    """
    if not utc_datetime_str:
        return ''

    try:
        # 解析时间字符串
        if isinstance(utc_datetime_str, str):
            # 处理SQLite日期时间格式
            utc_datetime = datetime.fromisoformat(utc_datetime_str.replace(' ', 'T'))
            if utc_datetime.tzinfo is None:
                # 如果没有时区信息，假设为UTC
                utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
        else:
            utc_datetime = utc_datetime_str

        # 转换为中国时区
        local_datetime = utc_datetime.astimezone(CHINA_TZ)

        # 格式化为字符串
        return local_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        # 如果转换失败，返回原字符串
        return utc_datetime_str

# 注册自定义过滤器到Jinja2
app.jinja_env.globals.update(utc_to_local=utc_to_local)

# 自定义日期时间过滤器，在模板中使用 | localtime
@app.template_filter('localtime')
def localtime_filter(value):
    """Jinja2过滤器：将UTC时间转换为本地时间"""
    return utc_to_local(value)


# 自定义摘要过滤器，清理HTML标签并截断文本
@app.template_filter('excerpt')
def excerpt_filter(value, max_length=200):
    """Jinja2过滤器：获取文章摘要（清理HTML并截断）"""
    from models import get_post_excerpt
    return get_post_excerpt(value, max_length)


def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Home page - list all published posts"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(include_drafts=False, page=page, per_page=per_page)
    categories = get_all_categories()
    popular_tags = get_popular_tags(limit=10)

    # Calculate pagination info
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # Calculate page range to display
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    return render_template('index.html',
                         posts=posts_data['posts'],
                         categories=categories,
                         popular_tags=popular_tags,
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis)


@app.route('/post/<int:post_id>')
def view_post(post_id):
    """View a single post"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('index'))

    # 检查访问权限
    from models import check_post_access
    session_passwords = session.get('unlocked_posts', {})

    access_check = check_post_access(
        post_id,
        session.get('user_id'),
        session_passwords
    )

    if not access_check['allowed']:
        # 权限不足，显示相应的提示页面
        reason = access_check['reason']

        if reason == 'password_required':
            # 密码保护文章，显示密码输入页面
            return render_template('post_password.html', post=post)

        elif reason == 'login_required':
            flash('此文章需要登录后才能查看', 'warning')
            return redirect(url_for('login', next=request.url))

        elif reason == 'private':
            flash('此文章为私密文章，无权访问', 'error')
            return redirect(url_for('index'))

        else:
            flash('无权访问此文章', 'error')
            return redirect(url_for('index'))

    # Render markdown content
    post['content_html'] = markdown2.markdown(
        post['content'],
        extras=['fenced-code-blocks', 'tables']
    )

    # Sanitize HTML to prevent XSS attacks
    post['content_html'] = bleach.clean(
        post['content_html'],
        tags=['p', 'a', 'strong', 'em', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote',
              'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr', 'table', 'thead', 'tbody',
              'tr', 'th', 'td', 'img', 'div', 'span'],
        attributes={
            'a': ['href', 'title', 'rel'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            '*': ['class', 'style']
        },
        strip_comments=False
    )

    # Get tags for the post
    post['tags'] = get_post_tags(post_id)

    # Get comments for the post
    comments = get_comments_by_post(post_id)

    return render_template('post.html', post=post, comments=comments)


@app.route('/api/posts')
def api_posts_cursor():
    """
    API endpoint for fetching posts with cursor-based pagination
    More efficient than traditional OFFSET pagination for large datasets

    Query params:
        - cursor: Time-based cursor (created_at timestamp)
        - per_page: Number of posts per page (default: 20)
        - category_id: Optional category filter

    Returns:
        JSON with posts, next_cursor, has_more
    """
    cursor_time = request.args.get('cursor')
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id')

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    # Use cursor-based pagination
    posts_data = get_all_posts_cursor(
        cursor_time=cursor_time,
        per_page=per_page,
        include_drafts=False,
        category_id=category_id
    )

    return jsonify({
        'success': True,
        'posts': posts_data['posts'],
        'next_cursor': posts_data['next_cursor'],
        'has_more': posts_data['has_more'],
        'per_page': posts_data['per_page']
    })


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Login page"""
    def is_safe_url(target):
        """验证URL是否安全，防止开放式重定向攻击"""
        if not target:
            return False
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return (
            test_url.scheme in ('http', 'https') and
            ref_url.netloc == test_url.netloc
        )

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            # 记录失败尝试
            log_login(username or 'Unknown', success=False, error_msg='字段为空')
            return render_template('login.html')

        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            # 重新生成会话以防止会话固定攻击（Flask 1.0+）
            try:
                session.regenerate()
            except AttributeError:
                # 如果Flask版本不支持regenerate，清除旧会话
                session.clear()

            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user.get('role', 'author')  # 存储角色信息
            session.permanent = False  # 确保会话不是永久的
            flash(f'欢迎回来，{user["username"]}！', 'success')

            # 记录成功登录
            log_login(username, success=True)

            # 安全地处理重定向
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'error')
            # 记录失败登录
            log_login(username, success=False, error_msg='密码错误或用户不存在')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            flash('请填写所有字段', 'error')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('新密码和确认密码不匹配', 'error')
            return render_template('change_password.html')

        # Strengthened password requirements
        if len(new_password) < 10:
            flash('新密码长度至少为10位', 'error')
            return render_template('change_password.html')

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', new_password):
            flash('密码必须包含至少一个大写字母', 'error')
            return render_template('change_password.html')

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', new_password):
            flash('密码必须包含至少一个小写字母', 'error')
            return render_template('change_password.html')

        # Check for at least one digit
        if not re.search(r'\d', new_password):
            flash('密码必须包含至少一个数字', 'error')
            return render_template('change_password.html')

        # Verify current password
        user = get_user_by_username(session['username'])
        if not check_password_hash(user['password_hash'], current_password):
            flash('当前密码错误', 'error')
            return render_template('change_password.html')

        # Update password
        new_password_hash = generate_password_hash(new_password)
        update_user_password(user['id'], new_password_hash)
        flash('密码修改成功', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('change_password.html')


@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard - list all posts including drafts"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id')

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(include_drafts=True, page=page, per_page=per_page, category_id=category_id)
    categories = get_all_categories()

    # Calculate pagination info
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # Calculate page range to display
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    return render_template('admin/dashboard.html',
                         posts=posts_data['posts'],
                         categories=categories,
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis,
                         current_category_id=category_id)


@app.route('/admin/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """Create a new post"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        is_published = request.form.get('is_published') is not None
        category_id = request.form.get('category_id')
        if category_id == '':
            category_id = None
        elif category_id is not None:
            category_id = int(category_id)

        # 访问权限设置
        access_level = request.form.get('access_level', 'public')
        access_password = request.form.get('access_password', '') if access_level == 'password' else None

        if not title or not content:
            flash('标题和内容不能为空', 'error')
            categories = get_all_categories()
            return render_template('admin/editor.html', post=None, categories=categories)

        # 获取当前用户ID作为作者
        author_id = session.get('user_id')

        # Create post first
        post_id = create_post(title, content, is_published, category_id, author_id, access_level, access_password)

        # Update AI history records with this post_id (for records created before saving)
        try:
            import sqlite3
            from models import DATABASE_URL
            db_path = DATABASE_URL.replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Update the most recent AI history record for this user that has no post_id
            cursor.execute('''
                UPDATE ai_tag_history
                SET post_id = ?
                WHERE id = (
                    SELECT id FROM ai_tag_history
                    WHERE user_id = ? AND post_id IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            ''', (post_id, author_id))

            updated = cursor.rowcount
            conn.commit()
            conn.close()

            if updated > 0:
                print(f"[AI History] Updated {updated} history record(s) with post_id={post_id}")
        except Exception as e:
            print(f"[AI History] Failed to update history: {e}")

        # Handle tags (in separate connection but after commit)
        tag_names = request.form.get('tags', '').split(',')
        if tag_names and tag_names[0]:  # Only if tags provided
            set_post_tags(post_id, tag_names)

        if is_published:
            flash('文章发布成功', 'success')
        else:
            flash('草稿保存成功', 'success')
        return redirect(url_for('view_post', post_id=post_id))

    categories = get_all_categories()
    return render_template('admin/editor.html', post=None, categories=categories)


@app.route('/admin/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Edit an existing post"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        # 如果文章已经发布，保持发布状态；否则根据表单决定
        if post['is_published']:
            is_published = True
        else:
            is_published = request.form.get('is_published') is not None
        category_id = request.form.get('category_id')
        if category_id == '':
            category_id = None
        elif category_id is not None:
            category_id = int(category_id)

        if not title or not content:
            flash('标题和内容不能为空', 'error')
            categories = get_all_categories()
            return render_template('admin/editor.html', post=post, categories=categories)

        # 访问权限设置
        access_level = request.form.get('access_level', 'public')
        access_password = request.form.get('access_password', '') if access_level == 'password' else None

        # Handle tags
        tag_names = request.form.get('tags', '').split(',')

        # Update post
        update_post(post_id, title, content, is_published, category_id, access_level, access_password)

        # Update tags separately
        if tag_names and tag_names[0]:
            set_post_tags(post_id, tag_names)
        else:
            # Clear all tags if empty
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))
            conn.commit()
            conn.close()

        flash('文章更新成功', 'success')
        return redirect(url_for('view_post', post_id=post_id))

    categories = get_all_categories()
    return render_template('admin/editor.html', post=post, categories=categories)


@app.route('/admin/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post_route(post_id):
    """Delete a post"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('admin_dashboard'))

    delete_post(post_id)
    flash('文章已删除', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/batch-update-category', methods=['POST'])
@login_required
def batch_update_category():
    """Batch update category for multiple posts"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = request.get_json()
        post_ids = data.get('post_ids', [])
        category_id = data.get('category_id')

        # 记录操作开始
        log_operation(user_id, username, '批量更新分类',
                    f'文章ID: {post_ids}, 目标分类: {category_id}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        # Convert empty string to None for uncategorized
        if category_id == '' or category_id == 'none':
            category_id = None
        elif category_id is not None:
            category_id = int(category_id)

        # 记录 SQL 操作
        log_sql('batch_update_category', f'UPDATE posts SET category_id = {category_id}',
                 f'post_ids={post_ids}')

        # Update category for each post with manual FTS update
        conn = get_db_connection()
        cursor = conn.cursor()

        updated_count = 0
        errors = []

        for post_id in post_ids:
            try:
                # Get post data for FTS update
                cursor.execute('SELECT title, content FROM posts WHERE id = ?', (post_id,))
                post_data = cursor.fetchone()

                if post_data:
                    # 记录每个文章的更新
                    log_sql('update_post', f'UPDATE posts SET category_id = {category_id} WHERE id = {post_id}')

                    # Update post
                    cursor.execute(
                        'UPDATE posts SET category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (category_id, post_id)
                    )

                    # Manually update FTS
                    log_sql('update_fts', f'DELETE FROM posts_fts WHERE rowid = {post_id}')
                    cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))

                    log_sql('insert_fts', f'INSERT INTO posts_fts(rowid, title, content) VALUES ({post_id}, ...)')
                    cursor.execute('INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
                                  (post_id, post_data[0], post_data[1]))

                    updated_count += 1
            except Exception as e:
                error_msg = f"文章 {post_id} 更新失败: {str(e)}"
                errors.append(error_msg)
                # 记录错误
                log_error(e, context=f'批量更新分类 - 文章 {post_id}', user_id=user_id)

        conn.commit()

        # 记录操作结果
        if errors:
            result_msg = f'部分成功: {updated_count}/{len(post_ids)} 篇文章更新成功'
            if updated_count == 0:
                result_msg = f'更新失败: {errors[0]}'
        else:
            result_msg = f'成功更新 {updated_count} 篇文章的分类'

        log_operation(user_id, username, '批量更新分类', result_msg)

        return jsonify({
            'success': updated_count > 0,
            'message': result_msg
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/admin/batch-delete', methods=['POST'])
@login_required
def batch_delete():
    """Batch delete multiple posts"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = request.get_json()
        post_ids = data.get('post_ids', [])

        # 记录操作开始
        log_operation(user_id, username, '批量删除文章',
                    f'文章ID: {post_ids}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        deleted_count = 0
        errors = []

        for post_id in post_ids:
            try:
                # Check if post exists
                cursor.execute('SELECT id FROM posts WHERE id = ?', (post_id,))
                if not cursor.fetchone():
                    errors.append(f"文章 {post_id} 不存在")
                    continue

                # Delete post (CASCADE will handle comments and post_tags)
                log_sql('delete_post', f'DELETE FROM posts WHERE id = {post_id}')
                cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))

                # Manually delete from FTS
                log_sql('delete_fts', f'DELETE FROM posts_fts WHERE rowid = {post_id}')
                cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))

                deleted_count += 1
            except Exception as e:
                error_msg = f"文章 {post_id} 删除失败: {str(e)}"
                errors.append(error_msg)
                log_error(e, context=f'批量删除 - 文章 {post_id}', user_id=user_id)

        conn.commit()

        # 记录操作结果
        if errors:
            result_msg = f'部分成功: {deleted_count}/{len(post_ids)} 篇文章删除成功'
            if deleted_count == 0:
                result_msg = f'删除失败: {errors[0]}'
        else:
            result_msg = f'成功删除 {deleted_count} 篇文章'

        log_operation(user_id, username, '批量删除文章', result_msg)

        return jsonify({
            'success': deleted_count > 0,
            'message': result_msg
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        log_error(e, context='批量删除文章', user_id=user_id)
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        log_error(e, context='批量删除文章', user_id=user_id)
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/admin/upload', methods=['POST'])
@login_required
def upload_image():
    """
    处理图片上传，包含多层安全验证

    安全验证流程:
        1. 文件存在性检查
        2. 文件扩展名白名单验证
        3. 文件类型实际内容验证（imghdr）
        4. 图片尺寸验证（防止DoS）
        5. 文件大小验证（5MB限制）
        6. 安全文件名生成（时间戳+随机后缀）

    Returns:
        JSON响应: {'success': True/False, 'url': '...'} 或 {'error': '...'}

    安全特性:
        - 防止伪造扩展名攻击
        - 防止过大图片DoS攻击
        - 防止路径遍历攻击（secure_filename）
        - 防止文件名猜测（随机后缀）
    """
    # 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    # 验证文件扩展名（第一层防护）
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400

    # 读取文件内容进行深度验证
    file_content = file.read()
    file.seek(0)  # 重置文件指针以便后续保存

    # 验证实际文件类型和尺寸（合并第二、三层防护 - 防止伪造扩展名和DoS攻击）
    try:
        from PIL import Image
        import io

        # 使用PIL检测文件类型和验证图片
        img = Image.open(io.BytesIO(file_content))
        file_type = img.format.lower() if img.format else None

        # 验证文件类型
        allowed_types = ['jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff']
        if file_type not in allowed_types:
            return jsonify({'success': False, 'error': f'无效的图片文件类型: {file_type}'}), 400

        # 验证图片尺寸
        width, height = img.size
        max_dimension = 4096
        if width > max_dimension or height > max_dimension:
            return jsonify({'success': False, 'error': f'图片尺寸过大，最大允许{max_dimension}x{max_dimension}'}), 400

        # 验证文件大小（第四层防护 - 5MB限制）
        file_size = len(file_content)
        max_file_size = 5 * 1024 * 1024  # 5MB
        if file_size > max_file_size:
            return jsonify({'success': False, 'error': f'文件大小超过限制（最大{max_file_size//1024//1024}MB）'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': '图片文件损坏或格式错误'}), 400

    # 生成安全的文件名（第五层防护 - 防止路径遍历和文件名猜测）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    secure_name = secure_filename(file.filename)
    ext = secure_name.rsplit('.', 1)[1].lower() if '.' in secure_name else file_type
    random_suffix = os.urandom(4).hex()  # 添加随机后缀防止文件名猜测
    filename = f"{timestamp}_{random_suffix}.{ext}"
    filepath = UPLOAD_FOLDER / filename

    # 保存文件
    try:
        with open(filepath, 'wb') as f:
            f.write(file_content)
        # 返回上传图片的URL
        url = url_for('static', filename=f'uploads/{filename}')
        return jsonify({'success': True, 'url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': f'文件保存失败: {str(e)}'}), 500


@app.route('/api/share/qrcode')
def generate_qrcode():
    """Generate QR code for WeChat sharing"""
    import qrcode
    from io import BytesIO
    import base64

    url = request.args.get('url', url_for('index', _external=True))

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = BytesIO()
    img.save(buffer)
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({'qrcode': f"data:image/png;base64,{img_str}"})


# Category Management Routes
@app.route('/admin/categories')
@login_required
def category_list():
    """List all categories"""
    categories = get_all_categories()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/new', methods=['POST'])
@login_required
def new_category():
    """Create a new category"""
    name = request.form.get('name')
    if not name:
        flash('分类名称不能为空', 'error')
        return redirect(url_for('category_list'))

    category_id = create_category(name)
    if category_id:
        flash('分类创建成功', 'success')
    else:
        flash('分类名称已存在', 'error')
    return redirect(url_for('category_list'))

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category_route(category_id):
    """Delete a category"""
    delete_category(category_id)
    flash('分类已删除', 'success')
    return redirect(url_for('category_list'))

@app.route('/category/<int:category_id>')
def view_category(category_id):
    """View all posts in a category"""
    category = get_category_by_id(category_id)
    if not category:
        flash('分类不存在', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(include_drafts=False, page=page, per_page=per_page, category_id=category_id)

    # Calculate pagination info
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # Calculate page range to display
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    # Get all categories for the filter bar
    categories = get_all_categories()

    return render_template('index.html',
                         posts=posts_data['posts'],
                         category=category,
                         categories=categories,
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis)


# Tag Management Routes
@app.route('/admin/tags')
@login_required
def tag_list():
    """List all tags"""
    tags = get_all_tags()
    return render_template('admin/tags.html', tags=tags)

@app.route('/admin/tags/new', methods=['POST'])
@login_required
def new_tag():
    """Create a new tag"""
    name = request.form.get('name')
    if not name:
        flash('标签名称不能为空', 'error')
        return redirect(url_for('tag_list'))

    tag_id = create_tag(name)
    if tag_id:
        flash('标签创建成功', 'success')
    else:
        flash('标签名称已存在', 'error')
    return redirect(url_for('tag_list'))

@app.route('/admin/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag_route(tag_id):
    """Delete a tag"""
    delete_tag(tag_id)
    flash('标签已删除', 'success')
    return redirect(url_for('tag_list'))

@app.route('/tag/<int:tag_id>')
def view_tag(tag_id):
    """View all posts with a tag"""
    tag = get_tag_by_id(tag_id)
    if not tag:
        flash('标签不存在', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_posts_by_tag(tag_id, include_drafts=False, page=page, per_page=per_page)

    # Calculate pagination info
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # Calculate page range to display
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    # Get all tags for the filter bar
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


@app.route('/search')
def search():
    """Search posts"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    if not query:
        return render_template('search.html', query='', posts=None, pagination=None)

    posts_data = search_posts(query, include_drafts=False, page=page, per_page=per_page)

    # Calculate pagination info
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # Calculate page range to display
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


# Comment Routes
@app.route('/post/<int:post_id>/verify-password', methods=['POST'])
def verify_post_password(post_id):
    """Verify password for password-protected post"""
    data = request.get_json()
    password = data.get('password', '')

    if not password:
        return jsonify({'success': False, 'message': '请输入密码'}), 400

    from models import verify_post_password

    if verify_post_password(post_id, password):
        # 密码正确，保存到session
        if 'unlocked_posts' not in session:
            session['unlocked_posts'] = {}

        session['unlocked_posts'][str(post_id)] = True
        session.modified = True

        return jsonify({
            'success': True,
            'message': '密码验证成功',
            'redirect': url_for('view_post', post_id=post_id)
        })
    else:
        return jsonify({'success': False, 'message': '密码错误，请重试'}), 401


@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    """Add a comment to a post"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('index'))

    author_name = request.form.get('author_name', '').strip()
    author_email = request.form.get('author_email', '').strip()
    content = request.form.get('content', '').strip()

    if not author_name or not content:
        flash('姓名和评论内容不能为空', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    if len(author_name) > 50:
        flash('姓名过长', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    if len(content) > 1000:
        flash('评论内容过长', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    create_comment(post_id, author_name, author_email, content)
    flash('评论提交成功', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/admin/comments')
@login_required
def comment_list():
    """List all comments"""
    comments = get_all_comments(include_hidden=True)
    return render_template('admin/comments.html', comments=comments)

@app.route('/admin/comments/<int:comment_id>/toggle', methods=['POST'])
@login_required
def toggle_comment(comment_id):
    """Toggle comment visibility"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT is_visible FROM comments WHERE id = ?', (comment_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        new_visibility = not result['is_visible']
        update_comment_visibility(comment_id, new_visibility)
        flash('评论状态已更新', 'success')
    else:
        flash('评论不存在', 'error')

    return redirect(url_for('comment_list'))

@app.route('/admin/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment_route(comment_id):
    """Delete a comment"""
    delete_comment(comment_id)
    flash('评论已删除', 'success')
    return redirect(url_for('comment_list'))


def create_admin_user():
    """
    Create default admin user if not exists
    Requires ADMIN_USERNAME and ADMIN_PASSWORD environment variables
    """
    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')

    # 强制要求设置环境变量
    if not username or not password:
        raise ValueError(
            "\n" + "="*70 +
            "\n SECURITY ERROR: ADMIN_USERNAME and ADMIN_PASSWORD must be set!" +
            "\n" +
            "\n To set up the admin user, export these environment variables:" +
            "\n   export ADMIN_USERNAME='your_username'" +
            "\n   export ADMIN_PASSWORD='your_secure_password'" +
            "\n" +
            "\n Password requirements:" +
            "\n - At least 12 characters long" +
            "\n - Must contain uppercase and lowercase letters" +
            "\n - Must contain at least one digit" +
            "\n" +
            "="*70
        )

    # 验证密码强度
    if len(password) < 12:
        raise ValueError("ADMIN_PASSWORD must be at least 12 characters long")

    if not re.search(r'[A-Z]', password):
        raise ValueError("ADMIN_PASSWORD must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        raise ValueError("ADMIN_PASSWORD must contain at least one lowercase letter")

    if not re.search(r'\d', password):
        raise ValueError("ADMIN_PASSWORD must contain at least one digit")

    # 检查常见弱密码
    weak_passwords = ['password', 'admin123', '123456789012', 'password123']
    if password.lower() in weak_passwords:
        raise ValueError("ADMIN_PASSWORD is too common. Please use a stronger password.")

    existing_user = get_user_by_username(username)
    if not existing_user:
        password_hash = generate_password_hash(password)
        user_id = create_user(username, password_hash, role='admin')
        if user_id:
            print(f"✓ Created admin user: {username}")
        else:
            print("✗ Failed to create admin user")
    else:
        print(f"ℹ Admin user already exists: {username}")


# Export Routes
@app.route('/admin/export')
@login_required
def export_page():
    """Export page with options"""
    return render_template('admin/export.html')


@app.route('/admin/export/markdown')
@login_required
def export_markdown():
    """Export all posts to markdown files"""
    try:
        from export import export_all_posts_to_markdown
        count, path = export_all_posts_to_markdown()
        flash(f'成功导出 {count} 篇文章到 {path}', 'success')
        log_operation(session.get('user_id'), session.get('username'), f'导出 {count} 篇文章为 Markdown')
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export to markdown')

    return redirect(url_for('export_page'))


@app.route('/admin/export/json')
@login_required
def export_json():
    """Export all posts to JSON"""
    try:
        from export import export_to_json
        count, path = export_to_json()
        flash(f'成功导出 {count} 篇文章到 {path}', 'success')
        log_operation(session.get('user_id'), session.get('username'), f'导出 {count} 篇文章为 JSON')
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export to JSON')

    return redirect(url_for('export_page'))


# Import Routes
@app.route('/admin/import')
@login_required
def import_page():
    """Import page with options"""
    return render_template('admin/import.html')


@app.route('/admin/import/json', methods=['POST'])
@login_required
def import_json():
    """Import posts from JSON file"""
    try:
        user_id = session.get('user_id')

        # Check if file was uploaded
        if 'import_file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(url_for('import_page'))

        file = request.files['import_file']

        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('import_page'))

        if not file.filename.endswith('.json'):
            flash('只支持JSON格式文件', 'error')
            return redirect(url_for('import_page'))

        # Save file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_file_path = tmp_file.name

        # Import posts
        from import_posts import import_from_json
        count, skipped, messages = import_from_json(tmp_file_path, user_id)

        # Clean up temp file
        import os
        os.unlink(tmp_file_path)

        # Show results
        for msg in messages[1:]:  # Skip summary message
            flash(msg, 'success' if '✅' in msg else 'warning' if '⚠️' in msg else 'error')

        flash(messages[0], 'success')  # Summary message
        log_operation(user_id, session.get('username'), f'导入 {count} 篇文章从 JSON')

    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from JSON')

    return redirect(url_for('import_page'))


@app.route('/admin/import/markdown', methods=['POST'])
@login_required
def import_markdown():
    """Import posts from markdown directory"""
    try:
        user_id = session.get('user_id')

        # Check if directory was uploaded as zip
        if 'import_file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(url_for('import_page'))

        file = request.files['import_file']

        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('import_page'))

        if not file.filename.endswith('.zip'):
            flash('只支持ZIP压缩包格式', 'error')
            return redirect(url_for('import_page'))

        # Extract zip file
        import tempfile
        import zipfile
        import shutil

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, 'import.zip')
            file.save(zip_path)

            # Extract zip
            extract_dir = os.path.join(tmp_dir, 'extracted')
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find posts directory or use extracted directory
            posts_dir = os.path.join(extract_dir, 'posts')
            if not os.path.exists(posts_dir):
                posts_dir = extract_dir

            # Import posts
            from import_posts import import_from_markdown_directory
            count, skipped, messages = import_from_markdown_directory(posts_dir, user_id)

        # Show results
        for msg in messages[1:]:  # Skip summary message
            flash(msg, 'success' if '✅' in msg else 'warning' if '⚠️' in msg else 'error')

        flash(messages[0], 'success')  # Summary message
        log_operation(user_id, session.get('username'), f'导入 {count} 篇文章从 Markdown')

    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from markdown')

    return redirect(url_for('import_page'))


# ==================== 用户管理路由 ====================

@app.route('/admin/users')
@can_manage_users
def user_list():
    """用户列表页面"""
    users = get_all_users()
    return render_template('admin/users.html', users=users)


@app.route('/admin/users/new', methods=['GET', 'POST'])
@can_manage_users
def new_user():
    """创建新用户"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'author')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')

        # 验证
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
            return render_template('admin/user_form.html', user=None)

        # 使用统一的密码强度验证
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('admin/user_form.html', user=None)

        # 检查用户名是否已存在
        if get_user_by_username(username):
            flash('用户名已存在', 'error')
            return render_template('admin/user_form.html', user=None)

        # 创建用户
        password_hash = generate_password_hash(password)
        user_id = create_user(username, password_hash, role, display_name, bio)

        if user_id:
            flash(f'用户 {username} 创建成功', 'success')
            log_operation(session.get('user_id'), session.get('username'), f'创建用户 {username}，角色 {role}')
            return redirect(url_for('user_list'))
        else:
            flash('创建用户失败', 'error')

    return render_template('admin/user_form.html', user=None)


@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@can_manage_users
def edit_user(user_id):
    """编辑用户"""
    user = get_user_by_id(user_id)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('user_list'))

    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role', 'author')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')
        is_active = request.form.get('is_active') == '1'

        # 检查用户名是否被其他用户占用
        existing_user = get_user_by_username(username)
        if existing_user and existing_user['id'] != user_id:
            flash('用户名已被使用', 'error')
            return render_template('admin/user_form.html', user=user)

        # 更新用户
        if update_user(user_id, username=username, display_name=display_name,
                      bio=bio, role=role, is_active=is_active):
            flash('用户信息更新成功', 'success')
            log_operation(session.get('user_id'), session.get('username'), f'更新用户 {username}')
            return redirect(url_for('user_list'))
        else:
            flash('更新失败', 'error')

    return render_template('admin/user_form.html', user=user)


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@can_manage_users
def delete_user_route(user_id):
    """删除用户"""
    # 不允许删除自己
    if user_id == session.get('user_id'):
        flash('不能删除自己的账号', 'error')
        return redirect(url_for('user_list'))

    user = get_user_by_id(user_id)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('user_list'))

    delete_user(user_id)
    flash(f'用户 {user["username"]} 已删除', 'success')
    log_operation(session.get('user_id'), session.get('username'), f'删除用户 {user["username"]}')
    return redirect(url_for('user_list'))


@app.route('/author/<int:author_id>')
def view_author(author_id):
    """查看作者页面"""
    author = get_user_by_id(author_id)
    if not author:
        flash('作者不存在', 'error')
        return redirect(url_for('index'))

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


# =============================================================================
# AI功能路由
# =============================================================================

@app.route('/admin/ai/generate-tags', methods=['POST'])
@login_required
def generate_tags():
    """
    AI生成标签API

    接收文章标题和内容，返回AI生成的标签
    """
    try:
        # 获取请求数据
        data = request.get_json()
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()

        # 验证输入
        if not title:
            return jsonify({
                'success': False,
                'error': '文章标题不能为空'
            }), 400

        if not content:
            return jsonify({
                'success': False,
                'error': '文章内容不能为空'
            }), 400

        # 获取当前用户的AI配置
        user_id = session.get('user_id')
        user_ai_config = get_user_ai_config(user_id)

        if not user_ai_config:
            return jsonify({
                'success': False,
                'error': '用户不存在'
            }), 404

        # 生成标签
        result = TagGenerator.generate_for_post(
            title=title,
            content=content,
            user_config=user_ai_config,
            max_tags=3
        )

        if result is None:
            return jsonify({
                'success': False,
                'error': 'AI标签生成功能未启用，请在设置中启用'
            }), 400

        # 记录生成历史（异步，不阻塞响应）
        try:
            post_id = data.get('post_id')
            # 始终保存历史记录，即使没有 post_id（新建文章的情况）
            history_id = save_ai_tag_history(
                post_id=int(post_id) if post_id else None,
                user_id=user_id,
                prompt=f"Title: {title}\nContent: {content[:100]}...",
                generated_tags=result['tags'],
                model_used=result['model'],
                tokens_used=result['tokens_used'],
                cost=result.get('cost', 0),
                currency=result.get('currency', 'USD')
            )
            print(f"[AI History] Saved record ID: {history_id}, post_id: {post_id}")
        except Exception as e:
            # 历史记录失败不影响主流程
            print(f"[AI History] Failed to save: {str(e)}")
            import traceback
            traceback.print_exc()
            log_error(e, context='保存AI历史记录失败')

        log_operation(session.get('user_id'), session.get('username'),
                     f'AI生成标签: {", ".join(result["tags"])} ({result["tokens_used"]} tokens)')

        return jsonify({
            'success': True,
            'tags': result['tags'],
            'tokens_used': result['tokens_used'],
            'model': result['model'],
            'cost': result.get('cost', 0)
        })

    except ValueError as e:
        # 配置错误
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        log_error(e, context='AI标签生成失败')
        return jsonify({
            'success': False,
            'error': f'生成失败: {str(e)}'
        }), 500


@app.route('/admin/ai/configure', methods=['GET', 'POST'])
@login_required
def ai_settings():
    """
    AI设置页面和API
    GET: 显示设置页面
    POST: 更新AI配置
    """
    user_id = session.get('user_id')

    if request.method == 'GET':
        # 获取用户当前AI配置
        ai_config = get_user_ai_config(user_id)
        supported_providers = TagGenerator.get_supported_providers()

        # 获取使用统计
        stats = get_ai_usage_stats(user_id)

        return render_template('admin/ai_settings.html',
                             ai_config=ai_config,
                             supported_providers=supported_providers,
                             stats=stats)

    else:  # POST
        try:
            # 更新AI配置
            data = request.get_json()

            # 验证数据
            ai_config = {}

            if 'ai_tag_generation_enabled' in data:
                ai_config['ai_tag_generation_enabled'] = bool(data['ai_tag_generation_enabled'])

            if 'ai_provider' in data:
                provider = data['ai_provider']
                # 验证提供商是否支持
                supported = [p['id'] for p in TagGenerator.get_supported_providers()]
                if provider not in supported:
                    return jsonify({
                        'success': False,
                        'error': f'不支持的AI提供商: {provider}'
                    }), 400
                ai_config['ai_provider'] = provider

            if 'ai_api_key' in data:
                api_key = data['ai_api_key'].strip()
                if api_key:
                    ai_config['ai_api_key'] = api_key

            if 'ai_model' in data:
                model = data['ai_model'].strip()
                if model:
                    ai_config['ai_model'] = model

            # 更新配置
            success = update_user_ai_config(user_id, ai_config)

            if success:
                log_operation(session.get('user_id'), session.get('username'),
                             '更新AI配置')
                return jsonify({
                    'success': True,
                    'message': 'AI配置已更新'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '配置更新失败'
                }), 500

        except Exception as e:
            log_error(e, context='更新AI配置失败')
            return jsonify({
                'success': False,
                'error': f'更新失败: {str(e)}'
            }), 500


@app.route('/admin/ai/test', methods=['POST'])
@login_required
def test_ai_config():
    """
    测试AI配置API

    支持两种模式：
    1. 测试表单中的配置（POST请求体中提供）
    2. 测试数据库中保存的配置
    """
    try:
        user_id = session.get('user_id')

        # 尝试从请求体获取配置（表单中的值）
        form_config = request.get_json()

        if form_config and form_config.get('ai_api_key'):
            # 使用表单中的配置进行测试
            ai_config = {
                'ai_tag_generation_enabled': True,
                'ai_provider': form_config.get('ai_provider', 'openai'),
                'ai_api_key': form_config.get('ai_api_key'),
                'ai_model': form_config.get('ai_model')
            }
        else:
            # 使用数据库中保存的配置
            ai_config = get_user_ai_config(user_id)

            if not ai_config:
                return jsonify({
                    'success': False,
                    'message': '未配置API密钥，请先在下方输入密钥'
                })

        # 测试配置
        result = TagGenerator.test_user_config(ai_config)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        })


@app.route('/admin/ai/history')
@login_required
def ai_history():
    """
    AI生成历史页面
    """
    user_id = session.get('user_id')
    history = get_ai_tag_history(user_id=user_id, limit=50)
    stats = get_ai_usage_stats(user_id)

    return render_template('admin/ai_history.html',
                         history=history,
                         stats=stats)


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    log_error(error, context='404 Not Found')
    return render_template('error.html', status_code=404), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    log_error(error, context='500 Internal Server Error')

    # 生产环境显示通用错误信息，开发环境显示详细信息
    if app.config.get('DEBUG'):
        error_message = str(error)
    else:
        error_message = "服务器内部错误，请稍后重试"

    return render_template('error.html', status_code=500, error=error_message), 500


@app.errorhandler(sqlite3.Error)
def database_error(error):
    """Handle database errors"""
    log_error(error, context='Database Error')

    # 生产环境显示通用错误信息，开发环境显示详细信息
    if app.config.get('DEBUG'):
        error_message = f"数据库错误: {str(error)}"
    else:
        error_message = "数据库错误，请稍后重试"

    return render_template('error.html', status_code=500, error=error_message), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    log_error(error, context='413 Payload Too Large')

    # For upload API endpoint, return JSON error
    if request.path.startswith('/admin/upload') or request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': f'文件太大，最大允许上传 16MB'
        }), 413

    # For regular pages, return HTML error page
    return render_template('error.html', status_code=413, error='上传的文件太大，最大允许 16MB'), 413



@app.cli.command()
def init():
    """Initialize the database and create admin user"""
    init_db()
    create_admin_user()
    print("Database initialized successfully")


if __name__ == '__main__':
    init_db()
    create_admin_user()
    # macOS ControlCenter often uses port 5000, so we use 5001
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=DEBUG, host='0.0.0.0', port=port)
