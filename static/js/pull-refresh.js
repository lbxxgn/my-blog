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
            spinner.style.animation = 'none';
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
            spinner.style.animation = '';
        }
    }

    async function startRefresh() {
        if (isRefreshing) return;

        isRefreshing = true;

        const indicator = document.getElementById('pullRefreshIndicator');
        if (indicator) {
            indicator.classList.add('refreshing');
            const spinner = indicator.querySelector('.spinner');
            if (spinner) {
                spinner.style.animation = 'spin 0.8s linear infinite';
            }
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
