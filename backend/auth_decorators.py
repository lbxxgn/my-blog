"""
权限装饰器模块
提供基于角色的访问控制装饰器
"""
from functools import wraps
from flask import session, flash, redirect, url_for, request
from models import get_user_by_username, get_post_by_id

# 角色层级（数字越大权限越高）
ROLE_HIERARCHY = {
    'author': 1,
    'editor': 2,
    'admin': 3
}


def login_required(f):
    """要求用户登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """
    要求特定角色的装饰器

    用法:
        @role_required('admin', 'editor')
        def some_admin_function():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_id') is None:
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            user = get_user_by_username(session.get('username'))
            if not user:
                flash('用户不存在', 'error')
                return redirect(url_for('logout'))

            if user.get('role') not in allowed_roles:
                flash('权限不足', 'error')
                return redirect(url_for('blog.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """要求管理员权限"""
    return role_required('admin')(f)


def editor_required(f):
    """要求编辑或管理员权限"""
    return role_required('editor', 'admin')(f)


def can_edit_post(f):
    """
    检查用户是否可以编辑文章
    - admin和editor可以编辑所有文章
    - author只能编辑自己的文章
    """
    @wraps(f)
    def decorated_function(post_id, *args, **kwargs):
        if session.get('user_id') is None:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        user = get_user_by_username(session.get('username'))
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('logout'))

        post = get_post_by_id(post_id)
        if not post:
            flash('文章不存在', 'error')
            return redirect(url_for('blog.index'))

        # admin和editor可以编辑所有文章
        if user.get('role') in ['admin', 'editor']:
            return f(post_id, *args, **kwargs)

        # author只能编辑自己的文章
        if user.get('role') == 'author':
            if post.get('author_id') == user.get('id'):
                return f(post_id, *args, **kwargs)
            else:
                flash('您只能编辑自己的文章', 'error')
                return redirect(url_for('view_post', post_id=post_id))

        flash('权限不足', 'error')
        return redirect(url_for('blog.index'))

    return decorated_function


def can_delete_post(f):
    """
    检查用户是否可以删除文章
    - 只有admin可以删除文章
    """
    @wraps(f)
    def decorated_function(post_id, *args, **kwargs):
        if session.get('user_id') is None:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        user = get_user_by_username(session.get('username'))
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('logout'))

        # 只有admin可以删除文章
        if user.get('role') != 'admin':
            flash('只有管理员可以删除文章', 'error')
            return redirect(url_for('admin_dashboard'))

        return f(post_id, *args, **kwargs)

    return decorated_function


def can_manage_users(f):
    """检查用户是否可以管理其他用户（仅admin）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        user = get_user_by_username(session.get('username'))
        if not user or user.get('role') != 'admin':
            flash('只有管理员可以管理用户', 'error')
            return redirect(url_for('admin_dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """获取当前登录用户信息"""
    if not session.get('user_id'):
        return None

    return get_user_by_username(session.get('username'))


def has_permission(role, required_role):
    """
    检查角色是否满足权限要求

    Args:
        role: 用户当前角色
        required_role: 所需的最低角色

    Returns:
        bool: 是否有权限
    """
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(required_role, 0)
