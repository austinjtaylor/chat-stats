// Shared functionality for UFA Stats pages
class UFAStats {
    constructor() {
        this.apiBase = 'http://localhost:8000/api';
        this.currentPage = this.getCurrentPage();
        this.initTheme();
        this.initNavigation();
    }

    // Initialize theme toggle functionality
    initTheme() {
        const themeToggle = document.getElementById('themeToggle');
        const sunIcon = document.getElementById('sunIcon');
        const moonIcon = document.getElementById('moonIcon');
        
        if (!themeToggle) return;
        
        // Get current theme from localStorage or default to light
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', currentTheme);
        
        if (currentTheme === 'dark') {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
        } else {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
        }
        
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.body.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            if (newTheme === 'dark') {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            } else {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            }
        });
    }

    // Initialize navigation highlighting
    initNavigation() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.stats-nav .nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href');
            
            if ((currentPath.includes('players') && href.includes('players')) ||
                (currentPath.includes('teams') && href.includes('teams')) ||
                (currentPath.includes('games') && href.includes('games'))) {
                link.classList.add('active');
            }
        });
    }

    // Get current page identifier
    getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('players')) return 'players';
        if (path.includes('teams')) return 'teams';
        if (path.includes('games')) return 'games';
        return 'index';
    }

    // API helper methods
    async fetchData(endpoint, params = {}) {
        try {
            const url = new URL(`${this.apiBase}${endpoint}`);
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, params[key]);
                }
            });

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            this.showError('Failed to load data. Please make sure the backend is running.');
            throw error;
        }
    }

    // Show error message
    showError(message) {
        const existingError = document.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        const container = document.querySelector('.stats-container') || document.body;
        container.insertBefore(errorDiv, container.firstChild);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    // Show loading state
    showLoading(element, message = 'Loading...') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        if (element) {
            element.innerHTML = `<div class="loading">${message}</div>`;
        }
    }

    // Format numbers with commas
    formatNumber(num) {
        if (num === null || num === undefined) return '-';
        return num.toLocaleString();
    }

    // Format percentage
    formatPercentage(value, decimals = 1) {
        if (value === null || value === undefined) return '-';
        return `${parseFloat(value).toFixed(decimals)}%`;
    }

    // Format decimal value
    formatDecimal(value, decimals = 3) {
        if (value === null || value === undefined) return '-';
        return parseFloat(value).toFixed(decimals);
    }

    // Create sortable table headers
    createSortableHeader(text, sortKey, currentSort = null) {
        const th = document.createElement('th');
        th.textContent = text;
        th.setAttribute('data-sort', sortKey);
        th.className = 'sortable';
        
        if (currentSort && currentSort.key === sortKey) {
            th.classList.add(currentSort.direction);
        }
        
        return th;
    }

    // Handle table sorting
    handleTableSort(table, sortKey, currentSort) {
        let direction = 'desc';
        if (currentSort && currentSort.key === sortKey) {
            direction = currentSort.direction === 'desc' ? 'asc' : 'desc';
        }

        // Update header classes
        const headers = table.querySelectorAll('th.sortable');
        headers.forEach(h => {
            h.classList.remove('asc', 'desc');
            if (h.getAttribute('data-sort') === sortKey) {
                h.classList.add(direction);
            }
        });

        return { key: sortKey, direction };
    }

    // Create pagination controls
    createPagination(currentPage, totalPages, onPageChange) {
        const nav = document.createElement('nav');
        nav.className = 'pagination';

        // Previous button
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '‹';
        prevBtn.disabled = currentPage === 1;
        prevBtn.onclick = () => currentPage > 1 && onPageChange(currentPage - 1);
        nav.appendChild(prevBtn);

        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);

        if (startPage > 1) {
            const firstBtn = document.createElement('button');
            firstBtn.textContent = '1';
            firstBtn.onclick = () => onPageChange(1);
            nav.appendChild(firstBtn);
            
            if (startPage > 2) {
                const ellipsis = document.createElement('span');
                ellipsis.textContent = '...';
                ellipsis.className = 'ellipsis';
                nav.appendChild(ellipsis);
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.textContent = i;
            pageBtn.className = i === currentPage ? 'active' : '';
            pageBtn.onclick = () => onPageChange(i);
            nav.appendChild(pageBtn);
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                const ellipsis = document.createElement('span');
                ellipsis.textContent = '...';
                ellipsis.className = 'ellipsis';
                nav.appendChild(ellipsis);
            }
            
            const lastBtn = document.createElement('button');
            lastBtn.textContent = totalPages;
            lastBtn.onclick = () => onPageChange(totalPages);
            nav.appendChild(lastBtn);
        }

        // Next button
        const nextBtn = document.createElement('button');
        nextBtn.textContent = '›';
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.onclick = () => currentPage < totalPages && onPageChange(currentPage + 1);
        nav.appendChild(nextBtn);

        return nav;
    }
}

// Initialize shared functionality when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    window.ufaStats = new UFAStats();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UFAStats;
}