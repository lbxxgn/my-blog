"""
认证相关路由

包括登录、登出、修改密码等认证功能。
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from urllib.parse import urlparse, urljoin
import re

from models import get_user_by_username, update_user
from auth_decorators import login_required
from logger import log_login

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)


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
    if len(password) < 10:
        return False, '密码长度至少为10位'

    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'

    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'

    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'

    return True, None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    # Note: limiter will be applied from the main app
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
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
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('用户名或密码错误', 'error')
            # 记录失败登录
            log_login(username, success=False, error_msg='密码错误或用户不存在')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('blog.index'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
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

        # 验证密码强度
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            flash(error_msg, 'error')
            return render_template('change_password.html')

        # 验证当前密码
        user = get_user_by_username(session['username'])
        if not check_password_hash(user['password_hash'], current_password):
            flash('当前密码错误', 'error')
            return render_template('change_password.html')

        # 更新密码
        new_password_hash = generate_password_hash(new_password)
        update_user(user['id'], password_hash=new_password_hash)
        flash('密码修改成功', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('change_password.html')
