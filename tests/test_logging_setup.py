"""日志配置：确保 INFO 控制台输出走 stdout（否则被 systemd 归入 error.log）。"""
import logging
import sys

from flask import Flask

from logger import setup_logging


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
