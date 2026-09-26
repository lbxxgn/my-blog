"""文章详情、密码校验、评论、沉淀（blog 蓝图子模块）。"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from utils.markdown_renderer import render_markdown
from models import (
    get_post_by_id,
    get_post_tags, get_comments_by_post, create_comment,
    check_post_access, verify_post_password, get_category_tree, precipitate_post_to_knowledge, get_adjacent_posts,
)

from . import blog_bp, logger, get_optimized_image_url, get_optimized_image_url_cached, extract_post_image_urls, extract_post_excerpt, rewrite_post_image_sources, determine_mobile_image_layout, build_post_card_payload, build_post_card_payloads, serialize_post_for_json  # noqa: F401


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

    # 渲染 Markdown 并清洗 HTML 防止 XSS（保留首行缩进等行内样式）
    post['content_html'] = render_markdown(post['content'])
    post['content_html'] = rewrite_post_image_sources(post['content_html'], size='medium')

    # 获取文章标签
    post['tags'] = get_post_tags(post_id)

    # 获取文章评论
    comments = get_comments_by_post(post_id)

    # 生成完整的文章URL用于分享
    post_url = url_for('blog.view_post', post_id=post_id, _external=True)

    # 知识库分类树（用于"沉淀到知识库"弹窗，仅登录用户）
    kb_tree = get_category_tree('knowledge') if session.get('user_id') else None

    # 上一篇/下一篇（仅公开博客文章）
    adjacent = get_adjacent_posts(post_id)

    return render_template('post.html', post=post, comments=comments, post_url=post_url,
                           kb_tree=kb_tree, adjacent=adjacent)

@blog_bp.route('/post/<int:post_id>/precipitate', methods=['POST'])
def precipitate_to_knowledge(post_id):
    """将博客文章沉淀为知识库文档"""
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': '请先登录'}), 401
    from models import get_category_by_id
    data = request.get_json(silent=True) or request.form
    category_id_raw = data.get('category_id')
    try:
        category_id = int(category_id_raw)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '请选择目标目录'}), 400
    category = get_category_by_id(category_id)
    if not category or category.get('space') != 'knowledge':
        return jsonify({'success': False, 'error': '目标目录不存在'}), 400
    doc_id = precipitate_post_to_knowledge(post_id, category_id)
    if doc_id:
        return jsonify({'success': True, 'doc_id': doc_id,
                        'redirect': url_for('knowledge.view_doc', doc_id=doc_id)})
    return jsonify({'success': False, 'error': '文章不存在或沉淀失败'}), 400

@blog_bp.route('/post/<int:post_id>/verify-password', methods=['POST'])
def verify_post_password_route(post_id):
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

    # AJAX 提交返回 JSON，前端失败时保留已输入内容
    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def comment_error(message, status=400):
        if is_xhr:
            return jsonify({'success': False, 'error': message}), status
        flash(message, 'error')
        return redirect(url_for('blog.view_post', post_id=post_id))

    if not author_name or not content:
        return comment_error('姓名和评论内容不能为空')

    if len(author_name) > 50:
        return comment_error('姓名过长')

    if len(content) > 1000:
        return comment_error('评论内容过长')

    create_comment(post_id, author_name, author_email, content)
    if is_xhr:
        return jsonify({'success': True, 'message': '评论提交成功'})
    flash('评论提交成功', 'success')
    return redirect(url_for('blog.view_post', post_id=post_id))
