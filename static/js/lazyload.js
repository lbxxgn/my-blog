/**
 * 图片懒加载和响应式图片
 *
 * 功能：
 * 1. 图片懒加载（Intersection Observer）
 * 2. 响应式图片加载（根据设备尺寸）
 * 3. 自动使用WebP格式（如果浏览器支持）
 * 4. 占位符显示
 */

class LazyLoadImage {
    constructor() {
        this.init();
    }

    init() {
        // 检查浏览器支持
        this.supportsIntersectionObserver = 'IntersectionObserver' in window;
        this.supportsWebP = this.checkWebPSupport();

        // 如果支持 Intersection Observer，创建观察器
        if (this.supportsIntersectionObserver) {
            this.observer = new IntersectionObserver(this.onIntersection.bind(this), {
                rootMargin: '50px 0px',
                threshold: 0.01
            });
        }

        // 初始化所有懒加载图片
        this.initImages();
    }

    /**
     * 检查浏览器是否支持WebP
     */
    checkWebPSupport() {
        const canvas = document.createElement('canvas');
        if (canvas.getContext && canvas.getContext('2d')) {
            return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
        }
        return false;
    }

    /**
     * 初始化所有懒加载图片
     */
    initImages() {
        // 查找所有带有 data-src 属性的图片
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => this.setupImage(img));

        // 观察这些图片
        if (this.observer) {
            images.forEach(img => this.observer.observe(img));
        } else {
            // 不支持 Intersection Observer，直接加载所有图片
            images.forEach(img => this.loadImage(img));
        }
    }

    /**
     * 设置图片占位符
     */
    setupImage(img) {
        const src = img.getAttribute('data-src');
        const placeholder = img.getAttribute('data-placeholder');

        // 设置占位符
        if (placeholder && !img.src) {
            img.src = placeholder;
        } else {
            // 使用默认占位符
            img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3Crect width='1' height='1' fill='%23e5e7eb'/%3E%3C/svg%3E";
        }

        // 添加加载类
        img.classList.add('lazy-loading');
    }

    /**
     * Intersection Observer 回调
     */
    onIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                this.loadImage(img);
                this.observer.unobserve(img);
            }
        });
    }

    /**
     * 加载图片
     */
    loadImage(img) {
        const src = img.getAttribute('data-src');
        const srcset = img.getAttribute('data-srcset');

        if (!src) return;

        // 移除加载类，添加加载中类
        img.classList.remove('lazy-loading');
        img.classList.add('lazy-load-in-progress');

        // 创建新图片对象来预加载
        const tempImg = new Image();

        tempImg.onload = () => {
            img.src = src;
            if (srcset) {
                img.srcset = srcset;
            }
            img.classList.remove('lazy-load-in-progress');
            img.classList.add('lazy-loaded');
        };

        tempImg.onerror = () => {
            img.classList.remove('lazy-load-in-progress');
            img.classList.add('lazy-load-error');
            console.error(`Failed to load image: ${src}`);
        };

        // 加载图片
        tempImg.src = src;
    }

    /**
     * 处理响应式图片
     */
    setupResponsiveImages() {
        const images = document.querySelectorAll('img[data-sizes]');
        images.forEach(img => {
            this.makeResponsive(img);
        });
    }

    /**
     * 使图片响应式
     */
    makeResponsive(img) {
        const sizes = img.getAttribute('data-sizes');
        if (!sizes) return;

        try {
            const sizesMap = JSON.parse(sizes);
            const width = this.getElementWidth(img);

            // 根据容器宽度选择合适的图片
            let selectedSize = 'original';
            if (width < 600) {
                selectedSize = 'thumbnail';
            } else if (width < 1200) {
                selectedSize = 'medium';
            } else {
                selectedSize = 'large';
            }

            // 如果对应尺寸的URL存在，替换src
            if (sizesMap[selectedSize]) {
                img.dataset.src = sizesMap[selectedSize];
            }
        } catch (e) {
            console.error('Error parsing data-sizes:', e);
        }
    }

    /**
     * 获取元素宽度
     */
    getElementWidth(element) {
        return element.parentElement ? element.parentElement.offsetWidth : window.innerWidth;
    }
}

// 创建全局实例
const lazyLoadImage = new LazyLoadImage();

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    lazyLoadImage.initImages();
    lazyLoadImage.setupResponsiveImages();

    // 监听窗口大小变化，更新响应式图片
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            lazyLoadImage.setupResponsiveImages();
        }, 300);
    });
});

// 导出实例供外部使用
window.lazyLoadImage = lazyLoadImage;

// 为动态添加的图片提供懒加载
function observeNewImages() {
    lazyLoadImage.initImages();
}

/**
 * 为文章内容中的图片添加懒加载
 */
function setupContentImages() {
    // 查找文章内容区域
    const contentArea = document.querySelector('.post-content, .article-content, .content, #post-content');
    if (!contentArea) return;

    // 为所有图片添加 data-src 属性
    const images = contentArea.querySelectorAll('img');
    images.forEach(img => {
        if (!img.hasAttribute('data-src')) {
            img.setAttribute('data-src', img.src);
            img.classList.add('lazy-loading');
        }
    });

    // 初始化懒加载
    lazyLoadImage.initImages();
}

// 导出函数
window.setupContentImages = setupContentImages;
window.observeNewImages = observeNewImages;
