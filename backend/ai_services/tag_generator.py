"""
Tag Generator - Main entry point for AI tag generation

Provides factory methods for creating LLM providers and
high-level interface for tag generation.
"""

import logging
from typing import Dict, List, Optional, Any
from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .volcengine_provider import VolcengineProvider
from .dashscope_provider import DashscopeProvider

logger = logging.getLogger(__name__)


class TagGenerator:
    """Main tag generator class that manages provider creation and tag generation"""

    # Supported providers
    SUPPORTED_PROVIDERS = {
        'openai': OpenAIProvider,
        'volcengine': VolcengineProvider,
        'dashscope': DashscopeProvider,
        # 'claude': ClaudeProvider,  # Future implementation
        # 'qwen': QwenProvider,      # Future implementation
    }

    @classmethod
    def create_provider(cls, provider_name: str, api_key: str, model: str = None) -> BaseLLMProvider:
        """
        Factory method to create LLM provider

        Args:
            provider_name: Name of the provider (openai, claude, qwen)
            api_key: API key for the provider
            model: Model name (optional, uses provider default if not specified)

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not supported
        """
        provider_name = provider_name.lower()

        if provider_name not in cls.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider_name}. "
                f"Supported providers: {list(cls.SUPPORTED_PROVIDERS.keys())}"
            )

        provider_class = cls.SUPPORTED_PROVIDERS[provider_name]

        # Set default model if not specified
        if not model:
            default_models = {
                'openai': 'gpt-3.5-turbo',
                'volcengine': 'doubao-pro-4k',
                'dashscope': 'qwen-turbo',
                'claude': 'claude-3-haiku-20240307',
                'qwen': 'qwen-turbo',
            }
            model = default_models.get(provider_name, 'default')

        return provider_class(api_key=api_key, model=model)

    @classmethod
    def generate_for_post(
        cls,
        title: str,
        content: str,
        user_config: Dict[str, Any],
        existing_tags: Optional[List[str]] = None,
        max_tags: int = 3
    ) -> Optional[Dict[str, any]]:
        """
        Generate tags for a blog post based on user configuration

        Args:
            title: Post title
            content: Post content
            user_config: User AI configuration dict containing:
                - ai_tag_generation_enabled: bool
                - ai_provider: str
                - ai_api_key: str
                - ai_model: str (optional)
            existing_tags: Existing tags (for updates)
            max_tags: Maximum tags to generate

        Returns:
            Dict with tags, tokens_used, model, cost, or None if disabled
        """
        # Check if AI tag generation is enabled
        if not user_config.get('ai_tag_generation_enabled', False):
            logger.info("AI tag generation is disabled for this user")
            return None

        # Get required configuration
        provider = user_config.get('ai_provider', 'openai')
        api_key = user_config.get('ai_api_key')
        model = user_config.get('ai_model')

        # Validate API key
        if not api_key:
            logger.warning("No API key configured for AI tag generation")
            raise ValueError("API密钥未配置，请在AI设置中配置您的API密钥")

        try:
            # Create provider
            llm_provider = cls.create_provider(provider, api_key, model)

            # Generate tags
            result = llm_provider.generate_tags(
                title=title,
                content=content,
                existing_tags=existing_tags,
                max_tags=max_tags
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate tags: {str(e)}")
            raise

    @classmethod
    def test_user_config(cls, user_config: Dict[str, Any]) -> Dict[str, any]:
        """
        Test user's AI configuration

        Args:
            user_config: User AI configuration

        Returns:
            Dict with success status and message
        """
        if not user_config.get('ai_tag_generation_enabled', False):
            return {
                'success': True,
                'message': 'AI功能已禁用'
            }

        api_key = user_config.get('ai_api_key')
        if not api_key:
            return {
                'success': False,
                'message': '未配置API密钥'
            }

        try:
            provider = user_config.get('ai_provider', 'openai')
            model = user_config.get('ai_model')
            llm_provider = cls.create_provider(provider, api_key, model)

            # Test connection
            if llm_provider.test_connection():
                return {
                    'success': True,
                    'message': f'连接成功 ({provider}/{model})'
                }
            else:
                return {
                    'success': False,
                    'message': '连接测试失败，请检查API密钥'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'配置错误: {str(e)}'
            }

    @classmethod
    def get_supported_providers(cls) -> List[Dict[str, str]]:
        """
        Get list of supported providers with their info

        Returns:
            List of provider info dicts
        """
        return [
            {
                'id': 'openai',
                'name': 'OpenAI',
                'description': 'GPT-3.5-turbo, GPT-4, GPT-4o',
                'default_model': 'gpt-3.5-turbo',
                'models': ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4-turbo', 'gpt-4'],
                'currency': 'USD'
            },
            {
                'id': 'volcengine',
                'name': '火山引擎',
                'description': '豆包系列模型',
                'default_model': 'doubao-pro-4k',
                'models': ['doubao-pro-32k', 'doubao-pro-4k', 'doubao-lite-4k'],
                'currency': 'CNY'
            },
            {
                'id': 'dashscope',
                'name': '阿里百炼',
                'description': '通义千问系列',
                'default_model': 'qwen-turbo',
                'models': [
                    'qwen-flash',
                    'qwen-turbo',
                    'qwen-plus',
                    'qwen-max',
                    'qwen-coder-plus',
                    'qwen-coder-plus-1106',
                    'qwen-coder-plus-latest',
                    'qwen-long-latest',
                    'qwen-long-2025-01-25',
                    'qwen-vl-max',
                    'qwen-vl-max-latest',
                ],
                'currency': 'CNY'
            },
            # Future providers can be added here
            # {
            #     'id': 'claude',
            #     'name': 'Anthropic Claude',
            #     'description': 'Claude 3 Haiku, Sonnet, Opus',
            #     'default_model': 'claude-3-haiku-20240307',
            #     'models': ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229']
            # },
        ]

    @classmethod
    def generate_summary(
        cls,
        title: str,
        content: str,
        user_config: Dict[str, Any],
        max_length: int = 200
    ) -> Optional[Dict[str, any]]:
        """
        Generate a summary for a blog post

        Args:
            title: Post title
            content: Post content
            user_config: User AI configuration
            max_length: Maximum length of summary

        Returns:
            Dict with summary, tokens_used, model, cost, or None if disabled
        """
        if not user_config.get('ai_tag_generation_enabled', False):
            logger.info("AI summary generation is disabled for this user")
            return None

        api_key = user_config.get('ai_api_key')
        if not api_key:
            logger.warning("No API key configured for AI summary generation")
            raise ValueError("API密钥未配置")

        try:
            provider = user_config.get('ai_provider', 'openai')
            model = user_config.get('ai_model')
            llm_provider = cls.create_provider(provider, api_key, model)

            result = llm_provider.generate_summary(
                title=title,
                content=content,
                max_length=max_length
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise

    @classmethod
    def recommend_related_posts(
        cls,
        current_post_id: int,
        title: str,
        content: str,
        all_posts: List[Dict],
        user_config: Dict[str, Any],
        max_recommendations: int = 3
    ) -> Optional[Dict[str, any]]:
        """
        Recommend related blog posts

        Args:
            current_post_id: ID of current post
            title: Current post title
            content: Current post content
            all_posts: List of all posts
            user_config: User AI configuration
            max_recommendations: Maximum number of recommendations

        Returns:
            Dict with recommendations, tokens_used, model, cost, or None if disabled
        """
        if not user_config.get('ai_tag_generation_enabled', False):
            logger.info("AI recommendation is disabled for this user")
            return None

        api_key = user_config.get('ai_api_key')
        if not api_key:
            logger.warning("No API key configured for AI recommendation")
            raise ValueError("API密钥未配置")

        try:
            provider = user_config.get('ai_provider', 'openai')
            model = user_config.get('ai_model')
            llm_provider = cls.create_provider(provider, api_key, model)

            result = llm_provider.recommend_related_posts(
                current_post_id=current_post_id,
                title=title,
                content=content,
                all_posts=all_posts,
                max_recommendations=max_recommendations
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            raise

    @classmethod
    def continue_writing(
        cls,
        title: str,
        content: str,
        user_config: Dict[str, Any],
        continuation_length: int = 500
    ) -> Optional[Dict[str, any]]:
        """
        Continue writing from where the content left off

        Args:
            title: Post title
            content: Existing content
            user_config: User AI configuration
            continuation_length: Target length of continuation

        Returns:
            Dict with continuation, tokens_used, model, cost, or None if disabled
        """
        if not user_config.get('ai_tag_generation_enabled', False):
            logger.info("AI writing continuation is disabled for this user")
            return None

        api_key = user_config.get('ai_api_key')
        if not api_key:
            logger.warning("No API key configured for AI writing continuation")
            raise ValueError("API密钥未配置")

        try:
            provider = user_config.get('ai_provider', 'openai')
            model = user_config.get('ai_model')
            llm_provider = cls.create_provider(provider, api_key, model)

            result = llm_provider.continue_writing(
                title=title,
                content=content,
                continuation_length=continuation_length
            )

            return result

        except Exception as e:
            logger.error(f"Failed to continue writing: {str(e)}")
            raise
