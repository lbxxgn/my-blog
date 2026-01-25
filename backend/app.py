from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import markdown2
import bleach
import os
import re
import sqlite3
from pathlib import Path

from config import SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH, BASE_DIR, DEBUG
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import logging module
from logger import setup_logging, log_login, log_operation, log_error, log_sql
from models import (
    get_db_connection, init_db, get_all_posts, get_all_posts_cursor, get_post_by_id,
    create_post, update_post, delete_post, update_post_with_tags,
    get_user_by_username, get_user_by_id, create_user, update_user, delete_user, get_all_users,
    get_all_categories, create_category, update_category, delete_category,
    get_category_by_id, get_posts_by_category, get_posts_by_author,
    create_tag, get_all_tags, get_popular_tags, get_tag_by_id, update_tag, delete_tag,
    get_tag_by_name, set_post_tags, get_post_tags, get_posts_by_tag,
    search_posts,
    create_comment, get_comments_by_post, get_all_comments,
    update_comment_visibility, delete_comment,
    get_db_context, paginate_query_cursor
)

# Import auth decorators
from auth_decorators import (
    login_required, role_required, admin_required, editor_required,
    can_edit_post, can_delete_post, can_manage_users, get_current_user
)

# Flask app with templates and static in parent directory
app = Flask(__name__,
            template_folder=str(BASE_DIR / 'templates'),
            static_folder=str(BASE_DIR / 'static'))
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# CSRF protection
csrf = CSRFProtect(app)

# Rate limiting to prevent brute force attacks
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Session security settings
from config import SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE

# Setup logging system
setup_logging(app)

# Timezone handling
from datetime import datetime, timedelta, timezone
import pytz

# Define China timezone (UTC+8)
CHINA_TZ = pytz.timezone('Asia/Shanghai')

def utc_to_local(utc_datetime_str):
    """Convert UTC datetime string to China timezone (UTC+8)"""
    if not utc_datetime_str:
        return ''

    try:
        # Parse the datetime string
        if isinstance(utc_datetime_str, str):
            # Handle SQLite datetime format
            utc_datetime = datetime.fromisoformat(utc_datetime_str.replace(' ', 'T'))
            if utc_datetime.tzinfo is None:
                # Assume UTC if no timezone info
                utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
        else:
            utc_datetime = utc_datetime_str

        # Convert to China timezone
        local_datetime = utc_datetime.astimezone(CHINA_TZ)

        # Format as string
        return local_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        # If conversion fails, return original string
        return utc_datetime_str

# Register custom filter for Jinja2
app.jinja_env.globals.update(utc_to_local=utc_to_local)

# Custom datetime filter that displays time in China timezone
@app.template_filter('localtime')
def localtime_filter(value):
    """Jinja2 filter to convert UTC to local time"""
    return utc_to_local(value)


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
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user.get('role', 'author')  # 存储角色信息
            flash(f'欢迎回来，{user["username"]}！', 'success')

            # 记录成功登录
            log_login(username, success=True)

            next_page = request.args.get('next')
            if next_page:
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

        if not title or not content:
            flash('标题和内容不能为空', 'error')
            categories = get_all_categories()
            return render_template('admin/editor.html', post=None, categories=categories)

        # 获取当前用户ID作为作者
        author_id = session.get('user_id')

        # Create post first
        post_id = create_post(title, content, is_published, category_id, author_id)

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

        # Handle tags
        tag_names = request.form.get('tags', '').split(',')

        # Update post and tags in a single transaction
        update_post_with_tags(post_id, title, content, is_published, category_id, tag_names)

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
    """Handle image upload"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400

    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{secure_filename(file.filename)}"
    filepath = UPLOAD_FOLDER / filename

    try:
        file.save(str(filepath))
        # Return URL to uploaded image
        url = url_for('static', filename=f'uploads/{filename}')
        return jsonify({'success': True, 'url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
    """Create default admin user if not exists"""
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')

    existing_user = get_user_by_username(username)
    if not existing_user:
        password_hash = generate_password_hash(password)
        user_id = create_user(username, password_hash)
        if user_id:
            print(f"Created admin user: {username}")
        else:
            print("Failed to create admin user")
    else:
        print(f"Admin user already exists: {username}")


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

        if len(password) < 10:
            flash('密码长度至少为10位', 'error')
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
    return render_template('error.html', status_code=500, error=str(error)), 500


@app.errorhandler(sqlite3.Error)
def database_error(error):
    """Handle database errors"""
    log_error(error, context='Database Error')
    return render_template('error.html', status_code=500, error=str(error)), 500


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
