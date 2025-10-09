/**
 * User Menu Component
 * Displays user info, subscription tier, and logout button
 */

import { signOut, getSession, type SessionInfo } from '../../lib/auth';

export class UserMenu {
  private menu: HTMLElement | null = null;
  private session: SessionInfo | null = null;
  private onLogout?: () => void;

  constructor(onLogout?: () => void) {
    this.onLogout = onLogout;
  }

  /**
   * Initialize the user menu and attach to container
   */
  async init(containerId: string): Promise<void> {
    this.session = await getSession();

    if (!this.session.isAuthenticated) {
      return;
    }

    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    this.menu = this.createMenu();
    container.appendChild(this.menu);
    this.attachEventListeners();
  }

  /**
   * Update the user menu with current session
   */
  async update(): Promise<void> {
    this.session = await getSession();

    if (!this.session.isAuthenticated && this.menu) {
      this.destroy();
      return;
    }

    if (this.session.isAuthenticated && !this.menu) {
      // Menu needs to be recreated - caller should use init()
      return;
    }

    // Update email display
    const emailEl = this.menu?.querySelector('.user-menu-email');
    if (emailEl) {
      emailEl.textContent = this.session.user?.email || '';
    }
  }

  /**
   * Show/hide the user menu
   */
  toggle(): void {
    this.menu?.classList.toggle('active');
  }

  /**
   * Hide the user menu dropdown
   */
  hide(): void {
    this.menu?.classList.remove('active');
  }

  /**
   * Destroy the menu and remove from DOM
   */
  destroy(): void {
    if (this.menu) {
      this.menu.remove();
      this.menu = null;
    }
  }

  /**
   * Create the menu HTML element
   */
  private createMenu(): HTMLElement {
    const menu = document.createElement('div');
    menu.className = 'user-menu-wrapper';

    const userEmail = this.session?.user?.email || '';
    const initials = this.getInitials(userEmail);

    menu.innerHTML = `
      <button class="user-menu-trigger" aria-label="User menu" aria-expanded="false">
        <div class="user-avatar">${initials}</div>
      </button>

      <div class="user-menu-dropdown">
        <div class="user-menu-header">
          <div class="user-menu-email">${userEmail}</div>
          <div class="user-menu-tier">
            <span class="tier-badge tier-free">Free Plan</span>
          </div>
        </div>

        <div class="user-menu-divider"></div>

        <div class="user-menu-items">
          <a href="/settings" class="user-menu-item">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 15a3 3 0 100-6 3 3 0 000 6z"></path>
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"></path>
            </svg>
            <span>Settings</span>
          </a>
        </div>

        <div class="user-menu-divider"></div>

        <button class="user-menu-item user-menu-logout">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span>Sign Out</span>
        </button>
      </div>
    `;

    return menu;
  }

  /**
   * Attach event listeners to menu elements
   */
  private attachEventListeners(): void {
    if (!this.menu) return;

    // Toggle dropdown
    const trigger = this.menu.querySelector('.user-menu-trigger');
    trigger?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
      const expanded = this.menu?.classList.contains('active');
      trigger.setAttribute('aria-expanded', String(expanded));
    });

    // Logout button
    const logoutBtn = this.menu.querySelector('.user-menu-logout');
    logoutBtn?.addEventListener('click', async (e) => {
      e.preventDefault();
      await this.handleLogout();
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (this.menu && !this.menu.contains(e.target as Node)) {
        this.hide();
      }
    });

    // Close dropdown on ESC key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.hide();
      }
    });

    // Prevent dropdown from closing when clicking inside
    const dropdown = this.menu.querySelector('.user-menu-dropdown');
    dropdown?.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }

  /**
   * Handle user logout
   */
  private async handleLogout(): Promise<void> {
    const confirmed = confirm('Are you sure you want to sign out?');
    if (!confirmed) return;

    const result = await signOut();

    if (result.success) {
      this.destroy();
      if (this.onLogout) {
        this.onLogout();
      }
      // Reload page to clear state
      window.location.reload();
    } else {
      alert(`Failed to sign out: ${result.error}`);
    }
  }

  /**
   * Get user initials from email
   */
  private getInitials(email: string): string {
    if (!email) return '?';

    const parts = email.split('@')[0].split(/[._-]/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return email.substring(0, 2).toUpperCase();
  }

  /**
   * Update subscription tier badge
   */
  updateTier(tier: string, queryCount?: number, queryLimit?: number): void {
    const tierBadge = this.menu?.querySelector('.tier-badge');
    if (!tierBadge) return;

    // Update tier display
    tierBadge.className = `tier-badge tier-${tier}`;
    tierBadge.textContent = `${tier.charAt(0).toUpperCase() + tier.slice(1)} Plan`;

    // Add query count if provided
    if (queryCount !== undefined && queryLimit !== undefined) {
      const header = this.menu?.querySelector('.user-menu-header');
      let usageEl = header?.querySelector('.user-menu-usage');

      if (!usageEl) {
        usageEl = document.createElement('div');
        usageEl.className = 'user-menu-usage';
        header?.appendChild(usageEl);
      }

      const percentage = (queryCount / queryLimit) * 100;
      const isNearLimit = percentage >= 80;

      usageEl.innerHTML = `
        <div class="usage-text ${isNearLimit ? 'usage-warning' : ''}">
          ${queryCount} / ${queryLimit} queries
        </div>
        <div class="usage-bar">
          <div class="usage-bar-fill ${isNearLimit ? 'usage-warning' : ''}"
               style="width: ${Math.min(percentage, 100)}%"></div>
        </div>
      `;
    }
  }
}

// Export singleton instance
let userMenuInstance: UserMenu | null = null;

export async function initUserMenu(containerId: string, onLogout?: () => void): Promise<UserMenu | null> {
  if (!userMenuInstance) {
    userMenuInstance = new UserMenu(onLogout);
    await userMenuInstance.init(containerId);
  }
  return userMenuInstance;
}

export function getUserMenu(): UserMenu | null {
  return userMenuInstance;
}

export function destroyUserMenu(): void {
  userMenuInstance?.destroy();
  userMenuInstance = null;
}
