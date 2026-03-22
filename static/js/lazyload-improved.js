/**
 * 改进版图片懒加载和响应式图片
 *
 * 功能增强：
 * 1. 更好的错误处理和重试机制
 * 2. 支持渐入动画
 * 3. 优化的Intersection Observer配置
 * 4. 响应式图片加载优化
 * 5. 动态添加图片的自动监听
 * 6. 性能优化：减少DOM操作和重排
 */

class LazyLoadImage {
    constructor() {
        this.init();
    }

    init() {
        // 检查浏览器支持
        this.supportsIntersectionObserver = 'IntersectionObserver' in window;
        this.supportsWebP = this.checkWebPSupport();
        this.imageCache = new Map();
        this.resizeTimer = null;

        // 配置参数
        this.options = {
            rootMargin: '100px 0px', // 提前100px加载
            threshold: 0.01,
            animationDuration: 300, // 图片加载动画时长
            maxRetries: 2 // 加载失败重试次数
        };

        // 如果支持 Intersection Observer，创建观察器
        if (this.supportsIntersectionObserver) {
            this.observer = new IntersectionObserver(
                this.onIntersection.bind(this),
                this.options
            );
        }

        // 初始化所有懒加载图片
        this.initImages();

        // 设置响应式图片监听
        this.setupResponsiveImages();

        // 添加窗口大小变化监听
        window.addEventListener('resize', this.onResize.bind(this));
    }

    /**
     * 检查浏览器是否支持WebP格式
     * @returns {boolean} 是否支持WebP
     */
    checkWebPSupport() {
        try {
            const canvas = document.createElement('canvas');
            if (canvas.getContext && canvas.getContext('2d')) {
                return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
            }
        } catch (e) {
            console.warn('WebP support check failed:', e);
        }
        return false;
    }

    /**
     * 初始化页面上所有已有的懒加载图片
     */
    initImages() {
        const images = document.querySelectorAll('img[data-src]:not(.lazy-processed)');
        images.forEach(img => this.setupImage(img));

        if (this.supportsIntersectionObserver) {
            images.forEach(img => this.observer.observe(img));
        } else {
            // 降级处理：不支持IntersectionObserver时直接加载
            images.forEach(img => this.loadImage(img));
        }
    }

    /**
     * 设置单张图片的懒加载配置
     * @param {HTMLImageElement} img 图片元素
     */
    setupImage(img) {
        if (img.classList.contains('lazy-processed')) return;

        const src = img.getAttribute('data-src');
        const placeholder = img.getAttribute('data-placeholder');
        const alt = img.getAttribute('alt') || '';

        // 设置占位符
        if (placeholder && !img.src) {
            img.src = placeholder;
        } else {
            // 使用SVG占位符
            img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3Crect width='1' height='1' fill='%23f3f4f6'/%3E%3C/svg%3E";
        }

        // 添加样式类
        img.classList.add('lazy-loading', 'lazy-processed');
        img.setAttribute('alt', alt);

        // 保存原始属性
        img.dataset.originalAlt = alt;
    }

    /**
     * Intersection Observer 回调函数
     * @param {IntersectionObserverEntry[]} entries 观察到的元素
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
     * @param {HTMLImageElement} img 图片元素
     * @param {number} retryCount 重试次数
     */
    loadImage(img, retryCount = 0) {
        if (img.classList.contains('lazy-loaded')) return;

        const src = img.getAttribute('data-src');
        const srcset = img.getAttribute('data-srcset');
        const sizes = img.getAttribute('data-sizes');

        if (!src) {
            console.warn('No data-src attribute found for image', img);
            return;
        }

        // 标记为加载中
        img.classList.remove('lazy-loading');
        img.classList.add('lazy-load-in-progress');

        // 处理响应式图片
        if (sizes && srcset) {
            this.makeResponsive(img, sizes);
        }

        // 创建临时图片对象进行加载
        const tempImg = new Image();

        // 加载成功
        tempImg.onload = () => {
            // 添加渐入动画
            img.style.opacity = '0';
            img.style.transition = `opacity ${this.options.animationDuration}ms ease-in-out`;

            // 设置最终图片源
            img.src = src;
            if (srcset) {
                img.srcset = srcset;
                if (sizes) {
                    img.sizes = sizes;
                }
            }

            // 完成加载
            img.classList.remove('lazy-load-in-progress');
            img.classList.add('lazy-loaded');

            // 显示图片
            requestAnimationFrame(() => {
                img.style.opacity = '1';
            });

            // 触发自定义事件
            img.dispatchEvent(new CustomEvent('lazyload:loaded', {
                detail: { src: src }
            }));
        };

        // 加载失败
        tempImg.onerror = () => {
            if (retryCount < this.options.maxRetries) {
                // 重试加载
                setTimeout(() => {
                    this.loadImage(img, retryCount + 1);
                }, 1000 * (retryCount + 1));
            } else {
                // 重试失败，显示错误状态
                img.classList.remove('lazy-load-in-progress');
                img.classList.add('lazy-load-error');
                img.src = this.getErrorPlaceholder();

                console.error(`Failed to load image after ${retryCount + 1} attempts: ${src}`);

                // 触发自定义错误事件
                img.dispatchEvent(new CustomEvent('lazyload:error', {
                    detail: { src: src, retries: retryCount + 1 }
                }));
            }
        };

        // 设置跨域（如果需要）
        if (img.crossOrigin) {
            tempImg.crossOrigin = img.crossOrigin;
        }

        tempImg.src = src;
        this.imageCache.set(src, tempImg);
    }

    /**
     * 处理响应式图片
     * @param {HTMLImageElement} img 图片元素
     * @param {string} sizesJson 尺寸配置JSON字符串
     */
    makeResponsive(img, sizesJson) {
        try {
            const sizesMap = JSON.parse(sizesJson);
            const width = this.getElementWidth(img);
            let selectedSize = 'original';

            // 根据设备宽度选择合适的图片尺寸
            if (width < 600) {
                selectedSize = 'thumbnail';
            } else if (width < 1200) {
                selectedSize = 'medium';
            } else if (width < 1920) {
                selectedSize = 'large';
            }

            // 如果支持WebP，尝试使用WebP格式
            if (this.supportsWebP && sizesMap[`${selectedSize}_webp`]) {
                img.setAttribute('data-src', sizesMap[`${selectedSize}_webp`]);
            } else if (sizesMap[selectedSize]) {
                img.setAttribute('data-src', sizesMap[selectedSize]);
            }

        } catch (e) {
            console.error('Error parsing data-sizes:', e);
        }
    }

    /**
     * 获取元素的实际宽度
     * @param {HTMLElement} element 目标元素
     * @returns {number} 元素宽度
     */
    getElementWidth(element) {
        if (!element) return window.innerWidth;

        // 如果元素已经被移除，使用窗口宽度
        if (!document.contains(element)) {
            return window.innerWidth;
        }

        // 尝试获取元素的实际宽度
        const rect = element.getBoundingClientRect();
        return rect.width || element.offsetWidth || element.clientWidth || window.innerWidth;
    }

    /**
     * 窗口大小变化处理
     */
    onResize() {
        clearTimeout(this.resizeTimer);
        this.resizeTimer = setTimeout(() => {
            // 重新初始化响应式图片
            this.setupResponsiveImages();
        }, 300);
    }

    /**
     * 设置所有响应式图片
     */
    setupResponsiveImages() {
        const images = document.querySelectorAll('img[data-sizes]:not(.lazy-responsive)');
        images.forEach(img => {
            img.classList.add('lazy-responsive');
            this.makeResponsive(img, img.getAttribute('data-sizes'));
        });
    }

    /**
     * 获取错误占位符图片
     * @returns {string} 错误占位符SVG
     */
    getErrorPlaceholder() {
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300'%3E%3Crect width='400' height='300' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dominant-baseline='middle' fill='%239ca3af' font-family='sans-serif' font-size='16'%3E图片加载失败%3C/text%3E%3C/svg%3E";
    }

    /**
     * 手动加载新添加的图片
     * @param {HTMLImageElement|string} selector 图片元素或选择器
     */
    observeNewImages(selector) {
        let images = [];

        if (typeof selector === 'string') {
            images = document.querySelectorAll(`${selector}:not(.lazy-processed)`);
        } else if (selector instanceof HTMLElement) {
            images = [selector];
        } else if (selector && typeof selector.forEach === 'function') {
            images = selector;
        }

        images.forEach(img => this.setupImage(img));

        if (this.supportsIntersectionObserver) {
            images.forEach(img => this.observer.observe(img));
        } else {
            images.forEach(img => this.loadImage(img));
        }
    }

    /**
     * 销毁实例，清理资源
     */
    destroy() {
        if (this.supportsIntersectionObserver) {
            this.observer.disconnect();
        }

        window.removeEventListener('resize', this.onResize.bind(this));
        this.imageCache.clear();
    }
}

// 全局实例化和导出
const lazyLoadImage = new LazyLoadImage();

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    lazyLoadImage.initImages();
    lazyLoadImage.setupResponsiveImages();
});

// 导出到全局作用域
window.lazyLoadImage = lazyLoadImage;
window.setupContentImages = (selector = '.post-content img') => {
    lazyLoadImage.observeNewImages(selector);
};
window.observeNewImages = (selector = 'img[data-src]') => {
    lazyLoadImage.observeNewImages(selector);
};

// 支持动态加载的内容
if (typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // 检查新添加的元素中的图片
                        const images = node.querySelectorAll ?
                            node.querySelectorAll('img[data-src]:not(.lazy-processed)') :
                            [];
                        images.forEach(img => lazyLoadImage.setupImage(img));

                        if (lazyLoadImage.supportsIntersectionObserver) {
                            images.forEach(img => lazyLoadImage.observer.observe(img));
                        } else {
                            images.forEach(img => lazyLoadImage.loadImage(img));
                        }
                    }
                });
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}