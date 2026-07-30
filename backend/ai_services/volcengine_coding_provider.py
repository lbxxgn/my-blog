"""
Volcengine Coding Plan provider

Uses Volcengine ARK Coding Plan's OpenAI-compatible endpoint.
"""

from .volcengine_provider import VolcengineProvider


class VolcengineCodingProvider(VolcengineProvider):
    """Volcengine ARK Coding Plan provider via OpenAI-compatible API."""

    BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3"

    COST_PER_1K_TOKENS = {
        'doubao-seed-2.0-lite': {'input': 0.0, 'output': 0.0},
        'glm-5.2': {'input': 0.0, 'output': 0.0},
        'kimi-k2.7-code': {'input': 0.0, 'output': 0.0},
        'deepseek-v4-pro': {'input': 0.0, 'output': 0.0},
        'deepseek-v4-flash': {'input': 0.0, 'output': 0.0},
        'minimax-m3': {'input': 0.0, 'output': 0.0},
        'minimax-m2.7': {'input': 0.0, 'output': 0.0},
        'kimi-k2.6': {'input': 0.0, 'output': 0.0},
        'doubao-seed-2.1-turbo': {'input': 0.0, 'output': 0.0},
    }

    def __init__(self, api_key: str, model: str = 'doubao-seed-2.0-lite'):
        super().__init__(api_key, model)
