"""
OpenAI provider implementation

仅声明 OpenAI 特有的模型/定价配置，
通用逻辑见 OpenAICompatibleProvider。
"""

from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI API provider"""

    PROVIDER_NAME = 'OpenAI'
    BASE_URL = None
    DEFAULT_MODEL = 'gpt-3.5-turbo'
    CURRENCY = 'USD'
    CURRENCY_SYMBOL = '$'

    # Cost per 1K tokens (as of 2024)
    COST_PER_1K_TOKENS = {
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        'gpt-4o': {'input': 0.005, 'output': 0.015},
    }

    DEFAULT_PRICING = {'input': 0.001, 'output': 0.002}

    EXTRA_VALID_MODELS = [
        'gpt-3.5-turbo-0125',
        'gpt-3.5-turbo-1106',
        'gpt-4o-2024-05-13',
        'gpt-4-turbo-2024-04-09',
    ]

    def __init__(self, api_key: str, model: str = 'gpt-3.5-turbo'):
        super().__init__(api_key, model)
