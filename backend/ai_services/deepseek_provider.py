"""
DeepSeek API provider

DeepSeek 提供 deepseek-v4-flash / deepseek-v4-pro 等模型，
通过 OpenAI 兼容 API 访问（旧别名 deepseek-chat/deepseek-reasoner 已于 2026-07-24 停用）。
仅声明特有配置，通用逻辑见 OpenAICompatibleProvider。
"""

from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API provider"""

    PROVIDER_NAME = 'DeepSeek'
    BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = 'deepseek-v4-flash'
    CURRENCY = 'CNY'
    CURRENCY_SYMBOL = '¥'

    # Cost per 1K tokens in CNY（高峰时段、缓存未命中价格）
    # Pricing based on DeepSeek official documentation
    COST_PER_1K_TOKENS = {
        'deepseek-v4-flash': {'input': 0.003, 'output': 0.009},
        'deepseek-v4-flash-vision-exp': {'input': 0.003, 'output': 0.009},
        'deepseek-v4-pro': {'input': 0.009, 'output': 0.027},
    }

    DEFAULT_PRICING = {'input': 0.003, 'output': 0.009}

    # Model descriptions for UI display
    MODEL_DESCRIPTIONS = {
        'deepseek-v4-flash': 'V4 Flash - 速度与成本优先，1M 上下文',
        'deepseek-v4-pro': 'V4 Pro - 复杂推理与 Agent 任务',
        'deepseek-v4-flash-vision-exp': 'V4 Flash Vision (实验) - 支持图片理解',
    }

    def __init__(self, api_key: str, model: str = 'deepseek-v4-flash'):
        super().__init__(api_key, model)
