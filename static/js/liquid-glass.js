(function () {
    'use strict';

    var body = document.body;
    if (!body || !body.classList.contains('liquid-glass')) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var selector = [
        '.post-card',
        '.sidebar-widget',
        '.discover-cat-card',
        '.profile-card',
        '.kb-doc-card',
        '.author-card-box',
        '.post-adjacent-card'
    ].join(',');
    var activeSurface = null;
    var pendingEvent = null;
    var frame = 0;

    function renderHighlight() {
        frame = 0;
        if (!activeSurface || !pendingEvent) return;

        var rect = activeSurface.getBoundingClientRect();
        activeSurface.style.setProperty('--liquid-x', (pendingEvent.clientX - rect.left) + 'px');
        activeSurface.style.setProperty('--liquid-y', (pendingEvent.clientY - rect.top) + 'px');
    }

    document.addEventListener('pointermove', function (event) {
        var target = event.target;
        if (!(target instanceof Element)) return;

        activeSurface = target.closest(selector);
        if (!activeSurface) return;

        pendingEvent = event;
        if (!frame) frame = window.requestAnimationFrame(renderHighlight);
    }, { passive: true });

    document.addEventListener('pointerout', function (event) {
        if (!activeSurface || activeSurface.contains(event.relatedTarget)) return;
        activeSurface = null;
        pendingEvent = null;
        if (frame) {
            window.cancelAnimationFrame(frame);
            frame = 0;
        }
    }, { passive: true });

    window.addEventListener('blur', function () {
        activeSurface = null;
        pendingEvent = null;
        if (frame) {
            window.cancelAnimationFrame(frame);
            frame = 0;
        }
    });
})();
