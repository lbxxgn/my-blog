"""
Volcengine ARK API provider

Implements LLM provider interface for Volcengine's (Volcengine ARK) API.
Volcengine provides OpenAI-compatible API with custom base URL.
"""

import logging
from typing import Dict, List, Optional
from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class VolcengineProvider(BaseLLMProvider):
    """Volcengine ARK API provider for tag generation

    Volcengine (火山引擎) provides the Doubao (豆包) series models
    through an OpenAI-compatible API.
    """

    # Base URL for Volcengine ARK API
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    # Cost per 1K tokens in CNY (Chinese Yuan)
    # Pricing based on Volcengine official documentation
    COST_PER_1K_TOKENS = {
        'doubao-pro-32k': {'input': 0.00012, 'output': 0.00012},
        'doubao-pro-4k': {'input': 0.00004, 'output': 0.00004},
        'doubao-lite-4k': {'input': 0.00003, 'output': 0.00003},
    }

    def __init__(self, api_key: str, model: str = 'doubao-pro-4k'):
        """
        Initialize Volcengine provider

        Args:
            api_key: Volcengine ARK API key
            model: Model to use (default: doubao-pro-4k)
        """
        super().__init__(api_key, model)
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Volcengine client using OpenAI SDK with custom base URL"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL
            )
        except ImportError:
            logger.error("OpenAI library not installed. Run: pip install openai")
            raise

    def generate_tags(
        self,
        title: str,
        content: str,
        existing_tags: Optional[List[str]] = None,
        max_tags: int = 3
    ) -> Dict[str, any]:
        """
        Generate tags using Volcengine ARK API

        Args:
            title: Post title
            content: Post content
            existing_tags: Existing tags for updates
            max_tags: Maximum tags to generate

        Returns:
            Dict with tags, tokens_used, model, and cost (in CNY)
        """
        if not self.client:
            self._init_client()

        prompt = self._build_prompt(title, content, existing_tags, max_tags)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的博客标签生成助手，擅长根据文章内容提取精准的标签。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=100,
            )

            # Extract response
            content_text = response.choices[0].message.content.strip()

            # Parse tags
            tags = self._parse_tags_from_response(content_text)

            # Calculate tokens and cost
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            cost = self._calculate_cost(input_tokens, output_tokens)

            logger.info(f"Generated tags: {tags}, tokens: {tokens_used}, cost: ¥{cost:.6f}")

            return {
                'tags': tags,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost,
                'currency': 'CNY',
                'raw_response': content_text
            }

        except Exception as e:
            logger.error(f"Volcengine API error: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """
        Test Volcengine ARK API connection

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.client:
                self._init_client()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"Volcengine connection test failed: {str(e)}")
            return False

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API cost in CNY

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in CNY (Chinese Yuan)
        """
        pricing = self.COST_PER_1K_TOKENS.get(self.model, {'input': 0.00004, 'output': 0.00004})
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        return input_cost + output_cost
