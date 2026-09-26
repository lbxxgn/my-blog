"""批量操作（admin 蓝图子模块）。"""

from flask import session, jsonify
import sqlite3

from models import (
    get_db_connection,
)
from auth_decorators import login_required, get_current_user
from logger import log_operation, log_error, log_sql, api_internal_error


from . import admin_bp, mobile_bp, logger, _auto_title, _async_ai_title, get_request_data, normalize_post_ids, filter_operable_post_ids, allowed_file, build_upload_response, validate_password_strength  # noqa: F401


@admin_bp.route('/batch-update-category', methods=['POST'])
@login_required
def batch_update_category():
    """批量更新文章分类"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = get_request_data()
        post_ids = normalize_post_ids(data.get('post_ids'))
        category_id = data.get('category_id')

        log_operation(user_id, username, '批量更新分类',
                    f'文章ID: {post_ids}, 目标分类: {category_id}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        post_ids, skipped = filter_operable_post_ids(post_ids)
        if not post_ids:
            return jsonify({'success': False, 'message': '没有可操作的文章（只能操作自己的文章）'}), 403

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
        log_error(e, context='批量操作数据库错误')
        return jsonify({'success': False, 'message': '数据库操作失败，请稍后重试'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        return api_internal_error(e)
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
        data = get_request_data()
        post_ids = normalize_post_ids(data.get('post_ids'))

        log_operation(user_id, username, '批量删除文章',
                    f'文章ID: {post_ids}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        # 与单篇删除（can_delete_post）一致：仅管理员可删除
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            return jsonify({'success': False, 'message': '只有管理员可以删除文章'}), 403

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
        return api_internal_error(e)
    finally:
        if conn:
            conn.close()

@admin_bp.route('/batch-publish', methods=['POST'])
@login_required
def batch_publish():
    """批量发布/取消发布文章"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = get_request_data()
        post_ids = normalize_post_ids(data.get('post_ids'))
        publish = data.get('publish')
        if publish is None:
            action = data.get('action', 'publish')
            publish = action != 'unpublish'
        elif isinstance(publish, str):
            publish = publish.lower() in ('1', 'true', 'yes', 'publish')

        log_operation(user_id, username, '批量发布/取消发布',
                    f'文章ID: {post_ids}, 操作: {"发布" if publish else "取消发布"}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        post_ids, skipped = filter_operable_post_ids(post_ids)
        if not post_ids:
            return jsonify({'success': False, 'message': '没有可操作的文章（只能操作自己的文章）'}), 403

        conn = get_db_connection()
        cursor = conn.cursor()

        updated_count = 0
        errors = []

        for post_id in post_ids:
            try:
                log_sql('batch_publish', f'UPDATE posts SET is_published = {publish} WHERE id = {post_id}')

                cursor.execute(
                    'UPDATE posts SET is_published = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (1 if publish else 0, post_id)
                )

                updated_count += 1
            except Exception as e:
                error_msg = f"文章 {post_id} 更新失败: {str(e)}"
                errors.append(error_msg)
                log_error(e, context=f'批量发布 - 文章 {post_id}', user_id=user_id)

        conn.commit()

        action = '发布' if publish else '取消发布'
        if errors:
            result_msg = f'部分成功: {updated_count}/{len(post_ids)} 篇文章{action}成功'
            if updated_count == 0:
                result_msg = f'{action}失败: {errors[0]}'
        else:
            result_msg = f'成功{action} {updated_count} 篇文章'

        log_operation(user_id, username, '批量发布/取消发布', result_msg)

        return jsonify({
            'success': updated_count > 0,
            'message': result_msg
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        log_error(e, context='批量操作数据库错误')
        return jsonify({'success': False, 'message': '数据库操作失败，请稍后重试'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        return api_internal_error(e)
    finally:
        if conn:
            conn.close()

@admin_bp.route('/batch-add-tags', methods=['POST'])
@login_required
def batch_add_tags():
    """批量添加标签到文章"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = get_request_data()
        post_ids = normalize_post_ids(data.get('post_ids'))
        tags = data.get('tags', [])  # 标签列表
        tag_ids = data.get('tag_ids', [])
        if not isinstance(tags, list):
            tags = [tag.strip() for tag in str(tags).split(',') if tag.strip()] if tags else []
        if not isinstance(tag_ids, list):
            tag_ids = [tag_ids] if tag_ids else []

        log_operation(user_id, username, '批量添加标签',
                    f'文章ID: {post_ids}, 标签: {tags}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        post_ids, skipped = filter_operable_post_ids(post_ids)
        if not post_ids:
            return jsonify({'success': False, 'message': '没有可操作的文章（只能操作自己的文章）'}), 403

        conn = get_db_connection()
        cursor = conn.cursor()

        if not tags and tag_ids:
            for tag_id in tag_ids:
                cursor.execute('SELECT name FROM tags WHERE id = ?', (int(tag_id),))
                tag = cursor.fetchone()
                if tag:
                    tags.append(tag['name'] if 'name' in tag.keys() else tag[0])

        if not tags:
            return jsonify({'success': False, 'message': '未指定任何标签'}), 400

        updated_count = 0
        errors = []

        for post_id in post_ids:
            try:
                # 获取或创建标签
                for tag_name in tags:
                    # 检查标签是否存在
                    cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                    tag = cursor.fetchone()

                    if not tag:
                        # 创建新标签
                        cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag_name,))
                        tag_id = cursor.lastrowid
                    else:
                        tag_id = tag[0]

                    # 检查文章是否已有此标签
                    cursor.execute('SELECT 1 FROM post_tags WHERE post_id = ? AND tag_id = ?',
                                 (post_id, tag_id))
                    if not cursor.fetchone():
                        # 添加标签关联
                        cursor.execute('INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                                     (post_id, tag_id))

                updated_count += 1
            except Exception as e:
                error_msg = f"文章 {post_id} 添加标签失败: {str(e)}"
                errors.append(error_msg)
                log_error(e, context=f'批量添加标签 - 文章 {post_id}', user_id=user_id)

        conn.commit()

        if errors:
            result_msg = f'部分成功: {updated_count}/{len(post_ids)} 篇文章添加标签成功'
            if updated_count == 0:
                result_msg = f'添加标签失败: {errors[0]}'
        else:
            result_msg = f'成功为 {updated_count} 篇文章添加标签'

        log_operation(user_id, username, '批量添加标签', result_msg)

        return jsonify({
            'success': updated_count > 0,
            'message': result_msg
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        log_error(e, context='批量操作数据库错误')
        return jsonify({'success': False, 'message': '数据库操作失败，请稍后重试'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        return api_internal_error(e)
    finally:
        if conn:
            conn.close()

@admin_bp.route('/batch-update-access', methods=['POST'])
@login_required
def batch_update_access():
    """批量更新文章访问权限"""
    user_id = session.get('user_id')
    username = session.get('username', 'Unknown')

    conn = None
    try:
        data = get_request_data()
        post_ids = normalize_post_ids(data.get('post_ids'))
        access_level = data.get('access_level') or data.get('access') or 'public'  # public, password, private
        access_password = data.get('access_password') or data.get('password') or ''  # 仅当access_level为password时使用

        log_operation(user_id, username, '批量更新访问权限',
                    f'文章ID: {post_ids}, 权限: {access_level}')

        if not post_ids:
            return jsonify({'success': False, 'message': '未选择任何文章'}), 400

        if access_level not in ['public', 'password', 'private']:
            return jsonify({'success': False, 'message': '无效的访问权限类型'}), 400

        post_ids, skipped = filter_operable_post_ids(post_ids)
        if not post_ids:
            return jsonify({'success': False, 'message': '没有可操作的文章（只能操作自己的文章）'}), 403

        conn = get_db_connection()
        cursor = conn.cursor()

        updated_count = 0
        errors = []

        for post_id in post_ids:
            try:
                log_sql('batch_update_access', f'UPDATE posts SET access_level = {access_level} WHERE id = {post_id}')

                cursor.execute(
                    'UPDATE posts SET access_level = ?, access_password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (access_level, access_password if access_level == 'password' else None, post_id)
                )

                updated_count += 1
            except Exception as e:
                error_msg = f"文章 {post_id} 更新失败: {str(e)}"
                errors.append(error_msg)
                log_error(e, context=f'批量更新访问权限 - 文章 {post_id}', user_id=user_id)

        conn.commit()

        access_level_names = {
            'public': '公开',
            'password': '密码保护',
            'private': '私密'
        }

        if errors:
            result_msg = f'部分成功: {updated_count}/{len(post_ids)} 篇文章更新成功'
            if updated_count == 0:
                result_msg = f'更新失败: {errors[0]}'
        else:
            result_msg = f'成功将 {updated_count} 篇文章设置为{access_level_names[access_level]}'

        log_operation(user_id, username, '批量更新访问权限', result_msg)

        return jsonify({
            'success': updated_count > 0,
            'message': result_msg
        })

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        log_error(e, context='批量操作数据库错误')
        return jsonify({'success': False, 'message': '数据库操作失败，请稍后重试'}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        return api_internal_error(e)
    finally:
        if conn:
            conn.close()
