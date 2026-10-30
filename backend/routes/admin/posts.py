"""文章管理与仪表盘（admin 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify

from models import (
    get_all_posts, get_all_post_ids, get_post_by_id, create_post, update_post, delete_post,
    get_all_categories, set_post_tags, get_db_connection, get_posts_by_author, get_all_users, get_all_tags,
    get_post_revisions, get_post_revision, restore_post_revision,
    soft_delete_post, get_deleted_posts, restore_deleted_post, purge_deleted_post,
)
from auth_decorators import login_required, can_edit_post, can_delete_post, role_required, get_current_user
from logger import log_operation, api_internal_error
from backend.config import UPLOAD_FOLDER
from utils.markdown_renderer import render_content, render_markdown
import re
import threading
from datetime import datetime
from flask import current_app


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


def _normalize_content_format(value):
    """把表单/接口传入的内容格式归一为 'html' 或 'markdown'。"""
    return 'markdown' if str(value or '').strip().lower() == 'markdown' else 'html'


def _parse_tag_names(raw):
    """标签支持中英文逗号，并去重。"""
    names = []
    for name in re.split(r'[,，]', raw or ''):
        name = name.strip()
        if name and name not in names:
            names.append(name)
    return names


def _normalize_publish_at(value):
    """把 datetime-local 值转为 SQLite 时间；无效值返回 None。"""
    raw = str(value or '').strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(raw, fmt).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    return None


@admin_bp.route('/preview', methods=['POST'])
@login_required
def preview_content():
    """把编辑器内容渲染为与文章详情页一致的安全 HTML，用于实时预览。"""
    try:
        data = request.get_json(silent=True) or {}
        html = render_content(data.get('content', ''), data.get('content_format'))
        return jsonify({'success': True, 'html': html})
    except Exception as e:
        return api_internal_error(e)


@admin_bp.route('/convert-format', methods=['POST'])
@login_required
def convert_content_format():
    """在 HTML 与 Markdown 之间转换正文，切换格式时避免内容丢失。"""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        target = _normalize_content_format(data.get('to'))
        if target == 'markdown':
            from models.knowledge import html_to_markdown
            converted = html_to_markdown(content)
        else:
            converted = render_markdown(content)
        return jsonify({'success': True, 'content': converted, 'content_format': target})
    except Exception as e:
        return api_internal_error(e)


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
    try:
        from models import publish_due_posts
        publish_due_posts()
    except Exception:
        pass
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    per_page = request.args.get('per_page', 20, type=int)
    # 表单中未选择的筛选项会以空字符串提交，必须归一为 None，
    # 否则会被当作 category_id='' / type='' 去查询，导致列表恒为空。
    category_id = request.args.get('category_id') or None
    type_filter = request.args.get('type') or None
    query = (request.args.get('q') or '').strip()
    status_filter = request.args.get('status') or ''
    access_filter = request.args.get('access_level') or ''
    author_filter = request.args.get('author_id', type=int)

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    is_manager = session.get('role') in ('admin', 'editor')
    if not is_manager:
        author_filter = session.get('user_id')

    def _load_posts(target_page):
        return get_all_posts(
            include_drafts=True, page=target_page, per_page=per_page,
            category_id=category_id, type=type_filter, post_type='blog',
            q=query or None, status=status_filter or None,
            access_level=access_filter or None, author_id=author_filter,
        )

    posts_data = _load_posts(page)
    # 翻页越界（如手动改 URL）时回到最后一页，避免看到“假空列表”
    if posts_data['total'] > 0 and page > posts_data['total_pages']:
        page = posts_data['total_pages']
        posts_data = _load_posts(page)

    categories = get_all_categories(post_type='blog', space='blog')
    authors = get_all_users() if is_manager else []

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
                         current_type=type_filter,
                         current_query=query,
                         current_status=status_filter,
                         current_access=access_filter,
                         current_author_id=author_filter,
                         authors=authors)

@admin_bp.route('/post-ids')
@login_required
def dashboard_post_ids():
    """返回当前筛选条件下的全部文章 ID，供后台“全选筛选结果”。"""
    category_id = request.args.get('category_id') or None
    type_filter = request.args.get('type') or None
    query = (request.args.get('q') or '').strip()
    status_filter = request.args.get('status') or ''
    access_filter = request.args.get('access_level') or ''
    author_filter = request.args.get('author_id', type=int)

    if session.get('role') not in ('admin', 'editor'):
        author_filter = session.get('user_id')

    ids = get_all_post_ids(
        include_drafts=True, category_id=category_id, type=type_filter, post_type='blog',
        q=query or None, status=status_filter or None,
        access_level=access_filter or None, author_id=author_filter,
    )
    return jsonify({'success': True, 'ids': ids, 'total': len(ids)})


@admin_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """创建新文章"""
    if request.method == 'POST':
        raw_title = (request.form.get('title') or '').strip()
        title = raw_title
        content = request.form.get('content')
        content_format = _normalize_content_format(request.form.get('content_format'))
        is_published = request.form.get('is_published') is not None
        category_id = request.form.get('category_id')
        if category_id == '':
            category_id = None
        elif category_id is not None:
            category_id = int(category_id)

        # 访问权限设置：密码保护必须提供非空密码，避免创建后永久锁死
        access_level = request.form.get('access_level', 'public')
        access_password = (request.form.get('access_password') or '').strip() if access_level == 'password' else None

        publish_at = _normalize_publish_at(request.form.get('publish_at'))
        if publish_at:
            is_published = False

        if access_level == 'password' and not access_password:
            message = '密码保护文章必须设置非空密码'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': message}), 400
            flash(message, 'error')
            categories = get_all_categories(post_type='blog', space='blog')
            all_tags = get_all_tags(post_type='blog')
            return render_template('admin/editor.html',
                post={
                    'title': title or '',
                    'content': content or '',
                    'content_format': content_format,
                    'is_published': is_published,
                    'category_id': category_id,
                    'access_level': access_level,
                    'access_password': '',
                },
                categories=categories, all_tags=all_tags)

        if not content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': '内容不能为空'}), 400
            flash('内容不能为空', 'error')
            categories = get_all_categories(post_type='blog', space='blog')
            all_tags = get_all_tags(post_type='blog')
            return render_template('admin/editor.html',
                post={
                    'title': title or '',
                    'content': content or '',
                    'content_format': content_format,
                    'is_published': is_published,
                    'category_id': category_id,
                    'access_level': access_level,
                    'access_password': access_password,
                },
                categories=categories, all_tags=all_tags)

        if not title:
            title = _auto_title(content)

        # 获取当前用户ID作为作者
        author_id = session.get('user_id')

        # 创建文章
        post_id = create_post(title, content, is_published, category_id, author_id, access_level, access_password, content_format=content_format)
        if post_id and publish_at:
            conn = get_db_connection()
            conn.execute('UPDATE posts SET publish_at = ? WHERE id = ?', (publish_at, post_id))
            conn.commit()
            conn.close()

        # 如果原标题为空，后台异步调用AI生成更好的标题
        if not raw_title and post_id:
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
        tag_names = _parse_tag_names(request.form.get('tags', ''))
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

    categories = get_all_categories(post_type='blog', space='blog')
    all_tags = get_all_tags(post_type='blog')
    return render_template('admin/editor.html', post=None, categories=categories, all_tags=all_tags)

@admin_bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@can_edit_post
def edit_post(post_id):
    """编辑现有文章"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        raw_title = (request.form.get('title') or '').strip()
        title = raw_title
        content = request.form.get('content')
        content_format = _normalize_content_format(request.form.get('content_format'))
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

        # 访问权限设置：留空表示沿用原密码；首次切换为密码保护必须填写
        access_level = request.form.get('access_level', 'public')
        submitted_password = (request.form.get('access_password') or '').strip()
        publish_at = _normalize_publish_at(request.form.get('publish_at'))
        if publish_at:
            is_published = False

        if access_level == 'password':
            access_password = submitted_password or post.get('access_password')
            if not access_password:
                flash('密码保护文章必须设置非空密码', 'error')
                categories = get_all_categories(post_type='blog', space='blog')
                all_tags = get_all_tags(post_type='blog')
                post['access_password'] = ''
                return render_template('admin/editor.html', post=post, categories=categories, all_tags=all_tags)
        else:
            access_password = None

        if not content:
            flash('内容不能为空', 'error')
            categories = get_all_categories(post_type='blog', space='blog')
            all_tags = get_all_tags(post_type='blog')
            # 保留用户已输入的数据，避免清空
            post['title'] = title or ''
            post['content'] = content or ''
            post['content_format'] = content_format
            post['category_id'] = category_id
            post['access_level'] = access_level
            post['access_password'] = access_password
            return render_template('admin/editor.html', post=post, categories=categories, all_tags=all_tags)

        if not title:
            title = _auto_title(content)

        # 处理标签
        tag_names = _parse_tag_names(request.form.get('tags', ''))

        # 更新文章
        update_post(post_id, title, content, is_published, category_id, access_level, access_password, content_format=content_format)
        conn = get_db_connection()
        conn.execute('UPDATE posts SET publish_at = ? WHERE id = ?', (publish_at, post_id))
        conn.commit()
        conn.close()

        # 如果原标题为空，后台异步调用AI生成更好的标题
        if not raw_title:
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

    categories = get_all_categories(post_type='blog', space='blog')
    all_tags = get_all_tags(post_type='blog')
    return render_template('admin/editor.html', post=post, categories=categories, all_tags=all_tags)

@admin_bp.route('/unpublish/<int:post_id>', methods=['POST'])
@can_edit_post
def unpublish_post(post_id):
    """取消发布，回到草稿状态。"""
    conn = get_db_connection()
    conn.execute('UPDATE posts SET is_published = 0, publish_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    flash('已取消发布，文章回到草稿状态', 'success')
    return redirect(url_for('admin.edit_post', post_id=post_id))


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

    soft_delete_post(post_id)

    # 如果是 AJAX 请求，返回 JSON
    if request.headers.get('Content-Type') == 'application/json' or \
       request.headers.get('Accept') == 'application/json':
        return jsonify({'success': True, 'message': '文章已移入回收站'})

    flash('文章已移入回收站', 'success')
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


@admin_bp.route('/trash')
@role_required('admin')
def trash_list():
    """回收站"""
    posts = get_deleted_posts()
    return render_template('admin/trash.html', posts=posts)


@admin_bp.route('/trash/<int:post_id>/restore', methods=['POST'])
@role_required('admin')
def restore_from_trash(post_id):
    if restore_deleted_post(post_id):
        flash('文章已恢复', 'success')
    else:
        flash('文章不存在或未删除', 'error')
    return redirect(url_for('admin.trash_list'))


@admin_bp.route('/trash/<int:post_id>/purge', methods=['POST'])
@role_required('admin')
def purge_from_trash(post_id):
    if purge_deleted_post(post_id):
        flash('文章已永久删除', 'success')
    else:
        flash('文章不存在或未删除', 'error')
    return redirect(url_for('admin.trash_list'))


@admin_bp.route('/revisions/<int:post_id>')
@can_edit_post
def revision_list(post_id):
    post = get_post_by_id(post_id)
    if not post:
        flash('文章不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    revisions = get_post_revisions(post_id)
    return render_template('admin/revisions.html', post=post, revisions=revisions)


@admin_bp.route('/revisions/<int:revision_id>/restore', methods=['POST'])
@role_required('admin', 'editor', 'author')
def restore_revision_route(revision_id):
    revision = get_post_revision(revision_id)
    if not revision:
        flash('版本不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    post = get_post_by_id(revision['post_id'])
    if not post:
        flash('文章不存在', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    user = get_current_user()
    if user.get('role') == 'author' and post.get('author_id') != user.get('id'):
        flash('无权恢复此版本', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    if restore_post_revision(revision_id):
        flash('已恢复到该历史版本', 'success')
    else:
        flash('恢复失败', 'error')
    return redirect(url_for('admin.revision_list', post_id=post['id']))
