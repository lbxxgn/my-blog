"""文章管理与仪表盘（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify

from models import (
    get_all_posts, get_post_by_id, create_post, update_post, delete_post,
    get_all_categories, set_post_tags, get_db_connection,
)
from auth_decorators import login_required, can_edit_post, can_delete_post
from logger import log_operation, api_internal_error
from backend.config import UPLOAD_FOLDER
import threading
from flask import current_app


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/image-status/<int:optimization_id>')
@login_required
def image_optimization_status(optimization_id):
    """查询图片优化状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, thumbnail_path, medium_path, large_path,
                   original_size, optimized_size
            FROM optimized_images
            WHERE id = ?
        ''', (optimization_id,))
        result = cursor.fetchone()
        conn.close()

        if not result:
            return jsonify({'success': False, 'error': '未找到优化记录'}), 404

        compression_ratio = 0
        if result['original_size'] and result['optimized_size']:
            compression_ratio = (1 - result['optimized_size'] / result['original_size']) * 100

        # 转换相对路径为URL
        def path_to_url(path):
            if not path:
                return None
            return url_for('static', filename=path.replace(str(UPLOAD_FOLDER.parent) + '/', '').replace('\\', '/'))

        return jsonify({
            'success': True,
            'status': result['status'],
            'sizes': {
                'thumbnail': path_to_url(result['thumbnail_path']),
                'medium': path_to_url(result['medium_path']),
                'large': path_to_url(result['large_path'])
            } if result['status'] == 'completed' else None,
            'compression_ratio': compression_ratio
        })
    except Exception as e:
        logger.error(f'Error fetching optimization status: {e}')
        return api_internal_error(e)

@admin_bp.route('/')
@login_required
def admin_dashboard():
    """管理仪表板 - 列出所有文章包括草稿"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id')
    type_filter = request.args.get('type')

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(include_drafts=True, page=page, per_page=per_page, category_id=category_id, type=type_filter)
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
                         current_category_id=category_id,
                         current_type=type_filter)

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

        if not content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': '内容不能为空'}), 400
            flash('内容不能为空', 'error')
            categories = get_all_categories()
            return render_template('admin/editor.html',
                post={
                    'title': title or '',
                    'content': content or '',
                    'is_published': is_published,
                    'category_id': category_id,
                    'access_level': access_level,
                    'access_password': access_password,
                },
                categories=categories)

        if not title:
            title = _auto_title(content)

        # 获取当前用户ID作为作者
        author_id = session.get('user_id')

        # 创建文章
        post_id = create_post(title, content, is_published, category_id, author_id, access_level, access_password)

        # 如果原标题为空，后台异步调用AI生成更好的标题
        if not request.form.get('title') and post_id:
            app = current_app._get_current_object()
            t = threading.Thread(target=_async_ai_title, args=(app, post_id, content, author_id))
            t.daemon = True
            t.start()

        # 更新AI历史记录
        try:
            conn = get_db_connection()
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
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'post_id': post_id,
                'is_published': is_published,
                'redirect': url_for('blog.view_post', post_id=post_id)
            })
        return redirect(url_for('blog.view_post', post_id=post_id))

    categories = get_all_categories()
    return render_template('admin/editor.html', post=None, categories=categories)

@admin_bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@can_edit_post
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

        # 访问权限设置
        access_level = request.form.get('access_level', 'public')
        access_password = request.form.get('access_password', '') if access_level == 'password' else None

        if not content:
            flash('内容不能为空', 'error')
            categories = get_all_categories()
            # 保留用户已输入的数据，避免清空
            post['title'] = title or ''
            post['content'] = content or ''
            post['category_id'] = category_id
            post['access_level'] = access_level
            post['access_password'] = access_password
            return render_template('admin/editor.html', post=post, categories=categories)

        if not title:
            title = _auto_title(content)

        # 处理标签
        tag_names = request.form.get('tags', '').split(',')

        # 更新文章
        update_post(post_id, title, content, is_published, category_id, access_level, access_password)

        # 如果原标题为空，后台异步调用AI生成更好的标题
        if not request.form.get('title'):
            user_id = session.get('user_id')
            app = current_app._get_current_object()
            t = threading.Thread(target=_async_ai_title, args=(app, post_id, content, user_id))
            t.daemon = True
            t.start()

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
@can_delete_post
def delete_post_route(post_id):
    """删除文章"""
    post = get_post_by_id(post_id)
    if post is None:
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'error': '文章不存在'}), 404
        flash('文章不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    delete_post(post_id)

    # 如果是 AJAX 请求，返回 JSON
    if request.headers.get('Content-Type') == 'application/json' or \
       request.headers.get('Accept') == 'application/json':
        return jsonify({'success': True, 'message': '文章已删除'})

    flash('文章已删除', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/convert-note/<int:post_id>', methods=['POST'])
@can_edit_post
def convert_note_to_post(post_id):
    """将笔记转换为文章"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    update_post(post_id, post['title'], post['content'], post['is_published'],
                post.get('category_id'), post.get('access_level', 'public'),
                post.get('access_password'), type='post')

    log_operation(user_id, username, '转换笔记为文章',
                  f'文章ID: {post_id}, 标题: {post["title"]}')

    flash('笔记已成功转换为文章', 'success')
    return redirect(url_for('admin.admin_dashboard'))
