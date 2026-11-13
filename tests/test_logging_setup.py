"""日志配置：确保 INFO 控制台输出走 stdout（否则被 systemd 归入 error.log）。"""
import logging
import sys
from pathlib import Path

from flask import Flask

import logger as log_module
from logger import setup_logging


def _read(path):
    path = Path(path)
    return path.read_text(encoding='utf-8') if path.exists() else ''


def test_console_handler_targets_stdout():
    app = Flask(__name__)
    setup_logging(app)

    stream_handlers = [h for h in app.logger.handlers if type(h) is logging.StreamHandler]
    assert stream_handlers, '应存在控制台 StreamHandler'
    assert all(h.stream is sys.stdout for h in stream_handlers), \
        '控制台日志必须写 stdout，避免正常请求进入 StandardError/error.log'


def test_error_file_handler_exists():
    app = Flask(__name__)
    setup_logging(app)

    file_handlers = [
        h for h in app.logger.handlers
        if isinstance(h, logging.handlers.TimedRotatingFileHandler)
    ]
    assert file_handlers, '应存在错误日志文件处理器'
    # 其中至少有一个只接收 ERROR 及以上的错误日志文件处理器
    assert any(h.level == logging.ERROR for h in file_handlers)


def test_logs_are_routed_by_type():
    """INFO/WARNING 进 app.log，ERROR 进 error.log，SQL 只进 sql.log。"""
    app = Flask(__name__)
    setup_logging(app)

    logging.getLogger('services.demo').info('demo-info')
    logging.getLogger('services.demo').warning('demo-warning')
    logging.getLogger('services.demo').error('demo-error')
    log_module.log_sql('demo_op', 'SELECT 1')
    log_module.log_login('alice')
    log_module.log_operation(1, 'alice', 'demo-action')

    app_text = _read(log_module.APP_LOG)
    error_text = _read(log_module.ERROR_LOG)
    sql_text = _read(log_module.SQL_LOG)

    assert 'demo-info' in app_text and 'demo-warning' in app_text
    assert 'demo-error' not in app_text
    assert 'demo-error' in error_text
    assert 'SELECT 1' in sql_text
    assert '应用启动' not in sql_text
    assert 'SUCCESS - 用户: alice' in _read(log_module.LOGIN_LOG)
    assert '操作: demo-action' in _read(log_module.OPERATION_LOG)
