"""
日志配置模块
提供统一的日志配置和记录功能
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
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
    """记录登录日志（追加模式）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if success:
        log_entry = f"[{timestamp}] SUCCESS - 用户: {username}\n"
    else:
        log_entry = f"[{timestamp}] FAILED - 用户: {username} - 原因: {error_msg}\n"

    try:
        with open(LOGIN_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write login log: {e}")


def log_operation(user_id, username, action, details=None):
    """记录操作日志（追加模式）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_entry = f"[{timestamp}] 用户ID: {user_id} | 用户: {username} | 操作: {action}"
    if details:
        log_entry += f" | 详情: {details}"
    log_entry += "\n"

    try:
        with open(OPERATION_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write operation log: {e}")


def log_error(error, context=None, user_id=None):
    """记录错误日志（追加模式）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    error_info = f"[{timestamp}] 错误: {str(error)}\n"
    if context:
        error_info += f"上下文: {context}\n"
    if user_id:
        error_info += f"用户ID: {user_id}\n"
    error_info += f"堆栈跟踪:\n{traceback.format_exc()}\n"

    try:
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(error_info)
    except Exception as e:
        print(f"Failed to write error log: {e}")


def api_internal_error(e, context=None):
    """
    记录完整异常到错误日志，并返回脱敏的统一500 JSON响应。

    避免把 str(e)（可能包含SQL、路径等内部信息）直接返回给客户端。
    """
    from flask import jsonify
    log_error(e, context=context)
    return jsonify({'success': False, 'error': '服务器内部错误'}), 500


def log_sql(operation, sql, params=None, result=None, execution_time=None):
    """记录 SQL 操作日志（追加模式）"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_entry = f"[{timestamp}] {operation}: {sql}"
    if params:
        log_entry += f" | 参数: {params}"
    if result:
        log_entry += f" | 结果: {result}"
    if execution_time:
        log_entry += f" | 执行时间: {execution_time:.2f}ms"
        # 慢查询警告
        if execution_time > 100:
            logging.getLogger(__name__).warning(f"慢查询警告 ({execution_time:.2f}ms): {sql}")
    log_entry += "\n"

    try:
        with open(SQL_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write SQL log: {e}")

