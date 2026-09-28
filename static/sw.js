/**
 * 最小 Service Worker —— 仅用于满足 PWA 安装条件（部分 Chrome 需要存在 SW），
 * 不做任何离线缓存，也不拦截请求。
 *
 * 注意：不要在这里调用 event.respondWith(fetch(event.request))。
 * 那样会在任意请求失败（证书未信任 / 断网 / 请求被中断等）时让 respondWith 的
 * Promise reject，Safari 会报：
 *   FetchEvent.respondWith received an error: TypeError: Load failed
 * 这里保留一个空的 fetch 监听（不调用 respondWith），请求完全交给浏览器处理。
 */
self.addEventListener('install', function () {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function () {
    // 故意留空：不拦截、不 respondWith，交给浏览器直接处理。
});
