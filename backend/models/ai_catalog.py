"""
AI 提供商与模型目录

目录为站点级全局配置：
- ai_providers 保存供应商（slug 供 users.ai_provider 引用）
- ai_models 保存每个供应商下的模型、定价与默认项

设计约定：
- slug / model_id 创建后不可修改，避免用户配置失联
- 被用户引用的供应商/模型禁止删除，只能停用
- 价格字段为每 1K tokens；NULL 表示沿用 Provider 类默认价，0 表示免费
"""

import math
import re
import sqlite3
from typing import Any, Dict, List, Optional

from .db import get_db_connection, get_db_context
from ai_services.provider_defaults import (
    DEFAULT_CATALOG,
    currency_symbol,
)
from ai_services.url_guard import UnsafeBaseUrlError, validate_ai_base_url

__all__ = [
    'CatalogError',
    'ensure_ai_catalog_tables',
    'get_catalog',
    'get_provider',
    'get_model',
    'resolve_provider',
    'resolve_model',
    'resolve_model_selection',
    'create_provider',
    'update_provider',
    'delete_provider',
    'create_model',
    'update_model',
    'delete_model',
]

SLUG_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]{1,31}$')
MODEL_ID_PATTERN = re.compile(r'^[A-Za-z0-9._:/@+\-]{1,128}$')
CURRENCY_PATTERN = re.compile(r'^[A-Z]{3}$')

ALLOWED_DRIVERS = {'dashscope', 'deepseek', 'openai_compatible'}
CREATABLE_DRIVERS = {'openai_compatible'}
_BUILTIN_CURRENCIES = {'CNY', 'USD'}

_ensured_databases = set()


class CatalogError(ValueError):
    """目录操作失败，携带 HTTP 状态码供路由层使用。"""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def _current_db_path() -> str:
    import backend.config as config

    return config.DATABASE_URL.replace('sqlite:///', '')


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _as_int(value, default: int = 0) -> int:
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise CatalogError('排序值必须是整数')


def _clean_text(value, field: str, max_length: int, required: bool = False) -> str:
    text = '' if value is None else str(value).strip()
    if required and not text:
        raise CatalogError(f'{field}不能为空')
    if len(text) > max_length:
        raise CatalogError(f'{field}长度不能超过 {max_length} 个字符')
    return text


def _normalize_slug(value) -> str:
    slug = _clean_text(value, '供应商标识', 32, required=True).lower()
    if not SLUG_PATTERN.match(slug):
        raise CatalogError('供应商标识只能包含小写字母、数字、- 和 _，长度 2-32，且必须以字母或数字开头')
    return slug


def _normalize_model_id(value) -> str:
    model_id = _clean_text(value, '模型 ID', 128, required=True)
    if not MODEL_ID_PATTERN.match(model_id):
        raise CatalogError('模型 ID 只能包含字母、数字、. - _ / : @ +，长度不超过 128')
    return model_id


def _normalize_currency(value) -> str:
    currency = _clean_text(value, '币种', 3, required=True).upper()
    if not CURRENCY_PATTERN.match(currency):
        raise CatalogError('币种必须是 3 位大写字母，例如 CNY、USD')
    return currency


def _normalize_price(value, field: str) -> Optional[float]:
    if value is None or value == '':
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        raise CatalogError(f'{field}必须是数字')
    if math.isnan(price) or math.isinf(price) or price < 0:
        raise CatalogError(f'{field}必须是非负数字')
    return round(price, 8)


def _validate_base_url(value, required: bool):
    url = '' if value is None else str(value).strip()
    if not url:
        if required:
            raise CatalogError('该供应商需要填写 Base URL')
        return None
    try:
        validate_ai_base_url(url)
    except UnsafeBaseUrlError as exc:
        raise CatalogError(str(exc))
    return url.rstrip('/')


def ensure_ai_catalog_tables(seed: bool = True) -> None:
    """幂等创建目录表；首次创建时写入内置供应商与模型。"""
    db_path = _current_db_path()
    if db_path in _ensured_databases:
        return

    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ai_providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                driver TEXT NOT NULL,
                base_url TEXT,
                currency TEXT NOT NULL DEFAULT 'CNY',
                allow_custom_model BOOLEAN DEFAULT 0,
                requires_base_url BOOLEAN DEFAULT 0,
                enabled BOOLEAN DEFAULT 1,
                is_builtin BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ai_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                display_name TEXT,
                description TEXT,
                input_price REAL,
                output_price REAL,
                enabled BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider_id, model_id),
                FOREIGN KEY(provider_id) REFERENCES ai_providers(id) ON DELETE CASCADE
            )
        ''')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_ai_models_provider '
            'ON ai_models(provider_id, sort_order, id)'
        )
        conn.commit()

        if seed:
            count = conn.execute('SELECT COUNT(*) FROM ai_providers').fetchone()[0]
            if count == 0:
                _seed_default_catalog(conn)
                conn.commit()

        _ensured_databases.add(db_path)
    finally:
        conn.close()


def _seed_default_catalog(conn) -> None:
    """写入内置目录；使用 INSERT OR IGNORE 保证幂等。"""
    for provider in DEFAULT_CATALOG:
        conn.execute('''
            INSERT OR IGNORE INTO ai_providers
                (slug, name, description, driver, base_url, currency,
                 allow_custom_model, requires_base_url, enabled, is_builtin, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            provider['slug'],
            provider['name'],
            provider.get('description') or '',
            provider['driver'],
            provider.get('base_url'),
            provider.get('currency') or 'CNY',
            1 if provider.get('allow_custom_model') else 0,
            1 if provider.get('requires_base_url') else 0,
            1 if provider.get('enabled', True) else 0,
            1 if provider.get('is_builtin') else 0,
            provider.get('sort_order') or 0,
        ))
        row = conn.execute(
            'SELECT id FROM ai_providers WHERE slug = ?', (provider['slug'],)
        ).fetchone()
        if not row:
            continue
        provider_pk = row['id']
        for model in provider.get('models') or []:
            conn.execute('''
                INSERT OR IGNORE INTO ai_models
                    (provider_id, model_id, display_name, description,
                     input_price, output_price, enabled, is_default, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                provider_pk,
                model['model_id'],
                model.get('display_name') or model['model_id'],
                model.get('description') or '',
                model.get('input_price'),
                model.get('output_price'),
                1 if model.get('enabled', True) else 0,
                1 if model.get('is_default') else 0,
                model.get('sort_order') or 0,
            ))


def _row_to_model(row) -> Dict[str, Any]:
    return {
        'id': row['id'],
        'provider_id': row['provider_id'],
        'model_id': row['model_id'],
        'display_name': row['display_name'] or row['model_id'],
        'description': row['description'] or '',
        'input_price': row['input_price'],
        'output_price': row['output_price'],
        'enabled': bool(row['enabled']),
        'is_default': bool(row['is_default']),
        'sort_order': row['sort_order'] or 0,
    }


def _row_to_provider(row) -> Dict[str, Any]:
    return {
        'id': row['slug'],
        'provider_pk': row['id'],
        'slug': row['slug'],
        'name': row['name'],
        'description': row['description'] or '',
        'driver': row['driver'],
        'base_url': row['base_url'],
        'currency': row['currency'] or 'CNY',
        'currency_symbol': currency_symbol(row['currency'] or 'CNY'),
        'allow_custom_model': bool(row['allow_custom_model']),
        'requires_base_url': bool(row['requires_base_url']),
        'enabled': bool(row['enabled']),
        'is_builtin': bool(row['is_builtin']),
        'sort_order': row['sort_order'] or 0,
    }


def _resolve_default_model(models: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    enabled = [m for m in models if m['enabled']]
    for model in enabled:
        if model['is_default']:
            return model
    if enabled:
        return enabled[0]
    for model in models:
        if model['is_default']:
            return model
    return models[0] if models else None


def _usage_counts(conn):
    provider_usage: Dict[str, int] = {}
    model_usage: Dict[tuple, int] = {}
    try:
        rows = conn.execute(
            'SELECT ai_provider, COUNT(*) AS cnt FROM users '
            'WHERE ai_provider IS NOT NULL AND ai_provider != "" '
            'GROUP BY ai_provider'
        ).fetchall()
        provider_usage = {row['ai_provider']: row['cnt'] for row in rows}
    except sqlite3.OperationalError:
        pass
    try:
        rows = conn.execute(
            'SELECT ai_provider, ai_model, COUNT(*) AS cnt FROM users '
            'WHERE ai_provider IS NOT NULL AND ai_provider != "" '
            'AND ai_model IS NOT NULL AND ai_model != "" '
            'GROUP BY ai_provider, ai_model'
        ).fetchall()
        model_usage = {(row['ai_provider'], row['ai_model']): row['cnt'] for row in rows}
    except sqlite3.OperationalError:
        pass
    return provider_usage, model_usage


def _catalog_from_defaults() -> List[Dict[str, Any]]:
    """数据库不可用时的回退目录。"""
    catalog = []
    for provider in DEFAULT_CATALOG:
        models = []
        for index, model in enumerate(provider.get('models') or []):
            models.append({
                'id': None,
                'provider_id': None,
                'model_id': model['model_id'],
                'display_name': model.get('display_name') or model['model_id'],
                'description': model.get('description') or '',
                'input_price': model.get('input_price'),
                'output_price': model.get('output_price'),
                'enabled': bool(model.get('enabled', True)),
                'is_default': bool(model.get('is_default')),
                'sort_order': model.get('sort_order') or index,
            })
        default_model = _resolve_default_model(models)
        catalog.append({
            **{k: v for k, v in provider.items() if k != 'models'},
            'id': provider['slug'],
            'provider_pk': None,
            'currency_symbol': currency_symbol(provider.get('currency') or 'CNY'),
            'usage_count': 0,
            'default_model': default_model['model_id'] if default_model else '',
            'models': [m['model_id'] for m in models if m['enabled']],
            'model_details': [
                {**m, 'provider_slug': provider['slug'],
                 'provider_name': provider['name'], 'usage_count': 0,
                 'currency': provider.get('currency') or 'CNY',
                 'currency_symbol': currency_symbol(provider.get('currency') or 'CNY')}
                for m in models
            ],
        })
    return catalog


def get_catalog(include_disabled: bool = True) -> List[Dict[str, Any]]:
    """返回完整目录（供应商 + 模型 + 引用统计）。"""
    ensure_ai_catalog_tables()
    conn = get_db_connection()
    try:
        provider_rows = conn.execute(
            'SELECT * FROM ai_providers ORDER BY sort_order, id'
        ).fetchall()
        model_rows = conn.execute(
            'SELECT * FROM ai_models ORDER BY provider_id, sort_order, id'
        ).fetchall()
        provider_usage, model_usage = _usage_counts(conn)
    except sqlite3.DatabaseError:
        return _catalog_from_defaults()
    finally:
        conn.close()

    models_by_provider: Dict[int, List[Dict[str, Any]]] = {}
    for row in model_rows:
        models_by_provider.setdefault(row['provider_id'], []).append(_row_to_model(row))

    catalog = []
    for row in provider_rows:
        provider = _row_to_provider(row)
        if not include_disabled and not provider['enabled']:
            continue
        models = models_by_provider.get(provider['provider_pk'], [])
        default_model = _resolve_default_model(models)
        provider['usage_count'] = provider_usage.get(provider['slug'], 0)
        provider['default_model'] = default_model['model_id'] if default_model else ''
        provider['models'] = [m['model_id'] for m in models if m['enabled']]
        provider['model_details'] = [
            {
                **m,
                'provider_slug': provider['slug'],
                'provider_name': provider['name'],
                'usage_count': model_usage.get((provider['slug'], m['model_id']), 0),
            }
            for m in models
        ]
        for model in provider['model_details']:
            model['currency'] = provider['currency']
            model['currency_symbol'] = provider['currency_symbol']
        catalog.append(provider)
    return catalog


def _load_provider(slug: str) -> Optional[Dict[str, Any]]:
    """按 slug 加载单个供应商（不统计引用数，适合高频运行时调用）。"""
    ensure_ai_catalog_tables()
    conn = get_db_connection()
    try:
        row = conn.execute(
            'SELECT * FROM ai_providers WHERE slug = ?', (slug,)
        ).fetchone()
        if not row:
            return None
        model_rows = conn.execute(
            'SELECT * FROM ai_models WHERE provider_id = ? '
            'ORDER BY sort_order, id',
            (row['id'],)
        ).fetchall()
    except sqlite3.DatabaseError:
        return None
    finally:
        conn.close()

    provider = _row_to_provider(row)
    models = [_row_to_model(model_row) for model_row in model_rows]
    default_model = _resolve_default_model(models)
    provider['usage_count'] = 0
    provider['default_model'] = default_model['model_id'] if default_model else ''
    provider['models'] = [m['model_id'] for m in models if m['enabled']]
    provider['model_details'] = [
        {
            **model,
            'provider_slug': provider['slug'],
            'provider_name': provider['name'],
            'usage_count': 0,
            'currency': provider['currency'],
            'currency_symbol': provider['currency_symbol'],
        }
        for model in models
    ]
    return provider


def get_provider(slug: str) -> Optional[Dict[str, Any]]:
    return _load_provider((slug or '').lower())


def get_model(provider_slug: str, model_id: str) -> Optional[Dict[str, Any]]:
    provider = get_provider(provider_slug)
    if not provider:
        return None
    for model in provider['model_details']:
        if model['model_id'] == model_id:
            return model
    return None


def resolve_provider(slug: str) -> Optional[Dict[str, Any]]:
    """运行时解析供应商（含默认模型与价格）。"""
    return get_provider((slug or '').lower())


def resolve_model(provider_slug: str, model_id: str) -> Optional[Dict[str, Any]]:
    """运行时解析模型，不限制启用状态，兼容存量用户。"""
    if not model_id:
        return None
    return get_model(provider_slug, model_id)


def resolve_model_selection(provider_slug: str, model_id: str):
    """
    保存配置时校验供应商与模型。

    Returns:
        (provider, model_id, error)
    """
    provider = get_provider(provider_slug)
    if not provider:
        return None, model_id, f'不支持的AI提供商: {provider_slug}'

    candidate = (model_id or '').strip()
    if not candidate:
        candidate = provider['default_model']
    if not candidate:
        if provider['allow_custom_model']:
            return provider, candidate, '请填写模型 ID'
        return provider, candidate, '该供应商暂无可用模型，请先在模型管理中配置'

    if provider['allow_custom_model']:
        return provider, candidate, None

    for model in provider['model_details']:
        if model['model_id'] == candidate and model['enabled']:
            return provider, candidate, None
    return provider, candidate, f'模型 {candidate} 未启用或不存在，请重新选择'


def _provider_row(conn, provider_id: int):
    return conn.execute(
        'SELECT * FROM ai_providers WHERE id = ?', (provider_id,)
    ).fetchone()


def _model_row(conn, model_pk: int):
    return conn.execute('''
        SELECT m.*, p.slug AS provider_slug, p.enabled AS provider_enabled,
               p.allow_custom_model AS provider_allow_custom_model
        FROM ai_models m
        JOIN ai_providers p ON p.id = m.provider_id
        WHERE m.id = ?
    ''', (model_pk,)).fetchone()


def _provider_usage(conn, slug: str) -> int:
    try:
        row = conn.execute(
            'SELECT COUNT(*) FROM users WHERE ai_provider = ?', (slug,)
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _model_usage(conn, slug: str, model_id: str) -> int:
    try:
        row = conn.execute(
            'SELECT COUNT(*) FROM users WHERE ai_provider = ? AND ai_model = ?',
            (slug, model_id)
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _enabled_model_count(conn, provider_id: int, exclude_pk: int = None) -> int:
    if exclude_pk is None:
        row = conn.execute(
            'SELECT COUNT(*) FROM ai_models WHERE provider_id = ? AND enabled = 1',
            (provider_id,)
        ).fetchone()
    else:
        row = conn.execute(
            'SELECT COUNT(*) FROM ai_models '
            'WHERE provider_id = ? AND enabled = 1 AND id != ?',
            (provider_id, exclude_pk)
        ).fetchone()
    return row[0] if row else 0


def _promote_default_model(conn, provider_id: int, exclude_pk: int = None) -> None:
    """把默认标记交给下一个启用模型；没有候选时清空。"""
    sql = (
        'SELECT id FROM ai_models WHERE provider_id = ? AND enabled = 1 '
    )
    params: List[Any] = [provider_id]
    if exclude_pk is not None:
        sql += 'AND id != ? '
        params.append(exclude_pk)
    sql += 'ORDER BY is_default DESC, sort_order, id LIMIT 1'
    row = conn.execute(sql, params).fetchone()
    conn.execute('UPDATE ai_models SET is_default = 0 WHERE provider_id = ?', (provider_id,))
    if row:
        conn.execute(
            'UPDATE ai_models SET is_default = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (row['id'],)
        )


def create_provider(data: Dict[str, Any]) -> int:
    ensure_ai_catalog_tables()
    slug = _normalize_slug(data.get('slug'))
    name = _clean_text(data.get('name'), '供应商名称', 100, required=True)
    description = _clean_text(data.get('description'), '供应商描述', 500)
    driver = _clean_text(data.get('driver') or 'openai_compatible', '驱动', 32).lower()
    if driver not in ALLOWED_DRIVERS or driver not in CREATABLE_DRIVERS:
        raise CatalogError('新增供应商仅支持 OpenAI 兼容驱动')
    currency = _normalize_currency(data.get('currency') or 'CNY')
    allow_custom_model = _as_bool(data.get('allow_custom_model'))
    requires_base_url = _as_bool(data.get('requires_base_url'))
    enabled = _as_bool(data.get('enabled'), True)
    sort_order = _as_int(data.get('sort_order'), 0)

    base_url = _validate_base_url(
        data.get('base_url'),
        required=not requires_base_url,
    )

    with get_db_context() as conn:
        try:
            cursor = conn.execute('''
                INSERT INTO ai_providers
                    (slug, name, description, driver, base_url, currency,
                     allow_custom_model, requires_base_url, enabled, is_builtin, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            ''', (
                slug, name, description, driver, base_url, currency,
                1 if allow_custom_model else 0,
                1 if requires_base_url else 0,
                1 if enabled else 0,
                sort_order,
            ))
        except sqlite3.IntegrityError:
            raise CatalogError(f'供应商标识 {slug} 已存在', 409)
        return cursor.lastrowid


def update_provider(provider_id: int, data: Dict[str, Any]) -> None:
    ensure_ai_catalog_tables()
    with get_db_context() as conn:
        row = _provider_row(conn, provider_id)
        if not row:
            raise CatalogError('供应商不存在', 404)

        driver = row['driver']
        updates = []
        params: List[Any] = []

        if 'name' in data:
            updates.append('name = ?')
            params.append(_clean_text(data.get('name'), '供应商名称', 100, required=True))
        if 'description' in data:
            updates.append('description = ?')
            params.append(_clean_text(data.get('description'), '供应商描述', 500))
        if 'currency' in data:
            updates.append('currency = ?')
            params.append(_normalize_currency(data.get('currency')))
        if 'allow_custom_model' in data:
            updates.append('allow_custom_model = ?')
            params.append(1 if _as_bool(data.get('allow_custom_model')) else 0)
        if 'requires_base_url' in data:
            updates.append('requires_base_url = ?')
            params.append(1 if _as_bool(data.get('requires_base_url')) else 0)
        if 'enabled' in data:
            updates.append('enabled = ?')
            params.append(1 if _as_bool(data.get('enabled')) else 0)
        if 'sort_order' in data:
            updates.append('sort_order = ?')
            params.append(_as_int(data.get('sort_order'), 0))

        final_requires_base_url = (
            _as_bool(data.get('requires_base_url'))
            if 'requires_base_url' in data else bool(row['requires_base_url'])
        )

        if 'base_url' in data or 'requires_base_url' in data:
            base_url = _validate_base_url(
                data.get('base_url', row['base_url']),
                required=(
                    driver == 'openai_compatible'
                    and not final_requires_base_url
                ),
            )
            updates.append('base_url = ?')
            params.append(base_url)

        if not updates:
            raise CatalogError('没有需要更新的字段')

        params.append(provider_id)
        conn.execute(
            f"UPDATE ai_providers SET {', '.join(updates)}, "
            'updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            params
        )


def delete_provider(provider_id: int) -> None:
    ensure_ai_catalog_tables()
    with get_db_context() as conn:
        row = _provider_row(conn, provider_id)
        if not row:
            raise CatalogError('供应商不存在', 404)
        if row['is_builtin']:
            raise CatalogError('内置供应商不可删除，请改为停用')

        usage = _provider_usage(conn, row['slug'])
        if usage > 0:
            raise CatalogError(
                f'该供应商仍被 {usage} 个用户使用，无法删除；请先停用或让用户更换供应商',
                409,
            )

        model_ids = [
            model_row['model_id'] for model_row in conn.execute(
                'SELECT model_id FROM ai_models WHERE provider_id = ?',
                (provider_id,)
            ).fetchall()
        ]
        if model_ids:
            placeholders = ','.join('?' * len(model_ids))
            try:
                model_refs = conn.execute(
                    f'SELECT COUNT(*) FROM users WHERE ai_model IN ({placeholders})',
                    model_ids
                ).fetchone()[0]
            except sqlite3.OperationalError:
                model_refs = 0
            if model_refs > 0:
                raise CatalogError(
                    f'该供应商的模型仍被 {model_refs} 个用户配置引用，无法删除；请改为停用',
                    409,
                )

        conn.execute('DELETE FROM ai_models WHERE provider_id = ?', (provider_id,))
        conn.execute('DELETE FROM ai_providers WHERE id = ?', (provider_id,))


def create_model(data: Dict[str, Any]) -> int:
    ensure_ai_catalog_tables()
    try:
        provider_id = int(data.get('provider_id'))
    except (TypeError, ValueError):
        raise CatalogError('请选择所属供应商')

    model_id = _normalize_model_id(data.get('model_id'))
    display_name = _clean_text(
        data.get('display_name') or model_id, '模型显示名', 100, required=True)
    description = _clean_text(data.get('description'), '模型描述', 500)
    input_price = _normalize_price(data.get('input_price'), '输入价格')
    output_price = _normalize_price(data.get('output_price'), '输出价格')
    enabled = _as_bool(data.get('enabled'), True)
    is_default = _as_bool(data.get('is_default'))
    sort_order = _as_int(data.get('sort_order'), 0)

    if is_default and not enabled:
        raise CatalogError('默认模型必须处于启用状态')

    with get_db_context() as conn:
        provider = _provider_row(conn, provider_id)
        if not provider:
            raise CatalogError('所属供应商不存在', 404)

        if enabled and not is_default:
            has_default = conn.execute(
                'SELECT 1 FROM ai_models WHERE provider_id = ? AND is_default = 1 AND enabled = 1',
                (provider_id,)
            ).fetchone()
            if not has_default:
                is_default = True

        if is_default:
            conn.execute(
                'UPDATE ai_models SET is_default = 0 WHERE provider_id = ?',
                (provider_id,)
            )

        try:
            cursor = conn.execute('''
                INSERT INTO ai_models
                    (provider_id, model_id, display_name, description,
                     input_price, output_price, enabled, is_default, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                provider_id, model_id, display_name, description,
                input_price, output_price,
                1 if enabled else 0,
                1 if is_default else 0,
                sort_order,
            ))
        except sqlite3.IntegrityError:
            raise CatalogError(f'模型 {model_id} 已存在于该供应商', 409)
        return cursor.lastrowid


def update_model(model_pk: int, data: Dict[str, Any]) -> None:
    ensure_ai_catalog_tables()
    with get_db_context() as conn:
        row = _model_row(conn, model_pk)
        if not row:
            raise CatalogError('模型不存在', 404)

        current_enabled = bool(row['enabled'])
        current_default = bool(row['is_default'])
        desired_enabled = (
            _as_bool(data.get('enabled')) if 'enabled' in data else current_enabled
        )
        explicit_default = 'is_default' in data
        desired_default = (
            _as_bool(data.get('is_default')) if explicit_default else current_default
        )

        if explicit_default and desired_default and not desired_enabled:
            raise CatalogError('默认模型必须处于启用状态')

        # 停用默认模型时自动移除默认标记，随后由其他启用模型接管
        if not explicit_default and current_default and not desired_enabled:
            desired_default = False

        if current_enabled and not desired_enabled:
            if row['provider_enabled'] and not row['provider_allow_custom_model']:
                if _enabled_model_count(conn, row['provider_id'], exclude_pk=model_pk) == 0:
                    raise CatalogError('该供应商至少需要保留一个启用模型')

        updates = []
        params: List[Any] = []

        if 'display_name' in data:
            display_name = _clean_text(data.get('display_name'), '模型显示名', 100)
            updates.append('display_name = ?')
            params.append(display_name or row['model_id'])
        if 'description' in data:
            updates.append('description = ?')
            params.append(_clean_text(data.get('description'), '模型描述', 500))
        if 'input_price' in data:
            updates.append('input_price = ?')
            params.append(_normalize_price(data.get('input_price'), '输入价格'))
        if 'output_price' in data:
            updates.append('output_price = ?')
            params.append(_normalize_price(data.get('output_price'), '输出价格'))
        if 'enabled' in data:
            updates.append('enabled = ?')
            params.append(1 if desired_enabled else 0)
        if 'sort_order' in data:
            updates.append('sort_order = ?')
            params.append(_as_int(data.get('sort_order'), 0))

        updates.append('is_default = ?')
        params.append(1 if desired_default else 0)

        if not updates:
            raise CatalogError('没有需要更新的字段')

        params.append(model_pk)
        conn.execute(
            f"UPDATE ai_models SET {', '.join(updates)}, "
            'updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            params
        )

        if desired_default:
            conn.execute(
                'UPDATE ai_models SET is_default = 0 WHERE provider_id = ? AND id != ?',
                (row['provider_id'], model_pk)
            )
        else:
            has_default = conn.execute(
                'SELECT 1 FROM ai_models WHERE provider_id = ? '
                'AND is_default = 1 AND enabled = 1',
                (row['provider_id'],)
            ).fetchone()
            if not has_default:
                _promote_default_model(conn, row['provider_id'])


def delete_model(model_pk: int) -> None:
    ensure_ai_catalog_tables()
    with get_db_context() as conn:
        row = _model_row(conn, model_pk)
        if not row:
            raise CatalogError('模型不存在', 404)

        usage = _model_usage(conn, row['provider_slug'], row['model_id'])
        if usage > 0:
            raise CatalogError(
                f'该模型仍被 {usage} 个用户使用，无法删除；请改为停用',
                409,
            )

        if row['enabled'] and row['provider_enabled'] and not row['provider_allow_custom_model']:
            if _enabled_model_count(conn, row['provider_id'], exclude_pk=model_pk) == 0:
                raise CatalogError('该供应商至少需要保留一个启用模型，无法删除')

        conn.execute('DELETE FROM ai_models WHERE id = ?', (model_pk,))

        if row['is_default']:
            _promote_default_model(conn, row['provider_id'])
