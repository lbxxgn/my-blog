"""
DeepSeek API provider

DeepSeek 当前官方模型为 deepseek-flash / deepseek-v4-pro，
通过 OpenAI 兼容 API 访问。旧名称 deepseek-v4-flash、
deepseek-v4-flash-vision-exp 仍可调用，但已由 deepseek-flash 接管。
仅声明特有配置，通用逻辑见 OpenAICompatibleProvider。
"""

from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API provider"""

    PROVIDER_NAME = 'DeepSeek'
    BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = 'deepseek-flash'
    CURRENCY = 'CNY'
    CURRENCY_SYMBOL = '¥'

    # Cost per 1K tokens in CNY（高峰时段、缓存未命中价格）
    # Pricing based on DeepSeek official documentation
    COST_PER_1K_TOKENS = {
        # 高峰时段、缓存未命中价格（官方 2026-10 文档）
        'deepseek-flash': {'input': 0.002, 'output': 0.008},
        'deepseek-v4-pro': {'input': 0.009, 'output': 0.027},
    }

    # 旧模型名仍被官方接受，但由 Flash 模型提供服务
    EXTRA_VALID_MODELS = ['deepseek-v4-flash', 'deepseek-v4-flash-vision-exp']

    DEFAULT_PRICING = {'input': 0.002, 'output': 0.008}

    # Model descriptions for UI display
    MODEL_DESCRIPTIONS = {
        'deepseek-flash': 'DeepSeek V4.1 Flash - 速度与成本优先，1M 上下文',
        'deepseek-v4-pro': 'DeepSeek V4 Pro - 复杂推理与 Agent 任务',
    }

    def __init__(self, api_key: str, model: str = None, **kwargs):
        super().__init__(api_key, model or self.DEFAULT_MODEL, **kwargs)
