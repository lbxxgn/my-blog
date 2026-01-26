"""
管理后台路由

包括管理仪表板、文章管理、分类管理、标签管理、评论管理、
导入导出、用户管理等功能。
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import sqlite3

from models import (
    get_all_posts, get_post_by_id, create_post, update_post, delete_post,
    get_all_categories, create_category, update_category, delete_category,
    get_category_by_id, get_posts_by_category,
    create_tag, get_all_tags, get_popular_tags, get_tag_by_id, update_tag, delete_tag,
    get_tag_by_name, set_post_tags, get_post_tags, get_posts_by_tag,
    create_comment, get_comments_by_post, get_all_comments,
    update_comment_visibility, delete_comment,
    search_posts, get_posts_by_author,
    get_user_by_username, get_user_by_id, create_user, update_user, delete_user, get_all_users,
    get_db_connection
)
from auth_decorators import login_required, can_manage_users
from logger import log_operation, log_error, log_sql
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

# 创建管理后台蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_password_strength(password):
    """
    验证密码强度

    要求:
        - 至少10位长度
        - 包含至少一个大写字母
        - 包含至少一个小写字母
        - 包含至少一个数字

    Args:
        password (str): 待验证的密码

    Returns:
        tuple: (is_valid, error_message)
    """
    import re
    if len(password) < 10:
        return False, '密码长度至少为10位'

    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'

    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'

    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'

    return True, None


# =============================================================================
# 管理仪表板和文章管理
# =============================================================================

@admin_bp.route('/')
@login_required
def admin_dashboard():
    """管理仪表板 - 列出所有文章包括草稿"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id')

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(include_drafts=True, page=page, per_page=per_page, category_id=category_id)
    categories = get_all_categories()

    # 计算分页信息
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # 计算显示的页码范围
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


@admin_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """创建新文章"""
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

        # 创建文章
        post_id = create_post(title, content, is_published, category_id, author_id, access_level, access_password)

        # 更新AI历史记录
        try:
            from models import DATABASE_URL
            db_path = DATABASE_URL.replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

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

        # 处理标签
        tag_names = request.form.get('tags', '').split(',')
        if tag_names and tag_names[0]:
            set_post_tags(post_id, tag_names)

        if is_published:
            flash('文章发布成功', 'success')
        else:
            flash('草稿保存成功', 'success')
        return redirect(url_for('blog.view_post', post_id=post_id))

    categories = get_all_categories()
    return render_template('admin/editor.html', post=None, categories=categories)


@admin_bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """编辑现有文章"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))

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

        # 处理标签
        tag_names = request.form.get('tags', '').split(',')

        # 更新文章
        update_post(post_id, title, content, is_published, category_id, access_level, access_password)

        # 更新标签
        if tag_names and tag_names[0]:
            set_post_tags(post_id, tag_names)
        else:
            # 清空所有标签
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))
            conn.commit()
            conn.close()

        flash('文章更新成功', 'success')
        return redirect(url_for('blog.view_post', post_id=post_id))

    categories = get_all_categories()
    return render_template('admin/editor.html', post=post, categories=categories)


@admin_bp.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post_route(post_id):
    """删除文章"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    delete_post(post_id)
    flash('文章已删除', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/batch-update-category', methods=['POST'])
@login_required
def batch_update_category():
    """批量更新文章分类"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = request.get_json()
        post_ids = data.get('post_ids', [])
        category_id = data.get('category_id')

        log_operation(user_id, username, '批量更新分类',
                    f'文章ID: {post_ids}, 目标分类: {category_id}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        # 将空字符串转换为None表示未分类
        if category_id == '' or category_id == 'none':
            category_id = None
        elif category_id is not None:
            category_id = int(category_id)

        log_sql('batch_update_category', f'UPDATE posts SET category_id = {category_id}',
                 f'post_ids={post_ids}')

        conn = get_db_connection()
        cursor = conn.cursor()

        updated_count = 0
        errors = []

        for post_id in post_ids:
            try:
                cursor.execute('SELECT title, content FROM posts WHERE id = ?', (post_id,))
                post_data = cursor.fetchone()

                if post_data:
                    log_sql('update_post', f'UPDATE posts SET category_id = {category_id} WHERE id = {post_id}')

                    cursor.execute(
                        'UPDATE posts SET category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (category_id, post_id)
                    )

                    log_sql('update_fts', f'DELETE FROM posts_fts WHERE rowid = {post_id}')
                    cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))

                    log_sql('insert_fts', f'INSERT INTO posts_fts(rowid, title, content) VALUES ({post_id}, ...)')
                    cursor.execute('INSERT INTO posts_fts(rowid, title, content) VALUES (?, ?, ?)',
                                  (post_id, post_data[0], post_data[1]))

                    updated_count += 1
            except Exception as e:
                error_msg = f"文章 {post_id} 更新失败: {str(e)}"
                errors.append(error_msg)
                log_error(e, context=f'批量更新分类 - 文章 {post_id}', user_id=user_id)

        conn.commit()

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


@admin_bp.route('/batch-delete', methods=['POST'])
@login_required
def batch_delete():
    """批量删除文章"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = request.get_json()
        post_ids = data.get('post_ids', [])

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
                # 删除标签关联
                cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))

                # 删除评论
                cursor.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))

                # 删除文章
                cursor.execute('DELETE FROM posts_fts WHERE rowid = ?', (post_id,))
                cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))

                deleted_count += 1
            except Exception as e:
                error_msg = f"文章 {post_id} 删除失败: {str(e)}"
                errors.append(error_msg)
                log_error(e, context=f'批量删除 - 文章 {post_id}', user_id=user_id)

        conn.commit()

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

    except Exception as e:
        if conn:
            conn.rollback()
        log_error(e, context='批量删除文章', user_id=user_id)
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/upload', methods=['POST'])
@login_required
def upload_image():
    """
    处理图片上传，包含多层安全验证

    安全验证流程:
        1. 文件存在性检查
        2. 文件扩展名白名单验证
        3. 文件类型实际内容验证（PIL）
        4. 图片尺寸验证（防止DoS）
        5. 文件大小验证（5MB限制）
        6. 安全文件名生成（时间戳+随机后缀）
    """
    # 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    # 验证文件扩展名
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400

    # 读取文件内容进行深度验证
    file_content = file.read()
    file.seek(0)  # 重置文件指针

    # 验证实际文件类型和尺寸
    try:
        from PIL import Image
        import io

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

        # 验证文件大小
        file_size = len(file_content)
        max_file_size = 5 * 1024 * 1024  # 5MB
        if file_size > max_file_size:
            return jsonify({'success': False, 'error': f'文件大小超过限制（最大{max_file_size//1024//1024}MB）'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': '图片文件损坏或格式错误'}), 400

    # 生成安全的文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    secure_name = secure_filename(file.filename)
    ext = secure_name.rsplit('.', 1)[1].lower() if '.' in secure_name else file_type
    random_suffix = os.urandom(4).hex()
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


# =============================================================================
# 分类管理
# =============================================================================

@admin_bp.route('/categories')
@login_required
def category_list():
    """列出所有分类"""
    categories = get_all_categories()
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/categories/new', methods=['POST'])
@login_required
def new_category():
    """创建新分类"""
    name = request.form.get('name')
    if not name:
        flash('分类名称不能为空', 'error')
        return redirect(url_for('admin.category_list'))

    category_id = create_category(name)
    if category_id:
        flash('分类创建成功', 'success')
    else:
        flash('分类名称已存在', 'error')
    return redirect(url_for('admin.category_list'))


@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category_route(category_id):
    """删除分类"""
    delete_category(category_id)
    flash('分类已删除', 'success')
    return redirect(url_for('admin.category_list'))


# =============================================================================
# 标签管理
# =============================================================================

@admin_bp.route('/tags')
@login_required
def tag_list():
    """列出所有标签"""
    tags = get_all_tags()
    return render_template('admin/tags.html', tags=tags)


@admin_bp.route('/tags/new', methods=['POST'])
@login_required
def new_tag():
    """创建新标签"""
    name = request.form.get('name')
    if not name:
        flash('标签名称不能为空', 'error')
        return redirect(url_for('admin.tag_list'))

    tag_id = create_tag(name)
    if tag_id:
        flash('标签创建成功', 'success')
    else:
        flash('标签名称已存在', 'error')
    return redirect(url_for('admin.tag_list'))


@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag_route(tag_id):
    """删除标签"""
    delete_tag(tag_id)
    flash('标签已删除', 'success')
    return redirect(url_for('admin.tag_list'))


# =============================================================================
# 评论管理
# =============================================================================

@admin_bp.route('/comments')
@login_required
def comment_list():
    """列出所有评论"""
    comments = get_all_comments(include_hidden=True)
    return render_template('admin/comments.html', comments=comments)


@admin_bp.route('/comments/<int:comment_id>/toggle', methods=['POST'])
@login_required
def toggle_comment(comment_id):
    """切换评论可见性"""
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

    return redirect(url_for('admin.comment_list'))


@admin_bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment_route(comment_id):
    """删除评论"""
    delete_comment(comment_id)
    flash('评论已删除', 'success')
    return redirect(url_for('admin.comment_list'))


# =============================================================================
# 导入导出
# =============================================================================

@admin_bp.route('/export')
@login_required
def export_page():
    """导出页面"""
    return render_template('admin/export.html')


@admin_bp.route('/export/markdown')
@login_required
def export_markdown():
    """导出所有文章为Markdown文件"""
    try:
        from export import export_all_posts_to_markdown
        count, path = export_all_posts_to_markdown()
        flash(f'成功导出 {count} 篇文章到 {path}', 'success')
        log_operation(session.get('user_id'), session.get('username'), f'导出 {count} 篇文章为 Markdown')
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export to markdown')

    return redirect(url_for('admin.export_page'))


@admin_bp.route('/export/json')
@login_required
def export_json():
    """导出所有文章为JSON"""
    try:
        from export import export_to_json
        count, path = export_to_json()
        flash(f'成功导出 {count} 篇文章到 {path}', 'success')
        log_operation(session.get('user_id'), session.get('username'), f'导出 {count} 篇文章为 JSON')
    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')
        log_error(e, context='Export to JSON')

    return redirect(url_for('admin.export_page'))


@admin_bp.route('/import')
@login_required
def import_page():
    """导入页面"""
    return render_template('admin/import.html')


@admin_bp.route('/import/json', methods=['POST'])
@login_required
def import_json():
    """从JSON文件导入文章"""
    try:
        user_id = session.get('user_id')

        if 'import_file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(url_for('admin.import_page'))

        file = request.files['import_file']

        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.import_page'))

        if not file.filename.endswith('.json'):
            flash('只支持JSON格式文件', 'error')
            return redirect(url_for('admin.import_page'))

        # 临时保存文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as tmp_file:
            file.save(tmp_file.name)
            tmp_file_path = tmp_file.name

        # 导入文章
        from import_posts import import_from_json
        count, skipped, messages = import_from_json(tmp_file_path, user_id)

        # 清理临时文件
        os.unlink(tmp_file_path)

        # 显示结果
        for msg in messages[1:]:
            flash(msg, 'success' if '✅' in msg else 'warning' if '⚠️' in msg else 'error')

        flash(messages[0], 'success')
        log_operation(user_id, session.get('username'), f'导入 {count} 篇文章从 JSON')

    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from JSON')

    return redirect(url_for('admin.import_page'))


@admin_bp.route('/import/markdown', methods=['POST'])
@login_required
def import_markdown():
    """从Markdown目录导入文章"""
    try:
        user_id = session.get('user_id')

        if 'import_file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(url_for('admin.import_page'))

        file = request.files['import_file']

        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.import_page'))

        if not file.filename.endswith('.zip'):
            flash('只支持ZIP压缩包格式', 'error')
            return redirect(url_for('admin.import_page'))

        # 解压ZIP文件
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, 'import.zip')
            file.save(zip_path)

            # 解压
            extract_dir = os.path.join(tmp_dir, 'extracted')
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 查找posts目录或使用解压目录
            posts_dir = os.path.join(extract_dir, 'posts')
            if not os.path.exists(posts_dir):
                posts_dir = extract_dir

            # 导入文章
            from import_posts import import_from_markdown_directory
            count, skipped, messages = import_from_markdown_directory(posts_dir, user_id)

        # 显示结果
        for msg in messages[1:]:
            flash(msg, 'success' if '✅' in msg else 'warning' if '⚠️' in msg else 'error')

        flash(messages[0], 'success')
        log_operation(user_id, session.get('username'), f'导入 {count} 篇文章从 Markdown')

    except Exception as e:
        flash(f'导入失败: {str(e)}', 'error')
        log_error(e, context='Import from markdown')

    return redirect(url_for('admin.import_page'))


# =============================================================================
# 用户管理
# =============================================================================

@admin_bp.route('/users')
@can_manage_users
def user_list():
    """用户列表页面"""
    users = get_all_users()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
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
            flash('用户创建成功', 'success')
            return redirect(url_for('admin.user_list'))
        else:
            flash('用户创建失败', 'error')

    return render_template('admin/user_form.html', user=None)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@can_manage_users
def edit_user(user_id):
    """编辑用户"""
    user = get_user_by_id(user_id)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.user_list'))

    if request.method == 'POST':
        role = request.form.get('role')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')

        # 如果提供新密码，验证并更新
        new_password = request.form.get('new_password')
        if new_password:
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                flash(error_msg, 'error')
                return render_template('admin/user_form.html', user=user)

            password_hash = generate_password_hash(new_password)
            update_user(user_id, role=role, display_name=display_name, bio=bio, password_hash=password_hash)
        else:
            update_user(user_id, role=role, display_name=display_name, bio=bio)

        flash('用户更新成功', 'success')
        return redirect(url_for('admin.user_list'))

    return render_template('admin/user_form.html', user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@can_manage_users
def delete_user_route(user_id):
    """删除用户"""
    # 不允许删除自己
    if user_id == session.get('user_id'):
        flash('不能删除自己的账号', 'error')
        return redirect(url_for('admin.user_list'))

    if delete_user(user_id):
        flash('用户已删除', 'success')
    else:
        flash('用户删除失败', 'error')

    return redirect(url_for('admin.user_list'))
