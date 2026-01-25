// Image lightbox functionality
document.addEventListener('DOMContentLoaded', function() {
    // 为文章内容中的所有图片添加灯箱效果
    const images = document.querySelectorAll('.post-content img');

    images.forEach(function(img, index) {
        // 跳过表情符号和极小图片（可能是图标）
        if (img.naturalWidth < 100 || img.naturalHeight < 100) {
            return;
        }

        // 确保图片有有效的src
        if (!img.src || img.src.startsWith('data:')) {
            return;
        }

        // 创建包装链接（如果还没有）
        if (!img.parentElement || img.parentElement.tagName !== 'A') {
            const link = document.createElement('a');
            link.href = img.src;
            link.setAttribute('data-lightbox', 'post-images');
            link.setAttribute('data-title', img.alt || `图片 ${index + 1}`);
            link.setAttribute('data-alt', img.alt || '');

            // 将图片包装在链接中
            img.parentNode.insertBefore(link, img);
            link.appendChild(img);

            // 设置链接样式
            link.style.display = 'inline-block';
            link.style.position = 'relative';
            link.style.lineHeight = '0';
        }
    });

    // 移动端优化：点击图片直接打开灯箱
    if ('ontouchstart' in window) {
        const imageLinks = document.querySelectorAll('.post-content a[data-lightbox]');
        imageLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                // 让Lightbox处理
                return true;
            });
        });
    }

    console.log('Image lightbox initialized for', images.length, 'images');
});
