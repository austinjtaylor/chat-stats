// Shared Header Component JavaScript

class HeaderComponent {
    constructor() {
        this.currentPage = this.detectCurrentPage();
    }

    async init() {
        await this.loadHeader();
        this.setupThemeToggle();
        this.highlightCurrentPage();
    }

    detectCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('players.html')) return 'players';
        if (path.includes('teams.html')) return 'teams';
        if (path.includes('games.html')) return 'games';
        if (path.includes('index.html') || path === '/' || path === '/frontend/' || path === '/frontend/index.html') return 'chat';
        return 'chat';
    }

    async loadHeader() {
        try {
            const response = await fetch('/components/header.html');
            const headerHtml = await response.text();
            
            // Insert header at the beginning of body
            const headerContainer = document.createElement('div');
            headerContainer.innerHTML = headerHtml;
            document.body.insertBefore(headerContainer.firstElementChild, document.body.firstChild);
        } catch (error) {
            console.error('Failed to load header:', error);
        }
    }

    highlightCurrentPage() {
        const navLinks = document.querySelectorAll('.app-nav .nav-link');
        navLinks.forEach(link => {
            const page = link.getAttribute('data-page');
            if (page === this.currentPage) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');
        const sunIcon = document.getElementById('sunIcon');
        const moonIcon = document.getElementById('moonIcon');
        
        // Load saved theme or default to dark
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        // Update icon visibility
        if (savedTheme === 'light') {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
        } else {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
        }
        
        // Toggle theme on click
        themeToggle?.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Update icon visibility
            if (newTheme === 'light') {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            } else {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            }
        });
    }
}

// Initialize header when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const header = new HeaderComponent();
        header.init();
    });
} else {
    const header = new HeaderComponent();
    header.init();
}