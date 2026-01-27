"""
DashScope API provider

Implements LLM provider interface for Alibaba's DashScope API.
DashScope provides OpenAI-compatible API with custom base URL.
"""

import logging
from typing import Dict, List, Optional
from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class DashscopeProvider(BaseLLMProvider):
    """Alibaba DashScope API provider for tag generation

    DashScope (阿里百炼) provides the Qwen (通义千问) series models
    through an OpenAI-compatible API.
    """

    # Base URL for DashScope OpenAI-compatible API
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

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
        """
        Initialize DashScope provider

        Args:
            api_key: DashScope API key
            model: Model to use (default: qwen-turbo)
        """
        super().__init__(api_key, model)
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize DashScope client using OpenAI SDK with custom base URL"""
        try:
            from openai import OpenAI

            # Validate API key format
            if not self.api_key or not isinstance(self.api_key, str):
                raise ValueError("API密钥格式无效：密钥不能为空")

            # DashScope API keys typically start with 'sk-'
            if not self.api_key.startswith('sk-'):
                logger.warning(f"API key may be invalid (doesn't start with 'sk-'): {self.api_key[:10]}...")

            # Validate model name
            valid_models = list(self.COST_PER_1K_TOKENS.keys())
            if self.model not in valid_models:
                logger.warning(f"Model '{self.model}' may not be valid. Supported models: {valid_models}")

            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL
            )
            logger.info(f"DashScope client initialized with model: {self.model}")
        except ImportError:
            logger.error("OpenAI library not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize DashScope client: {str(e)}")
            raise

    def generate_tags(
        self,
        title: str,
        content: str,
        existing_tags: Optional[List[str]] = None,
        max_tags: int = 3
    ) -> Dict[str, any]:
        """
        Generate tags using DashScope API

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
            logger.error(f"DashScope API error: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """
        Test DashScope API connection

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
            logger.error(f"DashScope connection test failed: {str(e)}")
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
        pricing = self.COST_PER_1K_TOKENS.get(self.model, {'input': 0.0003, 'output': 0.0006})
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        return input_cost + output_cost

    def generate_summary(
        self,
        title: str,
        content: str,
        max_length: int = 200
    ) -> Dict[str, any]:
        """Generate a summary for a blog post"""
        if not self.client:
            self._init_client()

        prompt = f"""请为以下文章生成一个简洁的摘要（{max_length}字以内）：

标题：{title}
内容：{content[:2000]}

要求：
1. 摘要应该突出文章的核心观点和价值
2. 语言简洁明了，吸引读者
3. 保持客观中立的语气
4. 直接返回摘要文本，不要其他内容
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的文章摘要生成助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300,
            )

            summary = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            cost = self._calculate_cost(input_tokens, output_tokens)

            return {
                'summary': summary,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost,
                'currency': 'CNY'
            }
        except Exception as e:
            logger.error(f"DashScope summary generation error: {str(e)}")
            raise

    def recommend_related_posts(
        self,
        current_post_id: int,
        title: str,
        content: str,
        all_posts: List[Dict],
        max_recommendations: int = 3
    ) -> Dict[str, any]:
        """Recommend related blog posts"""
        if not self.client:
            self._init_client()

        candidates = [
            {"id": p["id"], "title": p["title"]}
            for p in all_posts if p["id"] != current_post_id
        ]

        if not candidates:
            return {'recommendations': [], 'tokens_used': 0, 'model': self.model}

        candidates_text = "\n".join([f"- ID {c['id']}: {c['title']}" for c in candidates[:20]])

        prompt = f"""根据当前文章，从以下候选文章中选择{max_recommendations}篇最相关的文章。

当前文章：
标题：{title}
内容摘要：{content[:500]}

候选文章：
{candidates_text}

要求：以JSON格式返回，格式如：{{"recommendations": [1, 5, 8]}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的内容推荐助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100,
            )

            import json
            import re

            response_text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            cost = self._calculate_cost(input_tokens, output_tokens)

            try:
                data = json.loads(response_text)
                recommendations = data.get('recommendations', [])
            except json.JSONDecodeError:
                numbers = re.findall(r'\d+', response_text)
                recommendations = [int(n) for n in numbers[:max_recommendations]]

            # Validate recommendations and create full post info
            valid_ids = {c["id"]: c for c in candidates}
            recommendations = [
                {
                    'id': r,
                    'title': valid_ids[r]['title'],
                    'url': f'/post/{r}'
                }
                for r in recommendations
                if r in valid_ids
            ][:max_recommendations]

            return {
                'recommendations': recommendations,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost,
                'currency': 'CNY'
            }
        except Exception as e:
            logger.error(f"DashScope recommendation error: {str(e)}")
            raise

    def continue_writing(
        self,
        title: str,
        content: str,
        continuation_length: int = 500
    ) -> Dict[str, any]:
        """Continue writing from where the content left off"""
        if not self.client:
            self._init_client()

        context = content[-1000:] if len(content) > 1000 else content

        prompt = f"""请续写以下文章，保持相同的风格和主题。

标题：{title}
当前内容末尾：{context}

要求：
1. 保持与原文相同的写作风格和语气
2. 延续当前的主题思路
3. 续写内容约{continuation_length}字
4. 不要重复已有的内容
5. 保持内容的连贯性和逻辑性
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的内容创作者。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=800,
            )

            continuation = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            cost = self._calculate_cost(input_tokens, output_tokens)

            return {
                'continuation': continuation,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost,
                'currency': 'CNY'
            }
        except Exception as e:
            logger.error(f"DashScope continuation error: {str(e)}")
            raise
