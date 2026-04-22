// PWA utilities: install prompt, online status, theme sync

(function() {
    'use strict';

    const STORAGE_KEY = 'pwa_banner_dismissed';
    const DISMISS_DAYS = 7;

    function isStandalone() {
        return window.matchMedia('(display-mode: standalone)').matches ||
               window.navigator.standalone === true;
    }

    function wasBannerDismissed() {
        try {
            const dismissed = localStorage.getItem(STORAGE_KEY);
            if (!dismissed) return false;
            const dismissedAt = parseInt(dismissed, 10);
            const now = Date.now();
            const daysElapsed = (now - dismissedAt) / (1000 * 60 * 60 * 24);
            return daysElapsed < DISMISS_DAYS;
        } catch (e) {
            return false;
        }
    }

    function dismissBanner() {
        try {
            localStorage.setItem(STORAGE_KEY, String(Date.now()));
        } catch (e) {
            // Ignore storage errors
        }
        const banner = document.getElementById('pwaInstallBanner');
        if (banner) {
            banner.style.display = 'none';
        }
    }

    function showInstallBanner() {
        if (isStandalone()) return;
        if (wasBannerDismissed()) return;

        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
        if (!isIOS || !isSafari) return;

        const banner = document.createElement('div');
        banner.id = 'pwaInstallBanner';
        banner.className = 'pwa-install-banner';
        banner.innerHTML = `
            <div class="pwa-banner-content">
                <span class="pwa-banner-text">添加到主屏幕，离线也能阅读</span>
                <button class="pwa-banner-btn pwa-banner-primary" id="pwaShowSteps">查看方法</button>
                <button class="pwa-banner-btn pwa-banner-secondary" id="pwaDismiss">不再提示</button>
            </div>
        `;
        document.body.appendChild(banner);

        document.getElementById('pwaDismiss').addEventListener('click', dismissBanner);
        document.getElementById('pwaShowSteps').addEventListener('click', showInstallSteps);
    }

    function showInstallSteps() {
        const modal = document.createElement('div');
        modal.className = 'pwa-steps-modal';
        modal.innerHTML = `
            <div class="pwa-steps-overlay" onclick="this.parentElement.remove()"></div>
            <div class="pwa-steps-content">
                <h3>添加到主屏幕</h3>
                <ol>
                    <li>点击 Safari 底部的 <strong>分享</strong> 按钮 <span class="pwa-share-icon">&#9650;</span></li>
                    <li>向上滑动，点击 <strong>添加到主屏幕</strong></li>
                    <li>点击右上角的 <strong>添加</strong></li>
                </ol>
                <button class="pwa-steps-close" onclick="this.closest('.pwa-steps-modal').remove()">知道了</button>
            </div>
        `;
        document.body.appendChild(modal);
    }

    function setupOnlineStatus() {
        function showStatus(online) {
            if (window.showAppToast) {
                const message = online ? '已恢复在线' : '已切换到离线模式，已缓存的文章仍可阅读';
                window.showAppToast(message, online ? 'success' : 'info');
            }
        }

        window.addEventListener('online', function() {
            console.log('[PWA] Online');
            showStatus(true);
        });

        window.addEventListener('offline', function() {
            console.log('[PWA] Offline');
            showStatus(false);
        });
    }

    function syncThemeColor() {
        const meta = document.getElementById('themeColorMeta');
        if (!meta) return;

        function update() {
            const isDark = document.documentElement.classList.contains('dark-theme') ||
                          document.body.classList.contains('dark-theme');
            meta.content = isDark ? '#065f46' : '#10b981';
        }

        const observer = new MutationObserver(update);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

        update();
    }

    document.addEventListener('DOMContentLoaded', function() {
        showInstallBanner();
        setupOnlineStatus();
        syncThemeColor();
    });
})();
