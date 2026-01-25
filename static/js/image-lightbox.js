// Image lightbox functionality
document.addEventListener('DOMContentLoaded', function() {
    // 为文章内容中的所有图片添加灯箱效果
    const images = document.querySelectorAll('.post-content img');

    images.forEach(function(img, index) {
        // 确保图片已加载
        if (!img.complete) {
            return;
        }

        // 跳过极小图片（可能是图标）
        if (img.naturalWidth && img.naturalWidth < 50) {
            return;
        }

        // 确保图片有有效的src
        if (!img.src || img.src.startsWith('data:')) {
            return;
        }

        // 检查是否已经被包装
        if (img.parentElement && img.parentElement.tagName === 'A') {
            // 已经包装过了，跳过
            return;
        }

        // 创建包装链接
        const link = document.createElement('a');
        link.href = img.src;
        link.setAttribute('data-lightbox', 'post-images');
        link.setAttribute('data-title', img.alt || `图片 ${index + 1}`);
        link.setAttribute('data-alt', img.alt || '');

        // 设置链接样式以保持图片正常显示
        link.style.display = 'inline-block';
        link.style.position = 'relative';
        link.style.lineHeight = '0';

        // 将图片包装在链接中
        img.parentNode.insertBefore(link, img);
        link.appendChild(img);
    });

    console.log('Image lightbox initialized for', images.length, 'images');
});
