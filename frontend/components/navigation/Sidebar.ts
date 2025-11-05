/**
 * Sidebar Component
 * Collapsible navigation sidebar similar to Claude.ai
 */

import { getSession, type SessionInfo } from '../../lib/auth';

export class Sidebar {
  private sidebar: HTMLElement | null = null;
  private backdrop: HTMLElement | null = null;
  private isExpanded: boolean = false;
  private session: SessionInfo | null = null;
  private userDropdown: HTMLElement | null = null;

  constructor() {
    // Load saved state from localStorage
    const savedState = localStorage.getItem('sidebar-expanded');
    this.isExpanded = savedState === 'true';
  }

  /**
   * Initialize the sidebar and attach to body
   */
  async init(): Promise<void> {
    this.session = await getSession();
    this.sidebar = this.createSidebar();
    this.backdrop = this.createBackdrop();

    document.body.appendChild(this.sidebar);
    document.body.appendChild(this.backdrop);

    // Apply initial state
    if (this.isExpanded) {
      this.sidebar.classList.add('expanded');
      document.body.classList.add('sidebar-expanded');
    }

    this.attachEventListeners();

    // Listen for auth state changes
    window.addEventListener('auth-state-changed', async () => {
      this.session = await getSession();
      this.updateUserSection();
    });
  }

  /**
   * Create the sidebar HTML element
   */
  private createSidebar(): HTMLElement {
    const sidebar = document.createElement('aside');
    sidebar.className = 'app-sidebar';
    sidebar.setAttribute('role', 'navigation');
    sidebar.setAttribute('aria-label', 'Main navigation');

    const currentPath = window.location.pathname;
    const isChat = currentPath === '/' || currentPath === '/index.html';
    const isStats = currentPath.includes('/stats/');

    sidebar.innerHTML = `
      <div class="sidebar-header">
        <button class="sidebar-toggle" aria-label="Toggle sidebar" aria-expanded="${this.isExpanded}" data-tooltip="Expand sidebar">
          <img src="/images/logo/chat-stats-logo-light.svg" alt="Chat Stats" class="sidebar-toggle-logo logo-light">
          <img src="/images/logo/chat-stats-logo-dark.svg" alt="Chat Stats" class="sidebar-toggle-logo logo-dark">
          <img src="/images/logo/chat-stats-logo-light2.svg" alt="Chat Stats" class="sidebar-toggle-icon sidebar-toggle-hamburger">
          <span class="sidebar-toggle-icon sidebar-toggle-arrow-right">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="4" x2="18" y2="20"></line>
              <line x1="6" y1="12" x2="14" y2="12"></line>
              <polyline points="10 8 14 12 10 16"></polyline>
            </svg>
          </span>
          <span class="sidebar-toggle-icon sidebar-toggle-arrow-left">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="6" y1="4" x2="6" y2="20"></line>
              <line x1="10" y1="12" x2="18" y2="12"></line>
              <polyline points="14 8 10 12 14 16"></polyline>
            </svg>
          </span>
        </button>
        <div class="sidebar-title">
          <h2>Chat Stats</h2>
        </div>
      </div>

      <nav class="sidebar-nav">
        <button class="sidebar-nav-item" data-action="new-chat" data-tooltip="New Chat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14"></path>
          </svg>
          <span>New Chat</span>
        </button>

        <a href="#" class="sidebar-nav-item" data-action="chats" data-tooltip="Chats">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
          </svg>
          <span>Chats</span>
        </a>

        <a href="/stats/index.html" class="sidebar-nav-item ${isStats ? 'active' : ''}" data-action="stats" data-tooltip="Stats">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7" rx="1"></rect>
            <rect x="14" y="3" width="7" height="7" rx="1"></rect>
            <rect x="14" y="14" width="7" height="7" rx="1"></rect>
            <rect x="3" y="14" width="7" height="7" rx="1"></rect>
          </svg>
          <span>Stats</span>
        </a>
      </nav>

      <div class="sidebar-middle-expander"></div>

      <div class="sidebar-user-section" id="sidebarUserSection">
        ${this.createUserSectionHTML()}
      </div>
    `;

    return sidebar;
  }

  /**
   * Create backdrop for mobile overlay
   */
  private createBackdrop(): HTMLElement {
    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    backdrop.addEventListener('click', () => this.collapse());
    return backdrop;
  }

  /**
   * Create user section HTML
   */
  private createUserSectionHTML(): string {
    if (!this.session?.isAuthenticated) {
      return '';
    }

    const email = this.session.user?.email || '';
    const initials = this.getInitials(email);

    return `
      <button class="sidebar-user-button" aria-label="User menu" aria-expanded="false">
        <div class="sidebar-user-avatar">${initials}</div>
        <div class="sidebar-user-info">
          <div class="sidebar-user-name">${email.split('@')[0]}</div>
          <div class="sidebar-user-plan">Free Plan</div>
        </div>
        <svg class="sidebar-user-dropdown-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
      <div class="sidebar-user-dropdown">
        <a href="/settings.html" class="sidebar-user-dropdown-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 15a3 3 0 100-6 3 3 0 000 6z"></path>
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"></path>
          </svg>
          <span>Settings</span>
        </a>
        <button class="sidebar-user-dropdown-item logout" data-action="logout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span>Sign Out</span>
        </button>
      </div>
    `;
  }

  /**
   * Update user section (when auth state changes)
   */
  private updateUserSection(): void {
    const userSection = this.sidebar?.querySelector('#sidebarUserSection');
    if (userSection) {
      userSection.innerHTML = this.createUserSectionHTML();
      this.attachUserSectionListeners();
    }
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    if (!this.sidebar) return;

    // Toggle button
    const toggleBtn = this.sidebar.querySelector('.sidebar-toggle');
    toggleBtn?.addEventListener('click', () => {
      this.toggle();
      // Add clicked class to suppress tooltip
      toggleBtn.classList.add('clicked');
    });
    toggleBtn?.addEventListener('mouseleave', () => {
      // Remove clicked class when mouse leaves
      toggleBtn.classList.remove('clicked');
    });

    // Middle expander (clickable area to toggle sidebar)
    const middleExpander = this.sidebar.querySelector('.sidebar-middle-expander');
    middleExpander?.addEventListener('click', () => {
      if (this.isExpanded) {
        this.collapse();
      } else {
        this.expand();
      }
    });

    // New chat button
    const newChatBtn = this.sidebar.querySelector('[data-action="new-chat"]');
    newChatBtn?.addEventListener('click', () => this.handleNewChat());

    // Chats button (placeholder for now)
    const chatsBtn = this.sidebar.querySelector('[data-action="chats"]');
    chatsBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      alert('Chat history feature coming soon!');
    });

    // User section listeners
    this.attachUserSectionListeners();

    // Close sidebar on navigation (mobile) and manage tooltip state
    const navItems = this.sidebar.querySelectorAll('.sidebar-nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        // Add clicked class to suppress tooltip
        item.classList.add('clicked');

        if (window.innerWidth <= 768) {
          this.collapse();
        }
      });

      item.addEventListener('mouseleave', () => {
        // Remove clicked class when mouse leaves
        item.classList.remove('clicked');
      });
    });

    // Close user dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (this.userDropdown && !this.sidebar?.contains(e.target as Node)) {
        this.hideUserDropdown();
      }
    });
  }

  /**
   * Attach user section event listeners
   */
  private attachUserSectionListeners(): void {
    if (!this.sidebar) return;

    // User button
    const userBtn = this.sidebar.querySelector('.sidebar-user-button');
    this.userDropdown = this.sidebar.querySelector('.sidebar-user-dropdown');

    userBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleUserDropdown();
    });

    // Logout button
    const logoutBtn = this.sidebar.querySelector('[data-action="logout"]');
    logoutBtn?.addEventListener('click', async () => {
      await this.handleLogout();
    });
  }

  /**
   * Handle new chat action
   */
  private handleNewChat(): void {
    // Navigate to chat page
    if (window.location.pathname !== '/index.html' && window.location.pathname !== '/') {
      window.location.href = '/index.html';
    } else {
      // Clear chat
      const chatMessages = document.getElementById('chatMessages');
      if (chatMessages) {
        chatMessages.innerHTML = '';
        document.body.classList.remove('chat-active');
      }
      // Dispatch event for script.ts to handle
      window.dispatchEvent(new Event('new-chat'));
    }
  }

  /**
   * Handle logout
   */
  private async handleLogout(): Promise<void> {
    const confirmed = confirm('Are you sure you want to sign out?');
    if (!confirmed) return;

    // Import signOut dynamically to avoid circular dependencies
    const { signOut } = await import('../../lib/auth');
    const result = await signOut();

    if (result.success) {
      window.location.reload();
    } else {
      alert(`Failed to sign out: ${result.error}`);
    }
  }

  /**
   * Toggle sidebar
   */
  toggle(): void {
    if (this.isExpanded) {
      this.collapse();
    } else {
      this.expand();
    }
  }

  /**
   * Expand sidebar
   */
  expand(): void {
    this.isExpanded = true;
    this.sidebar?.classList.add('expanded');
    document.body.classList.add('sidebar-expanded');
    this.backdrop?.classList.add('active');
    localStorage.setItem('sidebar-expanded', 'true');

    const toggleBtn = this.sidebar?.querySelector('.sidebar-toggle');
    toggleBtn?.setAttribute('aria-expanded', 'true');
  }

  /**
   * Collapse sidebar
   */
  collapse(): void {
    this.isExpanded = false;
    this.sidebar?.classList.remove('expanded');
    document.body.classList.remove('sidebar-expanded');
    this.backdrop?.classList.remove('active');
    localStorage.setItem('sidebar-expanded', 'false');

    const toggleBtn = this.sidebar?.querySelector('.sidebar-toggle');
    toggleBtn?.setAttribute('aria-expanded', 'false');

    // Also hide user dropdown
    this.hideUserDropdown();
  }

  /**
   * Toggle user dropdown
   */
  private toggleUserDropdown(): void {
    if (this.userDropdown?.classList.contains('active')) {
      this.hideUserDropdown();
    } else {
      this.showUserDropdown();
    }
  }

  /**
   * Show user dropdown
   */
  private showUserDropdown(): void {
    this.userDropdown?.classList.add('active');
    const userBtn = this.sidebar?.querySelector('.sidebar-user-button');
    userBtn?.setAttribute('aria-expanded', 'true');
  }

  /**
   * Hide user dropdown
   */
  private hideUserDropdown(): void {
    this.userDropdown?.classList.remove('active');
    const userBtn = this.sidebar?.querySelector('.sidebar-user-button');
    userBtn?.setAttribute('aria-expanded', 'false');
  }

  /**
   * Get user initials
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
   * Update user plan display
   */
  updateUserPlan(plan: string): void {
    const planEl = this.sidebar?.querySelector('.sidebar-user-plan');
    if (planEl) {
      planEl.textContent = `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan`;
    }
  }

  /**
   * Destroy the sidebar
   */
  destroy(): void {
    this.sidebar?.remove();
    this.backdrop?.remove();
    this.sidebar = null;
    this.backdrop = null;
  }
}

// Export singleton instance
let sidebarInstance: Sidebar | null = null;

export async function initSidebar(): Promise<Sidebar> {
  if (!sidebarInstance) {
    sidebarInstance = new Sidebar();
    await sidebarInstance.init();
  }
  return sidebarInstance;
}

export function getSidebar(): Sidebar | null {
  return sidebarInstance;
}

export function destroySidebar(): void {
  sidebarInstance?.destroy();
  sidebarInstance = null;
}
