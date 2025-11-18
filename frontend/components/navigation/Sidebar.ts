/**
 * Sidebar Component
 * Collapsible navigation sidebar similar to Claude.ai
 */

import { getSession, type SessionInfo } from '../../lib/auth';
import {
  getCachedProfile,
  getCachedSubscription,
  updateCachedProfile,
  updateCachedSubscription,
  clearCachedUserData,
} from '../../lib/userCache';

// Get API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface UserProfile {
  full_name: string | null;
  theme: string;
  default_season: number | null;
  notifications_enabled: boolean;
  email_digest_frequency: string;
  favorite_stat_categories: string[];
}

interface SubscriptionData {
  tier: string;
  status: string;
  queries_this_month: number;
  query_limit: number;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
}

export class Sidebar {
  private sidebar: HTMLElement | null = null;
  private backdrop: HTMLElement | null = null;
  private isExpanded: boolean = false;
  private session: SessionInfo | null = null;
  private userDropdown: HTMLElement | null = null;
  private profile: UserProfile | null = null;
  private subscription: SubscriptionData | null = null;

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

    // Load cached data first for instant display
    if (this.session.isAuthenticated) {
      this.profile = getCachedProfile();
      this.subscription = getCachedSubscription();
    }

    // Check if sidebar already exists in the DOM (pre-rendered)
    const existingSidebar = document.getElementById('appSidebar');

    if (existingSidebar) {
      // Enhance existing sidebar
      this.sidebar = existingSidebar;
      this.backdrop = document.querySelector('.sidebar-backdrop');

      // Render user section with cached data (instant display, no fetching!)
      this.renderUserSection(false);

      // Apply initial state
      if (this.isExpanded) {
        this.sidebar.classList.add('expanded');
        document.body.classList.add('sidebar-expanded');
      }

      // Remove loading class if present
      document.documentElement.classList.remove('sidebar-expanded-loading');

      // Attach all event listeners (including user section)
      this.attachEventListeners();

      // Fetch fresh data in background if authenticated
      if (this.session.isAuthenticated) {
        this.fetchUserDataInBackground();
      }
    } else {
      // Fallback: create sidebar dynamically (for pages without pre-rendered sidebar)
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

      // Fetch fresh data in background if authenticated
      if (this.session.isAuthenticated) {
        this.fetchUserDataInBackground();
      }
    }

    // Listen for auth state changes
    window.addEventListener('auth-state-changed', async () => {
      this.session = await getSession();

      if (!this.session.isAuthenticated) {
        // Clear cache on logout
        clearCachedUserData();
      }

      await this.updateUserSection();
    });

    // Listen for profile updates (e.g., when user changes their name in settings)
    window.addEventListener('profile-updated', (event: Event) => {
      const customEvent = event as CustomEvent;
      const newFullName = customEvent.detail.full_name;

      // Update profile data
      if (this.profile) {
        this.profile.full_name = newFullName;
        // Update cache
        updateCachedProfile(this.profile);
      }

      // Re-render user section with new initials
      this.renderUserSection(true);
    });

    // Create mobile hamburger menu button
    this.createMobileMenuButton();
  }

  /**
   * Fetch user data in background and update cache
   */
  private async fetchUserDataInBackground(): Promise<void> {
    try {
      await Promise.all([
        this.fetchUserProfile(),
        this.fetchSubscription(),
      ]);

      // Re-render user section with fresh data
      // Need to re-attach listeners since we're replacing the HTML
      this.renderUserSection(true);
    } catch (error) {
      console.error('Failed to fetch user data in background:', error);
    }
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
    const isStats = currentPath.includes('/stats/');

    sidebar.innerHTML = `
      <div class="sidebar-header">
        <button class="sidebar-toggle" aria-label="Toggle sidebar" aria-expanded="${this.isExpanded}" data-tooltip="Expand sidebar">
          <img src="/images/logo/chat-stats-logo-light.svg" alt="Chat Stats" class="sidebar-toggle-logo logo-light">
          <img src="/images/logo/chat-stats-logo-dark.svg" alt="Chat Stats" class="sidebar-toggle-logo logo-dark">
          <img src="/images/logo/chat-stats-logo-light2.svg" alt="Chat Stats" class="sidebar-toggle-icon sidebar-toggle-hamburger logo-light">
          <img src="/images/logo/chat-stats-logo-dark2.svg" alt="Chat Stats" class="sidebar-toggle-icon sidebar-toggle-hamburger logo-dark">
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
   * Create mobile hamburger menu button
   */
  private createMobileMenuButton(): void {
    // Create hamburger button (shows when sidebar is closed)
    const mobileButton = document.createElement('button');
    mobileButton.className = 'mobile-menu-button';
    mobileButton.setAttribute('aria-label', 'Open menu');
    mobileButton.innerHTML = `
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="3" y1="7" x2="21" y2="7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="3" y1="17" x2="16" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;

    // Add click handler to open sidebar
    mobileButton.addEventListener('click', () => this.toggle());

    // Append to body (outside sidebar so it's always visible)
    document.body.appendChild(mobileButton);

    // Create close button (shows when sidebar is open)
    const closeButton = document.createElement('button');
    closeButton.className = 'mobile-close-button';
    closeButton.setAttribute('aria-label', 'Close menu');
    closeButton.innerHTML = `
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;

    // Add click handler to close sidebar
    closeButton.addEventListener('click', () => this.collapse());

    // Append to body
    document.body.appendChild(closeButton);

    // Set up mobile new chat button (already in HTML)
    this.setupMobileNewChatButton();
  }

  /**
   * Set up mobile new chat button click handler
   */
  private setupMobileNewChatButton(): void {
    const mobileNewChatButton = document.getElementById('mobileNewChatButton');
    if (mobileNewChatButton) {
      mobileNewChatButton.addEventListener('click', () => this.handleNewChat());
    }
  }

  /**
   * Create user section HTML
   */
  private createUserSectionHTML(): string {
    if (!this.session?.isAuthenticated) {
      return '';
    }

    const email = this.session.user?.email || '';
    const fullName = this.profile?.full_name || null;
    const initials = this.getInitials(fullName, email);

    // Display name: use full_name if available, otherwise use email username
    const displayName = fullName || email.split('@')[0];

    // Display plan tier
    const tier = this.subscription?.tier || 'free';
    const planDisplay = tier.charAt(0).toUpperCase() + tier.slice(1) + ' Plan';

    return `
      <button class="sidebar-user-button" aria-label="User menu" aria-expanded="false">
        <div class="sidebar-user-avatar">${initials}</div>
        <div class="sidebar-user-info">
          <div class="sidebar-user-name">${displayName}</div>
          <div class="sidebar-user-plan">${planDisplay}</div>
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
          <span>Log out</span>
        </button>
      </div>
    `;
  }

  /**
   * Render user section with current data (no fetching)
   */
  private renderUserSection(attachListeners: boolean = true): void {
    const userSection = this.sidebar?.querySelector('#sidebarUserSection');
    if (userSection) {
      userSection.innerHTML = this.createUserSectionHTML();
      if (attachListeners) {
        this.attachUserSectionListeners();
      }
    }
  }

  /**
   * Update user section (fetch fresh data and re-render)
   */
  private async updateUserSection(): Promise<void> {
    // Re-fetch user data
    await Promise.all([
      this.fetchUserProfile(),
      this.fetchSubscription(),
    ]);

    // Re-render with fresh data
    this.renderUserSection(true);
  }

  /**
   * Fetch user profile data from API
   */
  private async fetchUserProfile(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/user/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        this.profile = await response.json();
        // Update cache with fresh data
        if (this.profile) {
          updateCachedProfile(this.profile);
        }
      }
    } catch (error) {
      console.error('Failed to fetch profile:', error);
    }
  }

  /**
   * Fetch subscription data from API
   */
  private async fetchSubscription(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/subscription/status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        this.subscription = await response.json();
        // Update cache with fresh data
        if (this.subscription) {
          updateCachedSubscription(this.subscription);
        }
      }
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
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
      // Add no-transitions class to prevent animations
      document.body.classList.add('no-transitions');

      // Force reflow
      void document.body.offsetHeight;

      // Clear chat
      const chatMessages = document.getElementById('chatMessages');
      if (chatMessages) {
        chatMessages.innerHTML = '';
        document.body.classList.remove('chat-active');
      }

      // Remove no-transitions class after layout change
      setTimeout(() => {
        document.body.classList.remove('no-transitions');
      }, 50);

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
   * Get user initials from full name or email
   */
  private getInitials(fullName: string | null, email: string): string {
    // If full name is available, use it
    if (fullName) {
      const nameParts = fullName.trim().split(/\s+/);
      if (nameParts.length >= 2) {
        // Use first letter of first name and first letter of last name
        return (nameParts[0][0] + nameParts[nameParts.length - 1][0]).toUpperCase();
      } else if (nameParts.length === 1 && nameParts[0].length >= 2) {
        // Single name: use first two letters
        return nameParts[0].substring(0, 2).toUpperCase();
      }
    }

    // Fall back to email-based logic
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
