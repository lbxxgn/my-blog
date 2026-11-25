"""错误处理器（404 / 500 / 数据库异常 / 413）。"""

import sqlite3

from flask import jsonify, render_template, request

from backend.config import MAX_CONTENT_LENGTH

__all__ = ['register_error_handlers']


def register_error_handlers(app):
    from backend.logger import log_error

    @app.errorhandler(404)
    def not_found_error(error):
        context = (
            f'404 Not Found | {request.method} {request.full_path} '
            f'| IP: {request.remote_addr} '
            f'| Referer: {request.referrer or "-"} '
            f'| UA: {request.user_agent or "-"}'
        )
        app.logger.warning(context)
        return render_template('error.html', status_code=404), 404

    @app.errorhandler(500)
    def internal_error(error):
        log_error(error, context='500 Internal Server Error')

        if app.config.get('DEBUG'):
            error_message = str(error)
        else:
            error_message = "服务器内部错误，请稍后重试"

        return render_template('error.html', status_code=500, error=error_message), 500

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        log_error(error, context='Database Error')

        if app.config.get('DEBUG'):
            error_message = f"数据库错误: {str(error)}"
        else:
            error_message = "数据库错误，请稍后重试"

        return render_template('error.html', status_code=500, error=error_message), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        log_error(error, context='413 Payload Too Large')
        limit_mb = MAX_CONTENT_LENGTH // 1024 // 1024

        if request.path.startswith('/admin/upload') or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': f'文件太大，最大允许上传 {limit_mb}MB'
            }), 413

        return render_template('error.html', status_code=413, error=f'上传的文件太大，最大允许 {limit_mb}MB'), 413
