// Load more functionality
document.addEventListener('DOMContentLoaded', function() {
    const loadMoreBtn = document.getElementById('load-more');
    const postsContainer = document.getElementById('posts-container');

    if (!loadMoreBtn || !postsContainer) return;

    loadMoreBtn.addEventListener('click', async function() {
        const page = this.dataset.page;
        const categoryId = this.dataset.category;

        // Disable button and show loading
        this.disabled = true;
        this.textContent = '加载中...';

        try {
            // Build URL with parameters
            let url = `/api/posts?page=${page}`;
            if (categoryId) {
                url += `&category_id=${categoryId}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.posts_html) {
                // Append new posts
                postsContainer.insertAdjacentHTML('beforeend', data.posts_html);

                // Update button state
                if (data.has_more) {
                    this.dataset.page = parseInt(page) + 1;
                    this.disabled = false;
                    this.textContent = '加载更多';
                } else {
                    this.remove();
                }

                // Re-initialize lazy loading for new images
                if (window.loadingUtils && window.loadingUtils.imageObserver) {
                    document.querySelectorAll('img[data-src]').forEach(img => {
                        window.loadingUtils.imageObserver.observe(img);
                    });
                }
            }
        } catch (error) {
            console.error('Failed to load more posts:', error);
            this.disabled = false;
            this.textContent = '加载失败，重试';
        }
    });
});
