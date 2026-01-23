// Smart header hide/show on scroll
let lastScrollTop = 0;
const header = document.querySelector('header');
let scrollThreshold = 100; // Start hiding after scrolling down 100px
let headerHeight = header.offsetHeight;

window.addEventListener('scroll', function() {
    let scrollTop = window.pageYOffset || document.documentElement.scrollTop;

    if (scrollTop < 0) {
        scrollTop = 0;
    }

    // At the top of page, always show header
    if (scrollTop <= 0) {
        header.classList.remove('header-hidden');
        return;
    }

    // Detect scroll direction
    if (scrollTop > lastScrollTop && scrollTop > scrollThreshold) {
        // Scrolling down - hide header
        header.classList.add('header-hidden');
    } else if (scrollTop < lastScrollTop) {
        // Scrolling up - show header
        header.classList.remove('header-hidden');
    }

    lastScrollTop = scrollTop;
}, false);
