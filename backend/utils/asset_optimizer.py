#!/usr/bin/env python3
import os
import json
import time
from flask import url_for, current_app

class AssetOptimizer:
    """
    静态资源优化器
    提供资源压缩、合并和版本管理功能
    """
    def __init__(self, app=None):
        self.app = app
        self.build_version = str(int(time.time()))
        self.use_minified = True

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.jinja_env.globals['static_file'] = self.static_file
        app.jinja_env.globals['asset_version'] = self.build_version

        # 配置默认值
        self.use_minified = app.config.get('USE_MINIFIED_ASSETS', True)
        self.build_version = app.config.get('ASSET_BUILD_VERSION', self.build_version)

    def static_file(self, path):
        """
        生成优化后的静态资源URL
        :param path: 资源路径，如 'css/style.css'
        :return: 优化后的URL
        """
        if not self.use_minified:
            return f"{url_for('static', filename=path)}?v={self.build_version}"

        # 处理CSS文件
        if path.endswith('.css'):
            # 主样式表使用合并包
            if path == 'css/style.css':
                return f"{url_for('static', filename='css/bundle.css')}?v={self.build_version}"
            # 移动端样式单独加载
            elif path == 'css/mobile-weibo.css':
                return f"{url_for('static', filename='css/mobile-weibo.css')}?v={self.build_version}"
            # PC端信息流样式单独加载
            elif path == 'css/pc-feed.css':
                return f"{url_for('static', filename='css/pc-feed.css')}?v={self.build_version}"

        # 处理JavaScript文件
        elif path.endswith('.js'):
            # 主脚本使用合并包
            if path == 'js/main.js':
                return f"{url_for('static', filename='js/bundle.js')}?v={self.build_version}"

        # 对于其他文件，使用单独的压缩版本
        if self.use_minified:
            base, ext = os.path.splitext(path)
            minified_path = f"{base}.min{ext}"

            # 检查压缩文件是否存在
            full_path = os.path.join(current_app.static_folder, minified_path)
            if os.path.exists(full_path):
                return f"{url_for('static', filename=minified_path)}?v={self.build_version}"

        # 回退到原始文件
        return f"{url_for('static', filename=path)}?v={self.build_version}"

    def get_build_info(self):
        """获取构建信息"""
        return {
            'build_version': self.build_version,
            'use_minified': self.use_minified,
            'use_bundled': True
        }

# 全局实例
asset_optimizer = AssetOptimizer()
