from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import markdown2
import os
from datetime import datetime
from pathlib import Path

from config import SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
from models import (
    get_db_connection, init_db, get_all_posts, get_post_by_id,
    create_post, update_post, delete_post, get_user_by_username, create_user,
    get_all_categories, create_category, update_category, delete_category,
    get_category_by_id, get_posts_by_category
)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


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
    posts = get_all_posts(include_drafts=False)
    categories = get_all_categories()
    return render_template('index.html', posts=posts, categories=categories)


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
    return render_template('post.html', post=post)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('login.html')

        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'欢迎回来，{user["username"]}！', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard - list all posts including drafts"""
    posts = get_all_posts(include_drafts=True)
    return render_template('admin/dashboard.html', posts=posts)


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

        post_id = create_post(title, content, is_published, category_id)
        flash('文章创建成功', 'success')
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

        update_post(post_id, title, content, is_published, category_id)
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

    posts = get_posts_by_category(category_id, include_drafts=False)
    return render_template('index.html', posts=posts, category=category)


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


@app.cli.command()
def init():
    """Initialize the database and create admin user"""
    init_db()
    create_admin_user()
    print("Database initialized successfully")


if __name__ == '__main__':
    init_db()
    create_admin_user()
    app.run(debug=True)
