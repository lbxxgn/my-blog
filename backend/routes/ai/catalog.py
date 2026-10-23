"""AI 提供商与模型目录管理（ai 蓝图子模块）。"""

from flask import abort, jsonify, render_template, request, session

from auth_decorators import admin_required
from logger import log_error, log_operation
from models import (
    CatalogError,
    create_model,
    create_provider,
    delete_model,
    delete_provider,
    get_catalog,
    update_model,
    update_provider,
)

from . import ai_bp


def _active_user():
    return session.get('user_id'), session.get('username')


def _json_payload():
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data


def _error_response(exc: CatalogError):
    return jsonify({'success': False, 'error': exc.message}), exc.status


def _unexpected_error(exc, action):
    log_error(exc, context=action)
    return jsonify({'success': False, 'error': f'{action}失败，请稍后重试'}), 500


@ai_bp.route('/catalog')
@admin_required
def ai_catalog():
    """供应商列表页（仅管理员）。"""
    return render_template('admin/ai_catalog.html',
                           catalog=get_catalog(include_disabled=True))


@ai_bp.route('/catalog/providers/<int:provider_id>')
@admin_required
def ai_catalog_provider(provider_id):
    """单个供应商配置页：维护该供应商下的模型。"""
    provider = next(
        (item for item in get_catalog(include_disabled=True)
         if item.get('provider_pk') == provider_id),
        None,
    )
    if not provider:
        abort(404)
    return render_template('admin/ai_catalog_provider.html', provider=provider)


@ai_bp.route('/catalog/data')
@admin_required
def ai_catalog_data():
    """返回目录数据，供管理页刷新或前端调试使用。"""
    return jsonify({'success': True, 'data': get_catalog(include_disabled=True)})


@ai_bp.route('/catalog/providers', methods=['POST'])
@admin_required
def ai_catalog_create_provider():
    try:
        provider_id = create_provider(_json_payload())
        user_id, username = _active_user()
        log_operation(user_id, username, f'新增AI供应商: {provider_id}')
        return jsonify({'success': True, 'id': provider_id})
    except CatalogError as exc:
        return _error_response(exc)
    except Exception as exc:
        return _unexpected_error(exc, '新增AI供应商')


@ai_bp.route('/catalog/providers/<int:provider_id>', methods=['PUT', 'POST'])
@admin_required
def ai_catalog_update_provider(provider_id):
    try:
        update_provider(provider_id, _json_payload())
        user_id, username = _active_user()
        log_operation(user_id, username, f'更新AI供应商: {provider_id}')
        return jsonify({'success': True})
    except CatalogError as exc:
        return _error_response(exc)
    except Exception as exc:
        return _unexpected_error(exc, '更新AI供应商')


@ai_bp.route('/catalog/providers/<int:provider_id>', methods=['DELETE'])
@admin_required
def ai_catalog_delete_provider(provider_id):
    try:
        delete_provider(provider_id)
        user_id, username = _active_user()
        log_operation(user_id, username, f'删除AI供应商: {provider_id}')
        return jsonify({'success': True})
    except CatalogError as exc:
        return _error_response(exc)
    except Exception as exc:
        return _unexpected_error(exc, '删除AI供应商')


@ai_bp.route('/catalog/models', methods=['POST'])
@admin_required
def ai_catalog_create_model():
    try:
        model_pk = create_model(_json_payload())
        user_id, username = _active_user()
        log_operation(user_id, username, f'新增AI模型: {model_pk}')
        return jsonify({'success': True, 'id': model_pk})
    except CatalogError as exc:
        return _error_response(exc)
    except Exception as exc:
        return _unexpected_error(exc, '新增AI模型')


@ai_bp.route('/catalog/models/<int:model_pk>', methods=['PUT', 'POST'])
@admin_required
def ai_catalog_update_model(model_pk):
    try:
        update_model(model_pk, _json_payload())
        user_id, username = _active_user()
        log_operation(user_id, username, f'更新AI模型: {model_pk}')
        return jsonify({'success': True})
    except CatalogError as exc:
        return _error_response(exc)
    except Exception as exc:
        return _unexpected_error(exc, '更新AI模型')


@ai_bp.route('/catalog/models/<int:model_pk>', methods=['DELETE'])
@admin_required
def ai_catalog_delete_model(model_pk):
    try:
        delete_model(model_pk)
        user_id, username = _active_user()
        log_operation(user_id, username, f'删除AI模型: {model_pk}')
        return jsonify({'success': True})
    except CatalogError as exc:
        return _error_response(exc)
    except Exception as exc:
        return _unexpected_error(exc, '删除AI模型')
