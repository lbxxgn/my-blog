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
        if (window.innerWidth <= 768) {
            initInfiniteScroll();
        }
    });

    function initInfiniteScroll() {
        // 隐藏桌面端的加载更多按钮
        const loadMoreBtn = document.getElementById('load-more');
        if (loadMoreBtn) {
            loadMoreBtn.style.display = 'none';
        }

        // 创建加载指示器
        createLoadIndicator();

        // 设置 Intersection Observer
        setupObserver();
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
        if (isLoading || !hasMore) return;

        isLoading = true;
        showLoadingIndicator();

        try {
            currentPage++;

            // 获取当前分类（如果有）
            const loadMoreBtn = document.getElementById('load-more');
            const categoryId = loadMoreBtn?.getAttribute('data-category') || '';

            // 构建 URL
            let url = `/?page=${currentPage}&format=json`;
            if (categoryId) {
                url += `&category=${categoryId}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.posts && data.posts.length > 0) {
                appendPosts(data.posts);
                hasMore = currentPage < data.total_pages;
            } else {
                hasMore = false;
            }
        } catch (error) {
            console.error('Failed to load more posts:', error);
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

        // 提取第一张图片作为封面
        const coverImage = extractCoverImage(post.content);

        article.innerHTML = `
            <a href="/post/${post.id}" class="post-card-link">
                ${coverImage ? `
                    <div class="post-card-image">
                        <img src="${coverImage}" alt="" loading="lazy">
                    </div>
                ` : `
                    <div class="post-card-image">
                        <span class="post-card-image-placeholder">📝</span>
                    </div>
                `}
                <div class="post-card-content">
                    <h2>${escapeHtml(post.title)}</h2>
                    <div class="post-excerpt">${escapeHtml(post.excerpt || truncateContent(post.content, 100))}</div>
                    <div class="post-meta">
                        ${post.category_name ? `<span class="post-category">${escapeHtml(post.category_name)}</span>` : ''}
                        ${post.author_display_name ? `<span>👤 ${escapeHtml(post.author_display_name)}</span>` : ''}
                        <time>${formatDate(post.created_at)}</time>
                    </div>
                </div>
                <div class="post-card-actions">
                    <button type="button" class="post-action-btn">
                        <span class="post-action-icon">❤️</span>
                        <span>${post.like_count || 0}</span>
                    </button>
                    <button type="button" class="post-action-btn">
                        <span class="post-action-icon">💬</span>
                        <span>${post.comment_count || 0}</span>
                    </button>
                    <button type="button" class="post-action-btn">
                        <span class="post-action-icon">🔗</span>
                    </button>
                </div>
            </a>
        `;

        return article;
    }

    function extractCoverImage(content) {
        // 从内容中提取第一张图片
        if (!content) return null;
        const imgMatch = content.match(/<img[^>]+src="([^"]+)"/);
        return imgMatch ? imgMatch[1] : null;
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
