// Global type declarations for existing JavaScript utilities

declare global {
  // DOM utility (simplified interface for compatibility)
  const DOM: any;

  // Format utility (simplified interface for compatibility)
  const Format: any;

  // Stats API client (simplified interface for compatibility)
  const statsAPI: any;

  // API Error class
  class APIError extends Error {
    constructor(message: string, status: number, details?: any);
    status: number;
    details?: any;
  }

  // UFA Stats utility
  const ufaStats: {
    apiBase: string;
    currentPage: 'players' | 'teams' | 'games' | 'index';
    api: typeof statsAPI | null;
    format: typeof Format | null;
    dom: typeof DOM | null;
    fetchData<T = any>(endpoint: string, params?: Record<string, any>): Promise<T>;
    showError(message: string): void;
    showLoading(element: string | HTMLElement | null, message?: string): void;
    formatNumber(num: number | null | undefined): string;
    formatPercentage(value: number | null | undefined, decimals?: number): string;
    formatDecimal(value: number | null | undefined, decimals?: number): string;
    formatStatValue(value: any, key: string): string;
    createSortableHeader(text: string, sortKey: string, currentSort?: any): HTMLTableCellElement;
    renderSortIndicator(key: string, currentSort: any): string;
    handleTableSort(table: HTMLElement, sortKey: string, currentSort: any): any;
    createPagination(options: { currentPage: number; totalPages: number; onPageChange: (page: number) => void }): HTMLElement;
    getCurrentPage(): 'players' | 'teams' | 'games' | 'index';
  };

  // External libraries
  const marked: {
    parse(markdown: string): string;
  };

  const Chart: any; // Chart.js library

  interface Window {
    DOM: typeof DOM;
    Format: typeof Format;
    statsAPI: typeof statsAPI;
    APIError: typeof APIError;
    ufaStats: typeof ufaStats;
    marked: typeof marked;
    Chart: typeof Chart;
  }
}

export {};