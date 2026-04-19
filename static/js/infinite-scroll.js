/**
 * 无限滚动加载
 */
(function() {
    'use strict';

    let isLoading = false;
    let hasMore = true;
    let currentPage = 1;
    let observer = null;

    // 常量
    const MOBILE_BREAKPOINT = 768;
    const DEBUG = false;

    function debug(...args) {
        if (DEBUG) console.log('[InfiniteScroll]', ...args);
    }

    document.addEventListener('DOMContentLoaded', function() {
        const container = document.getElementById('posts-container');

        // 只在存在posts-container时初始化
        if (container) {
            initInfiniteScroll();
        }
    });

    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        if (window.innerWidth <= MOBILE_BREAKPOINT && !observer && document.getElementById('posts-container')) {
            initInfiniteScroll();
        }
    });

    function initInfiniteScroll() {
        debug('Initializing...');

        // 隐藏桌面端的加载更多按钮
        const loadMoreBtn = document.getElementById('load-more');
        if (loadMoreBtn) {
            loadMoreBtn.style.display = 'none';
        }

        // 创建加载指示器
        createLoadIndicator();

        // 设置 Intersection Observer
        setupObserver();

        debug('Initialized successfully');
    }

    function buildFeedUrl(page = 1, cursor = null) {
        const currentUrl = new URL(window.location.href);

        // 清除可能存在的旧参数
        currentUrl.searchParams.delete('page');
        currentUrl.searchParams.delete('cursor');

        // 根据分页类型添加参数
        if (cursor) {
            currentUrl.searchParams.set('cursor', cursor);
        } else if (page) {
            currentUrl.searchParams.set('page', page);
        }

        currentUrl.searchParams.set('format', 'json');
        return `${currentUrl.pathname}?${currentUrl.searchParams.toString()}`;
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
        indicator.innerHTML = `
            <span class="spinner"></span>
            <span class="load-more-text">下拉加载更多</span>
        `;

        // 添加到容器后面
        container.appendChild(indicator);

        debug('Load indicator created and appended');
    }

    function setupObserver() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (!indicator) {
            console.error('[InfiniteScroll] Load indicator not found for observer!');
            return;
        }

        debug('Setting up observer...');

        observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                debug('Observer callback:', {
                    isIntersecting: entry.isIntersecting,
                    isLoading: isLoading,
                    hasMore: hasMore
                });

                if (entry.isIntersecting && !isLoading && hasMore) {
                    debug('Triggering loadMorePosts');
                    loadMorePosts();
                }
            });
        }, {
            rootMargin: '200px'
        });

        observer.observe(indicator);
        debug('Observer setup complete');
    }

    async function loadMorePosts() {
        if (isLoading || !hasMore) {
            debug('Skipping load: isLoading=' + isLoading + ', hasMore=' + hasMore);
            return;
        }

        isLoading = true;
        showLoadingIndicator();

        try {
            // 检查是否应该使用游标分页
            const loadMoreBtn = document.getElementById('load-more');
            let url, data;

            if (loadMoreBtn && loadMoreBtn.dataset.cursor) {
                // 游标分页
                debug('Loading posts with cursor:', loadMoreBtn.dataset.cursor);
                url = buildFeedUrl(null, loadMoreBtn.dataset.cursor);
                debug('Fetching:', url);

                const response = await fetch(url);
                data = await response.json();

                if (data.posts && data.posts.length > 0) {
                    appendPosts(data.posts);
                    hasMore = data.has_more;
                    debug('Loaded', data.posts.length, 'posts, hasMore=', hasMore);

                    // 更新下一页的游标
                    if (data.next_cursor) {
                        loadMoreBtn.dataset.cursor = data.next_cursor;
                    } else {
                        loadMoreBtn.disabled = true;
                        loadMoreBtn.textContent = '没有更多了';
                    }
                } else {
                    hasMore = false;
                    loadMoreBtn.disabled = true;
                    loadMoreBtn.textContent = '没有更多了';
                    debug('No more posts');
                }
            } else {
                // 传统OFFSET分页
                debug('Loading page', currentPage + 1);
                currentPage++;
                url = buildFeedUrl(currentPage);
                debug('Fetching:', url);

                const response = await fetch(url);
                data = await response.json();

                if (data.posts && data.posts.length > 0) {
                    appendPosts(data.posts);
                    hasMore = currentPage < data.total_pages;
                    debug('Loaded', data.posts.length, 'posts, hasMore=', hasMore);
                } else {
                    hasMore = false;
                    debug('No more posts');
                }
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

        debug('Appending', posts.length, 'posts');

        // 如果指示器存在，将新文章插入到指示器之前
        // 否则直接添加到容器末尾
        posts.forEach((post, index) => {
            const card = createPostCard(post);

            if (indicator) {
                container.insertBefore(card, indicator);
            } else {
                container.appendChild(card);
            }
        });

        debug('Appended', posts.length, 'posts');
    }

    function createPostCard(post) {
        const article = document.createElement('article');
        article.className = 'post-card';
        const imageUrls = Array.isArray(post.image_urls) ? post.image_urls.slice(0, 9) : extractImageUrls(post.content);
        const imageCount = imageUrls.length;
        const imageLayout = post.mobile_image_layout || getMobileImageLayout(imageCount);

        try {
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
        } catch (error) {
            console.error('[InfiniteScroll] Error creating card for post:', post.id, error);
        }

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

    async function refreshPosts() {
        const container = document.getElementById('posts-container');
        if (!container) {
            return false;
        }

        try {
            if (observer) {
                observer.disconnect();
                observer = null;
            }

            const response = await fetch(buildFeedUrl(1), {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`刷新失败: ${response.status}`);
            }

            const data = await response.json();
            const posts = Array.isArray(data.posts) ? data.posts : [];

            container.innerHTML = '';
            currentPage = 1;
            hasMore = currentPage < (data.total_pages || 1);
            isLoading = false;

            if (posts.length === 0) {
                container.innerHTML = '<div class="empty-state"><p>还没有发布任何文章。</p></div>';
                return true;
            }

            posts.forEach(post => {
                container.appendChild(createPostCard(post));
            });

            if (hasMore) {
                createLoadIndicator();
                setupObserver();
            }

            return true;
        } catch (error) {
            console.error('[InfiniteScroll] Failed to refresh posts:', error);
            return false;
        }
    }

    window.InfiniteScroll = {
        reset: function() {
            currentPage = 1;
            hasMore = true;
            isLoading = false;
        },
        loadMore: loadMorePosts,
        refresh: refreshPosts,
        destroy: function() {
            if (observer) {
                observer.disconnect();
                observer = null;
            }
        }
    };

})();
