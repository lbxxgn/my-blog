"""
OpenAI provider implementation

Implements LLM provider interface for OpenAI's API.
"""

import logging
from typing import Dict, List, Optional
from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider for tag generation"""

    # Cost per 1K tokens (as of 2024)
    COST_PER_1K_TOKENS = {
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        'gpt-4o': {'input': 0.005, 'output': 0.015},
    }

    def __init__(self, api_key: str, model: str = 'gpt-3.5-turbo'):
        """
        Initialize OpenAI provider

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-3.5-turbo)
        """
        super().__init__(api_key, model)
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
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
        Generate tags using OpenAI API

        Args:
            title: Post title
            content: Post content
            existing_tags: Existing tags for updates
            max_tags: Maximum tags to generate

        Returns:
            Dict with tags, tokens_used, model, and cost
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

            logger.info(f"Generated tags: {tags}, tokens: {tokens_used}, cost: ${cost:.6f}")

            return {
                'tags': tags,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost,
                'raw_response': content_text
            }

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """
        Test OpenAI API connection

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
            logger.error(f"OpenAI connection test failed: {str(e)}")
            return False

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API cost

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = self.COST_PER_1K_TOKENS.get(self.model, {'input': 0.001, 'output': 0.002})
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        return input_cost + output_cost
