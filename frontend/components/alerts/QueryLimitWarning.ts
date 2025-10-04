/**
 * Query Limit Warning Component
 * Shows a warning banner when users approach their query limit
 */

export class QueryLimitWarning {
  private banner: HTMLElement | null = null;
  private dismissed: boolean = false;

  constructor() {
    // Check if user dismissed this warning in current session
    this.dismissed = sessionStorage.getItem('query-warning-dismissed') === 'true';
  }

  /**
   * Show the warning banner
   */
  show(queriesUsed: number, queryLimit: number, tier: string = 'free'): void {
    // Don't show if already dismissed or not close to limit
    const percentage = (queriesUsed / queryLimit) * 100;
    if (this.dismissed || percentage < 80) {
      return;
    }

    // Don't show if already visible
    if (this.banner && this.banner.classList.contains('active')) {
      return;
    }

    if (this.banner) {
      this.banner.classList.add('active');
      return;
    }

    this.banner = this.createBanner(queriesUsed, queryLimit, tier);
    document.body.appendChild(this.banner);

    // Animate in
    setTimeout(() => {
      this.banner?.classList.add('active');
    }, 100);
  }

  /**
   * Hide the warning banner
   */
  hide(): void {
    if (this.banner) {
      this.banner.classList.remove('active');
    }
  }

  /**
   * Dismiss the warning (won't show again this session)
   */
  dismiss(): void {
    this.dismissed = true;
    sessionStorage.setItem('query-warning-dismissed', 'true');
    this.hide();
  }

  /**
   * Destroy the banner and remove from DOM
   */
  destroy(): void {
    if (this.banner) {
      this.banner.remove();
      this.banner = null;
    }
  }

  /**
   * Create the banner HTML element
   */
  private createBanner(queriesUsed: number, queryLimit: number, tier: string): HTMLElement {
    const banner = document.createElement('div');
    banner.className = 'query-limit-warning';

    const queriesRemaining = queryLimit - queriesUsed;
    const percentage = (queriesUsed / queryLimit) * 100;
    const isAtLimit = queriesRemaining === 0;

    banner.innerHTML = `
      <div class="query-limit-warning-content">
        <div class="query-limit-warning-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        </div>

        <div class="query-limit-warning-text">
          <div class="query-limit-warning-title">
            ${isAtLimit ? 'Query Limit Reached' : 'Approaching Query Limit'}
          </div>
          <div class="query-limit-warning-message">
            ${isAtLimit
              ? `You've used all ${queryLimit} queries on the ${tier} plan this month.`
              : `You've used ${queriesUsed} of ${queryLimit} queries this month (${Math.round(percentage)}%). Only ${queriesRemaining} ${queriesRemaining === 1 ? 'query' : 'queries'} remaining.`
            }
          </div>
        </div>

        <div class="query-limit-warning-actions">
          ${tier === 'free' ? `
            <a href="/pricing" class="query-limit-warning-btn query-limit-warning-btn-upgrade">
              Upgrade to Pro
            </a>
          ` : ''}
          <button class="query-limit-warning-btn query-limit-warning-btn-dismiss" id="dismissWarningBtn">
            ${isAtLimit ? 'Close' : 'Dismiss'}
          </button>
        </div>

        ${!isAtLimit ? `
          <button class="query-limit-warning-close" id="closeWarningBtn" aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        ` : ''}
      </div>

      <div class="query-limit-warning-progress">
        <div class="query-limit-warning-progress-bar" style="width: ${percentage}%"></div>
      </div>
    `;

    this.attachEventListeners(banner);
    return banner;
  }

  /**
   * Attach event listeners to banner elements
   */
  private attachEventListeners(banner: HTMLElement): void {
    // Dismiss button
    const dismissBtn = banner.querySelector('#dismissWarningBtn');
    dismissBtn?.addEventListener('click', () => this.dismiss());

    // Close button
    const closeBtn = banner.querySelector('#closeWarningBtn');
    closeBtn?.addEventListener('click', () => this.dismiss());
  }

  /**
   * Reset dismissal (for new sessions)
   */
  static resetDismissal(): void {
    sessionStorage.removeItem('query-warning-dismissed');
  }
}

// Export singleton instance
let queryLimitWarningInstance: QueryLimitWarning | null = null;

export function showQueryLimitWarning(queriesUsed: number, queryLimit: number, tier: string = 'free'): void {
  if (!queryLimitWarningInstance) {
    queryLimitWarningInstance = new QueryLimitWarning();
  }
  queryLimitWarningInstance.show(queriesUsed, queryLimit, tier);
}

export function hideQueryLimitWarning(): void {
  queryLimitWarningInstance?.hide();
}

export function destroyQueryLimitWarning(): void {
  queryLimitWarningInstance?.destroy();
  queryLimitWarningInstance = null;
}
