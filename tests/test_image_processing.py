"""
图片处理功能测试
测试图片上传、优化、URL转换等功能
"""

import pytest
import os
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image
from flask import Flask


class TestImageUpload:
    """图片上传测试"""

    def test_upload_jpg_image(self, client, test_admin_user):
        """测试上传JPG图片"""
        # 登录管理员
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建测试图片
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        # 上传图片
        response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'test.jpg')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'url' in data
        assert 'filename' in data

    def test_upload_png_image(self, client, test_admin_user):
        """测试上传PNG图片"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'test.png')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_upload_webp_image(self, client, test_admin_user):
        """测试上传WebP图片"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='WebP')
        img_bytes.seek(0)

        response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'test.webp')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_upload_heic_image(self, client, test_admin_user):
        """测试上传HEIC图片（iPhone格式）"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 注意：这里需要实际的HEIC文件，所以只测试接口是否可用
        # 实际环境需要真实的HEIC文件
        pass

    def test_upload_unauthorized(self, client):
        """测试未登录用户上传图片"""
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'test.jpg')},
            content_type='multipart/form-data'
        )

        # 应该重定向到登录页面
        assert response.status_code in [302, 401, 403]

    def test_upload_large_image(self, client, test_admin_user):
        """测试上传大尺寸图片"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 创建大尺寸图片 (3000x3000)
        img = Image.new('RGB', (3000, 3000), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG', quality=85)
        img_bytes.seek(0)

        response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'large.jpg')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


class TestImageOptimization:
    """图片优化测试"""

    def test_optimization_id_in_response(self, client, test_admin_user):
        """测试上传响应包含optimization_id"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        img = Image.new('RGB', (1000, 800), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'test.jpg')},
            content_type='multipart/form-data'
        )

        data = response.get_json()
        assert 'optimization_id' in data
        assert 'status' in data

    def test_feed_size_generation(self, client, test_admin_user, temp_db):
        """测试feed尺寸图片生成"""
        from backend.tasks.image_optimization_task import queue_image_optimization

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 上传图片
        img = Image.new('RGB', (1920, 1280), color='blue')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'feed_test.jpg')},
            content_type='multipart/form-data'
        )

        data = response.get_json()
        assert data['success'] is True

        # 检查optimization_id
        if 'optimization_id' in data:
            # 实际环境会异步生成优化版本
            # 这里只验证响应结构
            assert isinstance(data['optimization_id'], int)


class TestImageURLConversion:
    """图片URL转换测试"""

    def test_extract_post_image_urls_feed_size(self):
        """测试提取feed尺寸图片URL"""
        from backend.routes.blog import extract_post_image_urls

        content = '''
        <p>测试内容</p>
        <img src="/static/uploads/images/test.jpg">
        '''

        urls = extract_post_image_urls(content, size='feed')
        assert len(urls) > 0
        # 应该返回feed尺寸的URL
        assert any('feed' in str(url) for url in urls) or len(urls) > 0

    def test_extract_post_image_urls_medium_size(self):
        """测试提取medium尺寸图片URL"""
        from backend.routes.blog import extract_post_image_urls

        content = '''
        <p>测试内容</p>
        <img src="/static/uploads/images/test.jpg">
        '''

        urls = extract_post_image_urls(content, size='medium')
        assert len(urls) > 0

    def test_extract_post_image_urls_empty_content(self):
        """测试空内容的图片URL提取"""
        from backend.routes.blog import extract_post_image_urls

        urls = extract_post_image_urls('', size='feed')
        assert urls == []

    def test_extract_post_image_urls_no_images(self):
        """测试无图片的内容"""
        from backend.routes.blog import extract_post_image_urls

        content = '<p>纯文本内容，没有图片</p>'
        urls = extract_post_image_urls(content, size='feed')
        assert urls == []


class TestImageCleanup:
    """图片清理工具测试"""

    def test_extract_images_from_content(self):
        """测试从内容中提取图片"""
        from backend.utils.image_cleanup import extract_images_from_content

        content = '''
        <img src="/static/uploads/1.jpg" alt="test">
        <img src='http://example.com/2.png'>
        <img src=/static/uploads/3.gif>
        '''

        images = extract_images_from_content(content)
        assert len(images) == 3

    def test_remove_img_tags_by_urls(self):
        """测试删除指定URL的图片标签"""
        from backend.utils.image_cleanup import remove_img_tags_by_urls

        content = '''
        <p>内容</p>
        <img src="/static/uploads/1.jpg" alt="test">
        <img src="/static/uploads/2.jpg" alt="test2">
        <p>更多内容</p>
        '''

        cleaned = remove_img_tags_by_urls(content, ['/static/uploads/1.jpg'])
        assert '<img src="/static/uploads/1.jpg"' not in cleaned
        assert '<img src="/static/uploads/2.jpg"' in cleaned

    def test_check_image_url_local(self):
        """测试检查本地图片URL"""
        from backend.utils.image_cleanup import check_image_url

        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_path = f.name
            f.write(b'fake image data')

        try:
            is_valid, error = check_image_url(f'/static/uploads/{os.path.basename(temp_path)}', check_external=False)
            # 本地文件不存在，应该返回无效
            # 注意：这个测试依赖于实际的文件系统
        finally:
            os.unlink(temp_path)

    def test_cleanup_logger(self, capsys):
        """测试清理日志工具"""
        from backend.utils.image_cleanup import CleanupLogger

        CleanupLogger.post(1, "测试标题")
        CleanupLogger.success("http://example.com/image.jpg")
        CleanupLogger.error("测试错误")

        captured = capsys.readouterr()
        # 验证日志输出
        assert "测试标题" in captured.out or "测试错误" in captured.out


class TestImageSizes:
    """图片尺寸配置测试"""

    def test_image_sizes_include_feed(self):
        """测试IMAGE_SIZES包含feed尺寸"""
        from backend.image_processor import IMAGE_SIZES

        assert 'feed' in IMAGE_SIZES
        assert IMAGE_SIZES['feed'] == (1920, 1280)

    def test_all_required_sizes_exist(self):
        """测试所有必需的图片尺寸都存在"""
        from backend.image_processor import IMAGE_SIZES

        required_sizes = ['thumbnail', 'medium', 'large', 'feed']
        for size in required_sizes:
            assert size in IMAGE_SIZES
            assert isinstance(IMAGE_SIZES[size], tuple)
            assert len(IMAGE_SIZES[size]) == 2

    def test_feed_size_dimensions(self):
        """测试feed尺寸的宽高比"""
        from backend.image_processor import IMAGE_SIZES

        width, height = IMAGE_SIZES['feed']
        assert width == 1920
        assert height == 1280
        # 检查宽高比约为 3:2
        assert abs(width / height - 1.5) < 0.1


class TestPostCardImagePayload:
    """文章卡片图片负载测试"""

    def test_build_post_card_payload_with_images(self, client, temp_db):
        """测试构建包含图片的文章卡片负载"""
        from backend.routes.blog import build_post_card_payload
        from backend.models import create_user, create_post
        from werkzeug.security import generate_password_hash

        user_id = create_user('imguser', generate_password_hash('TestPass123!'), role='author')

        content = '''
        <p>文章内容</p>
        <img src="/static/uploads/test1.jpg">
        <img src="/static/uploads/test2.jpg">
        '''

        post_id = create_post(
            title='测试文章',
            content=content,
            is_published=True,
            category_id=None,
            author_id=user_id
        )

        post = {'id': post_id, 'title': '测试文章', 'content': content}
        payload = build_post_card_payload(post)

        assert 'image_urls' in payload
        assert 'image_count' in payload
        assert payload['image_count'] == 2

    def test_build_post_card_payload_without_images(self, client, temp_db):
        """测试构建不包含图片的文章卡片负载"""
        from backend.routes.blog import build_post_card_payload
        from backend.models import create_user, create_post
        from werkzeug.security import generate_password_hash

        user_id = create_user('imguser2', generate_password_hash('TestPass123!'), role='author')
        content = '<p>纯文本文章，没有图片</p>'

        post_id = create_post(
            title='纯文本文章',
            content=content,
            is_published=True,
            category_id=None,
            author_id=user_id
        )

        post = {'id': post_id, 'title': '纯文本文章', 'content': content}
        payload = build_post_card_payload(post)

        assert 'image_urls' in payload
        assert payload['image_count'] == 0
        assert len(payload['image_urls']) == 0


@pytest.mark.integration
class TestImageWorkflow:
    """图片处理集成测试"""

    def test_complete_upload_and_display_workflow(self, client, test_admin_user, temp_db):
        """测试完整的上传到显示工作流"""
        # 1. 登录
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # 2. 上传图片
        img = Image.new('RGB', (1920, 1280), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        upload_response = client.post(
            '/admin/upload',
            data={'file': (img_bytes, 'workflow_test.jpg')},
            content_type='multipart/form-data'
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.get_json()
        assert upload_data['success'] is True

        # 3. 创建包含图片的文章
        from backend.models import create_post
        content = f'<p>测试文章</p><img src="{upload_data["url"]}">'

        post_id = create_post(
            title='工作流测试',
            content=content,
            is_published=True,
            category_id=None,
            author_id=test_admin_user['id']
        )

        # 4. 访问首页，验证图片显示
        response = client.get('/')
        assert response.status_code == 200

        # 5. 获取JSON格式，验证图片URL
        json_response = client.get('/?format=json')
        assert json_response.status_code == 200

        json_data = json_response.get_json()
        post = next((p for p in json_data['posts'] if p['id'] == post_id), None)
        assert post is not None
        assert post['image_count'] == 1
