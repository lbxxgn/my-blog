"""
自定义 OpenAI 兼容 API provider

用于接入任意提供 OpenAI 兼容 chat completions 接口的服务，
由用户在设置中填写 Base URL、API 密钥与模型 ID。
仅声明特有配置，通用逻辑见 OpenAICompatibleProvider。
"""

from .openai_compatible import OpenAICompatibleProvider


class CustomOpenAIProvider(OpenAICompatibleProvider):
    """自定义 OpenAI 兼容 API provider（用户自备 Base URL）"""

    PROVIDER_NAME = 'Custom OpenAI-compatible'
    BASE_URL = None                    # 由构造参数传入
    DEFAULT_MODEL = None               # 必须由用户指定模型
    API_KEY_PREFIX = None              # 自定义服务密钥格式未知，不做前缀检查
    CURRENCY = 'USD'
    CURRENCY_SYMBOL = '$'

    # 自定义服务定价未知，成本按 0 估算
    COST_PER_1K_TOKENS = {}
    DEFAULT_PRICING = {'input': 0.0, 'output': 0.0}

    def __init__(self, api_key: str, model: str = None, base_url: str = None):
        if not base_url:
            raise ValueError("自定义提供商需要填写 Base URL")
        if not model:
            raise ValueError("自定义提供商需要填写模型 ID")
        self.BASE_URL = base_url.rstrip('/')
        super().__init__(api_key, model)
