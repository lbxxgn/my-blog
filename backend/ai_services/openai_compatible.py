"""
OpenAI 兼容 API 的共享 Provider 基类

OpenAI / DashScope / Volcengine 均提供 OpenAI 兼容的 chat completions API，
三者实现仅有 BASE_URL、模型定价表、币种等差异。本基类收敛公共逻辑，
子类只需声明类属性（参考 volcengine_coding_provider 的既有范式）。

新增 OpenAI 兼容服务商时，继承本类并设置：
    PROVIDER_NAME / BASE_URL / DEFAULT_MODEL / COST_PER_1K_TOKENS / CURRENCY
"""

import json
import logging
import re
from typing import Dict, List, Optional

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """基于 OpenAI SDK 的兼容 API Provider 基类"""

    # ---- 子类必须/可选覆盖的类属性 ----
    PROVIDER_NAME = 'OpenAI-compatible'
    BASE_URL = None                    # None 表示使用 OpenAI 官方端点
    DEFAULT_MODEL = None               # 子类必须设置
    COST_PER_1K_TOKENS = {}
    DEFAULT_PRICING = {'input': 0.001, 'output': 0.002}
    EXTRA_VALID_MODELS = []            # 定价表之外额外认可的型号（仅用于告警）
    API_KEY_PREFIX = 'sk-'             # API key 预期前缀，None 表示不检查
    CURRENCY = 'USD'
    CURRENCY_SYMBOL = '$'

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model or self.DEFAULT_MODEL)
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        try:
            from openai import OpenAI

            if not self.api_key or not isinstance(self.api_key, str):
                raise ValueError("API密钥格式无效：密钥不能为空")

            if self.API_KEY_PREFIX and not self.api_key.startswith(self.API_KEY_PREFIX):
                logger.warning(f"API key may be invalid (doesn't start with '{self.API_KEY_PREFIX}'): {self.api_key[:10]}...")

            valid_models = list(self.COST_PER_1K_TOKENS.keys()) + list(self.EXTRA_VALID_MODELS)
            if valid_models and self.model not in valid_models:
                logger.warning(f"Model '{self.model}' may not be valid. Supported models: {valid_models}")

            client_kwargs = {'api_key': self.api_key}
            if self.BASE_URL:
                client_kwargs['base_url'] = self.BASE_URL
            self.client = OpenAI(**client_kwargs)
            logger.info(f"{self.PROVIDER_NAME} client initialized with model: {self.model}")
        except ImportError:
            logger.error("OpenAI library not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize {self.PROVIDER_NAME} client: {str(e)}")
            raise

    def _chat(self, system_prompt: str, user_prompt: str,
              temperature: float, max_tokens: int):
        """发起一次 chat completion，返回 (文本, usage)"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip(), response.usage

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """按定价表估算调用成本（币种见 CURRENCY）"""
        pricing = self.COST_PER_1K_TOKENS.get(self.model, self.DEFAULT_PRICING)
        return (input_tokens / 1000) * pricing['input'] + (output_tokens / 1000) * pricing['output']

    def _usage_dict(self, usage, cost: float) -> Dict[str, any]:
        return {
            'tokens_used': usage.total_tokens,
            'input_tokens': usage.prompt_tokens,
            'output_tokens': usage.completion_tokens,
            'model': self.model,
            'cost': cost,
            'currency': self.CURRENCY,
        }

    def generate_tags(
        self,
        title: str,
        content: str,
        existing_tags: Optional[List[str]] = None,
        max_tags: int = 3
    ) -> Dict[str, any]:
        """生成文章标签"""
        if not self.client:
            self._init_client()

        prompt = self._build_prompt(title, content, existing_tags, max_tags)

        try:
            content_text, usage = self._chat(
                "你是一个专业的博客标签生成助手，擅长根据文章内容提取精准的标签。",
                prompt, temperature=0.7, max_tokens=100)

            tags = self._parse_tags_from_response(content_text)
            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

            logger.info(f"Generated tags: {tags}, tokens: {usage.total_tokens}, "
                        f"cost: {self.CURRENCY_SYMBOL}{cost:.6f}")

            return {
                'tags': tags,
                **self._usage_dict(usage, cost),
                'raw_response': content_text,
            }

        except Exception as e:
            logger.error(f"{self.PROVIDER_NAME} API error: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """测试 API 连通性"""
        try:
            if not self.client:
                self._init_client()

            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"{self.PROVIDER_NAME} connection test failed: {str(e)}")
            return False

    def generate_summary(
        self,
        title: str,
        content: str,
        max_length: int = 200
    ) -> Dict[str, any]:
        """生成文章摘要"""
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
            summary, usage = self._chat(
                "你是一个专业的文章摘要生成助手，擅长提取文章核心内容。",
                prompt, temperature=0.5, max_tokens=300)

            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

            logger.info(f"Generated summary ({len(summary)} chars), tokens: {usage.total_tokens}, "
                        f"cost: {self.CURRENCY_SYMBOL}{cost:.6f}")

            return {
                'summary': summary,
                **self._usage_dict(usage, cost),
            }

        except Exception as e:
            logger.error(f"{self.PROVIDER_NAME} summary generation error: {str(e)}")
            raise

    def recommend_related_posts(
        self,
        current_post_id: int,
        title: str,
        content: str,
        all_posts: List[Dict],
        max_recommendations: int = 3
    ) -> Dict[str, any]:
        """推荐相关文章"""
        if not self.client:
            self._init_client()

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
            response_text, usage = self._chat(
                "你是一个专业的内容推荐助手，擅长识别文章之间的关联性。",
                prompt, temperature=0.3, max_tokens=100)

            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

            # Parse response
            try:
                data = json.loads(response_text)
                recommendations = data.get('recommendations', [])
            except json.JSONDecodeError:
                # Try to extract list of numbers
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

            logger.info(f"Generated {len(recommendations)} recommendations, tokens: {usage.total_tokens}, "
                        f"cost: {self.CURRENCY_SYMBOL}{cost:.6f}")

            return {
                'recommendations': recommendations,
                **self._usage_dict(usage, cost),
            }

        except Exception as e:
            logger.error(f"{self.PROVIDER_NAME} recommendation error: {str(e)}")
            raise

    def continue_writing(
        self,
        title: str,
        content: str,
        continuation_length: int = 500
    ) -> Dict[str, any]:
        """续写文章"""
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
            continuation, usage = self._chat(
                "你是一个专业的内容创作者，擅长续写文章并保持风格一致。",
                prompt, temperature=0.8, max_tokens=800)

            cost = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)

            logger.info(f"Generated continuation ({len(continuation)} chars), tokens: {usage.total_tokens}, "
                        f"cost: {self.CURRENCY_SYMBOL}{cost:.6f}")

            return {
                'continuation': continuation,
                **self._usage_dict(usage, cost),
            }

        except Exception as e:
            logger.error(f"{self.PROVIDER_NAME} continuation error: {str(e)}")
            raise
