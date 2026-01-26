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

    def generate_summary(
        self,
        title: str,
        content: str,
        max_length: int = 200
    ) -> Dict[str, any]:
        """
        Generate a summary for a blog post

        Args:
            title: Post title
            content: Post content
            max_length: Maximum length of summary

        Returns:
            Dict with summary, tokens_used, model
        """
        if not self.client:
            self._init_client()

        prompt = f"""请为以下文章生成一个简洁的摘要（{max_length}字以内）：

标题：{title}

内容：
{content[:2000]}

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
                    {
                        "role": "system",
                        "content": "你是一个专业的文章摘要生成助手，擅长提取文章核心内容。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=300,
            )

            summary = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            cost = self._calculate_cost(input_tokens, output_tokens)

            logger.info(f"Generated summary ({len(summary)} chars), tokens: {tokens_used}, cost: ${cost:.6f}")

            return {
                'summary': summary,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost
            }

        except Exception as e:
            logger.error(f"OpenAI summary generation error: {str(e)}")
            raise

    def recommend_related_posts(
        self,
        current_post_id: int,
        title: str,
        content: str,
        all_posts: List[Dict],
        max_recommendations: int = 3
    ) -> Dict[str, any]:
        """
        Recommend related blog posts

        Args:
            current_post_id: ID of current post
            title: Current post title
            content: Current post content
            all_posts: List of all posts
            max_recommendations: Maximum number of recommendations

        Returns:
            Dict with recommendations (list of post IDs), tokens_used, model
        """
        if not self.client:
            self._init_client()

        # Filter out current post and create a list of candidate posts
        candidates = [
            {"id": p["id"], "title": p["title"]}
            for p in all_posts
            if p["id"] != current_post_id
        ]

        if not candidates:
            return {
                'recommendations': [],
                'tokens_used': 0,
                'model': self.model
            }

        # Create a formatted list of candidate posts
        candidates_text = "\n".join([
            f"- ID {c['id']}: {c['title']}"
            for c in candidates[:20]  # Limit to 20 candidates
        ])

        prompt = f"""根据当前文章，从以下候选文章中选择{max_recommendations}篇最相关的文章。

当前文章：
标题：{title}
内容摘要：{content[:500]}

候选文章：
{candidates_text}

要求：
1. 选择与当前文章主题最相关的文章
2. 可以基于技术栈、主题、领域等关联性
3. 以JSON格式返回，格式如：{{"recommendations": [1, 5, 8]}}
4. 只返回ID数字列表，不要其他内容
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的内容推荐助手，擅长识别文章之间的关联性。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
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

            # Parse response
            try:
                data = json.loads(response_text)
                recommendations = data.get('recommendations', [])
            except json.JSONDecodeError:
                # Try to extract list of numbers
                numbers = re.findall(r'\d+', response_text)
                recommendations = [int(n) for n in numbers[:max_recommendations]]

            # Validate recommendations
            valid_ids = {c["id"] for c in candidates}
            recommendations = [r for r in recommendations if r in valid_ids][:max_recommendations]

            logger.info(f"Generated {len(recommendations)} recommendations, tokens: {tokens_used}, cost: ${cost:.6f}")

            return {
                'recommendations': recommendations,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost
            }

        except Exception as e:
            logger.error(f"OpenAI recommendation error: {str(e)}")
            raise

    def continue_writing(
        self,
        title: str,
        content: str,
        continuation_length: int = 500
    ) -> Dict[str, any]:
        """
        Continue writing from where the content left off

        Args:
            title: Post title
            content: Existing content
            continuation_length: Target length of continuation

        Returns:
            Dict with continuation text, tokens_used, model
        """
        if not self.client:
            self._init_client()

        # Get the last part of the content as context
        context = content[-1000:] if len(content) > 1000 else content

        prompt = f"""请续写以下文章，保持相同的风格和主题。

标题：{title}

当前内容末尾：
{context}

要求：
1. 保持与原文相同的写作风格和语气
2. 延续当前的主题思路
3. 续写内容约{continuation_length}字
4. 不要重复已有的内容
5. 保持内容的连贯性和逻辑性
6. 直接返回续写内容，不要开头说明
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的内容创作者，擅长续写文章并保持风格一致。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=800,
            )

            continuation = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            cost = self._calculate_cost(input_tokens, output_tokens)

            logger.info(f"Generated continuation ({len(continuation)} chars), tokens: {tokens_used}, cost: ${cost:.6f}")

            return {
                'continuation': continuation,
                'tokens_used': tokens_used,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': self.model,
                'cost': cost
            }

        except Exception as e:
            logger.error(f"OpenAI continuation error: {str(e)}")
            raise
