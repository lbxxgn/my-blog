/**
 * 游标分页 - 加载更多功能
 *
 * 功能说明:
 *   - 使用基于时间戳的游标分页（比传统 OFFSET 更高效）
 *   - 点击"加载更多"按钮动态加载文章
 *   - 自动初始化新加载图片的懒加载
 *   - 提供平滑的加载动画效果
 *
 * 技术优势:
 *   - 游标分页对大数据集性能更好
 *   - 避免传统 OFFSET 的深度分页问题
 *   - 支持分类筛选
 *
 * API 端点: /api/posts?cursor={timestamp}&per_page={count}&category_id={id}
 *
 * 依赖: 无（原生 JavaScript + Fetch API）
 */

// Enhanced Load more functionality with cursor-based pagination
document.addEventListener('DOMContentLoaded', function() {
    const loadMoreBtn = document.getElementById('load-more');
    const postsContainer = document.getElementById('posts-container');

    if (!loadMoreBtn || !postsContainer) return;

    // State for cursor-based pagination
    let currentCursor = null;
    let currentPerPage = 20;

    loadMoreBtn.addEventListener('click', async function() {
        const categoryId = this.dataset.category;

        // Disable button and show loading
        const originalText = this.textContent;
        this.disabled = true;
        this.textContent = '加载中...';

        try {
            // Build URL with cursor-based pagination
            let url = `/api/posts?per_page=${currentPerPage}`;
            if (currentCursor) {
                url += `&cursor=${encodeURIComponent(currentCursor)}`;
            }
            if (categoryId) {
                url += `&category_id=${categoryId}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                // Render new posts
                data.posts.forEach(post => {
                    const postCard = createPostCard(post);
                    postsContainer.appendChild(postCard);
                });

                // Update cursor for next page
                currentCursor = data.next_cursor;

                // Update button state
                if (data.has_more) {
                    this.disabled = false;
                    this.textContent = originalText;
                } else {
                    this.remove();
                }

                // Re-initialize lazy loading for new images
                if (window.loadingUtils && window.loadingUtils.imageObserver) {
                    document.querySelectorAll('img[data-src]').forEach(img => {
                        window.loadingUtils.imageObserver.observe(img);
                    });
                }

                // Animate new content
                if (window.ProgressiveLoader) {
                    const newItems = postsContainer.querySelectorAll('.post-card');
                    const startIndex = Math.max(0, newItems.length - data.posts.length);
                    for (let i = startIndex; i < newItems.length; i++) {
                        const item = newItems[i];
                        item.style.opacity = '0';
                        item.style.transform = 'translateY(20px)';

                        setTimeout(() => {
                            item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                            item.style.opacity = '1';
                            item.style.transform = 'translateY(0)';
                        }, (i - startIndex) * 100);
                    }
                }
            } else {
                throw new Error(data.error || '加载失败');
            }
        } catch (error) {
            console.error('Failed to load more posts:', error);
            this.disabled = false;
            this.textContent = '加载失败，重试';
        }
    });

    /**
     * Create a post card element from post data
     * @param {Object} post - Post data object
     * @returns {HTMLElement} Post card element
     */
    function createPostCard(post) {
        const article = document.createElement('article');
        article.className = 'post-card';

        const link = document.createElement('a');
        link.href = `/post/${post.id}`;
        link.className = 'post-card-link';

        const meta = [];
        if (post.category_name) {
            meta.push(`<span class="post-category">${escapeHtml(post.category_name)}</span>`);
            meta.push('<span>·</span>');
        }
        meta.push(`<time datetime="${post.created_at}">${escapeHtml((post.created_at||'').substring(0, 10))}</time>`);

        link.innerHTML = `
            <h2>${escapeHtml(post.title)}</h2>
            <div class="post-meta">
                ${meta.join('')}
            </div>
            <div class="post-excerpt">
                ${escapeHtml((post.content || '').substring(0, 200))}...
            </div>
        `;

        article.appendChild(link);
        return article;
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
