// Shared functionality for UFA Stats pages - TypeScript version

import type { SortConfig } from '../types/models';

type PageType = 'players' | 'teams' | 'games' | 'index';

interface PaginationOptions {
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
}

class UFAStats {
    apiBase: string;
    currentPage: PageType;
    api: typeof window.statsAPI | null;
    format: typeof window.Format | null;
    dom: typeof window.DOM | null;

    constructor() {
        this.apiBase = '/api';  // Use relative path for API
        this.currentPage = this.getCurrentPage();
        // Theme is now handled by header.js
        // Navigation highlighting is also handled by header.js

        // Use global utilities if available
        this.api = window.statsAPI || null;
        this.format = window.Format || null;
        this.dom = window.DOM || null;
    }

    // Get current page from URL (kept for compatibility)
    getCurrentPage(): PageType {
        const path = window.location.pathname;
        if (path.includes('players')) return 'players';
        if (path.includes('teams')) return 'teams';
        if (path.includes('games')) return 'games';
        return 'index';
    }

    // API helper methods
    async fetchData<T = any>(endpoint: string, params: Record<string, any> = {}): Promise<T> {
        try {
            // Use statsAPI if available, otherwise fall back to fetch
            if (this.api && typeof this.api.get === 'function') {
                return await this.api.get(endpoint, params);
            }

            // Fallback to direct fetch
            const url = new URL(`${this.apiBase}${endpoint}`, window.location.origin);
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, String(params[key]));
                }
            });

            const response = await fetch(url.toString());
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
    showError(message: string): void {
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
    showLoading(element: string | HTMLElement | null, message: string = 'Loading...'): void {
        let targetElement: HTMLElement | null = null;

        if (typeof element === 'string') {
            targetElement = document.querySelector(element) as HTMLElement | null;
        } else if (element instanceof HTMLElement) {
            targetElement = element;
        }

        if (targetElement) {
            targetElement.innerHTML = `<div class="loading">${message}</div>`;
        }
    }

    // Format numbers with commas
    formatNumber(num: number | null | undefined): string {
        // Use Format utility if available
        if (this.format && this.format.number) {
            return this.format.number(num);
        }
        if (num === null || num === undefined) return '-';
        return num.toLocaleString();
    }

    // Format percentage
    formatPercentage(value: number | null | undefined, decimals: number = 1): string {
        // Use Format utility if available
        if (this.format && this.format.percentage) {
            return this.format.percentage(value, decimals);
        }
        if (value === null || value === undefined) return '-';
        return `${parseFloat(String(value)).toFixed(decimals)}%`;
    }

    // Format decimal value
    formatDecimal(value: number | null | undefined, decimals: number = 3): string {
        if (value === null || value === undefined) return '-';
        return parseFloat(String(value)).toFixed(decimals);
    }

    // Format stat value based on key
    formatStatValue(value: any, key: string): string {
        if (value === null || value === undefined) return '-';

        // Percentage fields
        if (key.includes('percentage') || key.includes('_pct') ||
            key === 'completion_percentage' || key === 'throw_percentage' ||
            key === 'catch_percentage' || key === 'huck_percentage' ||
            key === 'hold_percentage' || key === 'break_percentage' ||
            key === 'o_line_conversion' || key === 'd_line_conversion' ||
            key === 'red_zone_conversion') {
            return this.formatPercentage(value);
        }

        // Plus/minus
        if (key === 'plus_minus' || key === 'calculated_plus_minus') {
            const num = Number(value);
            return String(num);
        }

        // Decimal fields (time-based)
        if (key === 'total_minutes' || key === 'minutes') {
            return this.formatDecimal(value, 1);
        }

        // Integer fields
        return this.formatNumber(value);
    }

    // Create sortable table headers
    createSortableHeader(text: string, sortKey: string, currentSort: SortConfig | null = null): HTMLTableCellElement {
        const th = document.createElement('th');
        th.textContent = text;
        th.setAttribute('data-sort', sortKey);
        th.className = 'sortable';

        if (currentSort && currentSort.key === sortKey) {
            th.classList.add(currentSort.direction);
        }

        return th;
    }

    // Render sort indicator
    renderSortIndicator(key: string, currentSort: SortConfig): string {
        if (currentSort.key === key) {
            return currentSort.direction === 'asc' ? ' ↑' : ' ↓';
        }
        return '';
    }

    // Handle table sorting
    handleTableSort(table: HTMLElement, sortKey: string, currentSort: SortConfig): SortConfig {
        let direction: 'asc' | 'desc' = 'desc';
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
    createPagination(options: PaginationOptions): HTMLElement {
        const { currentPage, totalPages, onPageChange } = options;
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
            pageBtn.textContent = String(i);
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
            lastBtn.textContent = String(totalPages);
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

    // Dropdown and theme toggle functionality is now handled by dropdown.ts which is imported in the entry files
    // This provides click-based dropdowns and proper theme toggle behavior
});

// Export for use in other scripts
export { UFAStats };
export default UFAStats;

// Make available globally for backward compatibility
if (typeof window !== 'undefined') {
    (window as any).UFAStats = UFAStats;
}