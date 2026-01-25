/**
 * 主交互功能
 *
 * 功能列表:
 *   1. 智能头部 - 根据滚动方向自动隐藏/显示导航栏
 *   2. 汉堡菜单 - 移动端响应式导航菜单
 *
 * 智能头部:
 *   - 向下滚动时隐藏导航栏（提供更多阅读空间）
 *   - 向上滚动时显示导航栏
 *   - 在页面顶部时始终显示
 *
 * 汉堡菜单:
 *   - 点击切换菜单显示
 *   - 点击链接自动关闭菜单
 *   - 点击菜单外区域关闭菜单
 *   - 窗口放大时自动关闭菜单
 *   - 打开菜单时禁止页面滚动
 *
 * 依赖: 无（原生 JavaScript）
 */

// =============================================================================
// 智能头部 - 根据滚动方向自动隐藏/显示
// =============================================================================
let lastScrollTop = 0;
const header = document.querySelector('header');
let scrollThreshold = 100; // Start hiding after scrolling down 100px
let headerHeight = header.offsetHeight;

window.addEventListener('scroll', function() {
    let scrollTop = window.pageYOffset || document.documentElement.scrollTop;

    if (scrollTop < 0) {
        scrollTop = 0;
    }

    // At the top of page, always show header
    if (scrollTop <= 0) {
        header.classList.remove('header-hidden');
        return;
    }

    // Detect scroll direction
    if (scrollTop > lastScrollTop && scrollTop > scrollThreshold) {
        // Scrolling down - hide header
        header.classList.add('header-hidden');
    } else if (scrollTop < lastScrollTop) {
        // Scrolling up - show header
        header.classList.remove('header-hidden');
    }

    lastScrollTop = scrollTop;
}, false);

// =============================================================================
// 汉堡菜单 - 移动端响应式导航
// =============================================================================
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');

if (hamburger && navLinks) {
    hamburger.addEventListener('click', function() {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');

        // Prevent body scroll when menu is open
        if (navLinks.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    });

    // Close menu when clicking on a link
    const menuLinks = navLinks.querySelectorAll('a');
    menuLinks.forEach(link => {
        link.addEventListener('click', function() {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(event) {
        const isClickInsideNav = navLinks.contains(event.target);
        const isClickOnHamburger = hamburger.contains(event.target);

        if (!isClickInsideNav && !isClickOnHamburger && navLinks.classList.contains('active')) {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // Close menu on window resize if open
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && navLinks.classList.contains('active')) {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
}
