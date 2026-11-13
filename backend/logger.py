"""
日志配置模块
提供统一的日志配置和记录功能
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback

# 日志目录
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# 日志文件路径
APP_LOG = LOG_DIR / 'app.log'
LOGIN_LOG = LOG_DIR / 'login.log'
OPERATION_LOG = LOG_DIR / 'operation.log'
ERROR_LOG = LOG_DIR / 'error.log'
SQL_LOG = LOG_DIR / 'sql.log'

# 确保日志文件存在
for log_file in [APP_LOG, LOGIN_LOG, OPERATION_LOG, ERROR_LOG, SQL_LOG]:
    if not log_file.exists():
        log_file.touch()

LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
MESSAGE_FORMAT = '%(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

_HANDLER_MARK = '_simple_blog_handler'
_file_handlers = {}

ERROR_LOGGER = 'simple_blog.error'
SQL_LOGGER = 'simple_blog.sql'
LOGIN_LOGGER = 'simple_blog.login'
OPERATION_LOGGER = 'simple_blog.operation'


class _LoggerPrefixFilter(logging.Filter):
    """按 logger 名称前缀过滤第三方日志（如 Flask 开发服务器）。"""

    def __init__(self, prefixes):
        super().__init__()
        self.prefixes = prefixes

    def filter(self, record):
        return not record.name.startswith(self.prefixes)


class _BelowLevelFilter(logging.Filter):
    """只放行低于指定级别的记录，避免 ERROR 同时写入 app.log。"""

    def __init__(self, level):
        super().__init__()
        self.level = level

    def filter(self, record):
        return record.levelno < self.level


def _get_file_handler(path, level, backup_count, message_only=False):
    """获取（并缓存）指向同一文件的唯一 handler，避免多个 handler 同时写一个文件。"""
    key = (os.path.abspath(str(path)), level, message_only)
    handler = _file_handlers.get(key)
    if handler is None:
        handler = logging.handlers.TimedRotatingFileHandler(
            path,
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handler.setLevel(level)
        fmt = MESSAGE_FORMAT if message_only else LOG_FORMAT
        handler.setFormatter(logging.Formatter(fmt, datefmt=DATE_FORMAT))
        setattr(handler, _HANDLER_MARK, True)
        _file_handlers[key] = handler
    return handler


def _drop_handler(handler):
    for key, cached in list(_file_handlers.items()):
        if cached is handler:
            _file_handlers.pop(key, None)


def _get_audit_logger(name, path, backup_count):
    """获取写单独审计文件的 logger（自带 handler，不向 root 传播）。"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    expected = os.path.abspath(str(path))
    owned = [h for h in logger.handlers if getattr(h, _HANDLER_MARK, False)]
    reusable = any(
        os.path.abspath(getattr(h, 'baseFilename', '')) == expected
        for h in owned
    )
    if not reusable:
        for handler in owned:
            logger.removeHandler(handler)
            handler.close()
            _drop_handler(handler)
        logger.addHandler(_get_file_handler(path, logging.INFO, backup_count, message_only=True))
    return logger


def _get_error_logger():
    """获取错误日志 logger，复用 root 上的同一个 error handler。"""
    logger = logging.getLogger(ERROR_LOGGER)
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    if not any(getattr(h, _HANDLER_MARK, False) for h in logger.handlers):
        logger.addHandler(_get_file_handler(ERROR_LOG, logging.ERROR, 90))
    return logger


def _clear_owned_handlers():
    loggers = [
        logging.getLogger(),
        logging.getLogger(ERROR_LOGGER),
        logging.getLogger(SQL_LOGGER),
        logging.getLogger(LOGIN_LOGGER),
        logging.getLogger(OPERATION_LOGGER),
    ]
    owned = {}
    for logger in loggers:
        for handler in list(logger.handlers):
            if getattr(handler, _HANDLER_MARK, False):
                logger.removeHandler(handler)
                owned[id(handler)] = handler
    for handler in owned.values():
        handler.close()
    _file_handlers.clear()


def setup_logging(app):
    """配置应用日志系统：项目内所有 logger 的日志都会落盘。"""
    _clear_owned_handlers()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 错误日志处理器 - 按日期分割
    error_handler = _get_file_handler(ERROR_LOG, logging.ERROR, 90)
    # 应用运行日志（INFO/WARNING），过滤 Flask 开发服务器的噪音
    app_handler = _get_file_handler(APP_LOG, logging.INFO, 30)
    if not any(isinstance(f, _LoggerPrefixFilter) for f in app_handler.filters):
        app_handler.addFilter(_LoggerPrefixFilter(('werkzeug',)))
    if not any(isinstance(f, _BelowLevelFilter) for f in app_handler.filters):
        app_handler.addFilter(_BelowLevelFilter(logging.ERROR))
    # SQL 日志仅供 log_sql 使用，消息已自带时间戳
    sql_handler = _get_file_handler(SQL_LOG, logging.INFO, 7, message_only=True)

    # 控制台输出到 stdout，避免 INFO 日志被 systemd 归入 StandardError/error.log
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    setattr(console_handler, _HANDLER_MARK, True)

    # Flask 自带 logger：不复用 root，避免重复写；单独持有同一批 handler
    app.logger.handlers.clear()
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False
    for handler in (error_handler, app_handler, console_handler):
        app.logger.addHandler(handler)

    # 项目模块普遍使用 logging.getLogger(__name__)，统一由 root 收集
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in (error_handler, app_handler, console_handler):
        root.addHandler(handler)

    _get_error_logger()
    _get_audit_logger(SQL_LOGGER, SQL_LOG, 7)

    app.logger.info('=' * 60)
    app.logger.info('应用启动')
    app.logger.info('=' * 60)


def log_login(username, success=True, error_msg=None):
    """记录登录日志（追加模式）"""
    timestamp = datetime.now().strftime(DATE_FORMAT)

    if success:
        log_entry = f"[{timestamp}] SUCCESS - 用户: {username}"
    else:
        log_entry = f"[{timestamp}] FAILED - 用户: {username} - 原因: {error_msg}"

    try:
        _get_audit_logger(LOGIN_LOGGER, LOGIN_LOG, 180).info(log_entry)
    except Exception as e:
        print(f"Failed to write login log: {e}")


def log_operation(user_id, username, action, details=None):
    """记录操作日志（追加模式）"""
    timestamp = datetime.now().strftime(DATE_FORMAT)

    log_entry = f"[{timestamp}] 用户ID: {user_id} | 用户: {username} | 操作: {action}"
    if details:
        log_entry += f" | 详情: {details}"

    try:
        _get_audit_logger(OPERATION_LOGGER, OPERATION_LOG, 180).info(log_entry)
    except Exception as e:
        print(f"Failed to write operation log: {e}")


def log_error(error, context=None, user_id=None):
    """记录错误日志（追加模式）"""
    error_info = f"错误: {str(error)}"
    if context:
        error_info += f"\n上下文: {context}"
    if user_id:
        error_info += f"\n用户ID: {user_id}"
    error_info += f"\n堆栈跟踪:\n{traceback.format_exc()}"

    try:
        _get_error_logger().error(error_info.rstrip('\n'))
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
    timestamp = datetime.now().strftime(DATE_FORMAT)

    log_entry = f"[{timestamp}] {operation}: {sql}"
    if params:
        log_entry += f" | 参数: {params}"
    if result:
        log_entry += f" | 结果: {result}"
    if execution_time is not None:
        log_entry += f" | 执行时间: {execution_time:.2f}ms"
        if execution_time > 100:
            log_entry += " | 慢查询"

    try:
        _get_audit_logger(SQL_LOGGER, SQL_LOG, 7).info(log_entry)
    except Exception as e:
        print(f"Failed to write SQL log: {e}")
