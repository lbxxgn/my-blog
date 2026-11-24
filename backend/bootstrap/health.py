"""存活 / 就绪探针。

探针会被容器与负载均衡高频调用，因此不参与限流。
"""

from flask import jsonify

__all__ = ['register_health_endpoints']


def register_health_endpoints(app, limiter):
    @app.route('/healthz')
    @limiter.exempt
    def healthz():
        """进程存活检查（不访问数据库）。"""
        return jsonify({'status': 'ok'}), 200

    @app.route('/readyz')
    @limiter.exempt
    def readyz():
        """就绪检查：数据库可连接且基础表已初始化。"""
        from backend.models import get_db_context

        try:
            with get_db_context() as conn:
                conn.execute('SELECT 1').fetchone()
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
                ).fetchone()
            if not row:
                raise RuntimeError('schema not initialized')
            return jsonify({'status': 'ready'}), 200
        except Exception as e:
            app.logger.error('readiness check failed: %s', e)
            return jsonify({'status': 'not ready'}), 503
