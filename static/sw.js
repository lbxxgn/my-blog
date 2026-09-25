/**
 * 最小 Service Worker —— 仅用于满足 PWA 安装条件（Chrome 要求存在 SW），
 * 不做任何离线缓存：所有请求直接由浏览器发起。
 *
 * 由 templates/base.html 在 HTTPS 或 localhost 环境下注册（/sw.js）。
 */
self.addEventListener('install', function (event) {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function (event) {
    // 不做缓存，直接透传，保证始终拿到最新内容
    event.respondWith(fetch(event.request));
});
