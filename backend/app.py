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
import logging
import os
import sys
from pathlib import Path

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 统一使用 backend.* 绝对导入；脚本方式启动时保证项目根目录在 sys.path 中
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# 项目配置导入
# =============================================================================
from backend.config import BASE_DIR, DEBUG

# =============================================================================
# 扩展导入
# =============================================================================
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

# =============================================================================
# 装配层导入
# =============================================================================
from backend.bootstrap.admin_user import create_admin_user
from backend.bootstrap.assets import (
    init_asset_manager,
    register_asset_maintenance,
    register_service_worker_route,
    register_static_cache_headers,
    vite_asset,
)
from backend.bootstrap.blueprints import register_blueprints
from backend.bootstrap.cli import register_cli_commands
from backend.bootstrap.config import apply_core_config, apply_defaults, enable_proxy_fix
from backend.bootstrap.errors import register_error_handlers
from backend.bootstrap.filters import register_context_processors, register_template_filters
from backend.bootstrap.health import register_health_endpoints
from backend.bootstrap.icons import register_site_icon_routes
from backend.bootstrap.security import (
    apply_rate_limits,
    init_extensions,
    register_csrf_exemptions,
    register_security_headers,
    run_startup_migrations,
)
from backend.models import init_db

# 延迟导入项目模块（避免循环导入问题）
def get_setup_logging():
    """获取setup_logging函数"""
    from backend.logger import setup_logging
    return setup_logging

logger = logging.getLogger(__name__)


# =============================================================================
# 注册HEIC格式支持（iPhone图片）
# =============================================================================
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    logger.info('HEIC/HEIF format support enabled for iPhone images')
except ImportError:
    logger.info('pillow-heif not installed, HEIC/HEIF support disabled')


# =============================================================================
# Flask应用初始化
# =============================================================================
def create_app(config_overrides=None):
    """创建 Flask 应用实例；模块级 app 仍保留以兼容 gunicorn 与测试。"""
    app = Flask(__name__,
                template_folder=str(BASE_DIR / 'templates'),
                static_folder=str(BASE_DIR / 'static'))

    csrf = CSRFProtect()
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["1000 per day", "200 per hour"],
        storage_uri="memory://",
        strategy="fixed-window",
    )
    cache = Cache()

    # 基础配置必须先于 proxy / 静态资源 / 迁移等依赖配置的分支
    apply_core_config(app, config_overrides)
    enable_proxy_fix(app)

    init_asset_manager(app)
    register_static_cache_headers(app)
    register_service_worker_route(app)
    register_site_icon_routes(app)
    register_security_headers(app)

    apply_defaults(app, config_overrides)
    init_extensions(app, csrf, limiter, cache)
    run_startup_migrations(app)

    register_context_processors(app, vite_asset)
    if app.config.get('SETUP_LOGGING', True):
        get_setup_logging()(app)
    register_template_filters(app)

    register_blueprints(app)
    register_csrf_exemptions(app, csrf)
    apply_rate_limits(app, limiter)

    register_asset_maintenance(app)
    register_error_handlers(app)
    register_health_endpoints(app, limiter)
    register_cli_commands(app)

    return app


app = create_app()
csrf = app.csrf_protect
limiter = app.limiter
cache = app.cache


# =============================================================================
# 后台线程：自动备份 / 异步任务
# =============================================================================
def _should_start_background_worker():
    """测试环境与调试重载父进程中不启动后台线程。"""
    if os.environ.get('TESTING') == '1' or 'pytest' in sys.modules:
        return False
    if DEBUG and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return False
    return True


def _maybe_start_backup_scheduler():
    """在 Web 进程内启动自动备份线程。"""
    if not _should_start_background_worker():
        return

    from backend.config import BACKUP_SCHEDULE_ENABLED

    if not BACKUP_SCHEDULE_ENABLED:
        return

    from backend.services.backup import start_backup_scheduler

    start_backup_scheduler()


def _maybe_start_task_worker():
    if not _should_start_background_worker():
        return

    from backend.services.task_queue import start_worker

    start_worker(app)


_maybe_start_backup_scheduler()
_maybe_start_task_worker()


# =============================================================================
# 主程序入口
# =============================================================================
if __name__ == '__main__':
    init_db()
    create_admin_user()
    # 启动时初始化资源和恢复任务
    app.auto_regenerate_assets()
    # macOS ControlCenter often uses port 5000, so we use 5001
    port = int(os.environ.get('PORT', 5001))
    # 默认监听所有网卡，可通过 HOST 环境变量覆盖（如仅需本机访问设 HOST=127.0.0.1）
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(debug=DEBUG, host=host, port=port)
