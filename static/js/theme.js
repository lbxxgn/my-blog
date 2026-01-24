// Theme switching
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = themeToggle.querySelector('.theme-toggle-icon');
    const themeText = themeToggle.querySelector('.theme-toggle-text');

    // Get saved theme or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';

    function applyTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-theme');
            themeIcon.textContent = '☀️';
            themeText.textContent = '亮色';
        } else {
            document.body.classList.remove('dark-theme');
            themeIcon.textContent = '🌙';
            themeText.textContent = '暗色';
        }
    }

    // Apply saved theme on load
    applyTheme(savedTheme);

    // Toggle theme on button click
    themeToggle.addEventListener('click', function() {
        const isDark = document.body.classList.contains('dark-theme');
        const newTheme = isDark ? 'light' : 'dark';

        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });
});
