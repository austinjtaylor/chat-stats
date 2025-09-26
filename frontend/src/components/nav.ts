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

    // Theme functionality is handled in dropdown.ts
});