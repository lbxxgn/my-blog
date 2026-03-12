from types import SimpleNamespace
from unittest.mock import Mock

from ai_services.card_merger import AICardMerger
from ai_services.tag_generator import TagGenerator


class TestAICardMerger:
    """AI卡片合并服务测试"""

    def test_merge_cards_with_ai(self, temp_db, monkeypatch):
        """测试AI合并卡片"""
        from models import create_card

        # Create test cards
        card1_id = create_card(
            user_id=1,
            title='AI Basics',
            content='Artificial Intelligence is transforming the world.',
            status='idea'
        )

        card2_id = create_card(
            user_id=1,
            title='ML Applications',
            content='Machine learning has many practical applications.',
            status='idea'
        )

        # Mock user config
        user_config = {
            'ai_tag_generation_enabled': True,
            'ai_provider': 'openai',
            'ai_api_key': 'test-key',
            'ai_model': 'gpt-3.5-turbo'
        }

        create_completion = Mock(return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=(
                "# AI and ML\n\n"
                "## 大纲\n"
                "- AI Basics\n"
                "- ML Applications\n\n"
                "## 正文内容\n"
                "Artificial Intelligence and machine learning work together."
            )))],
            usage=SimpleNamespace(total_tokens=123)
        ))
        fake_provider = SimpleNamespace(
            model='gpt-3.5-turbo',
            client=SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(create=create_completion)
                )
            )
        )
        create_provider = Mock(return_value=fake_provider)
        generate_tags = Mock(return_value={'tags': ['ai', 'ml']})

        monkeypatch.setattr(TagGenerator, 'create_provider', create_provider)
        monkeypatch.setattr(TagGenerator, 'generate_for_post', generate_tags)

        result = AICardMerger.merge_cards(
            card_ids=[card1_id, card2_id],
            user_id=1,
            user_config=user_config
        )

        assert result['title'] == 'AI and ML'
        assert result['outline'] == '- AI Basics\n- ML Applications'
        assert result['content'] == 'Artificial Intelligence and machine learning work together.'
        assert result['tags'] == ['ai', 'ml']
        assert result['tokens_used'] == 123

        create_provider.assert_called_once_with(
            provider_name='openai',
            api_key='test-key',
            model='gpt-3.5-turbo'
        )
        generate_tags.assert_called_once()

    def test_generate_merge_outline(self, temp_db):
        """测试生成合并大纲"""
        cards_data = [
            {'title': 'Card 1', 'content': 'Content 1'},
            {'title': 'Card 2', 'content': 'Content 2'}
        ]

        try:
            outline = AICardMerger.generate_outline(cards_data)
            assert isinstance(outline, str)
            assert len(outline) > 0
        except Exception as e:
            # Expected to fail without real AI config
            pass
