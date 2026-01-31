"""
数据模型测试
"""

import pytest
from models import (
    get_user_by_username, get_user_by_id, create_user, update_user, delete_user, get_all_users,
    create_post, get_post_by_id, update_post, delete_post, get_all_posts,
    create_category, get_all_categories, get_category_by_id, update_category, delete_category,
    create_tag, get_all_tags, get_tag_by_id, get_popular_tags,
    create_comment, get_comments_by_post, get_all_comments,
    # Browser extension API functions
    init_api_keys_table, init_card_annotations_table,
    generate_api_key, validate_api_key, create_card, get_cards_by_user,
    create_annotation, get_annotations_by_url
)
from werkzeug.security import generate_password_hash, check_password_hash


class TestUserModels:
    """用户模型测试"""

    def test_create_user(self, temp_db):
        """测试创建用户"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user(
            username='testuser',
            password_hash=password_hash,
            role='author',
            display_name='Test User',
            bio='Test bio'
        )

        assert user_id is not None
        assert user_id > 0

    def test_get_user_by_username(self, temp_db):
        """测试通过用户名获取用户"""
        password_hash = generate_password_hash('TestPassword123!')
        create_user('testuser', password_hash, role='author')

        user = get_user_by_username('testuser')
        assert user is not None
        assert user['username'] == 'testuser'
        assert user['role'] == 'author'

    def test_get_user_by_id(self, temp_db):
        """测试通过ID获取用户"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('testuser', password_hash, role='author')

        user = get_user_by_id(user_id)
        assert user is not None
        assert user['username'] == 'testuser'

    def test_update_user(self, temp_db):
        """测试更新用户"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('testuser', password_hash, role='author')

        update_user(user_id, display_name='Updated Name', bio='Updated bio')

        user = get_user_by_id(user_id)
        assert user['display_name'] == 'Updated Name'
        assert user['bio'] == 'Updated bio'

    def test_delete_user(self, temp_db):
        """测试删除用户"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('testuser', password_hash, role='author')

        result = delete_user(user_id)
        assert result is True

        user = get_user_by_id(user_id)
        assert user is None


class TestPostModels:
    """文章模型测试"""

    def test_create_post(self, temp_db, test_user):
        """测试创建文章"""
        post_id = create_post(
            title='Test Post',
            content='Test content',
            is_published=True,
            category_id=None,
            author_id=test_user['id']
        )

        assert post_id is not None
        assert post_id > 0

    def test_get_post_by_id(self, temp_db, test_post):
        """测试通过ID获取文章"""
        post = get_post_by_id(test_post['id'])
        assert post is not None
        assert post['title'] == 'Test Post'

    def test_update_post(self, temp_db, test_post):
        """测试更新文章"""
        update_post(
            test_post['id'],
            title='Updated Title',
            content='Updated content',
            is_published=True
        )

        post = get_post_by_id(test_post['id'])
        assert post['title'] == 'Updated Title'

    def test_delete_post(self, temp_db, test_post):
        """测试删除文章"""
        delete_post(test_post['id'])

        post = get_post_by_id(test_post['id'])
        assert post is None

    def test_get_all_posts(self, temp_db, test_user):
        """测试获取所有文章"""
        # 创建多篇文章
        create_post('Post 1', 'Content 1', True, None, test_user['id'])
        create_post('Post 2', 'Content 2', True, None, test_user['id'])
        create_post('Post 3', 'Content 3', False, None, test_user['id'])  # 草稿

        posts_data = get_all_posts(include_drafts=False)
        assert len(posts_data['posts']) == 2

        posts_data = get_all_posts(include_drafts=True)
        assert len(posts_data['posts']) == 3


class TestCategoryModels:
    """分类模型测试"""

    def test_create_category(self, temp_db):
        """测试创建分类"""
        category_id = create_category('Technology')
        assert category_id is not None
        assert category_id > 0

    def test_get_all_categories(self, temp_db):
        """测试获取所有分类"""
        create_category('Technology')
        create_category('Lifestyle')

        categories = get_all_categories()
        assert len(categories) == 2

    def test_get_category_by_id(self, temp_db):
        """测试通过ID获取分类"""
        category_id = create_category('Technology')
        category = get_category_by_id(category_id)

        assert category is not None
        assert category['name'] == 'Technology'

    def test_update_category(self, temp_db):
        """测试更新分类"""
        category_id = create_category('Technology')
        update_category(category_id, 'Tech')

        category = get_category_by_id(category_id)
        assert category['name'] == 'Tech'

    def test_delete_category(self, temp_db):
        """测试删除分类"""
        category_id = create_category('Technology')
        delete_category(category_id)

        category = get_category_by_id(category_id)
        assert category is None


class TestTagModels:
    """标签模型测试"""

    def test_create_tag(self, temp_db):
        """测试创建标签"""
        tag_id = create_tag('python')
        assert tag_id is not None
        assert tag_id > 0

    def test_get_all_tags(self, temp_db):
        """测试获取所有标签"""
        create_tag('python')
        create_tag('flask')

        tags = get_all_tags()
        assert len(tags) == 2

    def test_get_tag_by_id(self, temp_db):
        """测试通过ID获取标签"""
        tag_id = create_tag('python')
        tag = get_tag_by_id(tag_id)

        assert tag is not None
        assert tag['name'] == 'python'

    def test_get_popular_tags(self, temp_db, test_post):
        """测试获取热门标签"""
        # 创建标签并关联到文章
        tag1_id = create_tag('python')
        tag2_id = create_tag('flask')
        tag3_id = create_tag('web')

        # 关联标签到测试文章
        from models import set_post_tags
        set_post_tags(test_post['id'], ['python', 'flask', 'web'])

        tags = get_popular_tags(limit=10)
        assert len(tags) == 3


class TestCommentModels:
    """评论模型测试"""

    def test_create_comment(self, temp_db, test_post):
        """测试创建评论"""
        comment_id = create_comment(
            test_post['id'],
            'Test Author',
            'test@example.com',
            'Test comment content'
        )

        assert comment_id is not None
        assert comment_id > 0

    def test_get_comments_by_post(self, temp_db, test_post):
        """测试获取文章评论"""
        create_comment(test_post['id'], 'Author 1', 'test1@example.com', 'Comment 1')
        create_comment(test_post['id'], 'Author 2', 'test2@example.com', 'Comment 2')

        comments = get_comments_by_post(test_post['id'])
        assert len(comments) == 2

    def test_get_all_comments(self, temp_db, test_post):
        """测试获取所有评论"""
        create_comment(test_post['id'], 'Author 1', 'test1@example.com', 'Comment 1')
        create_comment(test_post['id'], 'Author 2', 'test2@example.com', 'Comment 2')

        comments = get_all_comments()
        assert len(comments) == 2


class TestCardModels:
    """卡片模型测试"""

    def test_create_card(self, temp_db):
        """测试创建卡片"""
        import json
        from models import create_card, get_card_by_id

        card_id = create_card(
            user_id=1,
            title='Test Card',
            content='Test content',
            tags=['test', 'idea'],
            status='idea',
            source='web'
        )

        assert card_id is not None
        assert card_id > 0

        card = get_card_by_id(card_id)
        assert card['title'] == 'Test Card'
        assert card['content'] == 'Test content'
        assert json.loads(card['tags']) == ['test', 'idea']
        assert card['status'] == 'idea'
        assert card['source'] == 'web'

    def test_get_cards_by_user(self, temp_db):
        """测试获取用户的所有卡片"""
        from models import create_card, get_cards_by_user

        create_card(user_id=1, title='Card 1', content='Content 1', status='idea')
        create_card(user_id=1, title='Card 2', content='Content 2', status='draft')
        create_card(user_id=2, title='Card 3', content='Content 3', status='idea')

        cards = get_cards_by_user(user_id=1)
        assert len(cards) == 2
        assert all(c['user_id'] == 1 for c in cards)

    def test_update_card_status(self, temp_db):
        """测试更新卡片状态"""
        from models import create_card, update_card_status, get_card_by_id

        card_id = create_card(user_id=1, title='Test', content='Content', status='idea')
        update_card_status(card_id, 'incubating')

        card = get_card_by_id(card_id)
        assert card['status'] == 'incubating'


class TestBrowserExtensionAPI:
    """浏览器插件API测试"""

    def test_init_api_keys_table(self, temp_db):
        """测试初始化API密钥表"""
        init_api_keys_table()
        # Should not raise an error
        assert True

    def test_init_card_annotations_table(self, temp_db):
        """测试初始化标注表"""
        init_card_annotations_table()
        # Should not raise an error
        assert True

    def test_generate_api_key(self, temp_db):
        """测试生成API密钥"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('apikeyuser', password_hash, role='author')

        api_key = generate_api_key(user_id)
        assert api_key is not None
        assert len(api_key) > 20  # API keys should be sufficiently long
        assert isinstance(api_key, str)

    def test_validate_api_key_valid(self, temp_db):
        """测试验证有效的API密钥"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('validateuser', password_hash, role='author')
        api_key = generate_api_key(user_id)

        validated_user_id = validate_api_key(api_key)
        assert validated_user_id == user_id

    def test_validate_api_key_invalid(self, temp_db):
        """测试验证无效的API密钥"""
        validated_user_id = validate_api_key('invalid_api_key_12345')
        assert validated_user_id is None

    def test_validate_api_key_none(self, temp_db):
        """测试验证空API密钥"""
        validated_user_id = validate_api_key(None)
        assert validated_user_id is None

    def test_validate_api_key_empty_string(self, temp_db):
        """测试验证空字符串API密钥"""
        validated_user_id = validate_api_key('')
        assert validated_user_id is None

    def test_create_card(self, temp_db):
        """测试创建知识库卡片"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('carduser', password_hash, role='author')

        card_id = create_card(
            user_id=user_id,
            title='Test Card',
            content='Test content for card',
            status='idea',
            source='web',
            tags=['test', 'knowledge']
        )

        assert card_id is not None
        assert card_id > 0

    def test_create_card_with_defaults(self, temp_db):
        """测试使用默认值创建卡片"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('carduser2', password_hash, role='author')

        card_id = create_card(
            user_id=user_id,
            title='Test Card 2',
            content='Test content'
        )

        assert card_id is not None

    def test_get_cards_by_user(self, temp_db):
        """测试获取用户卡片"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('carduser3', password_hash, role='author')

        # Create multiple cards
        create_card(user_id, 'Card 1', 'Content 1', status='idea')
        create_card(user_id, 'Card 2', 'Content 2', status='draft')
        create_card(user_id, 'Card 3', 'Content 3', status='idea')

        cards = get_cards_by_user(user_id)
        assert len(cards) == 3

    def test_get_cards_by_user_with_status(self, temp_db):
        """测试按状态获取用户卡片"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('carduser4', password_hash, role='author')

        create_card(user_id, 'Card 1', 'Content 1', status='idea')
        create_card(user_id, 'Card 2', 'Content 2', status='draft')
        create_card(user_id, 'Card 3', 'Content 3', status='idea')

        idea_cards = get_cards_by_user(user_id, status='idea')
        draft_cards = get_cards_by_user(user_id, status='draft')

        assert len(idea_cards) == 2
        assert len(draft_cards) == 1

    def test_create_annotation(self, temp_db):
        """测试创建标注"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('annouser', password_hash, role='author')

        annotation_id = create_annotation(
            user_id=user_id,
            source_url='https://example.com/test',
            annotation_text='Selected text',
            xpath='/html/body/p[1]',
            color='yellow',
            note='Test note',
            annotation_type='highlight'
        )

        assert annotation_id is not None
        assert annotation_id > 0

    def test_create_annotation_with_defaults(self, temp_db):
        """测试使用默认值创建标注"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('annouser2', password_hash, role='author')

        annotation_id = create_annotation(
            user_id=user_id,
            source_url='https://example.com/test2',
            annotation_text='Selected text 2',
            xpath='/html/body/p[2]',
            color='yellow',
            note=''
        )

        assert annotation_id is not None

    def test_get_annotations_by_url(self, temp_db):
        """测试获取URL的标注"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('annouser3', password_hash, role='author')

        # Create multiple annotations for same URL
        create_annotation(user_id, 'https://example.com/test', 'Text 1', '/html/p[1]', 'yellow', '')
        create_annotation(user_id, 'https://example.com/test', 'Text 2', '/html/p[2]', 'blue', '')
        create_annotation(user_id, 'https://example.com/other', 'Text 3', '/html/p[3]', 'green', '')

        annotations = get_annotations_by_url(user_id, 'https://example.com/test')
        assert len(annotations) == 2

    def test_get_annotations_by_url_empty(self, temp_db):
        """测试获取不存在的URL的标注"""
        password_hash = generate_password_hash('TestPassword123!')
        user_id = create_user('annouser4', password_hash, role='author')

        annotations = get_annotations_by_url(user_id, 'https://example.com/nonexistent')
        assert len(annotations) == 0
