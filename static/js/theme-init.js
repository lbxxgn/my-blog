/**
 * 首帧前应用主题，避免暗色闪烁（FOUC）。
 *
 * 必须同步加载（不要加 defer），并在 <body> 开头执行：
 * 提前给 body 加上 dark-theme，后续样式才会按暗色渲染。
 * 与 base.js 的主题切换逻辑保持同一数据源（localStorage.theme）。
 */
(function () {
    'use strict';
    try {
        var theme = localStorage.getItem('theme');
        if (theme !== 'dark' && theme !== 'light') {
            theme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
                ? 'dark'
                : 'light';
        }
        if (theme === 'dark') {
            document.body.classList.add('dark-theme');
        }
    } catch (error) {
        // localStorage 不可用（隐私模式等）时退回系统配色
    }
})();
