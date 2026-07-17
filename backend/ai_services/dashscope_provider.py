"""
DashScope API provider

DashScope (阿里百炼) provides the Qwen (通义千问) series models
through an OpenAI-compatible API.
仅声明特有配置，通用逻辑见 OpenAICompatibleProvider。
"""

from .openai_compatible import OpenAICompatibleProvider


class DashscopeProvider(OpenAICompatibleProvider):
    """Alibaba DashScope API provider"""

    PROVIDER_NAME = 'DashScope'
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = 'qwen-turbo'
    CURRENCY = 'CNY'
    CURRENCY_SYMBOL = '¥'

    # Cost per 1K tokens in CNY (Chinese Yuan)
    # Pricing based on DashScope official documentation
    # Note: qwen-long-* models use character-based billing (1 yuan per 1M chars)
    # Using token-based pricing estimates here for simplicity
    COST_PER_1K_TOKENS = {
        # Flash series - Cheapest and fastest
        'qwen-flash': {'input': 0.0001, 'output': 0.0002},

        # Turbo series - Low cost, fast response
        'qwen-turbo': {'input': 0.0003, 'output': 0.0006},

        # Plus series - Balanced performance and cost
        'qwen-plus': {'input': 0.0008, 'output': 0.002},
        'qwen-coder-plus': {'input': 0.0008, 'output': 0.002},
        'qwen-coder-plus-1106': {'input': 0.0008, 'output': 0.002},
        'qwen-coder-plus-latest': {'input': 0.0008, 'output': 0.002},

        # Long context models - Extended context support
        'qwen-long-latest': {'input': 0.0005, 'output': 0.002},
        'qwen-long-2025-01-25': {'input': 0.0005, 'output': 0.002},

        # Max series - Highest quality
        'qwen-max': {'input': 0.02, 'output': 0.06},

        # Vision-Language models - Multimodal capabilities
        'qwen-vl-max': {'input': 0.02, 'output': 0.06},
        'qwen-vl-max-latest': {'input': 0.02, 'output': 0.06},
    }

    DEFAULT_PRICING = {'input': 0.0003, 'output': 0.0006}

    # Model descriptions for UI display
    MODEL_DESCRIPTIONS = {
        'qwen-flash': 'Flash - 极速响应，超低成本',
        'qwen-turbo': 'Turbo - 高性价比',
        'qwen-plus': 'Plus - 均衡性能',
        'qwen-max': 'Max - 最高质量',
        'qwen-coder-plus': 'Coder Plus - 代码生成优化',
        'qwen-coder-plus-1106': 'Coder Plus 1106 - 代码生成',
        'qwen-coder-plus-latest': 'Coder Plus Latest - 最新代码模型',
        'qwen-long-latest': 'Long Latest - 长文本处理',
        'qwen-long-2025-01-25': 'Long - 长文本处理',
        'qwen-vl-max': 'VL Max - 视觉理解',
        'qwen-vl-max-latest': 'VL Max Latest - 最新视觉模型',
    }

    def __init__(self, api_key: str, model: str = 'qwen-turbo'):
        super().__init__(api_key, model)
