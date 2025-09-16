// Navigation and Theme Management
document.addEventListener('DOMContentLoaded', () => {
    // Highlight current page
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll<HTMLAnchorElement>('.app-nav .nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        // Check if current path matches the link
        if ((currentPath === '/' || currentPath === '/index.html') && href === '/index.html') {
            link.classList.add('active');
        } else if (currentPath.includes('players') && href?.includes('players')) {
            link.classList.add('active');
        } else if (currentPath.includes('teams') && href?.includes('teams')) {
            link.classList.add('active');
        } else if (currentPath.includes('games') && href?.includes('games')) {
            link.classList.add('active');
        }
    });

    // Theme toggle functionality
    const themeToggle = document.getElementById('themeToggle');
    const sunIcon = document.getElementById('sunIcon') as HTMLElement | null;
    const moonIcon = document.getElementById('moonIcon') as HTMLElement | null;

    // Load saved theme or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Update icon visibility
    if (sunIcon && moonIcon) {
        if (savedTheme === 'light') {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
        } else {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
        }
    }

    // Toggle theme on click
    themeToggle?.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Update icon visibility
        if (sunIcon && moonIcon) {
            if (newTheme === 'light') {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            } else {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            }
        }
    });
});