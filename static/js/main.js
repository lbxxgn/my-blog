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

// Hamburger Menu Toggle
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');

if (hamburger && navLinks) {
    hamburger.addEventListener('click', function() {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');

        // Prevent body scroll when menu is open
        if (navLinks.classList.contains('active')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    });

    // Close menu when clicking on a link
    const menuLinks = navLinks.querySelectorAll('a');
    menuLinks.forEach(link => {
        link.addEventListener('click', function() {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(event) {
        const isClickInsideNav = navLinks.contains(event.target);
        const isClickOnHamburger = hamburger.contains(event.target);

        if (!isClickInsideNav && !isClickOnHamburger && navLinks.classList.contains('active')) {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        }
    });

    // Close menu on window resize if open
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && navLinks.classList.contains('active')) {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
}
