// Global type declarations for existing JavaScript utilities

declare global {
  // DOM utility
  const DOM: {
    $(selector: string): HTMLElement | null;
    $$(selector: string): NodeListOf<HTMLElement>;
    create(tag: string, className?: string, text?: string): HTMLElement;
    show(element: HTMLElement): void;
    hide(element: HTMLElement): void;
    toggle(element: HTMLElement): void;
    addClass(element: HTMLElement, className: string): void;
    removeClass(element: HTMLElement, className: string): void;
    hasClass(element: HTMLElement, className: string): boolean;
    on(element: HTMLElement, event: string, handler: EventListener): void;
    off(element: HTMLElement, event: string, handler: EventListener): void;
  };

  // Format utility
  const Format: {
    number(value: number | null | undefined): string;
    percentage(value: number | null | undefined, decimals?: number): string;
    date(dateString: string): string;
    time(minutes: number, seconds?: number): string;
    playerName(name: string): string;
    teamName(name: string): string;
    statValue(value: number | null | undefined, isPercentage?: boolean): string;
  };

  // Stats API client
  const statsAPI: {
    query(queryText: string, sessionId?: string): Promise<any>;
    getStats(): Promise<any>;
    searchPlayers(params: any): Promise<any>;
    searchTeams(params: any): Promise<any>;
    getPlayerStats(params: any): Promise<any>;
    getTeamStats(params: any): Promise<any>;
    getGameStats(params: any): Promise<any>;
    getGameDetails(gameId: string): Promise<any>;
    getDatabaseInfo(): Promise<any>;
  };

  // API Error class
  class APIError extends Error {
    constructor(message: string, status: number, details?: any);
    status: number;
    details?: any;
  }

  // UFA Stats utility
  const ufaStats: {
    fetchData(endpoint: string): Promise<any>;
    handleTableSort(table: HTMLElement, sortKey: string, currentSort: any): any;
    renderSortIndicator(key: string, currentSort: any): string;
    formatStatValue(value: any, key: string): string;
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