"""
Base class for LLM providers

Defines the interface that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, api_key: str, model: str):
        """
        Initialize the LLM provider

        Args:
            api_key: API key for the provider
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate_tags(
        self,
        title: str,
        content: str,
        existing_tags: Optional[List[str]] = None,
        max_tags: int = 3
    ) -> Dict[str, any]:
        """
        Generate tags for a blog post

        Args:
            title: Post title
            content: Post content (may be truncated)
            existing_tags: Existing tags (for updates)
            max_tags: Maximum number of tags to generate

        Returns:
            Dict containing:
                - tags: List of generated tags
                - tokens_used: Number of tokens used
                - model: Model used
                - cost: Estimated cost (optional)
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the API connection is working

        Returns:
            True if connection successful, False otherwise
        """
        pass

    def _build_prompt(
        self,
        title: str,
        content: str,
        existing_tags: Optional[List[str]] = None,
        max_tags: int = 3
    ) -> str:
        """
        Build the prompt for tag generation

        Args:
            title: Post title
            content: Post content
            existing_tags: Existing tags
            max_tags: Maximum tags to generate

        Returns:
            Formatted prompt string
        """
        existing_tags_str = ""
        if existing_tags:
            existing_tags_str = f"\n当前标签：{', '.join(existing_tags)}\n（如果是更新文章，请基于现有标签优化，而不是完全替换）"

        prompt = f"""根据以下文章内容，生成{max_tags}个最相关的标签。

标题：{title}{existing_tags_str}

内容摘要（前500字）：
{content[:500]}

要求：
1. 标签应该简洁明了（2-4个字）
2. 标签应该反映文章的核心主题
3. 避免过于宽泛的标签（如"技术"、"文章"、"笔记"）
4. 优先使用具体的技术栈、框架、业务领域等关键词
5. 以JSON格式返回，格式如：{{"tags": ["标签1", "标签2", "标签3"]}}"""

        return prompt

    def _parse_tags_from_response(self, response_text: str) -> List[str]:
        """
        Parse tags from LLM response

        Args:
            response_text: Raw response from LLM

        Returns:
            List of extracted tags
        """
        import json
        import re

        # Try to parse as JSON directly
        try:
            data = json.loads(response_text)
            if isinstance(data, dict) and 'tags' in data:
                return data['tags']
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from response
        json_match = re.search(r'\{[^}]*"tags"[^}]*\}', response_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if isinstance(data, dict) and 'tags' in data:
                    return data['tags']
            except json.JSONDecodeError:
                pass

        # Try to extract list from response
        list_match = re.search(r'\["[^"]*"(?:\s*,\s*"[^"]*")*\]', response_text)
        if list_match:
            try:
                return json.loads(list_match.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback: extract quoted strings
        tags = re.findall(r'"([^"]{2,10})"', response_text)
        return tags[:3] if tags else ["未分类"]
