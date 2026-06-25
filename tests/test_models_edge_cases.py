"""
模型边界测试
测试用户、文章、分类、标签、评论等模型在边界条件下的行为
"""

import pytest
from werkzeug.security import generate_password_hash, check_password_hash


class TestUserModelEdgeCases:
    """用户模型边界测试"""

    def test_create_user_with_empty_username(self, init_database):
        """测试空用户名：模型层允许插入空字符串，返回有效用户 ID"""
        from backend.models.models import create_user, get_user_by_id
        password_hash = generate_password_hash('test123')
        user_id = create_user(username='', password_hash=password_hash)
        # 空字符串满足 NOT NULL，因此创建成功
        assert user_id is not None
        assert get_user_by_id(user_id) is not None

    def test_create_user_with_very_long_username(self, init_database):
        """测试超长用户名"""
        from backend.models.models import create_user
        long_username = 'a' * 200
        password_hash = generate_password_hash('test123')
        user_id = create_user(username=long_username, password_hash=password_hash)
        assert user_id is not None

    def test_create_user_with_special_chars_in_email(self, init_database):
        """测试特殊字符邮箱：users 表无 email 字段，验证用户名可包含特殊字符"""
        from backend.models.models import create_user
        password_hash = generate_password_hash('test123')
        user_id = create_user(
            username='test+label@example.co.uk',
            password_hash=password_hash
        )
        assert user_id is not None

    def test_verify_password_with_wrong_password(self, init_database):
        """测试错误密码验证"""
        from backend.models.models import create_user, get_user_by_id
        password_hash = generate_password_hash('correctpassword')
        user_id = create_user(username='testuser', password_hash=password_hash)
        user = get_user_by_id(user_id)
        assert user is not None
        assert check_password_hash(user['password_hash'], 'wrongpassword') is False

    def test_get_user_by_nonexistent_id(self, init_database):
        """测试获取不存在的用户"""
        from backend.models.models import get_user_by_id
        user = get_user_by_id(99999)
        assert user is None


class TestPostModelEdgeCases:
    """文章模型边界测试"""

    def test_create_post_with_empty_title(self, init_database):
        """测试空标题：模型层允许插入空标题"""
        from backend.models.models import create_post, get_post_by_id
        post_id = create_post(title='', content='Content', author_id=1)
        assert post_id is not None
        assert get_post_by_id(post_id) is not None

    def test_create_post_with_very_long_content(self, init_database):
        """测试超长内容"""
        from backend.models.models import create_post
        long_content = 'a' * 100000
        post_id = create_post(title='Test', content=long_content, author_id=1)
        assert post_id is not None

    def test_create_post_with_html_content(self, init_database):
        """测试HTML内容"""
        from backend.models.models import create_post
        html_content = '<p>Hello</p><script>alert(1)</script>'
        post_id = create_post(title='Test', content=html_content, author_id=1)
        assert post_id is not None

    def test_update_nonexistent_post(self, init_database):
        """测试更新不存在的文章：update_post 对不存在 ID 返回 True 但不影响行"""
        from backend.models.models import update_post, get_post_by_id
        result = update_post(post_id=99999, title='New Title', content='New Content', is_published=True)
        assert result is True
        assert get_post_by_id(99999) is None

    def test_delete_nonexistent_post(self, init_database):
        """测试删除不存在的文章：delete_post 不抛异常"""
        from backend.models.models import delete_post
        # 函数无返回值，主要验证不抛异常
        delete_post(post_id=99999)

    def test_get_all_posts_with_pagination(self, init_database):
        """测试分页获取文章"""
        from backend.models.models import create_post, get_all_posts
        # 创建多篇文章
        for i in range(15):
            create_post(title=f'Post {i}', content=f'Content {i}', author_id=1, is_published=True)

        result = get_all_posts(include_drafts=True, page=1, per_page=10)
        assert len(result['posts']) == 10

        result_page2 = get_all_posts(include_drafts=True, page=2, per_page=10)
        assert len(result_page2['posts']) == 5


class TestCategoryTagModelEdgeCases:
    """分类和标签模型边界测试"""

    def test_create_category_with_duplicate_name(self, init_database):
        """测试重复分类名：第二次创建返回 None"""
        from backend.models.models import create_category
        first_id = create_category(name='Technology', slug='tech')
        assert first_id is not None
        # 尝试创建同名分类
        second_id = create_category(name='Technology', slug='tech-2')
        assert second_id is None

    def test_create_tag_with_empty_name(self, init_database):
        """测试空标签名：模型层允许插入空字符串"""
        from backend.models.models import create_tag, get_tag_by_id
        tag_id = create_tag(name='')
        assert tag_id is not None
        assert get_tag_by_id(tag_id) is not None

    def test_get_popular_tags(self, init_database):
        """测试获取热门标签"""
        from backend.models.models import create_tag, create_post, set_post_tags, get_popular_tags
        tag1 = create_tag(name='Python')
        tag2 = create_tag(name='JavaScript')
        assert tag1 is not None
        assert tag2 is not None

        # 创建文章并关联标签
        for i in range(5):
            post_id = create_post(title=f'Post {i}', content='Content', author_id=1, is_published=True)
            set_post_tags(post_id, ['Python'])

        popular = get_popular_tags(limit=10)
        assert isinstance(popular, list)
        assert len(popular) >= 1
        assert any(tag['name'] == 'Python' for tag in popular)


class TestCommentModelEdgeCases:
    """评论模型边界测试"""

    def test_create_comment_with_empty_content(self, init_database):
        """测试空评论内容：模型层允许插入空字符串"""
        from backend.models.models import create_comment, get_comments_by_post
        from backend.models.models import create_post
        post_id = create_post(title='Post', content='Content', author_id=1, is_published=True)
        comment_id = create_comment(post_id=post_id, author_name='Test', author_email='test@test.com', content='')
        assert comment_id is not None
        comments = get_comments_by_post(post_id, include_hidden=True)
        assert any(c['id'] == comment_id for c in comments)

    def test_create_comment_with_long_content(self, init_database):
        """测试超长评论内容"""
        from backend.models.models import create_comment, create_post, get_comments_by_post
        post_id = create_post(title='Post', content='Content', author_id=1, is_published=True)
        long_content = 'a' * 5000
        comment_id = create_comment(post_id=post_id, author_name='Test', content=long_content)
        comments = get_comments_by_post(post_id, include_hidden=True)
        assert any(c['id'] == comment_id for c in comments)

    def test_create_comment_with_html(self, init_database):
        """测试包含HTML的评论"""
        from backend.models.models import create_comment, create_post, get_comments_by_post
        post_id = create_post(title='Post', content='Content', author_id=1, is_published=True)
        html_content = '<p>Nice post!</p><script>alert(1)</script>'
        comment_id = create_comment(post_id=post_id, author_name='Test', content=html_content)
        comments = get_comments_by_post(post_id, include_hidden=True)
        assert any(c['id'] == comment_id for c in comments)

    def test_get_comments_by_nonexistent_post(self, init_database):
        """测试获取不存在文章的评论"""
        from backend.models.models import get_comments_by_post
        comments = get_comments_by_post(post_id=99999)
        assert comments == []

    def test_toggle_comment_visibility(self, init_database):
        """测试切换评论可见性"""
        from backend.models.models import create_comment, create_post, get_comments_by_post
        from backend.models.models import update_comment_visibility
        post_id = create_post(title='Post', content='Content', author_id=1, is_published=True)
        comment_id = create_comment(post_id=post_id, author_name='Test', content='Test comment')

        # 切换为不可见
        update_comment_visibility(comment_id, is_visible=False)
        visible_comments = get_comments_by_post(post_id, include_hidden=False)
        assert all(c['id'] != comment_id for c in visible_comments)

        # 切换为可见
        update_comment_visibility(comment_id, is_visible=True)
        visible_comments = get_comments_by_post(post_id, include_hidden=False)
        assert any(c['id'] == comment_id for c in visible_comments)

    def test_delete_nonexistent_comment(self, init_database):
        """测试删除不存在的评论：delete_comment 不抛异常"""
        from backend.models.models import delete_comment
        delete_comment(comment_id=99999)
