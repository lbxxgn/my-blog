"""Jinja2模板助手函数"""
from flask import url_for
from typing import Optional, Dict

def static_file(filename: str) -> str:
    """
    返回带版本号的静态文件URL

    使用方式:
    <link rel="stylesheet" href="{{ static_file('css/style.css') }}">
    """
    from flask import current_app

    if not hasattr(current_app, 'asset_manager'):
        return url_for('static', filename=filename)

    asset_manager = current_app.asset_manager
    # 获取文件hash作为版本号（查询参数）
    if filename in asset_manager.manifest:
        file_hash = asset_manager.manifest[filename]['hash']
        return url_for('static', filename=filename) + f'?v={file_hash}'

    return url_for('static', filename=filename)

def static_file_with_integrity(filename: str) -> Dict[str, Optional[str]]:
    """
    返回带版本号和SRI的静态文件信息

    使用方式:
    {% set asset = static_file_with_integrity('js/editor.js') %}
    <script src="{{ asset.url }}" integrity="{{ asset.integrity }}"></script>
    """
    from flask import current_app

    if not hasattr(current_app, 'asset_manager'):
        return {'url': url_for('static', filename=filename), 'integrity': None}

    asset_manager = current_app.asset_manager
    integrity = asset_manager.get_integrity(filename)

    # 获取文件hash作为版本号（查询参数）
    url = url_for('static', filename=filename)
    if filename in asset_manager.manifest:
        file_hash = asset_manager.manifest[filename]['hash']
        url += f'?v={file_hash}'

    return {
        'url': url,
        'integrity': integrity
    }

def register_template_helpers(app):
    """注册模板助手函数到Flask应用"""
    app.jinja_env.globals.update(
        static_file=static_file,
        static_file_with_integrity=static_file_with_integrity
    )
