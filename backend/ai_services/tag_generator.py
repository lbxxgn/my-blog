"""
Tag Generator - Main entry point for AI tag generation

Provides factory methods for creating LLM providers and
high-level interface for tag generation.
"""

import logging
from typing import Dict, List, Optional, Any
from .base import BaseLLMProvider
from .dashscope_provider import DashscopeProvider
from .deepseek_provider import DeepSeekProvider
from .custom_provider import CustomOpenAIProvider

logger = logging.getLogger(__name__)


class TagGenerator:
    """Main tag generator class that manages provider creation and tag generation"""

    # 内置供应商到代码适配器的映射（slug -> class）
    SUPPORTED_PROVIDERS = {
        'dashscope': DashscopeProvider,
        'deepseek': DeepSeekProvider,
        'custom': CustomOpenAIProvider,
    }

    # 驱动到代码适配器的映射（目录中新增供应商使用 openai_compatible）
    DRIVER_CLASSES = {
        'dashscope': DashscopeProvider,
        'deepseek': DeepSeekProvider,
        'openai_compatible': CustomOpenAIProvider,
    }

    DRIVER_DEFAULT_MODELS = {
        'dashscope': DashscopeProvider.DEFAULT_MODEL,
        'deepseek': DeepSeekProvider.DEFAULT_MODEL,
    }

    @classmethod
    def _catalog_provider(cls, provider_name: str):
        """从目录解析供应商；目录不可用时返回 None 交由回退逻辑处理。"""
        try:
            from models.ai_catalog import resolve_provider

            return resolve_provider(provider_name)
        except Exception as exc:
            logger.warning(f"Failed to load AI provider catalog: {exc}")
            return None

    @classmethod
    def create_provider(cls, provider_name: str, api_key: str, model: str = None,
                        base_url: str = None) -> BaseLLMProvider:
        """
        Factory method to create LLM provider

        Args:
            provider_name: Provider slug configured in the AI catalog
            api_key: API key for the provider
            model: Model name (optional, uses catalog default if not specified)
            base_url: API base URL (required for providers that ask users to fill it)

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not supported
        """
        provider_name = (provider_name or 'dashscope').lower()
        catalog_provider = cls._catalog_provider(provider_name)

        if catalog_provider:
            driver = catalog_provider.get('driver') or 'openai_compatible'
            provider_class = cls.SUPPORTED_PROVIDERS.get(provider_name) or \
                cls.DRIVER_CLASSES.get(driver)

            if not provider_class:
                raise ValueError(f"Unsupported provider driver: {driver}")

            model = model or catalog_provider.get('default_model') or \
                cls.DRIVER_DEFAULT_MODELS.get(driver)

            if not model:
                raise ValueError(f"供应商 {provider_name} 未配置可用模型，请先在模型管理中配置")

            model_spec = next(
                (m for m in catalog_provider.get('model_details', [])
                 if m.get('model_id') == model),
                None
            )

            pricing = None
            if model_spec and (
                model_spec.get('input_price') is not None
                or model_spec.get('output_price') is not None
            ):
                class_pricing = getattr(provider_class, 'COST_PER_1K_TOKENS', {}).get(model) \
                    or getattr(provider_class, 'DEFAULT_PRICING', {'input': 0, 'output': 0})
                pricing = {
                    'input': model_spec.get('input_price')
                    if model_spec.get('input_price') is not None
                    else class_pricing.get('input', 0),
                    'output': model_spec.get('output_price')
                    if model_spec.get('output_price') is not None
                    else class_pricing.get('output', 0),
                }

            if catalog_provider.get('requires_base_url'):
                # 由用户填写 Base URL，保留旧 custom 行为
                resolved_base_url = base_url or None
            else:
                resolved_base_url = catalog_provider.get('base_url') or None

            return provider_class(
                api_key=api_key,
                model=model,
                base_url=resolved_base_url,
                pricing=pricing,
                currency=catalog_provider.get('currency'),
                currency_symbol=catalog_provider.get('currency_symbol'),
                valid_models=[
                    item.get('model_id')
                    for item in catalog_provider.get('model_details', [])
                    if item.get('model_id')
                ],
                allow_any_model=bool(catalog_provider.get('allow_custom_model')),
            )

        # 目录不可用时的兼容回退
        if provider_name not in cls.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider_name}. "
                f"Supported providers: {list(cls.SUPPORTED_PROVIDERS.keys())}"
            )

        provider_class = cls.SUPPORTED_PROVIDERS[provider_name]
        if not model:
            model = cls.DRIVER_DEFAULT_MODELS.get(provider_name)

        if provider_name == 'custom':
            return provider_class(api_key=api_key, model=model, base_url=base_url)

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
                - ai_base_url: str (optional, required for the custom provider)
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
        provider = user_config.get('ai_provider', 'dashscope')
        api_key = user_config.get('ai_api_key')
        model = user_config.get('ai_model')
        base_url = user_config.get('ai_base_url')

        # Validate API key
        if not api_key:
            logger.warning("No API key configured for AI tag generation")
            raise ValueError("API密钥未配置，请在AI设置中配置您的API密钥")

        try:
            # Create provider
            llm_provider = cls.create_provider(provider, api_key, model, base_url=base_url)

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
            provider = user_config.get('ai_provider', 'dashscope')
            model = user_config.get('ai_model')
            base_url = user_config.get('ai_base_url')
            llm_provider = cls.create_provider(provider, api_key, model, base_url=base_url)

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
    def get_supported_providers(cls) -> List[Dict[str, Any]]:
        """
        Get providers configured in the AI catalog.

        Returns:
            List of provider info dicts (contains models/model_details)
        """
        try:
            from models.ai_catalog import get_catalog

            return get_catalog(include_disabled=True)
        except Exception as exc:
            logger.warning(f"Failed to load AI provider catalog, using defaults: {exc}")
            from .provider_defaults import DEFAULT_CATALOG

            return [
                {
                    **{k: v for k, v in provider.items() if k != 'models'},
                    'id': provider['slug'],
                    'provider_pk': None,
                    'currency_symbol': '¥' if provider.get('currency') == 'CNY' else '$',
                    'usage_count': 0,
                    'default_model': next(
                        (m['model_id'] for m in provider.get('models', [])
                         if m.get('is_default')),
                        (provider.get('models') or [{}])[0].get('model_id', '')
                    ),
                    'models': [m['model_id'] for m in provider.get('models', [])
                              if m.get('enabled', True)],
                    'model_details': provider.get('models', []),
                }
                for provider in DEFAULT_CATALOG
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
            provider = user_config.get('ai_provider', 'dashscope')
            model = user_config.get('ai_model')
            base_url = user_config.get('ai_base_url')
            llm_provider = cls.create_provider(provider, api_key, model, base_url=base_url)

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
            provider = user_config.get('ai_provider', 'dashscope')
            model = user_config.get('ai_model')
            base_url = user_config.get('ai_base_url')
            llm_provider = cls.create_provider(provider, api_key, model, base_url=base_url)

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
            provider = user_config.get('ai_provider', 'dashscope')
            model = user_config.get('ai_model')
            base_url = user_config.get('ai_base_url')
            llm_provider = cls.create_provider(provider, api_key, model, base_url=base_url)

            result = llm_provider.continue_writing(
                title=title,
                content=content,
                continuation_length=continuation_length
            )

            return result

        except Exception as e:
            logger.error(f"Failed to continue writing: {str(e)}")
            raise
