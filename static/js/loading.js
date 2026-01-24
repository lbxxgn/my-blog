// Image lazy loading with Intersection Observer
document.addEventListener('DOMContentLoaded', function() {
    // Lazy load images
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.getAttribute('data-src');

                if (src) {
                    img.src = src;
                    img.onload = () => img.classList.add('loaded');
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '50px 0px'
    });

    // Observe all images with data-src
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });

    // Show skeleton cards while loading
    const showSkeleton = (container, count = 3) => {
        for (let i = 0; i < count; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'skeleton-card';
            skeleton.innerHTML = `
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-meta"></div>
                <div class="skeleton skeleton-excerpt"></div>
                <div class="skeleton skeleton-excerpt"></div>
            `;
            container.appendChild(skeleton);
        }
    };

    // Export functions for use in other scripts
    window.loadingUtils = {
        showSkeleton,
        imageObserver
    };
});
