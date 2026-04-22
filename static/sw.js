// PWA Service Worker with three-layer caching

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const PAGE_CACHE = `pages-${CACHE_VERSION}`;
const IMAGE_CACHE = `images-${CACHE_VERSION}`;

const PRECACHE_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/css/enhancements.css',
    '/static/css/mobile-weibo.css',
    '/static/css/pc-feed.css',
    '/static/js/bundle.js',
    '/static/js/enhancements.js',
    '/static/js/infinite-scroll.js',
    '/static/js/theme.js',
    '/static/icon-180.png',
    '/static/icon-192.png',
    '/static/icon-512.png',
];

self.addEventListener('install', function(event) {
    console.log('[SW] Installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(function(cache) {
                return cache.addAll(PRECACHE_ASSETS);
            })
            .then(function() {
                return self.skipWaiting();
            })
            .catch(function(error) {
                console.log('[SW] Pre-cache failed:', error);
            })
    );
});

self.addEventListener('activate', function(event) {
    console.log('[SW] Activating...');
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (!cacheName.endsWith(CACHE_VERSION)) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(function() {
            return self.clients.claim();
        })
    );
});

function getCacheStrategy(request) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    if (pathname.match(/\.(css|js|woff2?|ttf|png|ico)$/)) {
        return 'static';
    }

    if (pathname.match(/\.(jpg|jpeg|gif|webp|svg|png)$/) && pathname.includes('/uploads/')) {
        return 'image';
    }

    if (request.mode === 'navigate' || (request.headers.get('accept') && request.headers.get('accept').includes('text/html'))) {
        return 'page';
    }

    if (pathname.startsWith('/api/')) {
        return 'network';
    }

    return 'network';
}

self.addEventListener('fetch', function(event) {
    const strategy = getCacheStrategy(event.request);

    if (strategy === 'static') {
        event.respondWith(
            caches.match(event.request).then(function(cachedResponse) {
                if (cachedResponse) {
                    return cachedResponse;
                }
                return fetch(event.request).then(function(networkResponse) {
                    if (!networkResponse || networkResponse.status !== 200) {
                        return networkResponse;
                    }
                    const clonedResponse = networkResponse.clone();
                    caches.open(STATIC_CACHE).then(function(cache) {
                        cache.put(event.request, clonedResponse);
                    });
                    return networkResponse;
                });
            })
        );
    } else if (strategy === 'page') {
        event.respondWith(
            fetch(event.request)
                .then(function(networkResponse) {
                    if (!networkResponse || networkResponse.status !== 200) {
                        throw new Error('Network response not ok');
                    }
                    const clonedResponse = networkResponse.clone();
                    caches.open(PAGE_CACHE).then(function(cache) {
                        cache.put(event.request, clonedResponse);
                    });
                    return networkResponse;
                })
                .catch(function() {
                    return caches.match(event.request).then(function(cachedResponse) {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        return caches.match('/');
                    });
                })
        );
    } else if (strategy === 'image') {
        event.respondWith(
            caches.match(event.request).then(function(cachedResponse) {
                const fetchPromise = fetch(event.request).then(function(networkResponse) {
                    if (networkResponse && networkResponse.status === 200) {
                        const clonedResponse = networkResponse.clone();
                        caches.open(IMAGE_CACHE).then(function(cache) {
                            cache.put(event.request, clonedResponse);
                        });
                    }
                    return networkResponse;
                }).catch(function() {
                    return cachedResponse;
                });

                return cachedResponse || fetchPromise;
            })
        );
    }
});
