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
版本: 2.1
"""

# =============================================================================
# 标准库导入
# =============================================================================
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from urllib.parse import urlparse, urljoin
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
from flask_wtf.csrf import CSRFProtect
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
    get_db_connection, init_db, get_db_context,
    get_user_by_username, get_user_by_id, create_user
)

# =============================================================================
# 权限装饰器导入
# =============================================================================
from auth_decorators import login_required

# =============================================================================
# Flask应用初始化
# =============================================================================
app = Flask(__name__,
            template_folder=str(BASE_DIR / 'templates'),
            static_folder=str(BASE_DIR / 'static'))

# 基础配置
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# =============================================================================
# CSRF保护配置
# =============================================================================
csrf = CSRFProtect(app)
app.config['WTF_CSRF_ENABLED'] = WTF_CSRF_ENABLED
app.config['WTF_CSRF_TIME_LIMIT'] = WTF_CSRF_TIME_LIMIT
app.config['WTF_CSRF_SSL_STRICT'] = WTF_CSRF_SSL_STRICT

# =============================================================================
# 速率限制配置
# =============================================================================
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# =============================================================================
# 会话安全配置
# =============================================================================
from config import SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE

# =============================================================================
# 模板上下文处理器
# =============================================================================
@app.context_processor
def inject_site_settings():
    """将网站设置注入到所有模板中"""
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
    """
    if len(password) < 10:
        return False, '密码长度至少为10位'

    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'

    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'

    if not re.search(r'\d', password):
        return False, '密码必须包含至少一个数字'

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

CHINA_TZ = pytz.timezone('Asia/Shanghai')

def utc_to_local(utc_datetime_str):
    """将UTC时间字符串转换为中国时区（UTC+8）的本地时间"""
    if not utc_datetime_str:
        return ''

    try:
        if isinstance(utc_datetime_str, str):
            utc_datetime = datetime.fromisoformat(utc_datetime_str.replace(' ', 'T'))
            if utc_datetime.tzinfo is None:
                utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
        else:
            utc_datetime = utc_datetime_str

        local_datetime = utc_datetime.astimezone(CHINA_TZ)
        return local_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        return utc_datetime_str

app.jinja_env.globals.update(utc_to_local=utc_to_local)

@app.template_filter('localtime')
def localtime_filter(value):
    """Jinja2过滤器：将UTC时间转换为本地时间"""
    return utc_to_local(value)

@app.template_filter('excerpt')
def excerpt_filter(value, max_length=200):
    """Jinja2过滤器：获取文章摘要（清理HTML并截断）"""
    from models import get_post_excerpt
    return get_post_excerpt(value, max_length)

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =============================================================================
# 注册蓝图
# =============================================================================
from routes import auth_bp, blog_bp, admin_bp, api_bp, ai_bp, knowledge_base_bp

# 注册认证蓝图
app.register_blueprint(auth_bp)

# 注册博客蓝图
app.register_blueprint(blog_bp)

# 注册管理后台蓝图
app.register_blueprint(admin_bp)

# 注册API蓝图
app.register_blueprint(api_bp, url_prefix='/api')

# 注册AI蓝图
app.register_blueprint(ai_bp)

# 注册知识库蓝图
app.register_blueprint(knowledge_base_bp, url_prefix='/knowledge_base')

# 为知识库 API 端点豁免 CSRF 保护
# 浏览器扩展无法处理 CSRF token
csrf.exempt(knowledge_base_bp)
# 对登录路由应用速率限制
limiter.limit("5 per minute")(app.view_functions['auth.login'])

# =============================================================================
# 兼容性endpoint别名（保持旧模板的url_for调用正常工作）
# =============================================================================
# 由于blueprint重构，endpoint名称从'index'变为'blog.index'等
# 为了保持模板兼容性，为旧endpoint名称创建路由包装器

# Blog endpoints
@app.route('/')
def index():
    """首页别名（兼容模板）"""
    return app.view_functions['blog.index']()

@app.route('/search')
def search():
    """搜索页面别名（兼容模板）"""
    return app.view_functions['blog.search']()

@app.route('/post/<int:post_id>')
def view_post(post_id):
    """查看文章别名（兼容模板）"""
    return app.view_functions['blog.view_post'](post_id)

@app.route('/category/<int:category_id>')
def view_category(category_id):
    """查看分类别名（兼容模板）"""
    return app.view_functions['blog.view_category'](category_id)

@app.route('/tag/<int:tag_id>')
def view_tag(tag_id):
    """查看标签别名（兼容模板）"""
    return app.view_functions['blog.view_tag'](tag_id)

@app.route('/author/<int:author_id>')
def view_author(author_id):
    """查看作者别名（兼容模板）"""
    return app.view_functions['blog.view_author'](author_id)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    """添加评论别名（兼容模板）"""
    return app.view_functions['blog.add_comment'](post_id)

# Auth endpoints
@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录别名（兼容模板）"""
    return app.view_functions['auth.login']()

@app.route('/logout')
def logout():
    """退出登录别名（兼容模板）"""
    return app.view_functions['auth.logout']()

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """修改密码别名（兼容模板）"""
    return app.view_functions['auth.change_password']()

# Admin endpoints
@app.route('/admin')
def admin_dashboard():
    """管理后台首页别名（兼容模板）"""
    return app.view_functions['admin.admin_dashboard']()

@app.route('/admin/new')
def new_post():
    """新建文章别名（兼容模板）"""
    return app.view_functions['admin.new_post']()

@app.route('/admin/users')
def user_list():
    """用户列表别名（兼容模板）"""
    return app.view_functions['admin.user_list']()

@app.route('/admin/users/new')
def new_user():
    """新建用户别名（兼容模板）"""
    return app.view_functions['admin.new_user']()

@app.route('/admin/categories')
def category_list():
    """分类列表别名（兼容模板）"""
    return app.view_functions['admin.categories']()

@app.route('/admin/categories/new', methods=['POST'])
def new_category():
    """新建分类别名（兼容模板）"""
    return app.view_functions['admin.new_category']()

@app.route('/admin/tags')
def tag_list():
    """标签列表别名（兼容模板）"""
    return app.view_functions['admin.tags']()

@app.route('/admin/tags/new', methods=['POST'])
def new_tag():
    """新建标签别名（兼容模板）"""
    return app.view_functions['admin.new_tag']()

@app.route('/admin/export')
def export_page():
    """导出页面别名（兼容模板）"""
    return app.view_functions['admin.export']()

@app.route('/admin/export/json')
def export_json():
    """导出JSON别名（兼容模板）"""
    return app.view_functions['admin.export_json']()

@app.route('/admin/export/markdown')
def export_markdown():
    """导出Markdown别名（兼容模板）"""
    return app.view_functions['admin.export_markdown']()

@app.route('/admin/import')
def import_page():
    """导入页面别名（兼容模板）"""
    return app.view_functions['admin.import_page']()

@app.route('/admin/import/json', methods=['POST'])
def import_json():
    """导入JSON别名（兼容模板）"""
    return app.view_functions['admin.import_json']()

@app.route('/admin/import/markdown', methods=['POST'])
def import_markdown():
    """导入Markdown别名（兼容模板）"""
    return app.view_functions['admin.import_markdown']()

@app.route('/admin/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    """编辑文章别名（兼容模板）"""
    return app.view_functions['admin.edit_post'](post_id)

@app.route('/admin/delete/<int:post_id>', methods=['POST'])
def delete_post_route(post_id):
    """删除文章别名（兼容模板）"""
    return app.view_functions['admin.delete_post_route'](post_id)

@app.route('/admin/batch-update-category', methods=['POST'])
def batch_update_category():
    """批量更新分类别名（兼容模板）"""
    return app.view_functions['admin.batch_update_category']()

@app.route('/admin/batch-delete', methods=['POST'])
def batch_delete():
    """批量删除别名（兼容模板）"""
    return app.view_functions['admin.batch_delete']()

@app.route('/admin/upload', methods=['POST'])
def upload():
    """文件上传别名（兼容模板）"""
    return app.view_functions['admin.upload']()

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
def delete_category_route(category_id):
    """删除分类别名（兼容模板）"""
    return app.view_functions['admin.delete_category_route'](category_id)

@app.route('/admin/tags/<int:tag_id>/delete', methods=['POST'])
def delete_tag_route(tag_id):
    """删除标签别名（兼容模板）"""
    return app.view_functions['admin.delete_tag_route'](tag_id)

@app.route('/admin/comments')
def comments_list():
    """评论列表别名（兼容模板）"""
    return app.view_functions['admin.comments']()

@app.route('/admin/comments/<int:comment_id>/toggle', methods=['POST'])
def toggle_comment(comment_id):
    """切换评论状态别名（兼容模板）"""
    return app.view_functions['admin.toggle_comment'](comment_id)

@app.route('/admin/comments/<int:comment_id>/delete', methods=['POST'])
def delete_comment_route(comment_id):
    """删除评论别名（兼容模板）"""
    return app.view_functions['admin.delete_comment_route'](comment_id)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    """编辑用户别名（兼容模板）"""
    return app.view_functions['admin.edit_user'](user_id)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
def delete_user_route(user_id):
    """删除用户别名（兼容模板）"""
    return app.view_functions['admin.delete_user_route'](user_id)

# AI endpoints
@app.route('/admin/ai/history')
def ai_history():
    """AI历史记录别名（兼容模板）"""
    return app.view_functions['ai.history']()

@app.route('/admin/ai/configure', methods=['GET', 'POST'])
def ai_settings():
    """AI设置页面别名（兼容模板）"""
    return app.view_functions['ai.configure']()

# =============================================================================
# 创建管理员用户
# =============================================================================
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

# =============================================================================
# 错误处理器
# =============================================================================
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    log_error(error, context='404 Not Found')
    return render_template('error.html', status_code=404), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    log_error(error, context='500 Internal Server Error')
    
    if app.config.get('DEBUG'):
        error_message = str(error)
    else:
        error_message = "服务器内部错误，请稍后重试"
    
    return render_template('error.html', status_code=500, error=error_message), 500

@app.errorhandler(sqlite3.Error)
def database_error(error):
    """Handle database errors"""
    log_error(error, context='Database Error')
    
    if app.config.get('DEBUG'):
        error_message = f"数据库错误: {str(error)}"
    else:
        error_message = "数据库错误，请稍后重试"
    
    return render_template('error.html', status_code=500, error=error_message), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    log_error(error, context='413 Payload Too Large')
    
    if request.path.startswith('/admin/upload') or request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': f'文件太大，最大允许上传 16MB'
        }), 413
    
    return render_template('error.html', status_code=413, error='上传的文件太大，最大允许 16MB'), 413

# =============================================================================
# CLI命令
# =============================================================================
@app.cli.command()
def init():
    """Initialize the database and create admin user"""
    init_db()
    create_admin_user()
    print("Database initialized successfully")

# =============================================================================
# 主程序入口
# =============================================================================
if __name__ == '__main__':
    init_db()
    create_admin_user()
    # macOS ControlCenter often uses port 5000, so we use 5001
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=DEBUG, host='0.0.0.0', port=port)
