// 全局命令面板（Cmd/Ctrl+K）
// 依赖：base.html 的 getCsrfToken/showAppToast；shortcuts.js 触发 open
(function () {
    'use strict';

    var SEARCH_URL = '/api/search/all';
    var MAX_RESULTS = 20;
    var DEBOUNCE_MS = 250;

    var overlay = null;
    var input = null;
    var resultsEl = null;
    var activeIndex = -1;
    var currentItems = [];
    var debounceTimer = null;
    var abortController = null;

    function isLoggedIn() {
        return !!document.getElementById('themeToggleNav') ||
            !!document.querySelector('.nav-links .dropdown .user-icon');
    }

    function esc(text) {
        var div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    function getActions() {
        var actions = [
            { icon: '✏️', title: '写文章', desc: '打开博客编辑器', badge: 'Ctrl+N', run: function () { location.href = '/admin/new'; } },
            { icon: '📚', title: '写文档', desc: '在知识库新建文档', run: function () { location.href = '/knowledge/doc/new'; } },
            { icon: '⚡', title: '快速记录', desc: '打开快速记事', run: function () { location.href = '/knowledge_base/quick-note'; } },
            { icon: '📖', title: '去回顾', desc: '每日回顾', run: function () { location.href = '/review'; } },
            { icon: '🔍', title: '搜索', desc: '打开搜索页', run: function () { location.href = '/search'; } },
            { icon: '🗂️', title: '知识库', desc: '浏览知识库', run: function () { location.href = '/knowledge'; } },
            { icon: '🌙', title: '切换主题', desc: '亮色 / 暗色模式', run: toggleTheme }
        ];
        return actions;
    }

    // 与 base.js 的主题切换保持同一数据源（localStorage 'theme' + body.dark-theme）
    function toggleTheme() {
        var isDark = document.body.classList.contains('dark-theme');
        var newTheme = isDark ? 'light' : 'dark';
        if (newTheme === 'dark') {
            document.body.classList.add('dark-theme');
        } else {
            document.body.classList.remove('dark-theme');
        }
        localStorage.setItem('theme', newTheme);
        var icon = newTheme === 'dark' ? '☀️' : '🌙';
        var navIcon = document.querySelector('#themeToggleNav .theme-toggle-nav-icon');
        if (navIcon) navIcon.textContent = icon;
        close();
    }

    function buildDom() {
        overlay = document.createElement('div');
        overlay.className = 'cmdk-overlay';
        overlay.innerHTML =
            '<div class="cmdk-panel" role="dialog" aria-label="命令面板">' +
            '  <div class="cmdk-input-row">' +
            '    <span class="cmdk-icon">🔍</span>' +
            '    <input type="text" class="cmdk-input" placeholder="搜索文章、卡片、文档、批注，或执行动作…" autocomplete="off">' +
            '    <span class="cmdk-esc-hint">Esc 关闭</span>' +
            '  </div>' +
            '  <div class="cmdk-results"></div>' +
            '</div>';
        document.body.appendChild(overlay);
        input = overlay.querySelector('.cmdk-input');
        resultsEl = overlay.querySelector('.cmdk-results');

        overlay.addEventListener('mousedown', function (e) {
            if (e.target === overlay) close();
        });
        input.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () { render(input.value.trim()); }, DEBOUNCE_MS);
        });
        // keydown 在 document 捕获阶段统一处理（见 bindKeys）
    }

    function bindKeys() {
        document.addEventListener('keydown', function (e) {
            if (!overlay) return;
            if (e.key === 'Escape') {
                e.stopImmediatePropagation();
                close();
                return;
            }
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                move(e.key === 'ArrowDown' ? 1 : -1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                execute(activeIndex >= 0 ? activeIndex : 0);
            }
        });
    }

    function move(delta) {
        if (!currentItems.length) return;
        activeIndex = (activeIndex + delta + currentItems.length) % currentItems.length;
        highlight();
    }

    function highlight() {
        var nodes = resultsEl.querySelectorAll('.cmdk-item');
        nodes.forEach(function (n, i) { n.classList.toggle('is-active', i === activeIndex); });
        var active = nodes[activeIndex];
        if (active && active.scrollIntoView) active.scrollIntoView({ block: 'nearest' });
    }

    function execute(index) {
        var item = currentItems[index];
        if (!item) return;
        if (item.url) {
            location.href = item.url;
        } else if (typeof item.run === 'function') {
            item.run();
        }
    }

    function itemHtml(item) {
        var title = item.url
            ? '<a href="' + esc(item.url) + '">' + esc(item.title) + '</a>'
            : esc(item.title);
        return '<div class="cmdk-item" data-index="' + item._idx + '">' +
            '<span class="cmdk-item-icon">' + item.icon + '</span>' +
            '<div class="cmdk-item-body">' +
            '<div class="cmdk-item-title">' + title + '</div>' +
            (item.desc ? '<div class="cmdk-item-desc">' + esc(item.desc) + '</div>' : '') +
            '</div>' +
            (item.badge ? '<span class="cmdk-item-badge">' + esc(item.badge) + '</span>' : '') +
            '</div>';
    }

    function renderActions(query) {
        var actions = getActions().filter(function (a) {
            if (!query) return true;
            return (a.title + a.desc).toLowerCase().indexOf(query.toLowerCase()) !== -1;
        });
        currentItems = actions.map(function (a, i) {
            a.icon = a.icon || '›';
            a._idx = i;
            return a;
        });
        activeIndex = currentItems.length ? 0 : -1;
        resultsEl.innerHTML = currentItems.length
            ? '<div class="cmdk-group-title">动作</div>' + currentItems.map(itemHtml).join('')
            : '<div class="cmdk-empty">无结果，回车去搜索页搜索</div>';
        bindItems();
    }

    function bindItems() {
        resultsEl.querySelectorAll('.cmdk-item').forEach(function (node) {
            node.addEventListener('click', function () { execute(Number(node.dataset.index)); });
            node.addEventListener('mousemove', function () {
                var idx = Number(node.dataset.index);
                if (idx !== activeIndex) { activeIndex = idx; highlight(); }
            });
        });
        highlight();
    }

    function renderSearch(query) {
        if (abortController) abortController.abort();
        abortController = new AbortController();
        resultsEl.innerHTML = '<div class="cmdk-loading">搜索中…</div>';
        fetch(SEARCH_URL + '?q=' + encodeURIComponent(query) + '&limit=6', {
            headers: { 'Accept': 'application/json', 'X-CSRFToken': window.getCsrfToken ? window.getCsrfToken() : '' },
            credentials: 'same-origin',
            signal: abortController.signal
        }).then(function (res) {
            if (res.status === 401) throw new Error('unauthorized');
            if (!res.ok) throw new Error('http_' + res.status);
            return res.json();
        }).then(function (data) {
            renderResults(query, data || {});
        }).catch(function (err) {
            if (err && err.name === 'AbortError') return;
            if (err && err.message === 'unauthorized') {
                close();
                if (window.showAppToast) window.showAppToast('请先登录', 'error');
                return;
            }
            resultsEl.innerHTML = '<div class="cmdk-empty">搜索出错，回车去搜索页搜索</div>';
            currentItems = [{ title: '去搜索页搜索「' + query + '」', icon: '🔍', url: '/search?q=' + encodeURIComponent(query), _idx: 0 }];
            activeIndex = 0;
            bindItems();
        });
    }

    function renderResults(query, data) {
        var groups = [];
        var matchedActions = getActions().filter(function (a) {
            return (a.title + a.desc).toLowerCase().indexOf(query.toLowerCase()) !== -1;
        });
        if (matchedActions.length) groups.push({ title: '动作', items: matchedActions });

        (data.posts || []).forEach(function (p) {
            groups.push({
                title: '文章', icon: '📝',
                items: [{ title: p.title, desc: p.excerpt || p.date || '', url: p.url || '/post/' + p.id }]
            });
        });
        (data.cards || []).forEach(function (c) {
            groups.push({
                title: '卡片', icon: '🗂️',
                items: [{ title: c.title || '（无标题卡片）', desc: (c.excerpt || '') + (c.tags && c.tags.length ? ' #' + c.tags.join(' #') : '') }]
            });
        });
        (data.docs || []).forEach(function (d) {
            groups.push({
                title: '文档', icon: '📚',
                items: [{ title: d.title, desc: d.excerpt || '', url: d.url || '/knowledge/doc/' + d.id }]
            });
        });
        (data.annotations || []).forEach(function (a) {
            groups.push({
                title: '批注', icon: '💬',
                items: [{ title: a.text || a.note || '批注', desc: a.note || a.source_url || '' }]
            });
        });

        var flat = [];
        var html = '';
        var lastGroup = null;
        groups.forEach(function (g) {
            g.items.forEach(function (item) {
                if (flat.length >= MAX_RESULTS) return;
                item.icon = item.icon || g.icon || '›';
                item._idx = flat.length;
                if (g.title !== lastGroup) {
                    html += '<div class="cmdk-group-title">' + esc(g.title) + '</div>';
                    lastGroup = g.title;
                }
                html += itemHtml(item);
                flat.push(item);
            });
        });

        if (!flat.length) {
            html = '<div class="cmdk-empty">无结果，回车去搜索页搜索</div>';
            flat.push({ title: '去搜索页搜索「' + query + '」', icon: '🔍', url: '/search?q=' + encodeURIComponent(query), _idx: 0 });
        }
        currentItems = flat;
        activeIndex = flat.length ? 0 : -1;
        resultsEl.innerHTML = html;
        bindItems();
    }

    function render(query) {
        if (!query) {
            renderActions('');
        } else {
            renderActions(query); // 同步渲染动作匹配项
            renderSearch(query);
        }
    }

    function open() {
        if (!isLoggedIn()) return;
        if (!overlay) { buildDom(); bindKeys(); }
        overlay.style.display = 'flex';
        render('');
        setTimeout(function () { input.focus(); input.select(); }, 0);
    }

    function close() {
        if (overlay) overlay.style.display = 'none';
        clearTimeout(debounceTimer);
        if (abortController) abortController.abort();
    }

    window.CommandPalette = { open: open, close: close, isOpen: function () { return !!(overlay && overlay.style.display !== 'none'); } };

    document.addEventListener('DOMContentLoaded', function () {
        // 桌面导航栏 ⌘K 按钮（仅登录、宽屏显示由 CSS 控制）
        if (!isLoggedIn()) return;
        var searchForm = document.querySelector('.search-form-nav');
        if (!searchForm) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'cmdk-nav-btn';
        btn.innerHTML = '<span>⌘K</span>';
        btn.title = '打开命令面板';
        btn.addEventListener('click', function (e) { e.preventDefault(); open(); });
        searchForm.parentNode.insertBefore(btn, searchForm.nextSibling);
    });
})();
