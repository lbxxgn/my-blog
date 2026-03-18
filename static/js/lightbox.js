// 自定义图片灯箱功能
(function() {
    'use strict';

    // 存储所有图片
    let images = [];
    let currentIndex = 0;
    let currentShowingOriginal = false; // 当前是否显示原图

    function notify(message, type = 'success') {
        if (window.showAppToast) {
            window.showAppToast(message, type);
        }
    }

    // 创建灯箱 DOM 结构
    function createLightbox() {
        // 检查是否已存在
        if (document.querySelector('.lightbox-overlay')) {
            return;
        }

        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'lightbox-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-label', '图片预览');

        // 创建容器
        const container = document.createElement('div');
        container.className = 'lightbox-container';

        // 创建图片元素
        const img = document.createElement('img');
        img.className = 'lightbox-img';
        img.alt = '灯箱图片';

        // 创建关闭按钮
        const closeBtn = document.createElement('button');
        closeBtn.className = 'lightbox-close';
        closeBtn.innerHTML = '×';
        closeBtn.setAttribute('aria-label', '关闭');

        // 创建导航按钮
        const prevBtn = document.createElement('button');
        prevBtn.className = 'lightbox-nav lightbox-prev';
        prevBtn.innerHTML = '‹';
        prevBtn.setAttribute('aria-label', '上一张');

        const nextBtn = document.createElement('button');
        nextBtn.className = 'lightbox-nav lightbox-next';
        nextBtn.innerHTML = '›';
        nextBtn.setAttribute('aria-label', '下一张');

        // 创建计数器
        const counter = document.createElement('div');
        counter.className = 'lightbox-counter';

        // 创建说明文本
        const caption = document.createElement('div');
        caption.className = 'lightbox-caption';

        // 创建工具栏（包含查看原图和下载按钮）
        const toolbar = document.createElement('div');
        toolbar.className = 'lightbox-toolbar';

        // 查看原图按钮
        const originalBtn = document.createElement('button');
        originalBtn.className = 'lightbox-original-btn';
        originalBtn.innerHTML = '📷 原图';
        originalBtn.setAttribute('aria-label', '查看原图');

        // 下载按钮
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'lightbox-download-btn';
        downloadBtn.innerHTML = '⬇️ 下载';
        downloadBtn.setAttribute('aria-label', '下载图片');

        toolbar.appendChild(originalBtn);
        toolbar.appendChild(downloadBtn);

        // 创建加载指示器
        const loading = document.createElement('div');
        loading.className = 'lightbox-loading';
        loading.innerHTML = '加载中...';

        // 组装 DOM
        container.appendChild(img);
        container.appendChild(loading);
        overlay.appendChild(container);
        overlay.appendChild(closeBtn);
        overlay.appendChild(prevBtn);
        overlay.appendChild(nextBtn);
        overlay.appendChild(counter);
        overlay.appendChild(caption);
        overlay.appendChild(toolbar);
        document.body.appendChild(overlay);

        // 绑定事件
        bindLightboxEvents(overlay, img, closeBtn, prevBtn, nextBtn, originalBtn, downloadBtn);
    }

    // 绑定灯箱事件
    function bindLightboxEvents(overlay, img, closeBtn, prevBtn, nextBtn, originalBtn, downloadBtn) {
        // 点击遮罩层关闭
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeLightbox();
            }
        });

        // 点击关闭按钮
        closeBtn.addEventListener('click', closeLightbox);

        // 点击导航按钮
        prevBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            showPreviousImage();
        });

        nextBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            showNextImage();
        });

        // 点击查看原图按钮
        if (originalBtn) {
            originalBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleOriginalImage(img, originalBtn);
            });
        }

        // 点击下载按钮
        if (downloadBtn) {
            downloadBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                downloadCurrentImage(img);
            });
        }

        // 键盘导航
        document.addEventListener('keydown', function(e) {
            if (!overlay.classList.contains('active')) {
                return;
            }

            switch(e.key) {
                case 'Escape':
                    closeLightbox();
                    break;
                case 'ArrowLeft':
                    showPreviousImage();
                    break;
                case 'ArrowRight':
                    showNextImage();
                    break;
            }
        });

        // 图片加载完成
        img.addEventListener('load', function() {
            const loading = overlay.querySelector('.lightbox-loading');
            if (loading) {
                loading.style.display = 'none';
            }
            img.classList.add('animate');
            setTimeout(() => img.classList.remove('animate'), 300);
        });

        // 触摸滑动支持
        let touchStartX = 0;
        let touchEndX = 0;

        overlay.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        overlay.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });

        function handleSwipe() {
            const swipeThreshold = 50;
            const diff = touchStartX - touchEndX;

            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    showNextImage();
                } else {
                    showPreviousImage();
                }
            }
        }
    }

    // 收集文章中的所有图片
    function collectImages() {
        images = [];
        const postContent = document.querySelector('.post-content');

        if (!postContent) {
            return;
        }

        const imgElements = postContent.querySelectorAll('img');

        imgElements.forEach(function(img, index) {
            // 跳过极小图片（可能是图标）
            if (img.naturalWidth && img.naturalWidth < 100) {
                return;
            }

            // 跳过已经包装在链接中的图片
            if (img.parentElement && img.parentElement.tagName === 'A') {
                return;
            }

            // 确保有有效的 src
            if (!img.src || img.src.startsWith('data:')) {
                return;
            }

            // 尝试从img元素获取原始URL信息
            const originalUrl = getOriginalImageUrl(img.src);

            images.push({
                src: img.src,
                originalUrl: originalUrl,
                alt: img.alt || `图片 ${index + 1}`,
                element: img
            });

            // 为图片添加索引标记和原始URL
            img.dataset.lightboxIndex = images.length - 1;
            if (originalUrl && originalUrl !== img.src) {
                img.dataset.originalUrl = originalUrl;
            }
        });
    }

    // 打开灯箱
    function openLightbox(index) {
        const overlay = document.querySelector('.lightbox-overlay');
        if (!overlay || !images.length) {
            return;
        }

        currentIndex = index;
        currentShowingOriginal = false; // 重置原图显示状态
        const imageData = images[currentIndex];

        const img = overlay.querySelector('.lightbox-img');
        const loading = overlay.querySelector('.lightbox-loading');
        const counter = overlay.querySelector('.lightbox-counter');
        const caption = overlay.querySelector('.lightbox-caption');
        const prevBtn = overlay.querySelector('.lightbox-prev');
        const nextBtn = overlay.querySelector('.lightbox-next');
        const originalBtn = overlay.querySelector('.lightbox-original-btn');

        // 显示加载指示器
        if (loading) {
            loading.style.display = 'block';
        }

        // 设置图片
        img.src = imageData.src;
        img.alt = imageData.alt;

        // 更新计数器
        updateCounter();

        // 更新说明文本
        if (caption) {
            if (imageData.alt) {
                caption.textContent = imageData.alt;
                caption.classList.add('show');
            } else {
                caption.classList.remove('show');
            }
        }

        // 更新导航按钮状态
        updateNavigationButtons(prevBtn, nextBtn);

        // 重置原图按钮状态
        if (originalBtn) {
            const hasOriginal = getOriginalImageUrl(imageData.src) !== imageData.src;
            if (hasOriginal) {
                originalBtn.style.display = 'block';
                originalBtn.innerHTML = '📷 原图';
                originalBtn.classList.remove('showing-original');
            } else {
                originalBtn.style.display = 'none';
            }
        }

        // 显示灯箱
        overlay.classList.add('active');
        document.body.classList.add('lightbox-open');

        // 防止页面滚动
        document.body.style.overflow = 'hidden';
    }

    // 关闭灯箱
    function closeLightbox() {
        const overlay = document.querySelector('.lightbox-overlay');
        if (!overlay) {
            return;
        }

        overlay.classList.remove('active');
        document.body.classList.remove('lightbox-open');
        document.body.style.overflow = '';

        // 清空图片源以防止下次打开时闪烁
        setTimeout(() => {
            const img = overlay.querySelector('.lightbox-img');
            if (img) {
                img.src = '';
            }
        }, 300);
    }

    // 显示上一张图片
    function showPreviousImage() {
        if (currentIndex > 0) {
            openLightbox(currentIndex - 1);
        } else {
            // 循环到最后一张
            openLightbox(images.length - 1);
        }
    }

    // 显示下一张图片
    function showNextImage() {
        if (currentIndex < images.length - 1) {
            openLightbox(currentIndex + 1);
        } else {
            // 循环到第一张
            openLightbox(0);
        }
    }

    // 更新计数器
    function updateCounter() {
        const counter = document.querySelector('.lightbox-counter');
        if (counter && images.length > 1) {
            counter.textContent = `${currentIndex + 1} / ${images.length}`;
        } else if (counter) {
            counter.textContent = '';
        }
    }

    // 更新导航按钮状态
    function updateNavigationButtons(prevBtn, nextBtn) {
        if (images.length <= 1) {
            prevBtn.style.display = 'none';
            nextBtn.style.display = 'none';
        } else {
            prevBtn.style.display = 'flex';
            nextBtn.style.display = 'flex';
        }
    }

    // 从优化图片URL提取原始图片URL
    function getOriginalImageUrl(optimizedUrl) {
        if (!optimizedUrl) return null;

        // 匹配优化图片URL格式：/static/uploads/optimized/{hash}_{size}.webp
        const optimizedMatch = optimizedUrl.match(/\/static\/uploads\/optimized\/([a-f0-9]+)_\w+\.webp/);
        if (optimizedMatch) {
            const hash = optimizedMatch[1];
            // 尝试查找原图，检查多个可能的路径和扩展名
            const possibleOriginalUrls = [
                // 尝试标准的images目录
                `/static/uploads/images/${hash}`,
                // 尝试直接在uploads目录下
                `/static/uploads/${hash}`,
                // 如果优化URL不在optimized目录，可能是原图
                optimizedUrl.replace('/optimized/', '/images/').replace(/_\w+\.webp$/, '')
            ];

            // 返回第一个可能的URL（实际存在性会在点击时验证）
            return possibleOriginalUrls[0];
        }

        // 如果不是优化图片URL，直接返回
        return optimizedUrl;
    }

    // 切换显示原图
    async function toggleOriginalImage(img, btn) {
        const imageData = images[currentIndex];
        if (!imageData) return;

        const loading = document.querySelector('.lightbox-loading');
        if (loading) {
            loading.style.display = 'block';
        }

        if (!currentShowingOriginal) {
            // 尝试通过API获取原图URL
            const urlMatch = imageData.src.match(/\/static\/uploads\/optimized\/([a-f0-9]+)_\w+\.webp/);

            if (urlMatch) {
                const hash = urlMatch[1];

                try {
                    // 调用API获取原图URL
                    const response = await fetch(`/api/image/original-url?hash=${hash}`);
                    const data = await response.json();

                    if (data.success && data.exists && data.original_url) {
                        // 加载原图
                        const tempImg = new Image();
                        tempImg.onload = function() {
                            img.src = data.original_url;
                            currentShowingOriginal = true;
                            btn.innerHTML = '🖼️ 优化版';
                            btn.classList.add('showing-original');
                            if (loading) loading.style.display = 'none';
                            console.log(`已切换到原图: ${data.original_url}`);
                        };
                        tempImg.onerror = function() {
                            notify('原图存在但无法加载，请先保存当前优化图', 'error');
                            if (loading) loading.style.display = 'none';
                        };
                        tempImg.src = data.original_url;
                    } else {
                        // 原图不存在
                        notify('原图文件不存在，请使用当前优化图或重新上传', 'error');
                        if (loading) loading.style.display = 'none';
                    }
                } catch (error) {
                    console.error('获取原图URL失败:', error);
                    notify('无法获取原图信息，请稍后再试', 'error');
                    if (loading) loading.style.display = 'none';
                }
            } else {
                // 无法从URL中提取hash
                notify('无法识别图片格式，请先下载当前图片', 'error');
                if (loading) loading.style.display = 'none';
            }
        } else {
            // 切换回优化版本
            img.src = imageData.src;
            currentShowingOriginal = false;
            btn.innerHTML = '📷 原图';
            btn.classList.remove('showing-original');
            if (loading) loading.style.display = 'none';
        }
    }

    // 下载当前图片
    function downloadCurrentImage(img) {
        if (!img || !img.src) return;

        // 生成文件名
        let filename = `image_${currentIndex + 1}_${Date.now()}`;

        // 尝试从URL中提取文件扩展名
        const urlMatch = img.src.match(/\.([a-z]+)(?:\?|$)/);
        if (urlMatch) {
            const ext = urlMatch[1];
            filename += `.${ext}`;
        } else {
            filename += '.jpg'; // 默认扩展名
        }

        // 使用fetch下载图片以避免CORS问题
        fetch(img.src)
            .then(response => response.blob())
            .then(blob => {
                const blobUrl = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = blobUrl;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(blobUrl);

                console.log(`下载图片: ${img.src} -> ${filename}`);
            })
            .catch(error => {
                console.error('下载失败:', error);

                // 降级方案：直接使用当前图片URL
                const link = document.createElement('a');
                link.href = img.src;
                link.download = filename;
                link.target = '_blank'; // 在新标签页中打开
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                notify('下载已开始，如打开新标签页请右键保存图片');
            });
    }

    // 为文章图片添加点击事件
    function addImageClickHandlers() {
        const postContent = document.querySelector('.post-content');
        if (!postContent) {
            return;
        }

        postContent.addEventListener('click', function(e) {
            const img = e.target.closest('img');
            if (!img) {
                return;
            }

            // 获取图片索引
            const index = parseInt(img.dataset.lightboxIndex);
            if (!isNaN(index)) {
                e.preventDefault();
                openLightbox(index);
            }
        });
    }

    // 初始化
    function init() {
        // 等待 DOM 加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initialize);
        } else {
            initialize();
        }
    }

    function initialize() {
        // 创建灯箱 DOM
        createLightbox();

        // 收集图片
        collectImages();

        // 添加点击事件
        addImageClickHandlers();

        console.log(`图片灯箱已初始化，找到 ${images.length} 张图片`);
    }

    // 启动
    init();
})();
