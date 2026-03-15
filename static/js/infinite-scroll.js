/**
 * 无限滚动加载
 */
(function() {
    'use strict';

    let isLoading = false;
    let hasMore = true;
    let currentPage = 1;
    let observer = null;

    document.addEventListener('DOMContentLoaded', function() {
        // 延迟初始化，确保页面完全加载
        setTimeout(function() {
            if (window.innerWidth <= 768) {
                initInfiniteScroll();
            }
        }, 100);
    });

    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768 && !observer) {
            initInfiniteScroll();
        }
    });

    function initInfiniteScroll() {
        console.log('[InfiniteScroll] Initializing...');

        // 隐藏桌面端的加载更多按钮
        const loadMoreBtn = document.getElementById('load-more');
        if (loadMoreBtn) {
            loadMoreBtn.style.display = 'none';
            console.log('[InfiniteScroll] Hidden load-more button');
        }

        // 创建加载指示器
        createLoadIndicator();

        // 设置 Intersection Observer
        setupObserver();

        console.log('[InfiniteScroll] Initialized successfully');
    }

    function createLoadIndicator() {
        const container = document.getElementById('posts-container');
        if (!container) return;

        const indicator = document.createElement('div');
        indicator.id = 'loadMoreIndicator';
        indicator.className = 'load-more-indicator';
        indicator.style.display = 'none';
        indicator.innerHTML = `
            <span class="spinner"></span>
            <span>加载中...</span>
        `;
        container.parentNode.appendChild(indicator);
    }

    function setupObserver() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (!indicator) return;

        observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting && !isLoading && hasMore) {
                    loadMorePosts();
                }
            });
        }, {
            rootMargin: '100px'
        });

        observer.observe(indicator);
    }

    async function loadMorePosts() {
        if (isLoading || !hasMore) {
            console.log('[InfiniteScroll] Skipping load: isLoading=' + isLoading + ', hasMore=' + hasMore);
            return;
        }

        console.log('[InfiniteScroll] Loading page ' + (currentPage + 1));
        isLoading = true;
        showLoadingIndicator();

        try {
            currentPage++;

            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('page', currentPage);
            currentUrl.searchParams.set('format', 'json');

            const url = `${currentUrl.pathname}?${currentUrl.searchParams.toString()}`;
            console.log('[InfiniteScroll] Fetching: ' + url);

            const response = await fetch(url);
            const data = await response.json();

            console.log('[InfiniteScroll] Response:', data);

            if (data.posts && data.posts.length > 0) {
                appendPosts(data.posts);
                hasMore = currentPage < data.total_pages;
                console.log('[InfiniteScroll] Loaded ' + data.posts.length + ' posts, hasMore=' + hasMore);
            } else {
                hasMore = false;
                console.log('[InfiniteScroll] No more posts');
            }
        } catch (error) {
            console.error('[InfiniteScroll] Failed to load more posts:', error);
            currentPage--; // 回退页码
        } finally {
            isLoading = false;
            hideLoadingIndicator();

            if (!hasMore) {
                showNoMoreIndicator();
            }
        }
    }

    function appendPosts(posts) {
        const container = document.getElementById('posts-container');
        if (!container) return;

        posts.forEach(post => {
            const card = createPostCard(post);
            container.appendChild(card);
        });
    }

    function createPostCard(post) {
        const article = document.createElement('article');
        article.className = 'post-card';
        const imageUrls = Array.isArray(post.image_urls) ? post.image_urls.slice(0, 9) : extractImageUrls(post.content);
        const imageCount = imageUrls.length;
        const imageLayout = post.mobile_image_layout || getMobileImageLayout(imageCount);

        article.innerHTML = `
            <a href="/post/${post.id}" class="post-card-link">
                <div class="post-card-content">
                    <h2>${escapeHtml(post.title)}</h2>
                    <div class="post-meta">
                        ${post.category_name ? `<span class="post-category">${escapeHtml(post.category_name)}</span>` : ''}
                        ${post.author_display_name ? `<span>👤 ${escapeHtml(post.author_display_name)}</span>` : ''}
                        <time>${formatDate(post.created_at)}</time>
                    </div>
                    <div class="post-excerpt">${escapeHtml(post.excerpt || truncateContent(post.content, 100))}</div>
                </div>
                ${renderPostMedia(imageUrls, imageCount, imageLayout)}
            </a>
        `;

        return article;
    }

    function renderPostMedia(imageUrls, imageCount, imageLayout) {
        if (!imageUrls || imageUrls.length === 0) {
            return '';
        }

        const items = imageUrls.map(url => `
            <div class="post-card-media-item">
                <img src="${escapeHtml(url)}" alt="" loading="lazy">
            </div>
        `).join('');

        return `
            <div class="post-card-media post-card-media--${imageLayout} post-card-media--count-${imageCount}">
                ${items}
            </div>
        `;
    }

    function extractImageUrls(content) {
        if (!content) return [];
        return Array.from(content.matchAll(/<img[^>]+src="([^"]+)"/g)).map(match => match[1]).slice(0, 9);
    }

    function getMobileImageLayout(imageCount) {
        if (imageCount <= 1) return 'single';
        if (imageCount <= 4) return 'grid-4';
        if (imageCount <= 6) return 'grid-6';
        return 'grid-9';
    }

    function truncateContent(content, maxLength) {
        if (!content) return '';
        // 移除 HTML 标签
        const text = content.replace(/<[^>]+>/g, '');
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;

        // 1小时内
        if (diff < 60 * 60 * 1000) {
            const mins = Math.floor(diff / (60 * 1000));
            return `${Math.max(1, mins)}分钟前`;
        }

        // 1天内
        if (diff < 24 * 60 * 60 * 1000) {
            const hours = Math.floor(diff / (60 * 60 * 1000));
            return `${hours}小时前`;
        }

        // 1周内
        if (diff < 7 * 24 * 60 * 60 * 1000) {
            const days = Math.floor(diff / (24 * 60 * 60 * 1000));
            return `${days}天前`;
        }

        // 显示日期
        if (typeof dateStr === 'string') {
            return dateStr.substring(0, 10);
        }
        return date.toISOString().substring(0, 10);
    }

    function showLoadingIndicator() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (indicator) {
            indicator.style.display = 'flex';
            indicator.innerHTML = `
                <span class="spinner"></span>
                <span>加载中...</span>
            `;
        }
    }

    function hideLoadingIndicator() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (indicator && hasMore) {
            indicator.style.display = 'none';
        }
    }

    function showNoMoreIndicator() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (indicator) {
            indicator.innerHTML = '<span>没有更多了</span>';
            indicator.style.display = 'flex';
        }
    }

    window.InfiniteScroll = {
        reset: function() {
            currentPage = 1;
            hasMore = true;
            isLoading = false;
        },
        loadMore: loadMorePosts
    };

})();
