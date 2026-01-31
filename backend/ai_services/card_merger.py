"""
AI Card Merger - Intelligent card merging service

Uses LLM to intelligently merge cards into coherent articles.
"""

import logging
from typing import Dict, List, Any
from .tag_generator import TagGenerator

logger = logging.getLogger(__name__)


class AICardMerger:
    """AI-powered card merger"""

    @staticmethod
    def merge_cards(
        card_ids: List[int],
        user_id: int,
        user_config: Dict[str, Any],
        merge_style: str = 'comprehensive'
    ) -> Dict[str, Any]:
        """
        Merge cards using AI to create coherent article

        Args:
            card_ids: List of card IDs to merge
            user_id: User ID
            user_config: User AI configuration
            merge_style: 'comprehensive' (full merge) or 'outline' (outline only)

        Returns:
            Dict containing:
                - title: Generated title
                - content: Merged content
                - outline: Article outline
                - tags: Generated tags
                - tokens_used: Token count
        """
        from models import get_cards_by_user

        # Get cards
        all_cards = get_cards_by_user(user_id)
        cards_to_merge = [c for c in all_cards if c['id'] in card_ids]

        if not cards_to_merge:
            raise ValueError('No valid cards found')

        # Prepare cards data for AI
        cards_data = []
        for card in cards_to_merge:
            cards_data.append({
                'title': card['title'] or '无标题',
                'content': card['content'],
                'created_at': card['created_at']
            })

        # Sort by created_at
        cards_data.sort(key=lambda x: x['created_at'])

        # Generate prompt
        prompt = AICardMerger._build_merge_prompt(cards_data, merge_style)

        # Call LLM
        provider = TagGenerator.create_provider(
            provider_name=user_config.get('ai_provider', 'openai'),
            api_key=user_config.get('ai_api_key'),
            model=user_config.get('ai_model')
        )

        # Generate completion
        messages = [
            {"role": "system", "content": "You are a helpful editor that organizes notes into coherent articles."},
            {"role": "user", "content": prompt}
        ]

        response = provider.client.chat.completions.create(
            model=provider.model,
            messages=messages,
            temperature=0.7
        )

        result_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        # Parse result
        result = AICardMerger._parse_merge_result(result_text)

        # Generate tags
        tag_result = TagGenerator.generate_for_post(
            title=result['title'],
            content=result['content'],
            user_config=user_config,
            max_tags=5
        )

        result['tags'] = tag_result.get('tags', []) if tag_result else []
        result['tokens_used'] = tokens_used

        return result

    @staticmethod
    def _build_merge_prompt(cards_data: List[Dict], merge_style: str) -> str:
        """Build prompt for AI merge"""
        cards_text = ""
        for i, card in enumerate(cards_data, 1):
            cards_text += f"\n卡片 {i}:\n"
            cards_text += f"标题: {card['title']}\n"
            cards_text += f"内容: {card['content']}\n"

        if merge_style == 'comprehensive':
            instruction = """
请将以上卡片整理成一篇连贯的文章。要求：
1. 提取一个合适的标题
2. 消除重复内容
3. 按逻辑组织内容
4. 使用Markdown格式
5. 输出格式：

# 标题

## 大纲
- 要点1
- 要点2
- ...

## 正文内容
[整合后的完整内容]

## 标签
tag1, tag2, tag3
"""
        else:  # outline
            instruction = """
请为以上卡片生成文章大纲。要求：
1. 提取一个合适的标题
2. 组织成清晰的章节结构
3. 使用Markdown格式
"""

        return f"以下是需要整理的卡片：\n{cards_text}\n{instruction}"

    @staticmethod
    def _parse_merge_result(result_text: str) -> Dict[str, str]:
        """Parse AI merge result"""
        lines = result_text.split('\n')

        title = '未命名文章'
        content = result_text
        outline = ''

        # Extract title
        for i, line in enumerate(lines):
            if line.strip().startswith('# '):
                title = line.strip().replace('# ', '').strip()
                content = '\n'.join(lines[i+1:]).strip()
                break

        # Extract outline if present
        if '## 大纲' in content or '## Outline' in content:
            parts = content.split('## ')[-1]
            if '\n\n' in parts:
                outline_parts = parts.split('\n\n')[0]
                outline = outline_parts.strip()
                content = content.replace('## 大纲\n' + outline + '\n\n', '')
                content = content.replace('## Outline\n' + outline + '\n\n', '')

        return {
            'title': title,
            'content': content.strip(),
            'outline': outline
        }

    @staticmethod
    def generate_outline(cards_data: List[Dict]) -> str:
        """Generate outline only"""
        prompt = "为以下卡片生成文章大纲：\n\n"
        for i, card in enumerate(cards_data, 1):
            prompt += f"{i}. {card.get('title', '无标题')}\n{card.get('content', '')}\n\n"

        prompt += "\n请生成清晰的章节结构，使用Markdown列表格式。"

        # This would call AI - simplified version
        return f"# 文章大纲\n\n1. 第一节\n2. 第二节\n3. 第三节"
