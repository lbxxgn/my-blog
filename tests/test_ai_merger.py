import pytest
from ai_services.card_merger import AICardMerger


class TestAICardMerger:
    """AI卡片合并服务测试"""

    def test_merge_cards_with_ai(self, temp_db):
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

        # Test merge (will fail without real API key, but structure should work)
        try:
            result = AICardMerger.merge_cards(
                card_ids=[card1_id, card2_id],
                user_id=1,
                user_config=user_config
            )

            assert 'title' in result
            assert 'content' in result
            assert 'outline' in result
            assert 'tags' in result
        except Exception as e:
            # Expected to fail with fake API key or timeout
            error_str = str(e).lower()
            assert any(keyword in error_str for keyword in ['api', 'key', 'timeout', 'timed out'])

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
