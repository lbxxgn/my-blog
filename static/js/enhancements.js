/* Blog Frontend Enhancements - Interactions */
(function() {
    'use strict';

    /* --- Scroll Reveal for dynamically loaded cards --- */
    var revealObserver = null;
    if ('IntersectionObserver' in window) {
        revealObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('scroll-revealed');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -40px 0px'
        });
    }

    function observeNewCards() {
        if (!revealObserver) return;
        var container = document.getElementById('posts-container');
        if (!container) return;

        var cards = container.querySelectorAll('.post-card-link');
        cards.forEach(function(card) {
            if (!card.classList.contains('scroll-revealed') &&
                !card.style.animationName &&
                getComputedStyle(card).opacity === '0') {
                revealObserver.observe(card);
            }
        });
    }

    /* Observe cards already on page */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', observeNewCards);
    } else {
        observeNewCards();
    }

    /* Re-observe when new cards are loaded via infinite scroll */
    var postsContainer = document.getElementById('posts-container');
    if (postsContainer) {
        var mutationObs = new MutationObserver(function() {
            setTimeout(observeNewCards, 50);
        });
        mutationObs.observe(postsContainer, { childList: true });
    }

    /* --- Reading Progress Bar --- */
    var progressBar = null;
    var articleEl = null;

    function initReadingProgress() {
        articleEl = document.querySelector('.post-full');
        if (!articleEl) return;

        progressBar = document.createElement('div');
        progressBar.className = 'reading-progress';
        progressBar.style.width = '0%';
        document.body.appendChild(progressBar);

        window.addEventListener('scroll', updateReadingProgress, { passive: true });
        updateReadingProgress();
    }

    function updateReadingProgress() {
        if (!progressBar || !articleEl) return;

        var rect = articleEl.getBoundingClientRect();
        var articleTop = rect.top + window.scrollY;
        var articleHeight = articleEl.scrollHeight;
        var scrollPos = window.scrollY + window.innerHeight * 0.3;
        var progress = (scrollPos - articleTop) / (articleHeight - window.innerHeight);
        progress = Math.max(0, Math.min(1, progress));

        progressBar.style.width = (progress * 100) + '%';

        if (progress >= 0.99) {
            progressBar.style.opacity = '0';
            progressBar.style.transition = 'opacity 0.5s ease';
        } else {
            progressBar.style.opacity = '1';
            progressBar.style.transition = 'width 0.1s linear';
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initReadingProgress);
    } else {
        initReadingProgress();
    }

    /* --- Smooth Scroll for Anchor Links --- */
    document.addEventListener('click', function(e) {
        var link = e.target.closest('a[href^="#"]');
        if (!link) return;

        var target = document.querySelector(link.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });

    /* --- Image Lazy Load Fade-In --- */
    document.addEventListener('load', function(e) {
        if (e.target && e.target.tagName === 'IMG' && e.target.hasAttribute('loading')) {
            var img = e.target;
            img.style.opacity = '0';
            img.style.transition = 'opacity 0.4s ease';
            requestAnimationFrame(function() {
                img.style.opacity = '1';
            });
        }
    }, true);

    /* --- Comments Collapse Toggle --- */
    var commentsSection = document.querySelector('.comments-section');
    if (commentsSection) {
        var trigger = commentsSection.querySelector('.comments-trigger');
        if (trigger) {
            trigger.addEventListener('click', function() {
                commentsSection.classList.toggle('collapsed');
            });
        }
    }

    /* --- Reader Mode Toggle --- */
    var readerToggle = document.getElementById('readerModeToggle');
    var readerExit = document.getElementById('readerExit');
    var readerKey = 'reader-mode:' + window.location.pathname;

    function enterReaderMode() {
        document.body.classList.add('reader-mode');
        if (readerToggle) readerToggle.classList.add('active');
        localStorage.setItem(readerKey, '1');
    }

    function exitReaderMode() {
        document.body.classList.remove('reader-mode');
        if (readerToggle) readerToggle.classList.remove('active');
        localStorage.removeItem(readerKey);
    }

    function toggleReaderMode() {
        if (document.body.classList.contains('reader-mode')) {
            exitReaderMode();
        } else {
            enterReaderMode();
        }
    }

    if (readerToggle) {
        readerToggle.addEventListener('click', toggleReaderMode);
    }
    if (readerExit) {
        readerExit.addEventListener('click', exitReaderMode);
    }

    // Keyboard shortcut: R to toggle, Esc to exit
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'r' || e.key === 'R') {
            toggleReaderMode();
        } else if (e.key === 'Escape' && document.body.classList.contains('reader-mode')) {
            exitReaderMode();
        }
    });

    // Restore reader mode if previously active for this post
    if (localStorage.getItem(readerKey) === '1') {
        enterReaderMode();
    }

    /* --- System Dark Mode Detection --- */
    if (!localStorage.getItem('theme')) {
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.body.classList.add('dark-theme');
        }
    }
})();
