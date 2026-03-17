"""
Volcengine Coding Plan provider

Uses Volcengine ARK Coding Plan's OpenAI-compatible endpoint.
"""

from .volcengine_provider import VolcengineProvider


class VolcengineCodingProvider(VolcengineProvider):
    """Volcengine ARK Coding Plan provider via OpenAI-compatible API."""

    BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3"

    COST_PER_1K_TOKENS = {
        'ark-code-latest': {'input': 0.0, 'output': 0.0},
        'doubao-seed-2.0-code': {'input': 0.0, 'output': 0.0},
        'doubao-seed-2.0-pro': {'input': 0.0, 'output': 0.0},
        'doubao-seed-2.0-lite': {'input': 0.0, 'output': 0.0},
        'doubao-seed-code': {'input': 0.0, 'output': 0.0},
        'doubao-seed-code-thinking': {'input': 0.0, 'output': 0.0},
        'minimax-m2.5': {'input': 0.0, 'output': 0.0},
        'glm-4.7': {'input': 0.0, 'output': 0.0},
        'deepseek-v3.2': {'input': 0.0, 'output': 0.0},
        'kimi-k2.5': {'input': 0.0, 'output': 0.0},
    }

    def __init__(self, api_key: str, model: str = 'ark-code-latest'):
        super().__init__(api_key, model)
