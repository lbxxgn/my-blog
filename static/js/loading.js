// Enhanced Skeleton Loading & Image Lazy Loading
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // ============ Image Lazy Loading with Intersection Observer ============
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.getAttribute('data-src');

                if (src) {
                    // Add loading class
                    img.classList.add('loading');

                    // Load image
                    img.src = src;

                    img.onload = () => {
                        img.classList.remove('loading');
                        img.classList.add('loaded');
                    };

                    img.onerror = () => {
                        img.classList.remove('loading');
                        img.classList.add('error');
                    };

                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '100px 0px',  // Load images 100px before they enter viewport
        threshold: 0.01
    });

    // Observe all images with data-src
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });

    // ============ Enhanced Skeleton Screens ============
    const SkeletonLoader = {
        /**
         * Show skeleton cards in a container
         * @param {HTMLElement} container - Container element
         * @param {number} count - Number of skeleton cards to show
         * @param {string} type - Type of skeleton: 'card', 'list', 'detail'
         */
        show(container, count = 3, type = 'card') {
            // Clear existing skeletons first
            this.hide(container);

            const skeletons = [];

            for (let i = 0; i < count; i++) {
                const skeleton = document.createElement('div');
                skeleton.className = `skeleton-wrapper skeleton-${type}`;
                skeleton.setAttribute('data-skeleton', 'true');

                // Stagger animation for each skeleton
                skeleton.style.animationDelay = `${i * 0.1}s`;

                if (type === 'card') {
                    skeleton.innerHTML = `
                        <div class="skeleton skeleton-title"></div>
                        <div class="skeleton skeleton-meta"></div>
                        <div class="skeleton skeleton-excerpt"></div>
                        <div class="skeleton skeleton-excerpt"></div>
                        <div class="skeleton skeleton-excerpt-short"></div>
                    `;
                } else if (type === 'list') {
                    skeleton.innerHTML = `
                        <div class="skeleton skeleton-list-title"></div>
                        <div class="skeleton skeleton-list-meta"></div>
                    `;
                } else if (type === 'detail') {
                    skeleton.innerHTML = `
                        <div class="skeleton skeleton-detail-title"></div>
                        <div class="skeleton skeleton-detail-meta"></div>
                        <div class="skeleton skeleton-detail-content"></div>
                        <div class="skeleton skeleton-detail-content"></div>
                        <div class="skeleton skeleton-detail-content"></div>
                    `;
                }

                container.appendChild(skeleton);
                skeletons.push(skeleton);
            }

            return skeletons;
        },

        /**
         * Hide all skeletons in a container with fade out animation
         * @param {HTMLElement} container - Container element
         */
        hide(container) {
            const skeletons = container.querySelectorAll('[data-skeleton]');
            skeletons.forEach((skeleton, index) => {
                // Stagger fade out
                setTimeout(() => {
                    skeleton.classList.add('skeleton-fade-out');
                    setTimeout(() => {
                        skeleton.remove();
                    }, 300);  // Wait for fade out animation
                }, index * 50);
            });
        },

        /**
         * Show page-level loading spinner
         * @param {boolean} show - Whether to show or hide
         */
        pageLoading(show) {
            let spinner = document.querySelector('.page-loader');

            if (show) {
                if (!spinner) {
                    spinner = document.createElement('div');
                    spinner.className = 'page-loader';
                    spinner.innerHTML = `
                        <div class="spinner"></div>
                        <div class="spinner-text">加载中...</div>
                    `;
                    document.body.appendChild(spinner);
                }
                spinner.style.display = 'block';
            } else if (spinner) {
                spinner.style.display = 'none';
            }
        },

        /**
         * Show inline loading for a specific element
         * @param {HTMLElement} element - Element to show loading in
         */
        inlineLoading(element) {
            element.classList.add('loading-inline');
        },

        /**
         * Hide inline loading
         * @param {HTMLElement} element - Element to hide loading from
         */
        inlineLoaded(element) {
            element.classList.remove('loading-inline');
        }
    };

    // ============ Progressive Content Loading ============
    const ProgressiveLoader = {
        /**
         * Load content progressively with animation
         * @param {HTMLElement} container - Container with content
         */
        animateContent(container) {
            const items = container.querySelectorAll('.post-card, .comment, article');
            items.forEach((item, index) => {
                item.style.opacity = '0';
                item.style.transform = 'translateY(20px)';

                setTimeout(() => {
                    item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                    item.style.opacity = '1';
                    item.style.transform = 'translateY(0)';
                }, index * 100);
            });
        }
    };

    // ============ Export utilities for global use ============
    window.SkeletonLoader = SkeletonLoader;
    window.ProgressiveLoader = ProgressiveLoader;
    window.loadingUtils = {
        showSkeleton: (container, count, type) => SkeletonLoader.show(container, count, type),
        hideSkeleton: (container) => SkeletonLoader.hide(container),
        pageLoading: (show) => SkeletonLoader.pageLoading(show),
        imageObserver: imageObserver,
        animateContent: (container) => ProgressiveLoader.animateContent(container)
    };

    // ============ Auto-initialize for pages with posts container ============
    const postsContainer = document.getElementById('posts-container');
    if (postsContainer && postsContainer.children.length === 0) {
        // Show skeletons if container is empty
        SkeletonLoader.show(postsContainer, 5, 'card');
    }

    // Animate existing content on page load
    if (postsContainer && postsContainer.children.length > 0) {
        ProgressiveLoader.animateContent(postsContainer);
    }
});
