/**
 * 微博式移动端布局控制
 * 处理底部导航、页面切换等功能
 */
(function() {
    'use strict';

    // 当前激活的页面
    let currentPage = 'home';

    // 初始化
    document.addEventListener('DOMContentLoaded', function() {
        initBottomNavigation();
        initDoubleTapToTop();
        initMobileLayout();
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
                    if (typeof openMobileEditor === 'function') {
                        openMobileEditor();
                    }
                    return;
                }

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
        // 隐藏所有页面
        document.querySelectorAll('.mobile-page').forEach(p => {
            p.style.display = 'none';
        });

        // 显示目标页面
        const targetPage = document.querySelector(`.mobile-page[data-page="${page}"]`);
        if (targetPage) {
            targetPage.style.display = 'block';
        }

        // 更新 URL hash
        history.pushState(null, '', `#${page}`);
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

        // 监听 hash 变化
        window.addEventListener('hashchange', function() {
            const hash = window.location.hash.slice(1) || 'home';
            if (hash !== currentPage && ['home', 'discover', 'my-posts', 'profile'].includes(hash)) {
                setActiveNavItem(hash);
                switchPage(hash);
            }
        });

        // 初始化 hash
        const initialHash = window.location.hash.slice(1);
        if (initialHash && ['home', 'discover', 'my-posts', 'profile'].includes(initialHash)) {
            setActiveNavItem(initialHash);
            switchPage(initialHash);
        }
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
        scrollToTop
    };

})();
