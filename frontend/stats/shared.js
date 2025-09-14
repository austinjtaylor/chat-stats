// Shared functionality for UFA Stats pages
class UFAStats {
    constructor() {
        this.apiBase = '/api';  // Use relative path for API
        this.currentPage = this.getCurrentPage();
        // Theme is now handled by header.js
        // Navigation highlighting is also handled by header.js
    }

    // Get current page from URL (kept for compatibility)
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

    // Set page data attribute for CSS styling
    const path = window.location.pathname;
    if (path.includes('players')) {
        document.body.setAttribute('data-page', 'players');
    } else if (path.includes('teams')) {
        document.body.setAttribute('data-page', 'teams');
    } else if (path.includes('games')) {
        document.body.setAttribute('data-page', 'games');
    }

    // Initialize theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Menu dropdown functionality
    const menuIcon = document.getElementById('menuIcon');
    const menuDropdown = document.getElementById('menuDropdown');
    const menuWrapper = document.querySelector('.menu-wrapper');
    let menuTimeout;

    if (menuWrapper && menuDropdown) {
        // Show dropdown on hover
        menuWrapper.addEventListener('mouseenter', () => {
            clearTimeout(menuTimeout);
            menuDropdown.classList.add('active');
            // Close settings dropdown if open
            const settingsDropdown = document.getElementById('settingsDropdown');
            if (settingsDropdown) {
                settingsDropdown.classList.remove('active');
            }
        });

        // Hide dropdown when leaving the wrapper
        menuWrapper.addEventListener('mouseleave', () => {
            menuTimeout = setTimeout(() => {
                menuDropdown.classList.remove('active');
            }, 200); // Small delay to prevent accidental closing
        });
    }

    // Settings dropdown functionality
    const settingsIcon = document.getElementById('settingsIcon');
    const settingsDropdown = document.getElementById('settingsDropdown');
    const settingsWrapper = document.querySelector('.settings-wrapper');
    let settingsTimeout;

    if (settingsWrapper && settingsDropdown) {
        // Show dropdown on hover
        settingsWrapper.addEventListener('mouseenter', () => {
            clearTimeout(settingsTimeout);
            settingsDropdown.classList.add('active');
            // Close menu dropdown if open
            if (menuDropdown) {
                menuDropdown.classList.remove('active');
            }
        });

        // Hide dropdown when leaving the wrapper
        settingsWrapper.addEventListener('mouseleave', () => {
            settingsTimeout = setTimeout(() => {
                settingsDropdown.classList.remove('active');
            }, 200); // Small delay to prevent accidental closing
        });
    }

    // Theme toggle functionality
    const themeToggleItem = document.getElementById('themeToggleItem');
    const themeSwitch = document.getElementById('themeSwitch');

    if (themeToggleItem && themeSwitch) {
        // Check current theme and update switch
        if (savedTheme === 'light') {
            themeSwitch.classList.add('active');
        }

        themeToggleItem.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';

            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);

            if (newTheme === 'light') {
                themeSwitch.classList.add('active');
            } else {
                themeSwitch.classList.remove('active');
            }
        });
    }

});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UFAStats;
}