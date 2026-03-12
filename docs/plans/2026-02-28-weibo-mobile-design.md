# 微博式移动端设计实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将博客移动端改造为微博式体验，包含大图卡片信息流、底部导航栏、沉浸式快速发布编辑器、无限滚动和下拉刷新。

**Architecture:** 渐进式增强设计 - 在现有响应式基础上，通过 CSS 媒体查询在 ≤768px 时启用微博式布局，保持桌面端现有体验不变。

**Tech Stack:** Vanilla JavaScript, CSS3, Flask templates, 复用现有后端 API

---

## 任务概览

1. 创建微博式移动端 CSS 样式
2. 创建移动端布局控制 JavaScript
3. 创建移动端快速发布编辑器
4. 实现无限滚动和下拉刷新
5. 更新模板集成新功能
6. 测试验证功能

---

### Task 1: 创建微博式移动端 CSS 样式

**Files:**
- Create: `static/css/mobile-weibo.css`
- Modify: `templates/base.html` (添加 CSS 引用)

**Step 1: 创建 mobile-weibo.css 基础结构**

```css
/* ========================================
   微博式移动端样式
   断点: @media (max-width: 768px)
   ======================================== */

/* 移动端布局容器 */
.mobile-weibo-layout {
    display: none;
}

@media (max-width: 768px) {
    /* 启用微博式移动端布局 */
    .mobile-weibo-layout {
        display: block;
    }

    /* 隐藏桌面端元素 */
    .desktop-only {
        display: none !important;
    }

    /* 调整主内容区域，为底部导航留出空间 */
    main {
        padding-bottom: 70px;
    }
}

/* 底部导航栏 */
.mobile-bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: var(--header-bg, #ffffff);
    border-top: 1px solid var(--border-color, #e0e0e0);
    display: none;
    z-index: 1000;
    padding-bottom: env(safe-area-inset-bottom, 0);
}

@media (max-width: 768px) {
    .mobile-bottom-nav {
        display: flex;
        align-items: center;
        justify-content: space-around;
    }
}

/* 导航按钮 */
.nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    height: 100%;
    text-decoration: none;
    color: var(--text-secondary, #777);
    font-size: 10px;
    transition: all 0.2s;
    position: relative;
    min-width: 48px;
    min-height: 48px;
}

.nav-item.active {
    color: var(--primary-color, #1abc9c);
}

.nav-item-icon {
    font-size: 22px;
    line-height: 1;
    margin-bottom: 2px;
}

/* 中央发布按钮（凸起设计）*/
.nav-item.publish-btn {
    position: relative;
    top: -12px;
}

.nav-item.publish-btn .nav-item-icon {
    width: 50px;
    height: 50px;
    background: linear-gradient(135deg, #1abc9c 0%, #16a089 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 28px;
    box-shadow: 0 4px 12px rgba(26, 188, 156, 0.4);
    transition: all 0.2s;
}

.nav-item.publish-btn:active .nav-item-icon {
    transform: scale(0.95);
}

/* 微博式大图卡片 */
@media (max-width: 768px) {
    .post-card {
        padding: 0 !important;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 12px;
    }

    .post-card-link {
        display: block;
        text-decoration: none;
    }

    /* 卡片图片区域 */
    .post-card-image {
        width: 100%;
        height: 200px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        position: relative;
    }

    .post-card-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .post-card-image-placeholder {
        color: white;
        font-size: 48px;
    }

    /* 卡片内容区域 */
    .post-card-content {
        padding: 16px;
    }

    .post-card h2 {
        font-size: 18px;
        line-height: 1.4;
        margin-bottom: 8px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .post-excerpt {
        font-size: 14px;
        color: var(--text-secondary, #777);
        line-height: 1.6;
        margin-bottom: 12px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .post-meta {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        font-size: 12px;
    }

    .post-category {
        background: var(--primary-color, #1abc9c);
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
    }

    /* 卡片底部互动区域 */
    .post-card-actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 20px;
        padding: 12px 16px;
        border-top: 1px solid var(--border-color, #f0f0f0);
    }

    .post-action-btn {
        display: flex;
        align-items: center;
        gap: 4px;
        color: var(--text-secondary, #999);
        font-size: 13px;
        background: none;
        border: none;
        cursor: pointer;
        padding: 4px 8px;
        min-width: 44px;
        min-height: 44px;
    }

    .post-action-btn:active {
        transform: scale(0.95);
    }

    .post-action-icon {
        font-size: 16px;
    }
}

/* 下拉刷新指示器 */
.pull-refresh-indicator {
    position: fixed;
    top: -60px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 40px;
    background: var(--header-bg, #fff);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    z-index: 999;
    transition: top 0.2s;
}

.pull-refresh-indicator.refreshing {
    top: 70px;
}

.pull-refresh-indicator .spinner {
    width: 24px;
    height: 24px;
    border: 3px solid var(--border-color, #e0e0e0);
    border-top-color: var(--primary-color, #1abc9c);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* 骨架屏加载 */
.skeleton-card {
    background: var(--gradient-card, #f8f9fa);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 12px;
}

.skeleton-image {
    width: 100%;
    height: 200px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
}

.skeleton-content {
    padding: 16px;
}

.skeleton-title {
    height: 20px;
    width: 80%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 12px;
}

.skeleton-text {
    height: 14px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 8px;
}

.skeleton-text:last-child {
    width: 60%;
}

@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* 移动端快速发布编辑器 */
.mobile-editor-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    display: none;
    opacity: 0;
    transition: opacity 0.2s;
}

.mobile-editor-overlay.show {
    display: flex;
    opacity: 1;
}

.mobile-editor-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--bg-color, #fff);
    z-index: 2001;
    transform: translateY(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    max-height: 100vh;
    padding-bottom: env(safe-area-inset-bottom, 0);
}

.mobile-editor-overlay.show + .mobile-editor-panel,
.mobile-editor-panel.show {
    transform: translateY(0);
}

.mobile-editor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color, #e0e0e0);
    min-height: 56px;
}

.mobile-editor-close {
    font-size: 24px;
    color: var(--text-secondary, #777);
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    min-width: 44px;
    min-height: 44px;
}

.mobile-editor-title {
    font-size: 17px;
    font-weight: 600;
    color: var(--heading-color, #333);
}

.mobile-editor-publish {
    background: linear-gradient(135deg, #1abc9c 0%, #16a089 100%);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 20px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    min-width: 44px;
    min-height: 44px;
}

.mobile-editor-publish:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.mobile-editor-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

.mobile-editor-textarea {
    width: 100%;
    min-height: 200px;
    border: none;
    font-size: 16px;
    line-height: 1.6;
    font-family: inherit;
    resize: none;
    outline: none;
    background: transparent;
    color: var(--text-color, #333);
}

.mobile-editor-textarea::placeholder {
    color: var(--text-secondary, #999);
}

/* 图片预览网格 */
.mobile-editor-images {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-top: 16px;
}

.mobile-editor-image-item {
    position: relative;
    aspect-ratio: 1;
    border-radius: 8px;
    overflow: hidden;
    background: var(--code-bg, #f6f8fa);
}

.mobile-editor-image-item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.mobile-editor-image-remove {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 24px;
    height: 24px;
    background: rgba(0, 0, 0, 0.5);
    color: white;
    border: none;
    border-radius: 50%;
    font-size: 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}

.mobile-editor-add-image {
    border: 2px dashed var(--border-color, #e0e0e0);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    color: var(--text-secondary, #999);
    cursor: pointer;
    background: none;
}

/* 已选标签和分类显示 */
.mobile-editor-selections {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
    padding: 12px;
    background: var(--code-bg, #f6f8fa);
    border-radius: 8px;
}

.selection-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    background: var(--primary-color, #1abc9c);
    color: white;
    border-radius: 16px;
    font-size: 13px;
}

.selection-pill.remove {
    background: var(--error-color, #ef4444);
    cursor: pointer;
}

.selection-pill-remove {
    font-size: 14px;
    cursor: pointer;
    line-height: 1;
}

/* 底部工具栏 */
.mobile-editor-toolbar {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    border-top: 1px solid var(--border-color, #e0e0e0);
    gap: 8px;
}

.toolbar-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border: none;
    background: none;
    color: var(--text-secondary, #777);
    font-size: 24px;
    cursor: pointer;
    border-radius: 8px;
    transition: all 0.2s;
}

.toolbar-btn:active {
    background: var(--code-bg, #f6f8fa);
    transform: scale(0.95);
}

/* 标签/分类选择器（半屏弹窗）*/
.selector-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2002;
    display: none;
}

.selector-overlay.show {
    display: block;
}

.selector-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--bg-color, #fff);
    z-index: 2003;
    transform: translateY(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    max-height: 60vh;
    border-radius: 16px 16px 0 0;
    padding-bottom: env(safe-area-inset-bottom, 0);
}

.selector-overlay.show + .selector-panel,
.selector-panel.show {
    transform: translateY(0);
}

.selector-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.selector-title {
    font-size: 17px;
    font-weight: 600;
}

.selector-close {
    font-size: 24px;
    color: var(--text-secondary, #777);
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
}

.selector-search {
    padding: 12px 16px;
}

.selector-search input {
    width: 100%;
    padding: 12px 16px;
    border: 1px solid var(--border-color, #e0e0e0);
    border-radius: 10px;
    font-size: 15px;
    outline: none;
}

.selector-search input:focus {
    border-color: var(--primary-color, #1abc9c);
}

.selector-content {
    overflow-y: auto;
    max-height: 40vh;
    padding: 8px 16px;
}

.selector-section-title {
    font-size: 13px;
    color: var(--text-secondary, #777);
    margin: 8px 0 12px;
    font-weight: 600;
}

.selector-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid var(--border-color, #f0f0f0);
}

.selector-item:last-child {
    border-bottom: none;
}

.selector-item-name {
    font-size: 15px;
    color: var(--text-color, #333);
}

.selector-item-check {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-color, #e0e0e0);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
}

.selector-item.selected .selector-item-check {
    background: var(--primary-color, #1abc9c);
    border-color: var(--primary-color, #1abc9c);
    color: white;
}

/* 发现页面样式 */
.mobile-discover-page {
    display: none;
}

@media (max-width: 768px) {
    .mobile-discover-page {
        display: block;
    }

    .desktop-discover {
        display: none;
    }
}

/* 我的文章页面 */
.mobile-my-posts {
    padding: 16px;
}

.mobile-posts-tabs {
    display: flex;
    background: var(--code-bg, #f6f8fa);
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 16px;
}

.mobile-posts-tab {
    flex: 1;
    text-align: center;
    padding: 10px;
    border-radius: 8px;
    font-size: 14px;
    color: var(--text-secondary, #777);
    background: none;
    border: none;
    cursor: pointer;
}

.mobile-posts-tab.active {
    background: var(--bg-color, #fff);
    color: var(--text-color, #333);
    font-weight: 600;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* 加载更多指示器 */
.load-more-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    color: var(--text-secondary, #999);
    font-size: 14px;
}

.load-more-indicator .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-color, #e0e0e0);
    border-top-color: var(--primary-color, #1abc9c);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: 8px;
}

/* 暗色主题适配 */
.dark-theme .mobile-editor-panel,
.dark-theme .selector-panel {
    background: var(--bg-color, #1a1a1a);
}

.dark-theme .mobile-editor-textarea {
    color: var(--text-color, #d4d4d4);
}

.dark-theme .selector-item-name {
    color: var(--text-color, #d4d4d4);
}
```

**Step 2: 在 base.html 中添加 CSS 引用**

在 `templates/base.html` 的 `<head>` 部分，在 style.css 之后添加：

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/mobile-weibo.css') }}?v=1.0">
```

**Step 3: 验证文件结构**

确认文件创建成功，CSS 语法正确。

**Step 4: 提交**

```bash
cd /Users/gn/simple-blog/.worktrees/feature-weibo-mobile
git add static/css/mobile-weibo.css templates/base.html
git commit -m "feat: add weibo-style mobile CSS styles"
```

---

### Task 2: 创建移动端布局控制 JavaScript

**Files:**
- Create: `static/js/mobile-layout.js`
- Modify: `templates/base.html` (添加 JS 引用)

**Step 1: 创建 mobile-layout.js**

```javascript
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
                    openMobileEditor();
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
```

**Step 2: 在 base.html 中添加 JS 引用**

在 `templates/base.html` 的脚本部分添加：

```html
<script src="{{ url_for('static', filename='js/mobile-layout.js') }}?v=1.0"></script>
```

**Step 3: 提交**

```bash
git add static/js/mobile-layout.js templates/base.html
git commit -m "feat: add mobile layout controller"
```

---

### Task 3: 创建移动端快速发布编辑器

**Files:**
- Create: `static/js/mobile-editor.js`
- Modify: `templates/base.html` (添加编辑器 HTML 结构)

**Step 1: 创建 mobile-editor.js**

```javascript
/**
 * 移动端快速发布编辑器
 * 提供沉浸式编辑体验
 */
(function() {
    'use strict';

    // 状态
    let selectedTags = [];
    let selectedCategory = null;
    let selectedImages = [];
    let accessLevel = 'public';
    let draftKey = 'mobile_editor_draft';

    // 初始化
    document.addEventListener('DOMContentLoaded', function() {
        initMobileEditor();
        loadDraft();
    });

    /**
     * 打开移动端编辑器
     */
    window.openMobileEditor = function() {
        const overlay = document.getElementById('mobileEditorOverlay');
        const panel = document.getElementById('mobileEditorPanel');

        if (overlay && panel) {
            overlay.classList.add('show');
            panel.classList.add('show');
            document.body.style.overflow = 'hidden';

            // 聚焦文本框
            setTimeout(() => {
                const textarea = document.getElementById('mobileEditorTextarea');
                if (textarea) textarea.focus();
            }, 300);
        }
    };

    /**
     * 关闭移动端编辑器
     */
    window.closeMobileEditor = function() {
        const overlay = document.getElementById('mobileEditorOverlay');
        const panel = document.getElementById('mobileEditorPanel');

        if (overlay && panel) {
            overlay.classList.remove('show');
            panel.classList.remove('show');
            document.body.style.overflow = '';
        }
    };

    /**
     * 初始化编辑器
     */
    function initMobileEditor() {
        // 关闭按钮
        const closeBtn = document.getElementById('mobileEditorClose');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                if (confirm('确定要关闭吗？未保存的内容将丢失。')) {
                    clearDraft();
                    closeMobileEditor();
                }
            });
        }

        // 点击遮罩关闭
        const overlay = document.getElementById('mobileEditorOverlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    if (confirm('确定要关闭吗？未保存的内容将丢失。')) {
                        clearDraft();
                        closeMobileEditor();
                    }
                }
            });
        }

        // 文本输入 - 自动保存草稿
        const textarea = document.getElementById('mobileEditorTextarea');
        if (textarea) {
            textarea.addEventListener('input', function() {
                saveDraft();
                updatePublishButton();
            });
        }

        // 标题输入
        const titleInput = document.getElementById('mobileEditorTitle');
        if (titleInput) {
            titleInput.addEventListener('input', function() {
                saveDraft();
            });
        }

        // 发布按钮
        const publishBtn = document.getElementById('mobileEditorPublish');
        if (publishBtn) {
            publishBtn.addEventListener('click', publishPost);
        }

        // 工具栏按钮
        initToolbarButtons();

        // 初始化标签和分类选择器
        initSelectors();
    }

    /**
     * 初始化工具栏按钮
     */
    function initToolbarButtons() {
        // 图片按钮
        const imageBtn = document.getElementById('toolbarImage');
        if (imageBtn) {
            imageBtn.addEventListener('click', function() {
                const input = document.getElementById('mobileEditorImageInput');
                if (input) input.click();
            });
        }

        // 图片输入
        const imageInput = document.getElementById('mobileEditorImageInput');
        if (imageInput) {
            imageInput.addEventListener('change', handleImageSelect);
        }

        // 标签按钮
        const tagsBtn = document.getElementById('toolbarTags');
        if (tagsBtn) {
            tagsBtn.addEventListener('click', openTagsSelector);
        }

        // 分类按钮
        const categoryBtn = document.getElementById('toolbarCategory');
        if (categoryBtn) {
            categoryBtn.addEventListener('click', openCategorySelector);
        }

        // 权限按钮
        const accessBtn = document.getElementById('toolbarAccess');
        if (accessBtn) {
            accessBtn.addEventListener('click', openAccessSelector);
        }
    }

    /**
     * 处理图片选择
     */
    function handleImageSelect(e) {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        // 限制最多9张图片
        const remaining = 9 - selectedImages.length;
        const filesToProcess = Array.from(files).slice(0, remaining);

        filesToProcess.forEach(file => {
            const reader = new FileReader();
            reader.onload = function(event) {
                selectedImages.push({
                    file: file,
                    dataUrl: event.target.result
                });
                renderImages();
                saveDraft();
            };
            reader.readAsDataURL(file);
        });

        // 清空 input
        e.target.value = '';
    }

    /**
     * 渲染图片预览
     */
    function renderImages() {
        const container = document.getElementById('mobileEditorImages');
        if (!container) return;

        container.innerHTML = '';

        selectedImages.forEach((img, index) => {
            const item = document.createElement('div');
            item.className = 'mobile-editor-image-item';
            item.innerHTML = `
                <img src="${img.dataUrl}" alt="">
                <button type="button" class="mobile-editor-image-remove" data-index="${index}">×</button>
            `;
            container.appendChild(item);
        });

        // 添加图片按钮（如果还没满9张）
        if (selectedImages.length < 9) {
            const addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'mobile-editor-image-item mobile-editor-add-image';
            addBtn.innerHTML = '+';
            addBtn.addEventListener('click', function() {
                document.getElementById('mobileEditorImageInput').click();
            });
            container.appendChild(addBtn);
        }

        // 删除按钮事件
        container.querySelectorAll('.mobile-editor-image-remove').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const index = parseInt(this.getAttribute('data-index'));
                selectedImages.splice(index, 1);
                renderImages();
                saveDraft();
            });
        });
    }

    /**
     * 初始化选择器
     */
    function initSelectors() {
        // 关闭选择器
        document.querySelectorAll('.selector-close, .selector-overlay').forEach(el => {
            el.addEventListener('click', closeSelectors);
        });
    }

    /**
     * 打开标签选择器
     */
    function openTagsSelector() {
        const overlay = document.getElementById('tagsSelectorOverlay');
        const panel = document.getElementById('tagsSelectorPanel');

        if (overlay && panel) {
            overlay.classList.add('show');
            panel.classList.add('show');
            renderTagsList();
        }
    }

    /**
     * 渲染标签列表
     */
    function renderTagsList() {
        const container = document.getElementById('tagsSelectorContent');
        if (!container) return;

        // 获取现有标签（从页面数据或 API）
        const allTags = window.availableTags || [];

        let html = '';

        // 常用标签（已选的在前）
        const selectedTagIds = selectedTags.map(t => t.id);
        const recentTags = allTags.filter(t => selectedTagIds.includes(t.id));
        const otherTags = allTags.filter(t => !selectedTagIds.includes(t.id));

        if (recentTags.length > 0) {
            html += '<div class="selector-section-title">常用标签</div>';
            recentTags.forEach(tag => {
                html += renderTagItem(tag, true);
            });
        }

        if (otherTags.length > 0) {
            html += '<div class="selector-section-title">全部标签</div>';
            otherTags.forEach(tag => {
                html += renderTagItem(tag, false);
            });
        }

        // 新建标签选项
        html += `
            <div class="selector-item" onclick="createNewTag()">
                <span class="selector-item-name">+ 新建标签</span>
            </div>
        `;

        container.innerHTML = html;

        // 绑定点击事件
        container.querySelectorAll('.selector-item').forEach(item => {
            item.addEventListener('click', function() {
                const tagId = this.getAttribute('data-tag-id');
                if (tagId) {
                    toggleTagSelection(parseInt(tagId));
                }
            });
        });
    }

    /**
     * 渲染单个标签项
     */
    function renderTagItem(tag, selected) {
        const isSelected = selectedTags.some(t => t.id === tag.id);
        return `
            <div class="selector-item ${isSelected ? 'selected' : ''}" data-tag-id="${tag.id}">
                <span class="selector-item-name">#${tag.name}</span>
                <span class="selector-item-check">${isSelected ? '✓' : ''}</span>
            </div>
        `;
    }

    /**
     * 切换标签选择
     */
    function toggleTagSelection(tagId) {
        const tag = (window.availableTags || []).find(t => t.id === tagId);
        if (!tag) return;

        const index = selectedTags.findIndex(t => t.id === tagId);
        if (index > -1) {
            selectedTags.splice(index, 1);
        } else {
            selectedTags.push(tag);
        }

        renderTagsList();
        renderSelections();
        saveDraft();
    }

    /**
     * 打开分类选择器
     */
    function openCategorySelector() {
        const overlay = document.getElementById('categorySelectorOverlay');
        const panel = document.getElementById('categorySelectorPanel');

        if (overlay && panel) {
            overlay.classList.add('show');
            panel.classList.add('show');
            renderCategoryList();
        }
    }

    /**
     * 渲染分类列表
     */
    function renderCategoryList() {
        const container = document.getElementById('categorySelectorContent');
        if (!container) return;

        const allCategories = window.availableCategories || [];

        let html = '';

        // 无分类选项
        html += `
            <div class="selector-item ${!selectedCategory ? 'selected' : ''}" data-category-id="">
                <span class="selector-item-name">无分类</span>
                <span class="selector-item-check">${!selectedCategory ? '✓' : ''}</span>
            </div>
        `;

        allCategories.forEach(cat => {
            const isSelected = selectedCategory && selectedCategory.id === cat.id;
            html += `
                <div class="selector-item ${isSelected ? 'selected' : ''}" data-category-id="${cat.id}">
                    <span class="selector-item-name">${cat.name}</span>
                    <span class="selector-item-check">${isSelected ? '✓' : ''}</span>
                </div>
            `;
        });

        container.innerHTML = html;

        // 绑定点击事件
        container.querySelectorAll('.selector-item').forEach(item => {
            item.addEventListener('click', function() {
                const catId = this.getAttribute('data-category-id');
                if (catId === '') {
                    selectedCategory = null;
                } else {
                    selectedCategory = (window.availableCategories || []).find(c => c.id === parseInt(catId));
                }
                renderCategoryList();
                renderSelections();
                closeSelectors();
                saveDraft();
            });
        });
    }

    /**
     * 渲染已选标签和分类
     */
    function renderSelections() {
        const container = document.getElementById('mobileEditorSelections');
        if (!container) return;

        let html = '';

        if (selectedCategory) {
            html += `
                <span class="selection-pill">
                    📂 ${selectedCategory.name}
                </span>
            `;
        }

        selectedTags.forEach(tag => {
            html += `
                <span class="selection-pill remove">
                    #${tag.name}
                    <span class="selection-pill-remove" data-tag-id="${tag.id}">×</span>
                </span>
            `;
        });

        container.innerHTML = html;
        container.style.display = (selectedCategory || selectedTags.length > 0) ? 'flex' : 'none';

        // 绑定移除事件
        container.querySelectorAll('.selection-pill-remove').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const tagId = parseInt(this.getAttribute('data-tag-id'));
                selectedTags = selectedTags.filter(t => t.id !== tagId);
                renderSelections();
                saveDraft();
            });
        });
    }

    /**
     * 关闭所有选择器
     */
    function closeSelectors() {
        document.querySelectorAll('.selector-overlay, .selector-panel').forEach(el => {
            el.classList.remove('show');
        });
    }

    /**
     * 打开权限选择器
     */
    function openAccessSelector() {
        // 简单版：直接切换
        const levels = ['public', 'login', 'private'];
        const currentIndex = levels.indexOf(accessLevel);
        accessLevel = levels[(currentIndex + 1) % levels.length];

        const btn = document.getElementById('toolbarAccess');
        if (btn) {
            const icons = { public: '🌐', login: '🔒', private: '👁️' };
            btn.querySelector('.toolbar-icon').textContent = icons[accessLevel];
        }

        saveDraft();
    }

    /**
     * 创建新标签
     */
    window.createNewTag = function() {
        const name = prompt('请输入新标签名称：');
        if (name && name.trim()) {
            // 这里应该调用 API 创建标签
            // 暂时先添加到本地
            const newTag = { id: Date.now(), name: name.trim() };
            if (!window.availableTags) window.availableTags = [];
            window.availableTags.push(newTag);
            selectedTags.push(newTag);
            renderTagsList();
            renderSelections();
            saveDraft();
        }
    };

    /**
     * 更新发布按钮状态
     */
    function updatePublishButton() {
        const textarea = document.getElementById('mobileEditorTextarea');
        const publishBtn = document.getElementById('mobileEditorPublish');

        if (textarea && publishBtn) {
            const hasContent = textarea.value.trim().length > 0;
            publishBtn.disabled = !hasContent;
        }
    }

    /**
     * 保存草稿
     */
    function saveDraft() {
        const title = document.getElementById('mobileEditorTitle')?.value || '';
        const content = document.getElementById('mobileEditorTextarea')?.value || '';

        const draft = {
            title,
            content,
            tags: selectedTags,
            category: selectedCategory,
            images: selectedImages.map(img => img.dataUrl), // 只保存 dataUrl
            accessLevel,
            savedAt: Date.now()
        };

        try {
            localStorage.setItem(draftKey, JSON.stringify(draft));
        } catch (e) {
            console.warn('Failed to save draft:', e);
        }
    }

    /**
     * 加载草稿
     */
    function loadDraft() {
        try {
            const draftData = localStorage.getItem(draftKey);
            if (!draftData) return;

            const draft = JSON.parse(draftData);
            if (!draft || !draft.content) return;

            // 检查草稿是否过期（24小时）
            if (Date.now() - draft.savedAt > 24 * 60 * 60 * 1000) {
                clearDraft();
                return;
            }

            // 恢复草稿
            if (document.getElementById('mobileEditorTitle')) {
                document.getElementById('mobileEditorTitle').value = draft.title || '';
            }
            if (document.getElementById('mobileEditorTextarea')) {
                document.getElementById('mobileEditorTextarea').value = draft.content || '';
            }

            selectedTags = draft.tags || [];
            selectedCategory = draft.category || null;
            accessLevel = draft.accessLevel || 'public';

            // 恢复图片（只恢复 dataUrl，没有 file 对象）
            if (draft.images && draft.images.length > 0) {
                selectedImages = draft.images.map(dataUrl => ({
                    dataUrl,
                    file: null
                }));
                renderImages();
            }

            renderSelections();
            updatePublishButton();
        } catch (e) {
            console.warn('Failed to load draft:', e);
        }
    }

    /**
     * 清除草稿
     */
    function clearDraft() {
        try {
            localStorage.removeItem(draftKey);
        } catch (e) {}

        // 重置状态
        selectedTags = [];
        selectedCategory = null;
        selectedImages = [];
        accessLevel = 'public';

        // 重置表单
        const titleInput = document.getElementById('mobileEditorTitle');
        const textarea = document.getElementById('mobileEditorTextarea');
        if (titleInput) titleInput.value = '';
        if (textarea) textarea.value = '';

        renderSelections();
        renderImages();
        updatePublishButton();
    }

    /**
     * 发布文章
     */
    async function publishPost() {
        const title = document.getElementById('mobileEditorTitle')?.value || '';
        const content = document.getElementById('mobileEditorTextarea')?.value || '';

        if (!content.trim()) {
            alert('请输入内容');
            return;
        }

        const publishBtn = document.getElementById('mobileEditorPublish');
        publishBtn.disabled = true;
        publishBtn.textContent = '发布中...';

        try {
            // 构建 FormData
            const formData = new FormData();
            formData.append('title', title || '无标题');
            formData.append('content', content);
            formData.append('is_published', 'true');
            formData.append('access_level', accessLevel);

            if (selectedCategory) {
                formData.append('category_id', selectedCategory.id);
            }

            if (selectedTags.length > 0) {
                formData.append('tags', selectedTags.map(t => t.name).join(', '));
            }

            // 获取 CSRF token
            const csrfToken = document.querySelector('meta[name="csrf_token"]')?.content;

            // 上传图片（如果有）
            // 这里简化处理，实际项目中需要先上传图片
            // 然后将图片 URL 插入内容

            // 提交文章
            const response = await fetch('/admin/editor', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            if (response.ok) {
                clearDraft();
                closeMobileEditor();
                alert('发布成功！');
                // 刷新页面
                window.location.reload();
            } else {
                const error = await response.text();
                throw new Error(error || '发布失败');
            }
        } catch (error) {
            console.error('Publish error:', error);
            alert('发布失败：' + error.message);
            publishBtn.disabled = false;
            publishBtn.textContent = '发布';
        }
    }

    // 暴露全局函数
    window.MobileEditor = {
        open: openMobileEditor,
        close: closeMobileEditor,
        publishPost
    };

})();
```

**Step 2: 在 base.html 中添加编辑器 HTML 结构**

在 `templates/base.html` 的 `</body>` 之前添加：

```html
<!-- 移动端快速发布编辑器 -->
<div id="mobileEditorOverlay" class="mobile-editor-overlay"></div>
<div id="mobileEditorPanel" class="mobile-editor-panel">
    <div class="mobile-editor-header">
        <button type="button" class="mobile-editor-close" id="mobileEditorClose">×</button>
        <span class="mobile-editor-title">发布内容</span>
        <button type="button" class="mobile-editor-publish" id="mobileEditorPublish" disabled>发布</button>
    </div>
    <div class="mobile-editor-content">
        <input type="text" id="mobileEditorTitle" class="mobile-editor-textarea" placeholder="标题（可选）" style="min-height: auto; font-size: 18px; font-weight: 600; margin-bottom: 12px;">
        <textarea id="mobileEditorTextarea" class="mobile-editor-textarea" placeholder="分享你的想法..."></textarea>
        <div id="mobileEditorImages" class="mobile-editor-images"></div>
        <div id="mobileEditorSelections" class="mobile-editor-selections" style="display: none;"></div>
    </div>
    <div class="mobile-editor-toolbar">
        <button type="button" class="toolbar-btn" id="toolbarImage" title="添加图片">
            <span class="toolbar-icon">📷</span>
        </button>
        <button type="button" class="toolbar-btn" id="toolbarTags" title="添加标签">
            <span class="toolbar-icon">🏷️</span>
        </button>
        <button type="button" class="toolbar-btn" id="toolbarCategory" title="选择分类">
            <span class="toolbar-icon">📂</span>
        </button>
        <button type="button" class="toolbar-btn" id="toolbarAccess" title="访问权限">
            <span class="toolbar-icon">🌐</span>
        </button>
        <input type="file" id="mobileEditorImageInput" accept="image/*" multiple style="display: none;">
    </div>
</div>

<!-- 标签选择器 -->
<div id="tagsSelectorOverlay" class="selector-overlay"></div>
<div id="tagsSelectorPanel" class="selector-panel">
    <div class="selector-header">
        <span class="selector-title">选择标签</span>
        <button type="button" class="selector-close">×</button>
    </div>
    <div class="selector-search">
        <input type="text" placeholder="搜索标签...">
    </div>
    <div class="selector-content" id="tagsSelectorContent"></div>
</div>

<!-- 分类选择器 -->
<div id="categorySelectorOverlay" class="selector-overlay"></div>
<div id="categorySelectorPanel" class="selector-panel">
    <div class="selector-header">
        <span class="selector-title">选择分类</span>
        <button type="button" class="selector-close">×</button>
    </div>
    <div class="selector-content" id="categorySelectorContent"></div>
</div>

<script>
// 将可用标签和分类数据传递给 JavaScript
window.availableTags = {{ all_tags|safe if all_tags else '[]' }};
window.availableCategories = {{ all_categories|safe if all_categories else '[]' }};
</script>
```

**Step 3: 在 base.html 中添加 JS 引用**

```html
<script src="{{ url_for('static', filename='js/mobile-editor.js') }}?v=1.0"></script>
```

**Step 4: 提交**

```bash
git add static/js/mobile-editor.js templates/base.html
git commit -m "feat: add mobile quick publish editor"
```

---

### Task 4: 实现无限滚动和下拉刷新

**Files:**
- Create: `static/js/infinite-scroll.js`
- Create: `static/js/pull-refresh.js`
- Modify: `templates/index.html` (更新文章列表结构)
- Modify: `templates/base.html` (添加 JS 引用)

**Step 1: 创建 infinite-scroll.js**

```javascript
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
            const categoryId = document.getElementById('load-more')?.getAttribute('data-category') || '';

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
                    <div class="post-excerpt">${escapeHtml(post.excerpt || '')}</div>
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
        const imgMatch = content.match(/<img[^>]+src="([^"]+)"/);
        return imgMatch ? imgMatch[1] : null;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatDate(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;

        // 1小时内
        if (diff < 60 * 60 * 1000) {
            const mins = Math.floor(diff / (60 * 1000));
            return `${mins}分钟前`;
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
        return dateStr.substring(0, 10);
    }

    function showLoadingIndicator() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (indicator) {
            indicator.style.display = 'flex';
        }
    }

    function hideLoadingIndicator() {
        const indicator = document.getElementById('loadMoreIndicator');
        if (indicator && !hasMore) {
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
```

**Step 2: 创建 pull-refresh.js**

```javascript
/**
 * 下拉刷新
 */
(function() {
    'use strict';

    let startY = 0;
    let isPulling = false;
    let isRefreshing = false;
    const threshold = 80; // 下拉阈值

    document.addEventListener('DOMContentLoaded', function() {
        if (window.innerWidth <= 768) {
            initPullRefresh();
        }
    });

    function initPullRefresh() {
        // 创建刷新指示器
        createRefreshIndicator();

        // 监听触摸事件
        document.addEventListener('touchstart', handleTouchStart, { passive: true });
        document.addEventListener('touchmove', handleTouchMove, { passive: false });
        document.addEventListener('touchend', handleTouchEnd, { passive: true });
    }

    function createRefreshIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'pullRefreshIndicator';
        indicator.className = 'pull-refresh-indicator';
        indicator.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(indicator);
    }

    function handleTouchStart(e) {
        if (isRefreshing) return;

        // 只有在页面顶部才允许下拉刷新
        if (window.scrollY > 5) return;

        startY = e.touches[0].pageY;
        isPulling = true;
    }

    function handleTouchMove(e) {
        if (!isPulling || isRefreshing) return;

        const currentY = e.touches[0].pageY;
        const diff = currentY - startY;

        // 只有向下拉才处理
        if (diff <= 0) return;

        // 防止原生滚动
        e.preventDefault();

        // 计算拉动距离（带阻尼效果）
        const pullDistance = Math.min(diff * 0.5, threshold * 2);

        // 更新指示器位置
        updateRefreshIndicator(pullDistance);
    }

    function handleTouchEnd(e) {
        if (!isPulling) return;

        isPulling = false;

        const indicator = document.getElementById('pullRefreshIndicator');
        if (!indicator) return;

        // 检查是否达到刷新阈值
        const currentTop = parseInt(indicator.style.top) || -60;
        if (currentTop >= 10) {
            // 触发刷新
            startRefresh();
        } else {
            // 回弹隐藏
            resetRefreshIndicator();
        }
    }

    function updateRefreshIndicator(distance) {
        const indicator = document.getElementById('pullRefreshIndicator');
        if (!indicator) return;

        // 从 -60px 到 20px
        const top = Math.min(-60 + distance, 20);
        indicator.style.top = top + 'px';

        // 旋转图标
        const spinner = indicator.querySelector('.spinner');
        if (spinner) {
            const rotation = (distance / threshold) * 180;
            spinner.style.transform = `rotate(${rotation}deg)`;
        }
    }

    function resetRefreshIndicator() {
        const indicator = document.getElementById('pullRefreshIndicator');
        if (!indicator) return;

        indicator.style.top = '-60px';
        indicator.classList.remove('refreshing');

        const spinner = indicator.querySelector('.spinner');
        if (spinner) {
            spinner.style.transform = '';
        }
    }

    async function startRefresh() {
        if (isRefreshing) return;

        isRefreshing = true;

        const indicator = document.getElementById('pullRefreshIndicator');
        if (indicator) {
            indicator.classList.add('refreshing');
        }

        try {
            // 执行刷新操作
            await performRefresh();
        } finally {
            // 延迟隐藏，让用户看到完成状态
            setTimeout(() => {
                isRefreshing = false;
                resetRefreshIndicator();
            }, 500);
        }
    }

    async function performRefresh() {
        // 刷新页面内容
        // 这里简单重载页面，实际项目中可以 AJAX 刷新
        window.location.reload();
    }

    // 暴露 API
    window.PullRefresh = {
        trigger: function() {
            startRefresh();
        }
    };

})();
```

**Step 3: 更新 index.html 文章卡片结构**

修改 `templates/index.html` 中的文章卡片，添加微博式大图卡片结构：

```html
{% for post in posts %}
    <a href="{{ url_for('view_post', post_id=post.id) }}" class="post-card-link">
        <article class="post-card">
            {% set cover_image = post.content|extract_first_image %}
            {% if cover_image %}
            <div class="post-card-image">
                <img src="{{ cover_image }}" alt="" loading="lazy">
            </div>
            {% else %}
            <div class="post-card-image">
                <span class="post-card-image-placeholder">📝</span>
            </div>
            {% endif %}
            <div class="post-card-content">
                <h2>{{ post.title }}</h2>
                <div class="post-excerpt">{{ post.content|excerpt }}</div>
                <div class="post-meta">
                    {% if post.category_name %}
                    <span class="post-category">{{ post.category_name }}</span>
                    {% endif %}
                    {% if post.author_display_name or post.author_username %}
                    <span>👤 {{ post.author_display_name or post.author_username }}</span>
                    {% endif %}
                    <time datetime="{{ post.created_at }}">{{ post.created_at|timeago }}</time>
                </div>
            </div>
            <div class="post-card-actions">
                <button type="button" class="post-action-btn">
                    <span class="post-action-icon">❤️</span>
                    <span>{{ post.like_count or 0 }}</span>
                </button>
                <button type="button" class="post-action-btn">
                    <span class="post-action-icon">💬</span>
                    <span>{{ post.comment_count or 0 }}</span>
                </button>
                <button type="button" class="post-action-btn">
                    <span class="post-action-icon">🔗</span>
                </button>
            </div>
        </article>
    </a>
{% endfor %}
```

**Step 4: 在 base.html 中添加 JS 引用**

```html
<script src="{{ url_for('static', filename='js/infinite-scroll.js') }}?v=1.0"></script>
<script src="{{ url_for('static', filename='js/pull-refresh.js') }}?v=1.0"></script>
```

**Step 5: 提交**

```bash
git add static/js/infinite-scroll.js static/js/pull-refresh.js templates/index.html templates/base.html
git commit -m "feat: add infinite scroll and pull-to-refresh"
```

---

### Task 5: 更新模板集成新功能

**Files:**
- Modify: `templates/base.html` (添加底部导航和移动端页面结构)
- Modify: `templates/index.html` (包装在移动端页面中)
- Modify: `backend/routes/blog.py` (添加 JSON 格式支持和模板数据)

**Step 1: 更新 base.html - 添加底部导航**

在 `templates/base.html` 的 `</main>` 之后、`<footer>` 之前添加：

```html
<!-- 移动端底部导航 -->
<nav class="mobile-bottom-nav">
    <a href="#home" class="nav-item active" data-page="home">
        <span class="nav-item-icon">🏠</span>
        <span class="nav-item-label">首页</span>
    </a>
    <a href="#discover" class="nav-item" data-page="discover">
        <span class="nav-item-icon">🔍</span>
        <span class="nav-item-label">发现</span>
    </a>
    <a href="#" class="nav-item publish-btn" data-page="publish">
        <span class="nav-item-icon">+</span>
    </a>
    <a href="#my-posts" class="nav-item" data-page="my-posts">
        <span class="nav-item-icon">📄</span>
        <span class="nav-item-label">文章</span>
    </a>
    <a href="#profile" class="nav-item" data-page="profile">
        <span class="nav-item-icon">👤</span>
        <span class="nav-item-label">我的</span>
    </a>
</nav>
```

**Step 2: 更新 base.html - 添加移动端页面容器**

在 `templates/base.html` 的 `<main>` 标签内部，用移动端页面容器包装：

```html
<main>
    <!-- 移动端首页 -->
    <div class="mobile-page" data-page="home" style="display: block;">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <!-- 移动端发现页面 -->
    <div class="mobile-page" data-page="discover" style="display: none;">
        <div class="container" style="padding: 16px;">
            <h2 style="margin-bottom: 16px; font-size: 20px;">发现</h2>

            <!-- 搜索框 -->
            <div class="form-group" style="margin-bottom: 20px;">
                <form action="{{ url_for('search') }}" method="get">
                    <input type="text" name="q" placeholder="搜索文章..." style="width: 100%; padding: 12px 16px; border-radius: 10px; border: 1px solid var(--border-color);">
                </form>
            </div>

            <!-- 热门标签 -->
            {% if popular_tags %}
            <div style="margin-bottom: 24px;">
                <h3 style="font-size: 16px; margin-bottom: 12px;">🔥 热门标签</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    {% for tag in popular_tags %}
                    <a href="{{ url_for('view_tag', tag_id=tag.id) }}" style="display: inline-block; padding: 8px 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 20px; text-decoration: none; font-size: 14px;">
                        #{{ tag.name }}
                    </a>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            <!-- 分类浏览 -->
            {% if categories %}
            <div style="margin-bottom: 24px;">
                <h3 style="font-size: 16px; margin-bottom: 12px;">📂 分类浏览</h3>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                    {% for cat in categories %}
                    <a href="{{ url_for('view_category', category_id=cat.id) }}" style="display: block; padding: 20px; background: var(--gradient-card); border-radius: 12px; text-align: center; text-decoration: none; color: var(--text-color); border: 1px solid var(--border-color);">
                        <div style="font-size: 24px; margin-bottom: 8px;">📁</div>
                        <div style="font-weight: 600;">{{ cat.name }}</div>
                    </a>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>
    </div>

    <!-- 移动端我的文章页面 -->
    <div class="mobile-page" data-page="my-posts" style="display: none;">
        <div class="mobile-my-posts">
            <h2 style="margin-bottom: 16px; font-size: 20px;">我的文章</h2>

            <div class="mobile-posts-tabs">
                <button class="mobile-posts-tab active" data-tab="published">已发布</button>
                <button class="mobile-posts-tab" data-tab="drafts">草稿</button>
            </div>

            <div id="my-posts-list">
                <!-- 文章列表将通过 JS 加载 -->
                <p style="text-align: center; color: var(--text-secondary); padding: 40px 0;">
                    {% if session.get('user_id') %}
                    <a href="{{ url_for('admin_dashboard') }}" style="color: var(--primary-color);">去管理后台查看 →</a>
                    {% else %}
                    <a href="{{ url_for('login') }}" style="color: var(--primary-color);">登录后查看 →</a>
                    {% endif %}
                </p>
            </div>
        </div>
    </div>

    <!-- 移动端个人中心页面 -->
    <div class="mobile-page" data-page="profile" style="display: none;">
        <div class="container" style="padding: 16px;">
            <h2 style="margin-bottom: 20px; font-size: 20px;">个人中心</h2>

            {% if session.get('user_id') %}
            <div style="background: var(--gradient-card); border-radius: 16px; padding: 20px; margin-bottom: 20px; border: 1px solid var(--border-color);">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #1abc9c 0%, #16a089 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px;">
                        👤
                    </div>
                    <div>
                        <div style="font-size: 18px; font-weight: 600;">{{ session.get('username', '用户') }}</div>
                        <div style="color: var(--text-secondary); font-size: 14px;">{{ session.get('role', 'user') }}</div>
                    </div>
                </div>
            </div>

            <div style="display: flex; flex-direction: column; gap: 12px;">
                <a href="{{ url_for('admin_dashboard') }}" style="display: flex; align-items: center; gap: 12px; padding: 16px; background: var(--bg-color); border-radius: 12px; text-decoration: none; color: var(--text-color); border: 1px solid var(--border-color);">
                    <span style="font-size: 24px;">📝</span>
                    <span style="flex: 1;">文章管理</span>
                    <span>→</span>
                </a>
                <a href="{{ url_for('change_password') }}" style="display: flex; align-items: center; gap: 12px; padding: 16px; background: var(--bg-color); border-radius: 12px; text-decoration: none; color: var(--text-color); border: 1px solid var(--border-color);">
                    <span style="font-size: 24px;">🔐</span>
                    <span style="flex: 1;">修改密码</span>
                    <span>→</span>
                </a>
                <a href="{{ url_for('logout') }}" style="display: flex; align-items: center; gap: 12px; padding: 16px; background: #fef2f2; border-radius: 12px; text-decoration: none; color: #dc2626; border: 1px solid #fecaca;">
                    <span style="font-size: 24px;">🚪</span>
                    <span style="flex: 1;">退出登录</span>
                    <span>→</span>
                </a>
            </div>
            {% else %}
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 48px; margin-bottom: 16px;">👋</div>
                <p style="margin-bottom: 24px; color: var(--text-secondary);">登录后可使用更多功能</p>
                <a href="{{ url_for('login') }}" style="display: inline-block; padding: 14px 40px; background: linear-gradient(135deg, #1abc9c 0%, #16a089 100%); color: white; border-radius: 25px; text-decoration: none; font-size: 16px; font-weight: 600;">
                    立即登录
                </a>
            </div>
            {% endif %}
        </div>
    </div>
</main>
```

**Step 3: 修改 blog.py - 添加 JSON 支持**

在 `backend/routes/blog.py` 的 index 函数中添加 JSON 格式支持：

```python
@blog_bp.route('/')
def index():
    """首页 - 列出所有已发布的文章"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    format = request.args.get('format', 'html')

    # 验证 per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(include_drafts=False, page=page, per_page=per_page)
    categories = get_all_categories()
    popular_tags = get_popular_tags(limit=10)

    # JSON 格式支持（用于无限滚动）
    if format == 'json':
        posts_list = []
        for post in posts_data['posts']:
            posts_list.append({
                'id': post['id'],
                'title': post['title'],
                'content': post['content'],
                'excerpt': post.get('excerpt', '')[:100] if post.get('excerpt') else post['content'][:100],
                'category_name': post.get('category_name'),
                'author_display_name': post.get('author_display_name'),
                'created_at': post['created_at'].isoformat() if hasattr(post['created_at'], 'isoformat') else str(post['created_at']),
                'like_count': post.get('like_count', 0),
                'comment_count': post.get('comment_count', 0)
            })

        return jsonify({
            'posts': posts_list,
            'page': posts_data['page'],
            'total_pages': posts_data['total_pages'],
            'total': posts_data['total']
        })

    # 获取所有标签和分类供移动端使用
    all_tags = get_all_tags()
    import json
    all_tags_json = json.dumps([{'id': t['id'], 'name': t['name']} for t in all_tags])
    all_categories_json = json.dumps([{'id': c['id'], 'name': c['name']} for c in categories])

    return render_template('index.html',
                         posts=posts_data['posts'],
                         categories=categories,
                         popular_tags=popular_tags,
                         pagination=posts_data,
                         all_tags=all_tags_json,
                         all_categories=all_categories_json)
```

**Step 4: 添加模板过滤器**

在 Flask 应用中添加两个模板过滤器（在 `backend/app.py` 中）：

```python
import re
from datetime import datetime

def extract_first_image(content):
    """从内容中提取第一张图片"""
    if not content:
        return None
    match = re.search(r'<img[^>]+src="([^"]+)"', content)
    return match.group(1) if match else None

def timeago(date):
    """时间格式化为相对时间"""
    if not date:
        return ''
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        except:
            return date[:10]
    now = datetime.now()
    diff = now - date
    seconds = diff.total_seconds()
    if seconds < 60:
        return '刚刚'
    elif seconds < 3600:
        return f'{int(seconds/60)}分钟前'
    elif seconds < 86400:
        return f'{int(seconds/3600)}小时前'
    elif seconds < 604800:
        return f'{int(seconds/86400)}天前'
    else:
        return date.strftime('%Y-%m-%d')

# 注册过滤器
app.jinja_env.filters['extract_first_image'] = extract_first_image
app.jinja_env.filters['timeago'] = timeago
```

**Step 5: 提交**

```bash
git add templates/base.html templates/index.html backend/routes/blog.py backend/app.py
git commit -m "feat: integrate mobile weibo layout into templates"
```

---

### Task 6: 测试验证功能

**Files:**
- 无新建文件，测试现有功能

**Step 1: 启动开发服务器**

```bash
# 确保虚拟环境已激活
source .venv/bin/activate

# 启动 Flask 开发服务器
cd /Users/gn/simple-blog/.worktrees/feature-weibo-mobile
FLASK_ENV=development FLASK_APP=backend/app.py flask run --host=0.0.0.0 --port=5000
```

**Step 2: 移动端功能测试清单**

在浏览器开发者工具中切换到移动设备模式（iPhone SE/iPhone 12/Android 等），测试：

1. **底部导航**
   - ✓ 5个导航按钮显示正常
   - ✓ 点击切换页面
   - ✓ 中央发布按钮凸起设计
   - ✓ 激活状态高亮

2. **文章卡片**
   - ✓ 大图在上的卡片布局
   - ✓ 占位图正确显示
   - ✓ 元数据显示正常（分类、作者、时间）
   - ✓ 互动按钮显示

3. **下拉刷新**
   - ✓ 下拉时显示刷新指示器
   - ✓ 达到阈值触发刷新
   - ✓ 回弹动画正常

4. **无限滚动**
   - ✓ 滚动到底部自动加载
   - ✓ 加载指示器显示
   - ✓ 新卡片正确追加

5. **快速发布编辑器**
   - ✓ 点击发布按钮打开编辑器
   - ✓ 沉浸式全屏面板
   - ✓ 文本输入正常
   - ✓ 草稿自动保存
   - ✓ 标签选择器
   - ✓ 分类选择器
   - ✓ 图片选择预览
   - ✓ 关闭和发布按钮

6. **发现页面**
   - ✓ 搜索框显示
   - ✓ 热门标签显示
   - ✓ 分类网格显示

7. **我的文章**
   - ✓ Tab 切换
   - ✓ 内容显示正常

8. **个人中心**
   - ✓ 用户信息显示
   - ✓ 菜单项正常
   - ✓ 登录/退出按钮

9. **暗色主题**
   - ✓ 切换暗色主题
   - ✓ 所有移动端元素正确适配

**Step 3: 桌面端兼容性测试**

调整浏览器宽度 > 768px，验证：
- ✓ 桌面端布局正常
- ✓ 移动端元素隐藏
- ✓ 原有功能不受影响

**Step 4: 最终提交（如果有修复）**

```bash
git add .
git commit -m "fix: weibo mobile layout bug fixes"
```

---

## 执行选项

Plan complete and saved to `docs/plans/2026-02-28-weibo-mobile-design.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
