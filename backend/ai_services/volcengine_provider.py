"""
Volcengine ARK API provider

Volcengine (火山引擎) provides the Doubao (豆包) series models
through an OpenAI-compatible API.
仅声明特有配置，通用逻辑见 OpenAICompatibleProvider。
"""

from .openai_compatible import OpenAICompatibleProvider


class VolcengineProvider(OpenAICompatibleProvider):
    """Volcengine ARK API provider"""

    PROVIDER_NAME = 'Volcengine'
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    DEFAULT_MODEL = 'doubao-pro-4k'
    # 火山引擎 ARK API key 为 UUID 形式，不做 sk- 前缀校验
    API_KEY_PREFIX = None
    CURRENCY = 'CNY'
    CURRENCY_SYMBOL = '¥'

    # Cost per 1K tokens in CNY (Chinese Yuan)
    # Pricing based on Volcengine official documentation
    COST_PER_1K_TOKENS = {
        'doubao-pro-32k': {'input': 0.00012, 'output': 0.00012},
        'doubao-pro-4k': {'input': 0.00004, 'output': 0.00004},
        'doubao-lite-4k': {'input': 0.00003, 'output': 0.00003},
    }

    DEFAULT_PRICING = {'input': 0.00004, 'output': 0.00004}

    def __init__(self, api_key: str, model: str = 'doubao-pro-4k'):
        super().__init__(api_key, model)
