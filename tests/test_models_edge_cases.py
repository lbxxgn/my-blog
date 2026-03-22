
import pytest
from unittest.mock import Mock, patch, MagicMock
import sqlite3

class TestUserModelEdgeCases:
    """用户模型边界测试"""
    
    def test_create_user_with_empty_username(self, init_database):
        """测试空用户名"""
        from backend.models.models import User
        with pytest.raises(ValueError):
            User.create(username='', password='test123', email='test@test.com')
    
    def test_create_user_with_very_long_username(self, init_database):
        """测试超长用户名"""
        from backend.models.models import User
        long_username = 'a' * 200
        user = User.create(username=long_username, password='test123', email='test@test.com')
        assert user is not None
    
    def test_create_user_with_special_chars_in_email(self, init_database):
        """测试特殊字符邮箱"""
        from backend.models.models import User
        user = User.create(
            username='testuser',
            password='test123',
            email='test+label@example.co.uk'
        )
        assert user is not None
    
    def test_verify_password_with_wrong_password(self, init_database):
        """测试错误密码验证"""
        from backend.models.models import User
        user = User.create(username='testuser', password='correctpassword', email='test@test.com')
        assert user.verify_password('wrongpassword') is False
    
    def test_get_user_by_nonexistent_id(self, init_database):
        """测试获取不存在的用户"""
        from backend.models.models import User
        user = User.get_by_id(99999)
        assert user is None

class TestPostModelEdgeCases:
    """文章模型边界测试"""
    
    def test_create_post_with_empty_title(self, init_database):
        """测试空标题"""
        from backend.models.models import Post
        with pytest.raises(ValueError):
            Post.create(title='', content='Content', author_id=1)
    
    def test_create_post_with_very_long_content(self, init_database):
        """测试超长内容"""
        from backend.models.models import Post
        long_content = 'a' * 100000
        post = Post.create(title='Test', content=long_content, author_id=1)
        assert post is not None
    
    def test_create_post_with_html_content(self, init_database):
        """测试HTML内容"""
        from backend.models.models import Post
        html_content = '<p>Hello</p><script>alert(1)</script>'
        post = Post.create(title='Test', content=html_content, author_id=1)
        assert post is not None
    
    def test_update_nonexistent_post(self, init_database):
        """测试更新不存在的文章"""
        from backend.models.models import Post
        result = Post.update(post_id=99999, title='New Title')
        assert result is False
    
    def test_delete_nonexistent_post(self, init_database):
        """测试删除不存在的文章"""
        from backend.models.models import Post
        result = Post.delete(post_id=99999)
        assert result is False
    
    def test_get_all_posts_with_pagination(self, init_database):
        """测试分页获取文章"""
        from backend.models.models import Post
        # 创建多篇文章
        for i in range(15):
            Post.create(title=f'Post {i}', content=f'Content {i}', author_id=1)
        
        posts = Post.get_all(limit=10, offset=0)
        assert len(posts) == 10
        
        posts_page2 = Post.get_all(limit=10, offset=10)
        assert len(posts_page2) == 5

class TestCategoryTagModelEdgeCases:
    """分类和标签模型边界测试"""
    
    def test_create_category_with_duplicate_name(self, init_database):
        """测试重复分类名"""
        from backend.models.models import Category
        Category.create(name='Technology', slug='tech')
        # 尝试创建同名分类
        with pytest.raises(Exception):
            Category.create(name='Technology', slug='tech-2')
    
    def test_create_tag_with_empty_name(self, init_database):
        """测试空标签名"""
        from backend.models.models import Tag
        with pytest.raises(ValueError):
            Tag.create(name='')
    
    def test_get_popular_tags(self, init_database):
        """测试获取热门标签"""
        from backend.models.models import Tag, Post
        # 创建标签和文章
        tag1 = Tag.create(name='Python')
        tag2 = Tag.create(name='JavaScript')
        
        # 创建文章并关联标签
        for i in range(5):
            post = Post.create(title=f'Post {i}', content='Content', author_id=1)
            # 关联标签 (这里需要根据实际模型 API 调整)
        
        popular = Tag.get_popular(limit=10)
        assert isinstance(popular, list)

class TestCommentModelEdgeCases:
    """评论模型边界测试"""
    
    def test_create_comment_with_empty_content(self, init_database):
        """测试空评论内容"""
        from backend.models.models import Comment
        with pytest.raises(ValueError):
            Comment.create(post_id=1, author_name='Test', content='')
    
    def test_create_comment_with_long_content(self, init_database):
        """测试超长评论内容"""
        from backend.models.models import Comment
        long_content = 'a' * 5000
        comment = Comment.create(post_id=1, author_name='Test', content=long_content)
        assert comment is not None
    
    def test_create_comment_with_html(self, init_database):
        """测试包含HTML的评论"""
        from backend.models.models import Comment
        html_content = '<p>Nice post!</p><script>alert(1)</script>'
        comment = Comment.create(post_id=1, author_name='Test', content=html_content)
        assert comment is not None
    
    def test_get_comments_by_nonexistent_post(self, init_database):
        """测试获取不存在文章的评论"""
        from backend.models.models import Comment
        comments = Comment.get_by_post(post_id=99999)
        assert comments == []
    
    def test_toggle_comment_visibility(self, init_database):
        """测试切换评论可见性"""
        from backend.models.models import Comment
        comment = Comment.create(post_id=1, author_name='Test', content='Test comment')
        
        # 切换为不可见
        result = Comment.toggle_visibility(comment.id, visible=False)
        assert result is True
        
        # 切换为可见
        result = Comment.toggle_visibility(comment.id, visible=True)
        assert result is True
    
    def test_delete_nonexistent_comment(self, init_database):
        """测试删除不存在的评论"""
        from backend.models.models import Comment
        result = Comment.delete(comment_id=99999)
        assert result is False
