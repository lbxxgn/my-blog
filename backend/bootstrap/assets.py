"""静态资源版本管理、静态文件缓存头、Service Worker 与 Vite 资源解析。"""

import json
import os

from flask import request

from backend.config import BASE_DIR
from backend.utils.asset_version import AssetVersionManager
from backend.utils.template_helpers import register_template_helpers

__all__ = [
    'init_asset_manager',
    'register_static_cache_headers',
    'register_service_worker_route',
    'register_asset_maintenance',
    'vite_asset',
]

# Vite manifest 读取缓存（按 mtime 失效）
_vite_manifest_cache = None
_vite_manifest_mtime = 0


def init_asset_manager(app):
    """初始化内容哈希版本管理（为 ``static_file`` 提供 ?v=hash），并注册模板助手。"""
    app.asset_manager = AssetVersionManager(app.static_folder)
    # 启动时刷新 manifest，保证与当前文件内容一致
    if app.config.get('REGENERATE_ASSETS', True):
        app.asset_manager.regenerate()
    register_template_helpers(app)


def register_static_cache_headers(app):
    """为静态文件响应添加缓存头，提升加载性能。"""

    @app.after_request
    def add_cache_headers_to_static_files(response):
        if not request.path.startswith('/static/'):
            return response

        filename = request.path.split('/static/')[-1]

        if filename.endswith(('.css', '.js')):
            # CSS/JS：长期缓存（1 年）
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            # 图片：中期缓存（1 周）
            response.headers['Cache-Control'] = 'public, max-age=604800'
        elif filename.endswith(('.woff', '.woff2', '.ttf', '.eot')):
            # 字体：长期缓存
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

        return response


def register_service_worker_route(app):
    """Service Worker 需要挂在根路径（作用域限制），静态资源在 /static/ 下无法满足。"""

    @app.route('/sw.js')
    def service_worker():
        response = app.send_static_file('sw.js')
        # SW 更新依赖网络获取，禁用缓存避免旧版本滞留
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        return response


def _get_vite_manifest():
    """读取并缓存 Vite 构建产物 manifest（按文件 mtime 失效）。"""
    global _vite_manifest_cache, _vite_manifest_mtime

    manifest_path = BASE_DIR / 'static' / 'frontend' / '.vite' / 'manifest.json'
    if not manifest_path.exists():
        return {}

    mtime = manifest_path.stat().st_mtime
    if _vite_manifest_cache is None or mtime != _vite_manifest_mtime:
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                _vite_manifest_cache = json.load(f)
            _vite_manifest_mtime = mtime
        except Exception:
            return {}
    return _vite_manifest_cache


def vite_asset(entry='src/main.tsx'):
    """根据 Vite manifest 返回前端资源路径：``{'js': [...], 'css': [...], 'assets': [...]}``。"""
    manifest = _get_vite_manifest()
    item = manifest.get(entry)
    if not item:
        return {'js': [], 'css': [], 'assets': []}

    js_files = [item.get('file')] if item.get('file') else []
    css_files = item.get('css', [])
    asset_files = item.get('assets', [])

    # 处理 imports（rolldown runtime 等）
    for imp in item.get('imports', []):
        imp_item = manifest.get(imp)
        if imp_item and imp_item.get('file') and imp_item.get('file') not in js_files:
            js_files.append(imp_item.get('file'))

    return {
        'js': [f'frontend/{p}' for p in js_files],
        'css': [f'frontend/{p}' for p in css_files],
        'assets': [f'frontend/{p}' for p in asset_files],
    }


def register_asset_maintenance(app):
    """挂载启动自检：缺 manifest 时重建，并恢复未完成的图片优化任务。"""
    logger = app.logger

    def auto_regenerate_assets():
        if getattr(app, 'asset_manager', None):
            if not app.asset_manager.manifest_file.exists():
                app.asset_manager.regenerate()

        # 恢复未完成的图片优化任务
        try:
            from backend.models import get_db_context
            from backend.tasks.image_optimization_task import queue_image_optimization

            with get_db_context() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT original_path FROM optimized_images
                    WHERE status IN ('pending', 'failed')
                       OR (status = 'completed' AND (medium_path IS NULL OR medium_path = ''))
                    ORDER BY created_at ASC
                ''')
                pending = cursor.fetchall()

            requeued = 0
            for row in pending:
                path = row['original_path']
                # 原图已不存在时无法重新优化，跳过避免无效任务
                if path and os.path.exists(path):
                    queue_image_optimization(path)
                    requeued += 1
            if requeued:
                logger.info(f'恢复了 {requeued} 个待优化任务')
        except Exception as e:
            logger.warning(f'恢复待优化任务失败: {e}')

    app.auto_regenerate_assets = auto_regenerate_assets
