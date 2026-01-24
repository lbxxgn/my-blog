"""
日志配置模块
提供统一的日志配置和记录功能
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import request, session, g
import traceback

# 日志目录
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# 日志文件路径
LOGIN_LOG = LOG_DIR / 'login.log'
OPERATION_LOG = LOG_DIR / 'operation.log'
ERROR_LOG = LOG_DIR / 'error.log'
SQL_LOG = LOG_DIR / 'sql.log'

# 确保日志文件存在
for log_file in [LOGIN_LOG, OPERATION_LOG, ERROR_LOG, SQL_LOG]:
    if not log_file.exists():
        log_file.touch()


def setup_logging(app):
    """配置应用日志系统"""

    # 创建日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 错误日志处理器 - 按日期分割
    error_handler = logging.handlers.TimedRotatingFileHandler(
        ERROR_LOG,
        when='midnight',  # 每天午夜轮转
        interval=1,
        backupCount=30,  # 保留30天的日志
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # SQL 操作日志处理器
    sql_handler = logging.handlers.TimedRotatingFileHandler(
        SQL_LOG,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    sql_handler.setLevel(logging.DEBUG)
    sql_handler.setFormatter(formatter)

    # 配置应用日志器
    app.logger.handlers.clear()  # 清除现有处理器
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(sql_handler)

    # 同时输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    app.logger.info('=' * 60)
    app.logger.info('应用启动')
    app.logger.info('=' * 60)


def log_login(username, success=True, error_msg=None):
    """记录登录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if success:
        LOGIN_LOG.write_text(f"[{timestamp}] SUCCESS - 用户: {username}\n", encoding='utf-8')
    else:
        LOGIN_LOG.write_text(f"[{timestamp}] FAILED - 用户: {username} - 原因: {error_msg}\n", encoding='utf-8')


def log_operation(user_id, username, action, details=None):
    """记录操作日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_entry = f"[{timestamp}] 用户ID: {user_id} | 用户: {username} | 操作: {action}"
    if details:
        log_entry += f" | 详情: {details}"
    log_entry += "\n"

    OPERATION_LOG.write_text(log_entry, encoding='utf-8')


def log_error(error, context=None, user_id=None):
    """记录错误日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    error_info = f"[{timestamp}] 错误: {str(error)}\n"
    if context:
        error_info += f"上下文: {context}\n"
    if user_id:
        error_info += f"用户ID: {user_id}\n"
    error_info += f"堆栈跟踪:\n{traceback.format_exc()}\n"

    ERROR_LOG.write_text(error_info, encoding='utf-8')


def log_sql(operation, sql, params=None, result=None):
    """记录 SQL 操作日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_entry = f"[{timestamp}] {operation}: {sql}"
    if params:
        log_entry += f" | 参数: {params}"
    if result:
        log_entry += f" | 结果: {result}"
    log_entry += "\n"

    SQL_LOG.write_text(log_entry, encoding='utf-8')


# 日志装饰器
def log_route(action):
    """装饰器：记录路由操作"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            username = session.get('username', 'Anonymous')

            try:
                result = f(*args, **kwargs)

                # 记录成功操作
                log_operation(user_id, username, action)

                return result
            except Exception as e:
                # 记录错误
                log_error(e, context=action, user_id=user_id)
                raise

        return decorated_function
    return decorator


def handle_errors(f):
    """装饰器：统一错误处理"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # 记录错误
            log_error(e, context=f.__name__, user_id=session.get('user_id'))

            # 根据错误类型返回不同的响应
            from flask import jsonify

            if hasattr(e, 'status_code'):
                status = e.status_code
            else:
                status = 500

            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'操作失败: {str(e)}'
            }), status

    return decorated_function
