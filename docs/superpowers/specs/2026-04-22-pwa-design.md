# PWA (Progressive Web App) Design

## Overview

Transform the blog into an installable Progressive Web App optimized for iPhone, enabling offline reading, home-screen installation, and a native-app-like experience while preserving all existing features.

## Goals

- Allow users to add the blog to their iPhone home screen with a standalone icon
- Enable offline reading of previously loaded articles and static assets
- Provide fast subsequent loads through caching
- Maintain a non-intrusive install prompt that respects user choice

## Non-Goals

- Push notifications (limited iOS support, not reliable enough)
- Background sync (not supported on iOS Safari)
- App Store distribution (pure web PWA only)

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `static/manifest.json` | Web App Manifest: app name, icons, theme color, display mode |
| `static/sw.js` | Service Worker: caching strategies, offline fallback |
| `static/js/pwa.js` | PWA utilities: install prompt, online status, display mode detection |
| `templates/offline.html` | Graceful offline page shown when no cached content available |

### Modified Files

| File | Changes |
|------|---------|
| `templates/base.html` | Inject manifest link, iOS meta tags, theme-color meta, register service worker |
| `static/css/style.css` | Optional: add-to-home-screen banner styles |

## iPhone-Specific Adaptations

### Meta Tags (in base.html `<head>`)

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="我的博客">
<meta name="theme-color" content="#10b981" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#065f46" media="(prefers-color-scheme: dark)">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icon-180.png">
```

### Manifest (`static/manifest.json`)

```json
{
  "name": "我的博客",
  "short_name": "博客",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#10b981",
  "icons": [
    { "src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### Icons Required

| Size | File | Purpose |
|------|------|---------|
| 180x180 | `icon-180.png` | iOS home screen icon |
| 192x192 | `icon-192.png` | Android/Chrome icon |
| 512x512 | `icon-512.png` | Splash screen, app store-like listing |

Icons should be simple, recognizable at small sizes. Reuse the existing blog logo or generate from initials.

## Service Worker Caching Strategy

### Three-Layer Cache

```
Static Assets (CSS/JS/Fonts)     → Cache First (long-term, version-bumped)
Article Pages (HTML)             → Network First (fallback to cache)
Images / Media                   → Stale While Revalidate (show cached, update quietly)
```

### Cache Versions

Use a `CACHE_VERSION` constant in `sw.js`. When deploying new code, bump the version to force cache refresh.

### Pre-cached on Install

- `static/css/style.css` and other core CSS files
- `static/js/bundle.js` and other core JS bundles
- `static/icon-*.png` icons
- `/offline.html` fallback page
- `/` homepage

### Runtime Caching

- Article detail pages: cached on first visit, available offline afterward
- Images in article content: cached on load, served from cache on repeat visits
- API responses (post lists): short-lived cache (5 minutes)

### Offline Fallback Behavior

| Scenario | Behavior |
|----------|----------|
| Static asset missing | Serve from cache (guaranteed pre-cached) |
| Article page not cached | Show `offline.html` with message + link to cached articles list |
| API request fails | Return empty result gracefully, infinite scroll stops |

## Install Prompt UI

### Detection

```javascript
// In pwa.js
const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
const isIOSStandalone = window.navigator.standalone === true;
```

### Banner Behavior

- Show only if NOT in standalone mode
- Dismissible with "不再提示" button
- Store dismissal in `localStorage` with 7-day expiry
- Show at bottom of page, non-intrusive (fixed bottom bar, z-index below modals)

### iOS Safari Install Steps (shown when user clicks banner)

1. Tap the Share button in Safari toolbar
2. Scroll down and tap "Add to Home Screen"
3. Tap "Add" in the top-right corner

Show these steps in a small modal with Safari UI screenshots or simple text instructions.

## Online/Offline Status Indicator

- Show a small toast when connection is lost: "已切换到离线模式，已缓存的文章仍可阅读"
- Show toast when connection returns: "已恢复在线"
- Use `window.addEventListener('online'/'offline', ...)` in `pwa.js`

## Dark Mode Integration

- The existing dark mode toggle continues to work normally
- `theme-color` meta tag updates dynamically when theme changes
- Service worker caches both light and dark CSS variants independently

## Error Handling

| Case | Handling |
|------|----------|
| Service Worker registration fails | Log to console, degrade gracefully (no PWA features) |
| Cache storage quota exceeded | LRU eviction: remove oldest cached article pages first |
| Manifest fails to load | No PWA install prompt shown, site works as normal web app |
| iOS private browsing mode | Service Worker may fail to register; degrade gracefully |

## Testing Checklist

- [ ] Blog installs to iPhone home screen with correct icon
- [ ] Launches in standalone mode (no Safari UI chrome)
- [ ] Static resources load from cache on second visit
- [ ] Previously visited article loads offline
- [ ] Unvisited article shows offline fallback page
- [ ] Install banner shows on Safari, hides after dismiss
- [ ] Install banner hidden when in standalone mode
- [ ] Theme color updates correctly in light/dark mode
- [ ] Existing features (infinite scroll, dark mode, reader mode) work unchanged

## Scope Note

This is a focused, single-phase feature. All components are frontend-only (no backend changes required). The implementation should not affect existing functionality in any way.
