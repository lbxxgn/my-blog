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
            console.log('[InfiniteScroll] DOM loaded, window width:', window.innerWidth);
            const container = document.getElementById('posts-container');
            console.log('[InfiniteScroll] posts-container exists:', !!container);

            // 在移动端或者存在posts-container时初始化
            if (window.innerWidth <= 768) {
                console.log('[InfiniteScroll] Mobile detected, initializing...');
                initInfiniteScroll();
            } else if (container && container.children.length > 0) {
                // 桌面端也支持无限滚动（如果容器存在且有内容）
                console.log('[InfiniteScroll] Desktop with posts-container, initializing...');
                initInfiniteScroll();
            } else {
                console.log('[InfiniteScroll] Skipped initialization (no posts-container or empty)');
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
        if (!container) {
            console.error('[InfiniteScroll] posts-container not found!');
            return;
        }

        // 如果已经存在，先删除
        const existing = document.getElementById('loadMoreIndicator');
        if (existing) {
            existing.remove();
        }

        const indicator = document.createElement('div');
        indicator.id = 'loadMoreIndicator';
        indicator.className = 'load-more-indicator';

        // 设置样式，使其可见（用于调试）
        indicator.style.display = 'flex';
        indicator.style.alignItems = 'center';
        indicator.style.justifyContent = 'center';
        indicator.style.marginTop = '20px';
        indicator.style.padding = '20px';
        indicator.style.textAlign = 'center';
        indicator.style.color = '#666';
        indicator.style.fontSize = '14px';
        indicator.style.minHeight = '60px';
        indicator.style.backgroundColor = '#f0f0f0';
        indicator.style.borderRadius = '8px';
        indicator.innerHTML = `
            <span class="spinner" style="display: inline-block; width: 20px; height: 20px; border: 2px solid #f3f3f3; border-top: 2px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite;"></span>
            <span style="margin-left: 10px;">下拉加载更多</span>
        `;

        // 添加到容器后面
        container.appendChild(indicator);

        // 调试：输出位置信息
        setTimeout(() => {
            const rect = indicator.getBoundingClientRect();
            console.log('[InfiniteScroll] Indicator position:', {
                top: rect.top,
                bottom: rect.bottom,
                windowHeight: window.innerHeight,
                isInViewport: rect.top < window.innerHeight && rect.bottom > 0
            });
        }, 100);

        console.log('[InfiniteScroll] Load indicator created and appended');
    }

    function setupObserver() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (!indicator) {
            console.error('[InfiniteScroll] Load indicator not found for observer!');
            return;
        }

        console.log('[InfiniteScroll] Setting up observer...');

        observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                const rect = indicator.getBoundingClientRect();
                console.log('[InfiniteScroll] Observer callback:', {
                    isIntersecting: entry.isIntersecting,
                    isLoading: isLoading,
                    hasMore: hasMore,
                    indicatorTop: rect.top,
                    indicatorBottom: rect.bottom,
                    windowHeight: window.innerHeight,
                    distanceToBottom: rect.top - window.innerHeight
                });

                if (entry.isIntersecting && !isLoading && hasMore) {
                    console.log('[InfiniteScroll] ✅ Triggering loadMorePosts...');
                    loadMorePosts();
                }
            });
        }, {
            rootMargin: '200px'  // 增加到200px，更容易触发
        });

        observer.observe(indicator);
        console.log('[InfiniteScroll] Observer setup complete, now observing indicator with rootMargin=200px');
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

        // 获取加载指示器
        const indicator = document.getElementById('loadMoreIndicator');

        // 如果指示器存在，将新文章插入到指示器之前
        // 否则直接添加到容器末尾
        posts.forEach(post => {
            const card = createPostCard(post);
            if (indicator) {
                container.insertBefore(card, indicator);
            } else {
                container.appendChild(card);
            }
        });

        console.log('[InfiniteScroll] Appended ' + posts.length + ' posts before indicator');
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
                <span class="spinner" style="display: inline-block; width: 20px; height: 20px; border: 2px solid #f3f3f3; border-top: 2px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite;"></span>
                <span style="margin-left: 10px;">加载中...</span>
            `;
        }
    }

    function hideLoadingIndicator() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (indicator) {
            // 保持指示器可见，这样观察器可以继续监控
            // 只有在没有更多内容时才改变文字
            if (hasMore) {
                indicator.innerHTML = `
                    <span style="display: inline-block; width: 20px; height: 20px;"></span>
                    <span style="margin-left: 10px;">下拉加载更多</span>
                `;
            }
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
