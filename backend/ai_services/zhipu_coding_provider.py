"""
Zhipu Coding Plan provider

Uses Zhipu's OpenAI-compatible Coding API endpoint.
"""

from .volcengine_provider import VolcengineProvider


class ZhipuCodingProvider(VolcengineProvider):
    """Zhipu AI Coding Plan provider."""

    BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"

    COST_PER_1K_TOKENS = {
        'glm-4.7': {'input': 0.0, 'output': 0.0},
        'glm-5': {'input': 0.0, 'output': 0.0},
    }

    def __init__(self, api_key: str, model: str = 'glm-4.7'):
        super().__init__(api_key, model)
