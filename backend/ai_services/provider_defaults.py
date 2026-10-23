"""
内置 AI 提供商与模型目录默认值

从现有 Provider 类推导出默认目录，供数据库迁移、首次种子与
目录表不可用时的运行回退使用。价格、默认模型、币种均以
Provider 类为唯一来源，避免多处维护。
"""

from typing import Any, Dict, List

from .custom_provider import CustomOpenAIProvider
from .dashscope_provider import DashscopeProvider
from .deepseek_provider import DeepSeekProvider

CURRENCY_SYMBOLS = {
    'CNY': '¥',
    'USD': '$',
}


def currency_symbol(currency: str) -> str:
    """返回币种符号；未知币种直接回退为币种代码。"""
    return CURRENCY_SYMBOLS.get((currency or '').upper(), currency or '$')


def _build_models(provider_class) -> List[Dict[str, Any]]:
    """从 Provider 类的定价表推导模型列表。"""
    pricing = getattr(provider_class, 'COST_PER_1K_TOKENS', {}) or {}
    descriptions = getattr(provider_class, 'MODEL_DESCRIPTIONS', {}) or {}
    default_model = getattr(provider_class, 'DEFAULT_MODEL', None)

    models: List[Dict[str, Any]] = []
    for index, (model_id, prices) in enumerate(pricing.items()):
        models.append({
            'model_id': model_id,
            'display_name': model_id,
            'description': descriptions.get(model_id, ''),
            'input_price': (prices or {}).get('input'),
            'output_price': (prices or {}).get('output'),
            'enabled': True,
            'is_default': model_id == default_model,
            'sort_order': (index + 1) * 10,
        })

    # 默认模型不在定价表中时也纳入目录，价格留空表示沿用驱动默认价
    if default_model and default_model not in pricing:
        models.insert(0, {
            'model_id': default_model,
            'display_name': default_model,
            'description': descriptions.get(default_model, ''),
            'input_price': None,
            'output_price': None,
            'enabled': True,
            'is_default': True,
            'sort_order': 0,
        })

    return models


def build_default_catalog() -> List[Dict[str, Any]]:
    """返回内置供应商目录（含模型与价格）。"""
    return [
        {
            'slug': 'dashscope',
            'name': '阿里百炼',
            'description': '通义千问系列',
            'driver': 'dashscope',
            'base_url': DashscopeProvider.BASE_URL,
            'currency': DashscopeProvider.CURRENCY,
            'allow_custom_model': False,
            'requires_base_url': False,
            'enabled': True,
            'is_builtin': True,
            'sort_order': 10,
            'models': _build_models(DashscopeProvider),
        },
        {
            'slug': 'deepseek',
            'name': 'DeepSeek',
            'description': 'deepseek-v4-flash / deepseek-v4-pro',
            'driver': 'deepseek',
            'base_url': DeepSeekProvider.BASE_URL,
            'currency': DeepSeekProvider.CURRENCY,
            'allow_custom_model': False,
            'requires_base_url': False,
            'enabled': True,
            'is_builtin': True,
            'sort_order': 20,
            'models': _build_models(DeepSeekProvider),
        },
        {
            'slug': 'custom',
            'name': '自定义 (OpenAI 兼容)',
            'description': '任意 OpenAI 兼容接口，需填写 Base URL 与模型 ID',
            'driver': 'openai_compatible',
            'base_url': None,
            'currency': CustomOpenAIProvider.CURRENCY,
            'allow_custom_model': True,
            'requires_base_url': True,
            'enabled': True,
            'is_builtin': True,
            'sort_order': 30,
            'models': [],
        },
    ]


DEFAULT_CATALOG = build_default_catalog()
