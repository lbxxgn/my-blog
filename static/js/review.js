/**
 * 回顾页 + 首页侧边栏「那年今日」小组件
 * 按元素存在性初始化，无需库依赖。
 */
(function () {
    'use strict';

    var TYPE_LABELS = { post: '文章', note: '笔记', knowledge: '知识库', card: '卡片' };
    var STATUS_LABELS = { idea: '想法', draft: '草稿', incubating: '孵化中', published: '已发布' };

    function escapeHTML(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function fetchJSON(url, options) {
        return fetch(url, options).then(function (resp) {
            if (!resp.ok && resp.status !== 202) {
                throw new Error('HTTP ' + resp.status);
            }
            return resp.json();
        });
    }

    function formatDate(d) {
        var m = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        return d.getFullYear() + '-' + m + '-' + day;
    }

    // ==================== 写作热力图 ====================

    function heatLevel(count) {
        if (count <= 0) return '';
        if (count === 1) return 'lv1';
        if (count <= 3) return 'lv2';
        if (count <= 6) return 'lv3';
        return 'lv4';
    }

    function renderHeatmap(el, activity, days) {
        el.innerHTML = '';
        var today = new Date();
        today.setHours(0, 0, 0, 0);

        // 起点对齐到周日，保证每列是完整的一周
        var start = new Date(today);
        start.setDate(start.getDate() - (days - 1));
        start.setDate(start.getDate() - start.getDay());

        var total = 0;
        var activeDays = 0;
        var fragment = document.createDocumentFragment();
        var cursor = new Date(start);
        while (cursor <= today) {
            var key = formatDate(cursor);
            var count = activity[key] || 0;
            total += count;
            if (count > 0) activeDays += 1;
            var cell = document.createElement('span');
            cell.className = 'hm-cell' + (heatLevel(count) ? ' ' + heatLevel(count) : '');
            cell.title = key + '：' + count + ' 条记录';
            fragment.appendChild(cell);
            cursor.setDate(cursor.getDate() + 1);
        }
        el.appendChild(fragment);

        // 连续记录天数：今天还没写则从昨天往前数
        var streak = 0;
        var streakCursor = new Date(today);
        if (!(activity[formatDate(streakCursor)] > 0)) {
            streakCursor.setDate(streakCursor.getDate() - 1);
        }
        while (activity[formatDate(streakCursor)] > 0) {
            streak += 1;
            streakCursor.setDate(streakCursor.getDate() - 1);
        }

        return { total: total, activeDays: activeDays, streak: streak };
    }

    function initHeatmap() {
        var el = document.getElementById('heatmap');
        if (!el) return;
        var statsEl = document.getElementById('heatmap-stats');
        fetchJSON('/api/review/activity?days=371').then(function (data) {
            var activity = (data && data.activity) || {};
            var stats = renderHeatmap(el, activity, (data && data.days) || 371);
            if (statsEl) {
                statsEl.innerHTML = '连续记录 <strong>' + stats.streak + '</strong> 天' +
                    ' · 近一年 <strong>' + stats.total + '</strong> 条' +
                    ' · 活跃 <strong>' + stats.activeDays + '</strong> 天';
            }
        }).catch(function () {
            if (statsEl) statsEl.textContent = '热力数据加载失败';
        });
    }

    // ==================== 那年今日 ====================

    function todayItemHTML(item) {
        var badge = '<span class="review-badge">' + (TYPE_LABELS[item.type] || escapeHTML(item.type)) + '</span>';
        var inner = badge +
            '<span class="review-item-year">' + escapeHTML(item.year) + '</span>' +
            '<span class="review-item-title">' + escapeHTML(item.title) + '</span>' +
            (item.excerpt ? '<span class="review-item-excerpt">' + escapeHTML(item.excerpt) + '</span>' : '');
        if (item.url) {
            return '<a class="review-item" href="' + escapeHTML(item.url) + '">' + inner + '</a>';
        }
        return '<div class="review-item">' + inner + '</div>';
    }

    function initToday() {
        var el = document.getElementById('today-list');
        if (!el) return;
        fetchJSON('/api/review/today').then(function (data) {
            var items = (data && data.items) || [];
            if (!items.length) {
                el.innerHTML = '<p class="review-empty">历史上的今天还没有留下记录，去写点什么吧。</p>';
                return;
            }
            el.innerHTML = items.map(todayItemHTML).join('');
        }).catch(function () {
            el.innerHTML = '<p class="review-empty">加载失败，请刷新重试。</p>';
        });
    }

    // ==================== 随机漫步 ====================

    function cardItemHTML(card) {
        var tags = (card.tags || []).map(function (t) {
            return '<span class="review-tag">#' + escapeHTML(t) + '</span>';
        }).join('');
        return '<div class="review-card">' +
            '<div class="review-card-head">' +
            '<span class="review-item-title">' + escapeHTML(card.title) + '</span>' +
            '<span class="review-badge">' + (STATUS_LABELS[card.status] || escapeHTML(card.status)) + '</span>' +
            '</div>' +
            (card.excerpt ? '<p class="review-item-excerpt">' + escapeHTML(card.excerpt) + '</p>' : '') +
            (tags ? '<div class="review-tags">' + tags + '</div>' : '') +
            '</div>';
    }

    function initRandom() {
        var list = document.getElementById('random-list');
        if (!list) return;
        var btn = document.getElementById('random-refresh');

        function load() {
            if (btn) btn.disabled = true;
            fetchJSON('/api/review/random').then(function (data) {
                var cards = (data && data.cards) || [];
                list.innerHTML = cards.length
                    ? cards.map(cardItemHTML).join('')
                    : '<p class="review-empty">还没有卡片，先用浏览器插件或快速记事收集一些灵感吧。</p>';
            }).catch(function () {
                list.innerHTML = '<p class="review-empty">加载失败，请刷新重试。</p>';
            }).finally(function () {
                if (btn) btn.disabled = false;
            });
        }

        if (btn) btn.addEventListener('click', load);
        load();
    }

    // ==================== 每周回顾 ====================

    function initWeekly() {
        var list = document.getElementById('weekly-list');
        var btn = document.getElementById('weekly-generate');
        var statusBox = document.getElementById('weekly-status');
        if (!list || !btn) return;

        function loadList() {
            fetchJSON('/api/review/weekly').then(function (data) {
                var reviews = (data && data.reviews) || [];
                if (!reviews.length) {
                    list.innerHTML = '<p class="review-empty">还没有每周回顾，点击右上角按钮生成第一篇。</p>';
                    return;
                }
                list.innerHTML = reviews.map(function (r) {
                    return '<a class="review-item" href="' + escapeHTML(r.url) + '">' +
                        '<span class="review-item-title">' + escapeHTML(r.title) + '</span>' +
                        '<span class="review-item-date">' + escapeHTML(r.created_local || '') + '</span>' +
                        '</a>';
                }).join('');
            }).catch(function () {
                list.innerHTML = '<p class="review-empty">加载失败，请刷新重试。</p>';
            });
        }

        function setBusy(busy, message) {
            btn.disabled = busy;
            if (statusBox) {
                if (message) {
                    statusBox.style.display = '';
                    statusBox.textContent = message;
                } else {
                    statusBox.style.display = 'none';
                    statusBox.textContent = '';
                }
            }
        }

        function pollStatus(attemptsLeft) {
            fetchJSON('/api/review/weekly/status').then(function (state) {
                if (state.status === 'done' || state.status === 'exists') {
                    setBusy(false);
                    if (window.showAppToast) window.showAppToast('本周回顾已生成');
                    loadList();
                } else if (state.status === 'error') {
                    setBusy(false, '生成失败：' + (state.error || '未知错误'));
                } else if (attemptsLeft > 0) {
                    setTimeout(function () { pollStatus(attemptsLeft - 1); }, 3000);
                } else {
                    setBusy(false, '生成时间较长，请稍后手动刷新查看。');
                }
            }).catch(function () {
                if (attemptsLeft > 0) {
                    setTimeout(function () { pollStatus(attemptsLeft - 1); }, 3000);
                } else {
                    setBusy(false, '状态查询失败，请稍后手动刷新查看。');
                }
            });
        }

        btn.addEventListener('click', function () {
            setBusy(true, '正在生成本周回顾，通常需要 30-60 秒…');
            fetchJSON('/api/review/weekly/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.getCsrfToken()
                },
                body: '{}'
            }).then(function (data) {
                if (data && data.status === 'exists') {
                    setBusy(false);
                    if (window.showAppToast) window.showAppToast('本周回顾已存在');
                    loadList();
                } else {
                    pollStatus(40); // 最多轮询约 2 分钟
                }
            }).catch(function () {
                setBusy(false, '请求失败，请稍后重试。');
            });
        });

        loadList();
    }

    // ==================== 首页侧边栏小组件 ====================

    function initSidebarWidget() {
        var widget = document.getElementById('review-sidebar-widget');
        if (!widget) return;
        var todayEl = document.getElementById('sidebar-today');
        var randomWrap = document.getElementById('sidebar-random-wrap');
        var randomEl = document.getElementById('sidebar-random');
        var switchBtn = document.getElementById('sidebar-card-switch');

        // 那年今日（前 3 条）
        fetchJSON('/api/review/today').then(function (data) {
            var items = ((data && data.items) || []).slice(0, 3);
            if (!items.length) {
                todayEl.innerHTML = '<p class="review-empty">历史上的今天还没有记录</p>';
                return;
            }
            todayEl.innerHTML = items.map(function (item) {
                var inner = '<span class="review-item-year">' + escapeHTML(item.year) + '</span>' +
                    '<span class="review-item-title">' + escapeHTML(item.title) + '</span>';
                return item.url
                    ? '<a class="review-item review-item-sm" href="' + escapeHTML(item.url) + '">' + inner + '</a>'
                    : '<div class="review-item review-item-sm">' + inner + '</div>';
            }).join('') + '<a class="review-more" href="/review">查看全部回顾 →</a>';
        }).catch(function () {
            todayEl.innerHTML = '<p class="review-empty">加载失败</p>';
        });

        // 随机卡片（换一张）
        var sidebarCards = [];
        var currentCardId = null;

        function renderSidebarCard() {
            if (!sidebarCards.length) {
                if (randomWrap) randomWrap.style.display = 'none';
                return;
            }
            var candidates = sidebarCards.filter(function (c) { return c.id !== currentCardId; });
            if (!candidates.length) candidates = sidebarCards;
            var card = candidates[Math.floor(Math.random() * candidates.length)];
            currentCardId = card.id;
            randomEl.innerHTML =
                '<div class="review-card review-card-sm">' +
                '<div class="review-item-title">' + escapeHTML(card.title) + '</div>' +
                (card.excerpt ? '<p class="review-item-excerpt">' + escapeHTML(card.excerpt) + '</p>' : '') +
                '</div>';
        }

        fetchJSON('/api/review/random').then(function (data) {
            sidebarCards = (data && data.cards) || [];
            if (sidebarCards.length && randomWrap) {
                randomWrap.style.display = '';
                renderSidebarCard();
            }
        }).catch(function () { /* 侧边栏失败静默 */ });

        if (switchBtn) {
            switchBtn.addEventListener('click', renderSidebarCard);
        }
    }

    // ==================== 启动 ====================

    document.addEventListener('DOMContentLoaded', function () {
        initHeatmap();
        initToday();
        initRandom();
        initWeekly();
        initSidebarWidget();
    });
})();
