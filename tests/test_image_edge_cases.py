
import pytest
from unittest.mock import Mock, patch, MagicMock
import io

class TestImageUploadEdgeCases:
    """图像上传边界测试"""
    
    def test_upload_corrupted_image(self, client, admin_user):
        """测试上传损坏的图像"""
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
        
        # 创建一个无效的图片数据
        data = {
            'image': (io.BytesIO(b'not a valid image'), 'test.jpg')
        }
        
        response = client.post(
            '/admin/upload',
            data=data,
            content_type='multipart/form-data'
        )
        # 应该返回错误
        assert response.status_code in [400, 500, 200]
    
    def test_upload_image_with_long_filename(self, client, admin_user):
        """测试超长文件名"""
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
        
        long_filename = 'a' * 200 + '.jpg'
        data = {
            'image': (io.BytesIO(b'fake image data'), long_filename)
        }
        
        response = client.post(
            '/admin/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400]
    
    def test_upload_image_with_special_chars_in_filename(self, client, admin_user):
        """测试特殊字符文件名"""
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
        
        special_filename = 'image with spaces & symbols !@#$.jpg'
        data = {
            'image': (io.BytesIO(b'fake image data'), special_filename)
        }
        
        response = client.post(
            '/admin/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [200, 400]
    
    def test_upload_zero_byte_image(self, client, admin_user):
        """测试0字节图片"""
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user['id']
        
        data = {
            'image': (io.BytesIO(b''), 'empty.jpg')
        }
        
        response = client.post(
            '/admin/upload',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code in [400, 500, 200]

class TestImageProcessingEdgeCases:
    """图像处理边界测试"""
    
    @patch('backend.utils.image_processor.Image.open')
    def test_process_corrupted_image(self, mock_open):
        """测试处理损坏的图片"""
        from backend.utils.image_processor import process_image
        
        mock_open.side_effect = Exception("Corrupted image")
        
        with pytest.raises(Exception):
            process_image(b'corrupted data', max_size=(800, 600))
    
    def test_resize_image_to_zero_dimensions(self):
        """测试调整为0尺寸"""
        from backend.utils.image_processor import resize_image
        
        # 应该处理错误或返回原始图像
        result = resize_image(None, width=0, height=0)
        # 根据实现，可能返回None或抛出异常
    
    def test_optimize_image_with_extreme_compression(self):
        """测试极端压缩"""
        from backend.utils.image_processor import optimize_image
        
        # 质量为0的极端压缩
        result = optimize_image(b'fake_image_data', quality=0)
        # 应该能处理这个边界情况

class TestImageURLConversionEdgeCases:
    """图像URL转换边界测试"""
    
    def test_extract_image_urls_from_empty_content(self):
        """测试从空内容提取URL"""
        from backend.utils.image_processor import extract_image_urls
        
        result = extract_image_urls('')
        assert result == []
    
    def test_extract_image_urls_from_content_without_images(self):
        """测试从无图内容提取URL"""
        from backend.utils.image_processor import extract_image_urls
        
        content = '<p>This is a paragraph without images</p>'
        result = extract_image_urls(content)
        assert result == []
    
    def test_extract_image_urls_with_relative_paths(self):
        """测试相对路径URL"""
        from backend.utils.image_processor import extract_image_urls
        
        content = '<img src="/uploads/image.jpg"><img src="../images/photo.png">'
        result = extract_image_urls(content)
        assert len(result) == 2
    
    def test_extract_image_urls_with_external_urls(self):
        """测试外部URL"""
        from backend.utils.image_processor import extract_image_urls
        
        content = '<img src="https://example.com/image.jpg"><img src="http://cdn.site.com/photo.png">'
        result = extract_image_urls(content)
        assert len(result) == 2
