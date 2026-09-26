/**
 * 全站共享工具函数（挂在 window.SB 上，避免全局命名冲突）。
 * 需在其它页面脚本之前加载（见 base.html）。
 */
(function () {
    'use strict';

    // 转义 HTML：同时处理属性场景，比 DOM 方案多转义引号
    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // 后端时间字符串（naive UTC，无时区后缀）按 UTC 解析，避免差 8 小时
    function parseServerDate(value) {
        if (!value) return null;
        if (typeof value !== 'string') {
            const d = new Date(value);
            return Number.isNaN(d.getTime()) ? null : d;
        }
        let s = value.trim();
        if (!/[zZ]$|[+-]\d{2}:?\d{2}$/.test(s)) {
            s = s.replace(' ', 'T') + 'Z';
        }
        const d = new Date(s);
        return Number.isNaN(d.getTime()) ? null : d;
    }

    // 后端时间 -> 本地日期 'YYYY-MM-DD'
    function formatLocalDate(value) {
        const d = parseServerDate(value);
        if (!d) return '';
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return y + '-' + m + '-' + day;
    }

    // 防抖
    function debounce(fn, wait) {
        let timer = null;
        return function () {
            const args = arguments;
            const ctx = this;
            if (timer) clearTimeout(timer);
            timer = setTimeout(function () { fn.apply(ctx, args); }, wait);
        };
    }

    // 轻提示：优先复用全局 showAppToast
    function showToast(message, type) {
        if (typeof window.showAppToast === 'function') {
            window.showAppToast(message, type);
            return;
        }
        const toast = document.createElement('div');
        toast.className = 'toast-message';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(function () { toast.classList.add('show'); }, 10);
        setTimeout(function () {
            toast.classList.remove('show');
            setTimeout(function () { toast.remove(); }, 300);
        }, 2000);
    }

    window.SB = {
        escapeHtml: escapeHtml,
        parseServerDate: parseServerDate,
        formatLocalDate: formatLocalDate,
        debounce: debounce,
        showToast: showToast,
    };
})();
