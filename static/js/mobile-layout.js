/**
 * 微博式移动端布局控制
 * 处理底部导航、页面切换等功能
 */
(function() {
    'use strict';

    // 当前激活的页面
    let currentPage = 'home';
    let currentMyPostsTab = 'published';

    // 初始化
    document.addEventListener('DOMContentLoaded', function() {
        initBottomNavigation();
        initDoubleTapToTop();
        initMobileLayout();
        initMyPostsTabs();
    });

    /**
     * 初始化底部导航
     */
    function initBottomNavigation() {
        const navItems = document.querySelectorAll('.nav-item[data-page]');

        navItems.forEach(item => {
            item.addEventListener('click', function(e) {
                const page = this.getAttribute('data-page');

                if (page === 'publish') {
                    e.preventDefault();
                    if (typeof window.openMobileEditor === 'function') {
                        window.openMobileEditor();
                    }
                    return;
                }

                // 如果点击的是首页按钮，且当前不在首页 URL，跳转到首页
                if (page === 'home' && window.location.pathname !== '/') {
                    // 让默认链接行为生效，跳转到首页
                    return;
                }

                // 阻止默认行为，使用 JavaScript 切换页面
                e.preventDefault();

                if (page !== currentPage) {
                    setActiveNavItem(page);
                    switchPage(page);
                }
            });
        });
    }

    /**
     * 设置激活的导航项
     */
    function setActiveNavItem(page) {
        document.querySelectorAll('.nav-item[data-page]').forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-page') === page) {
                item.classList.add('active');
            }
        });
        currentPage = page;
    }

    /**
     * 切换页面
     */
    function switchPage(page) {
        // 只在移动端执行页面切换
        if (window.innerWidth > 768) {
            return;
        }

        // 隐藏所有页面
        document.querySelectorAll('.mobile-page').forEach(p => {
            p.style.display = 'none';
        });

        // 显示目标页面
        const targetPage = document.querySelector(`.mobile-page[data-page="${page}"]`);
        if (targetPage) {
            targetPage.style.display = 'block';
        }

        if (page === 'my-posts') {
            loadMyPosts(currentMyPostsTab);
        }
    }

    /**
     * 双击导航项返回顶部
     */
    function initDoubleTapToTop() {
        let lastTap = 0;
        const homeNav = document.querySelector('.nav-item[data-page="home"]');

        if (homeNav) {
            homeNav.addEventListener('click', function(e) {
                const now = Date.now();
                if (now - lastTap < 300) {
                    // 双击 - 返回顶部
                    e.preventDefault();
                    scrollToTop();
                }
                lastTap = now;
            });
        }
    }

    /**
     * 平滑滚动到顶部
     */
    function scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    /**
     * 初始化移动端布局
     */
    function initMobileLayout() {
        // 检查是否是移动端
        if (window.innerWidth <= 768) {
            enableMobileLayout();
        }

        // 监听窗口大小变化
        window.addEventListener('resize', function() {
            if (window.innerWidth <= 768) {
                enableMobileLayout();
            } else {
                disableMobileLayout();
            }
        });

        // 监听 hash 变化（只在移动端执行页面切换）
        // 注意：移除了自动根据 hash 切换页面的逻辑，避免之前访问过的 hash 影响首页显示
        window.addEventListener('hashchange', function() {
            // 清除 hash，保持在首页
            if (window.location.hash && window.location.hash !== '#home') {
                history.replaceState(null, '', ' ');
            }
        });

        // 初始化：确保移动端始终显示首页
        if (window.innerWidth <= 768) {
            setActiveNavItem('home');
            // 清除任何非首页的 hash
            if (window.location.hash && window.location.hash !== '#home') {
                history.replaceState(null, '', ' ');
            }
        } else {
            // 桌面端清除 hash
            if (window.location.hash) {
                history.replaceState(null, '', ' ');
            }
        }
    }

    function initMyPostsTabs() {
        const tabButtons = document.querySelectorAll('.mobile-posts-tab');
        if (tabButtons.length === 0) {
            return;
        }

        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tab = this.getAttribute('data-tab') || 'published';
                currentMyPostsTab = tab;

                tabButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                loadMyPosts(tab);
            });
        });
    }

    async function loadMyPosts(tab) {
        const container = document.getElementById('my-posts-list');
        if (!container) {
            return;
        }

        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 40px 0;">加载中...</p>';

        try {
            const response = await fetch(`/mobile/my-posts?tab=${encodeURIComponent(tab)}`);
            const data = await response.json();

            if (response.status === 401) {
                container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 40px 0;"><a href="/login" style="color: var(--primary-color);">登录后查看 →</a></p>';
                return;
            }

            if (!data.posts || data.posts.length === 0) {
                container.innerHTML = `<p style="text-align: center; color: var(--text-secondary); padding: 40px 0;">${tab === 'drafts' ? '还没有草稿' : '还没有已发布文章'}</p>`;
                return;
            }

            // 添加 posts-list 类以启用卡片间距
            container.className = 'posts-list';
            container.innerHTML = data.posts.map(renderMyPostItem).join('');
        } catch (error) {
            console.error('Failed to load my posts:', error);
            container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 40px 0;">加载失败，请稍后重试</p>';
        }
    }

    function renderMyPostItem(post) {
        const title = escapeHtml(post.title || '无标题');
        const category = post.category_name ? `<span class="post-category">${escapeHtml(post.category_name)}</span>` : '';
        const status = post.is_published ? '已发布' : '草稿';
        const access = formatAccess(post.access_level);
        const href = `/post/${post.id}`;
        const editHref = `/admin/edit/${post.id}`;

        return `
            <article class="post-card" style="position: relative;">
                <!-- 编辑按钮 - 优雅圆形设计 -->
                <a href="${editHref}" class="my-post-edit-btn" aria-label="编辑文章">
                    ✎
                </a>

                <a href="${href}" class="post-card-link">
                    <div class="post-card-image">
                        <span class="post-card-image-placeholder">${post.is_published ? '📝' : '📄'}</span>
                    </div>
                    <div class="post-card-content">
                        <h2>${title}</h2>
                        <div class="post-excerpt">${escapeHtml(truncateContent(post.content || '', 100))}</div>
                        <div class="post-meta">
                            <span>${status}</span>
                            ${category}
                            <span>${access}</span>
                            <time>${formatDate(post.created_at)}</time>
                        </div>
                    </div>
                </a>
            </article>
        `;
    }

    function truncateContent(content, maxLength) {
        const text = String(content || '').replace(/<[^>]+>/g, '');
        if (text.length <= maxLength) {
            return text;
        }
        return `${text.slice(0, maxLength)}...`;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function formatDate(dateStr) {
        if (!dateStr) {
            return '';
        }

        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) {
            return String(dateStr).slice(0, 10);
        }

        return date.toISOString().slice(0, 10);
    }

    function formatAccess(accessLevel) {
        const accessMap = {
            public: '公开',
            login: '登录可见',
            password: '密码保护',
            private: '私密'
        };

        return accessMap[accessLevel] || '公开';
    }

    /**
     * 启用移动端布局
     */
    function enableMobileLayout() {
        document.body.classList.add('mobile-layout-active');
    }

    /**
     * 禁用移动端布局
     */
    function disableMobileLayout() {
        document.body.classList.remove('mobile-layout-active');
    }

    // 暴露全局函数
    window.MobileLayout = {
        setActiveNavItem,
        switchPage,
        scrollToTop,
        loadMyPosts
    };

})();
