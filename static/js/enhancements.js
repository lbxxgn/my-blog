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

    // Keyboard shortcut: R to toggle, Esc to exit (only on pages with a reader-mode toggle)
    document.addEventListener('keydown', function(e) {
        if (!readerToggle) return;
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
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

    /* --- System Dark Mode Detection: handled by the inline script in base.html --- */

    /* --- Mobile Bottom Nav Auto-Hide --- */
    var bottomNav = document.querySelector('.mobile-bottom-nav');
    if (bottomNav && window.innerWidth <= 768) {
        var lastScrollY = window.scrollY;
        var navTicking = false;

        window.addEventListener('scroll', function() {
            if (navTicking) return;
            navTicking = true;
            requestAnimationFrame(function() {
                var y = window.scrollY;
                if (y > lastScrollY && y > 60) {
                    bottomNav.classList.add('nav-hidden');
                } else {
                    bottomNav.classList.remove('nav-hidden');
                }
                lastScrollY = y;
                navTicking = false;
            });
        }, { passive: true });
    }

    /* --- Global Back Button Auto-Hide --- */
    var globalBackBtn = document.querySelector('.mobile-back-btn.global');
    if (globalBackBtn && window.innerWidth <= 768) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 10) {
                globalBackBtn.classList.add('scrolled-away');
            } else {
                globalBackBtn.classList.remove('scrolled-away');
            }
        }, { passive: true });
    }

    /* --- Post TOC (wide screens, blog post pages) --- */
    function initPostToc() {
        var content = document.querySelector('.post-content');
        if (!content) return;

        var headings = content.querySelectorAll('h2, h3');
        if (headings.length < 3) return;

        var toc = document.createElement('aside');
        toc.className = 'post-toc';
        var ul = document.createElement('ul');
        headings.forEach(function(h, i) {
            if (!h.id) h.id = 'post-toc-head-' + i;
            var li = document.createElement('li');
            if (h.tagName === 'H3') li.className = 'toc-l3';
            var a = document.createElement('a');
            a.href = '#' + h.id;
            a.textContent = h.textContent;
            li.appendChild(a);
            ul.appendChild(li);
        });
        var title = document.createElement('div');
        title.className = 'post-toc-title';
        title.textContent = '目录';
        toc.appendChild(title);
        toc.appendChild(ul);
        document.body.appendChild(toc);

        // 滚动高亮当前小节
        if ('IntersectionObserver' in window) {
            var links = toc.querySelectorAll('a');
            var observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        links.forEach(function(l) { l.classList.remove('active'); });
                        var active = toc.querySelector('a[href="#' + entry.target.id + '"]');
                        if (active) active.classList.add('active');
                    }
                });
            }, { rootMargin: '0px 0px -70% 0px' });
            Array.prototype.forEach.call(headings, function(h) { observer.observe(h); });
        }
    }
    document.addEventListener('DOMContentLoaded', initPostToc);
})();
