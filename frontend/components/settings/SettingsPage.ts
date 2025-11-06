/**
 * Settings Page Component
 * Displays user settings with tabbed interface: Profile, Billing, Usage
 */

import { getSession, signOut, type SessionInfo } from '../../lib/auth';
import { showPaymentMethodModal } from '../billing/PaymentMethodModal';
import { showCancelSubscriptionModal } from './CancelSubscriptionModal';
import {
  getCachedProfile,
  getCachedSubscription,
  getCachedPaymentMethod,
  getCachedInvoices,
  updateCachedProfile,
  updateCachedSubscription,
  updateCachedPaymentMethod,
  updateCachedInvoices,
} from '../../lib/userCache';

// Get API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface SubscriptionData {
  tier: string;
  status: string;
  queries_this_month: number;
  query_limit: number;
  current_period_end?: string;
  stripe_customer_id?: string;
  cancel_at_period_end?: boolean;
}

interface UserProfile {
  full_name: string | null;
  theme: string;
  default_season: number | null;
  notifications_enabled: boolean;
  email_digest_frequency: string;
  favorite_stat_categories: string[];
}

interface PaymentMethod {
  id: string;
  type: string;
  card: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  } | null;
  link: {
    email: string;
  } | null;
}

interface Invoice {
  id: string;
  date: number;
  amount_paid: number;
  currency: string;
  status: string;
  invoice_pdf: string;
  hosted_invoice_url: string;
}

type TabName = 'general' | 'billing' | 'usage' | 'account';

export class SettingsPage {
  private container: HTMLElement | null = null;
  private session: SessionInfo | null = null;
  private subscription: SubscriptionData | null = null;
  private profile: UserProfile | null = null;
  private paymentMethod: PaymentMethod | null = null;
  private invoices: Invoice[] = [];
  private activeTab: TabName = 'general';
  private saveTimeout: number | null = null;
  private originalFullName: string = '';
  private hasUnsavedChanges: boolean = false;

  /**
   * Initialize and render the settings page
   */
  async init(containerId: string): Promise<void> {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    // Get session
    this.session = await getSession();
    if (!this.session.isAuthenticated) {
      this.renderUnauthenticated();
      return;
    }

    // Load cached data FIRST for instant rendering
    this.profile = getCachedProfile();
    this.subscription = getCachedSubscription();
    this.paymentMethod = getCachedPaymentMethod();
    this.invoices = getCachedInvoices();

    // Check URL hash for tab (support legacy 'profile' hash for backwards compatibility)
    const hash = window.location.hash.slice(1);
    if (hash === 'profile') {
      // Redirect legacy 'profile' hash to 'general'
      window.location.hash = 'general';
      this.activeTab = 'general';
    } else if (hash && ['general', 'billing', 'usage', 'account'].includes(hash)) {
      this.activeTab = hash as TabName;
    }

    // Render immediately with cached data (instant display!)
    this.render();
    this.setupHashNavigation();

    // Fetch fresh data in background
    this.fetchAllDataInBackground();
  }

  /**
   * Fetch all data in background and update UI
   */
  private async fetchAllDataInBackground(): Promise<void> {
    try {
      // Fetch all data in parallel
      await Promise.all([
        this.fetchSubscription(),
        this.fetchProfile(),
        this.fetchPaymentMethod(),
        this.fetchInvoices(),
      ]);

      // Re-render with fresh data
      this.render();
    } catch (error) {
      console.error('Failed to fetch data in background:', error);
    }
  }

  /**
   * Fetch user subscription data from API
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
   * Fetch user profile data from API
   */
  private async fetchProfile(): Promise<void> {
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
   * Fetch payment method data from API
   */
  private async fetchPaymentMethod(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/stripe/payment-methods`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        this.paymentMethod = data.payment_method;
        // Update cache with fresh data
        updateCachedPaymentMethod(this.paymentMethod);
        console.log('Fetched payment method:', this.paymentMethod ? 'Found' : 'None', this.paymentMethod);
      }
    } catch (error) {
      console.error('Failed to fetch payment method:', error);
    }
  }

  /**
   * Fetch payment method with retry logic (for handling Stripe propagation delays)
   */
  private async fetchPaymentMethodWithRetry(maxRetries: number = 3, delayMs: number = 500): Promise<void> {
    console.log('Fetching payment method with retry logic...');

    // Initial delay to allow Stripe to propagate the update
    await new Promise(resolve => setTimeout(resolve, delayMs));

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      await this.fetchPaymentMethod();

      if (this.paymentMethod) {
        console.log(`Payment method found on attempt ${attempt}`);
        return;
      }

      if (attempt < maxRetries) {
        console.log(`Payment method not found on attempt ${attempt}, retrying in ${delayMs}ms...`);
        await new Promise(resolve => setTimeout(resolve, delayMs));
      } else {
        console.warn(`Payment method not found after ${maxRetries} attempts`);
      }
    }
  }

  /**
   * Fetch invoice history from API
   */
  private async fetchInvoices(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/stripe/invoices`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        this.invoices = data.invoices || [];
        // Update cache with fresh data
        updateCachedInvoices(this.invoices);
      }
    } catch (error) {
      console.error('Failed to fetch invoices:', error);
    }
  }

  /**
   * Setup hash navigation for tabs
   */
  private setupHashNavigation(): void {
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.slice(1);
      if (hash === 'profile') {
        // Redirect legacy 'profile' hash to 'general'
        window.location.hash = 'general';
        this.switchTab('general');
      } else if (hash && ['general', 'billing', 'usage', 'account'].includes(hash)) {
        this.switchTab(hash as TabName);
      }
    });
  }

  /**
   * Switch to a different tab
   */
  private switchTab(tab: TabName): void {
    this.activeTab = tab;

    // Update tab buttons
    const tabButtons = this.container?.querySelectorAll('.settings-tab-button');
    tabButtons?.forEach(btn => {
      if (btn.getAttribute('data-tab') === tab) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update tab content
    const tabContents = this.container?.querySelectorAll('.settings-tab-content');
    tabContents?.forEach(content => {
      if (content.getAttribute('data-tab') === tab) {
        content.classList.add('active');
      } else {
        content.classList.remove('active');
      }
    });
  }

  /**
   * Render unauthenticated state
   */
  private renderUnauthenticated(): void {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="settings-container">
        <div class="settings-unauthenticated">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 15a3 3 0 100-6 3 3 0 000 6z"></path>
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"></path>
          </svg>
          <h2>Sign in to access settings</h2>
          <p>Create an account or sign in to manage your profile, subscription, and usage.</p>
          <button class="btn-primary" id="settings-signin-btn">Sign In</button>
        </div>
      </div>
    `;

    // Attach event listener
    const signinBtn = this.container.querySelector('#settings-signin-btn');
    signinBtn?.addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('show-login-modal'));
    });
  }

  /**
   * Render the settings page
   */
  private render(): void {
    if (!this.container || !this.session || !this.subscription) return;

    const user = this.session.user;
    const sub = this.subscription;

    this.container.innerHTML = `
      <div class="settings-container">
        <div class="settings-header">
          <h1>Settings</h1>
        </div>

        <!-- Tab Navigation -->
        <div class="settings-tabs">
          <button class="settings-tab-button ${this.activeTab === 'general' ? 'active' : ''}" data-tab="general">
            General
          </button>
          <button class="settings-tab-button ${this.activeTab === 'billing' ? 'active' : ''}" data-tab="billing">
            Billing
          </button>
          <button class="settings-tab-button ${this.activeTab === 'usage' ? 'active' : ''}" data-tab="usage">
            Usage
          </button>
          <button class="settings-tab-button ${this.activeTab === 'account' ? 'active' : ''}" data-tab="account">
            Account
          </button>
        </div>

        <!-- General Tab -->
        <div class="settings-tab-content ${this.activeTab === 'general' ? 'active' : ''}" data-tab="general">
          ${this.renderGeneralTab(user)}
        </div>

        <!-- Billing Tab -->
        <div class="settings-tab-content ${this.activeTab === 'billing' ? 'active' : ''}" data-tab="billing">
          ${this.renderBillingTab(sub)}
        </div>

        <!-- Usage Tab -->
        <div class="settings-tab-content ${this.activeTab === 'usage' ? 'active' : ''}" data-tab="usage">
          ${this.renderUsageTab(sub)}
        </div>

        <!-- Account Tab -->
        <div class="settings-tab-content ${this.activeTab === 'account' ? 'active' : ''}" data-tab="account">
          ${this.renderAccountTab()}
        </div>
      </div>
    `;

    // Attach event listeners
    this.attachEventListeners();
  }

  /**
   * Render General tab content
   */
  private renderGeneralTab(user: any): string {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    const fullName = this.profile?.full_name || '';

    // Store original full name for comparison
    if (!this.originalFullName && fullName) {
      this.originalFullName = fullName;
    }

    // Generate initials from full name
    const getInitials = (name: string): string => {
      if (!name || !name.trim()) return '';
      const parts = name.trim().split(' ').filter(p => p);
      if (parts.length === 0) return '';
      if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
      return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    };

    const initials = getInitials(fullName);

    return `
      <!-- Account Information (no section title) -->
      <div class="settings-section">
        <div class="settings-card settings-card-with-avatar">
          <div class="settings-field">
            <label>Name</label>
            <div class="name-input-row">
              <div class="avatar-box">
                <div class="user-avatar-large" id="user-avatar-display">
                  ${initials || 'U'}
                </div>
              </div>
              <input
                type="text"
                id="full-name-input"
                class="settings-input settings-input-with-avatar"
                placeholder="Your name here"
                value="${fullName}"
                autocomplete="off"
              />
            </div>
          </div>

          <div class="settings-field">
            <label>Email</label>
            <div class="settings-value">${user?.email || 'N/A'}</div>
          </div>

          <!-- Save/Cancel buttons (hidden by default) -->
          <div class="settings-card-actions" id="name-change-actions" style="display: none;">
            <button class="btn-secondary" id="cancel-name-btn">Cancel</button>
            <button class="btn-primary" id="save-name-btn">Save changes</button>
          </div>
        </div>
      </div>

      <!-- Color Mode (title inside card) -->
      <div class="settings-section">
        <div class="settings-card">
          <h3 class="settings-card-title">Color mode</h3>
          <div class="theme-options">
            <button class="theme-option ${savedTheme === 'light' ? 'active' : ''}" data-theme="light">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="5"></circle>
                <line x1="12" y1="1" x2="12" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="23"></line>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                <line x1="1" y1="12" x2="3" y2="12"></line>
                <line x1="21" y1="12" x2="23" y2="12"></line>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
              </svg>
              <div>
                <div class="theme-option-title">Light</div>
              </div>
            </button>
            <button class="theme-option ${savedTheme === 'dark' ? 'active' : ''}" data-theme="dark">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
              </svg>
              <div>
                <div class="theme-option-title">Dark</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Render Billing tab content
   */
  private renderBillingTab(sub: SubscriptionData): string {
    const tierName = sub.tier.charAt(0).toUpperCase() + sub.tier.slice(1);
    const renewalDate = sub.current_period_end
      ? new Date(sub.current_period_end).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        })
      : 'N/A';

    // Format payment method display
    let paymentMethodDisplay = 'No payment method on file';

    if (this.paymentMethod?.card) {
      // Regular card payment method
      paymentMethodDisplay = `${this.paymentMethod.card.brand.charAt(0).toUpperCase() + this.paymentMethod.card.brand.slice(1)} •••• ${this.paymentMethod.card.last4}`;
    } else if (this.paymentMethod?.link) {
      // Link payment method (doesn't expose card details)
      paymentMethodDisplay = `Payment method via Link`;
    }

    return `
      <!-- Subscription Plan Section -->
      <div class="settings-section">
        <h2 class="settings-section-title">Subscription</h2>
        <div class="settings-card">
          <div class="subscription-plan-header">
            <div class="subscription-plan-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
              </svg>
            </div>
            <div class="subscription-plan-info">
              <div class="subscription-plan-name">${tierName} plan</div>
              <div class="subscription-plan-description">
                ${sub.query_limit} queries per month
              </div>
              ${sub.tier !== 'free' && sub.current_period_end ? `
                <div class="subscription-renewal-info">
                  ${sub.cancel_at_period_end
                    ? `Your subscription will end on ${renewalDate}.`
                    : `Your subscription will automatically renew on ${renewalDate}.`
                  }
                </div>
              ` : ''}
            </div>
            ${sub.tier !== 'free' && !sub.cancel_at_period_end ? `
              <button class="btn-danger" id="cancel-subscription-btn">
                Cancel
              </button>
            ` : sub.tier === 'free' ? `
              <button class="btn-primary" id="upgrade-btn">
                Upgrade Plan
              </button>
            ` : ''}
          </div>
        </div>
      </div>

      <!-- Payment Section -->
      ${sub.tier !== 'free' ? `
        <div class="settings-section">
          <h2 class="settings-section-title">Payment</h2>
          <div class="settings-card">
            <div class="payment-method-row">
              <div class="payment-method-info">
                <svg class="payment-card-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                  <line x1="1" y1="10" x2="23" y2="10"></line>
                </svg>
                <span class="payment-method-display">${paymentMethodDisplay}</span>
              </div>
              <div style="display: flex; gap: 8px;">
                ${this.paymentMethod ? `
                  <button class="btn-secondary btn-small" id="remove-payment-btn" style="color: #ef4444;">
                    Remove
                  </button>
                ` : ''}
                <button class="btn-secondary btn-small" id="update-payment-btn">
                  ${this.paymentMethod ? 'Update' : 'Add'}
                </button>
              </div>
            </div>
          </div>
        </div>
      ` : ''}

      <!-- Invoices Section -->
      ${sub.tier !== 'free' && this.invoices.length > 0 ? `
        <div class="settings-section">
          <h2 class="settings-section-title">Invoices</h2>
          <div class="settings-card">
            <table class="invoices-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${this.invoices.map(invoice => `
                  <tr>
                    <td>${new Date(invoice.date * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</td>
                    <td>$${invoice.amount_paid.toFixed(2)}</td>
                    <td><span class="invoice-status invoice-status-${invoice.status}">${invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}</span></td>
                    <td><a href="${invoice.hosted_invoice_url}" target="_blank" class="btn-link">View</a></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      ` : ''}
    `;
  }

  /**
   * Render Usage tab content
   */
  private renderUsageTab(sub: SubscriptionData): string {
    const usagePercentage = (sub.queries_this_month / sub.query_limit) * 100;
    const isAtLimit = usagePercentage >= 100;
    const isNearLimit = usagePercentage >= 80;

    return `
      <div class="settings-section">
        <h2 class="settings-section-title">Usage This Month</h2>
        <div class="settings-card">
          <div class="usage-stats">
            <div class="usage-number ${isNearLimit ? 'usage-warning' : ''}">
              ${sub.queries_this_month} / ${sub.query_limit}
            </div>
            <div class="usage-label">queries used</div>
          </div>

          <div class="usage-bar-container">
            <div class="usage-bar">
              <div class="usage-bar-fill ${isNearLimit ? 'usage-warning' : ''}"
                   style="width: ${Math.min(usagePercentage, 100)}%"></div>
            </div>
            <div class="usage-percentage">${Math.round(usagePercentage)}%</div>
          </div>

          ${isNearLimit && sub.tier === 'free' ? `
            <div class="usage-warning-message">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              <span>${isAtLimit
                ? "You've reached your monthly limit. Upgrade to continue asking questions."
                : "You're approaching your monthly limit. Consider upgrading to continue asking questions."}</span>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Render Account tab content
   */
  private renderAccountTab(): string {
    return `
      <!-- Log Out Section -->
      <div class="settings-section">
        <div class="settings-card">
          <div class="account-action-row">
            <div class="account-action-info">
              <h3 class="account-action-title">Log out of all devices</h3>
            </div>
            <button class="btn-secondary" id="logout-btn">Log out</button>
          </div>
        </div>
      </div>

      <!-- Delete Account Section -->
      <div class="settings-section">
        <div class="settings-card settings-card-danger">
          <div class="account-action-row">
            <div class="account-action-info">
              <h3 class="account-action-title">Delete account</h3>
              <p class="account-action-description">
                Permanently delete your account and all associated data. This action cannot be undone.
              </p>
            </div>
            <button class="btn-danger" id="delete-account-btn">Delete account</button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    // Tab buttons
    const tabButtons = this.container?.querySelectorAll('.settings-tab-button');
    tabButtons?.forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab') as TabName;
        if (tab) {
          window.location.hash = tab;
          this.switchTab(tab);
        }
      });
    });

    // Theme options
    const themeOptions = this.container?.querySelectorAll('.theme-option');
    themeOptions?.forEach(option => {
      option.addEventListener('click', () => {
        const theme = option.getAttribute('data-theme');
        if (theme) {
          this.setTheme(theme);
        }
      });
    });

    // Full name input with live avatar update and save/cancel buttons
    const fullNameInput = this.container?.querySelector('#full-name-input') as HTMLInputElement;
    fullNameInput?.addEventListener('input', (e) => {
      const target = e.target as HTMLInputElement;
      this.handleFullNameChange(target.value);
    });

    // Save name button
    const saveNameBtn = this.container?.querySelector('#save-name-btn');
    saveNameBtn?.addEventListener('click', () => this.handleSaveFullName());

    // Cancel name button
    const cancelNameBtn = this.container?.querySelector('#cancel-name-btn');
    cancelNameBtn?.addEventListener('click', () => this.handleCancelNameChange());

    // Update payment button
    const updatePaymentBtn = this.container?.querySelector('#update-payment-btn');
    updatePaymentBtn?.addEventListener('click', () => this.handleManageBilling());

    // Remove payment button
    const removePaymentBtn = this.container?.querySelector('#remove-payment-btn');
    removePaymentBtn?.addEventListener('click', () => this.handleRemovePaymentMethod());

    // Cancel subscription button
    const cancelSubscriptionBtn = this.container?.querySelector('#cancel-subscription-btn');
    cancelSubscriptionBtn?.addEventListener('click', () => this.handleCancelSubscription());

    // Upgrade button
    const upgradeBtn = this.container?.querySelector('#upgrade-btn');
    upgradeBtn?.addEventListener('click', () => {
      window.location.href = '/pricing';
    });

    // Logout button
    const logoutBtn = this.container?.querySelector('#logout-btn');
    logoutBtn?.addEventListener('click', () => this.handleLogout());

    // Delete account button
    const deleteAccountBtn = this.container?.querySelector('#delete-account-btn');
    deleteAccountBtn?.addEventListener('click', () => this.handleDeleteAccount());
  }

  /**
   * Set theme
   */
  private setTheme(theme: string): void {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    // Update active state
    const themeOptions = this.container?.querySelectorAll('.theme-option');
    themeOptions?.forEach(option => {
      if (option.getAttribute('data-theme') === theme) {
        option.classList.add('active');
      } else {
        option.classList.remove('active');
      }
    });
  }

  /**
   * Handle manage billing click (opens custom payment method modal)
   */
  private async handleManageBilling(): Promise<void> {
    const token = this.session?.session?.access_token;
    const userEmail = this.session?.user?.email;
    const userName = this.profile?.full_name || '';

    if (!token || !userEmail) return;

    // Show payment method modal
    showPaymentMethodModal({
      currentPaymentMethod: this.paymentMethod,
      userEmail: userEmail,
      userName: userName,
      accessToken: token,
      onSuccess: async () => {
        // Refresh payment method data after successful update
        // Use retry logic to handle Stripe propagation delays
        await this.fetchPaymentMethodWithRetry();
        this.render();
      },
      onCancel: () => {
        // Do nothing on cancel
      },
    });
  }

  /**
   * Handle remove payment method click
   */
  private async handleRemovePaymentMethod(): Promise<void> {
    if (!this.paymentMethod) return;

    // Confirm removal
    if (!confirm('Are you sure you want to remove this payment method? Your subscription will remain active until the end of the current billing period.')) {
      return;
    }

    const token = this.session?.session?.access_token;
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/stripe/remove-payment-method`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payment_method_id: this.paymentMethod.id,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to remove payment method');
      }

      // Success - refresh payment method
      this.paymentMethod = null;
      this.render();
      alert('Payment method removed successfully');
    } catch (error) {
      console.error('Error removing payment method:', error);
      alert(error instanceof Error ? error.message : 'Failed to remove payment method');
    }
  }

  /**
   * Handle cancel subscription click
   */
  private async handleCancelSubscription(): Promise<void> {
    // Get end date for display in modal
    const endDate = this.subscription?.current_period_end
      ? new Date(this.subscription.current_period_end).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        })
      : 'the end of your billing period';

    // Show cancel modal
    showCancelSubscriptionModal({
      endDate: endDate,
      onConfirm: async (reason: string, feedback: string) => {
        await this.processCancellation(reason, feedback);
      },
      onCancel: () => {
        // Do nothing on cancel
      },
    });
  }

  /**
   * Process subscription cancellation with reason and feedback
   */
  private async processCancellation(reason: string, feedback: string): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/stripe/cancel-subscription`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cancellation_reason: reason,
          cancellation_feedback: feedback,
        }),
      });

      if (response.ok) {
        alert('Your subscription has been scheduled for cancellation at the end of your billing period.');
        // Reload to update UI
        window.location.reload();
      } else {
        const error = await response.json();
        alert(`Failed to cancel subscription: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
      alert('Failed to cancel subscription');
    }
  }

  /**
   * Handle full name change - update avatar and show save/cancel buttons
   */
  private handleFullNameChange(value: string): void {
    // Update avatar initials in real-time
    const getInitials = (name: string): string => {
      if (!name || !name.trim()) return '';
      const parts = name.trim().split(' ').filter(p => p);
      if (parts.length === 0) return '';
      if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
      return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    };

    const avatarDisplay = this.container?.querySelector('#user-avatar-display');
    if (avatarDisplay) {
      avatarDisplay.textContent = getInitials(value) || 'U';
    }

    // Show/hide save/cancel buttons based on whether value changed
    const hasChanged = value.trim() !== (this.originalFullName || '');
    const actionsDiv = this.container?.querySelector('#name-change-actions') as HTMLElement;
    if (actionsDiv) {
      actionsDiv.style.display = hasChanged ? 'flex' : 'none';
    }

    this.hasUnsavedChanges = hasChanged;
  }

  /**
   * Handle save full name button click
   */
  private async handleSaveFullName(): Promise<void> {
    const fullNameInput = this.container?.querySelector('#full-name-input') as HTMLInputElement;
    if (!fullNameInput) return;

    const fullName = fullNameInput.value;

    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/user/profile`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: fullName.trim() || null,
        }),
      });

      if (response.ok) {
        this.profile = await response.json();

        // Update cache with fresh profile data
        if (this.profile) {
          updateCachedProfile(this.profile);
        }

        // Update original name and hide buttons
        this.originalFullName = fullName.trim();
        this.hasUnsavedChanges = false;

        const actionsDiv = this.container?.querySelector('#name-change-actions') as HTMLElement;
        if (actionsDiv) {
          actionsDiv.style.display = 'none';
        }

        // Dispatch event to update user menu initials
        const event = new CustomEvent('profile-updated', {
          detail: { full_name: fullName.trim() },
        });
        window.dispatchEvent(event);

        // Show success notification
        this.showNotification('Account preferences updated');
      } else {
        alert('Failed to save name. Please try again.');
      }
    } catch (error) {
      console.error('Failed to save full name:', error);
      alert('Failed to save name. Please try again.');
    }
  }

  /**
   * Show notification toast in top right corner
   */
  private showNotification(message: string): void {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'settings-notification';
    notification.innerHTML = `
      <svg class="notification-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <circle cx="12" cy="12" r="10"></circle>
        <path d="M12 16v-4"></path>
        <path d="M12 8h.01"></path>
      </svg>
      <span class="notification-message">${message}</span>
      <button class="notification-close" aria-label="Close notification">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    `;

    // Add to body
    document.body.appendChild(notification);

    // Trigger animation
    setTimeout(() => {
      notification.classList.add('show');
    }, 10);

    // Close handlers
    const closeNotification = () => {
      notification.classList.remove('show');
      setTimeout(() => {
        document.body.removeChild(notification);
      }, 300);
    };

    // Close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      closeNotification();
    });

    // Close on click anywhere on screen
    const clickHandler = (e: MouseEvent) => {
      if (!notification.contains(e.target as Node)) {
        closeNotification();
        document.removeEventListener('click', clickHandler);
      }
    };
    // Add listener after a short delay to prevent immediate closing
    setTimeout(() => {
      document.addEventListener('click', clickHandler);
    }, 100);

    // Auto-close after 5 seconds
    setTimeout(() => {
      if (document.body.contains(notification)) {
        closeNotification();
        document.removeEventListener('click', clickHandler);
      }
    }, 5000);
  }

  /**
   * Handle cancel name change button click
   */
  private handleCancelNameChange(): void {
    // Restore original name
    const fullNameInput = this.container?.querySelector('#full-name-input') as HTMLInputElement;
    if (fullNameInput) {
      fullNameInput.value = this.originalFullName || '';
    }

    // Update avatar back to original
    const getInitials = (name: string): string => {
      if (!name || !name.trim()) return '';
      const parts = name.trim().split(' ').filter(p => p);
      if (parts.length === 0) return '';
      if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
      return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    };

    const avatarDisplay = this.container?.querySelector('#user-avatar-display');
    if (avatarDisplay) {
      avatarDisplay.textContent = getInitials(this.originalFullName) || 'U';
    }

    // Hide save/cancel buttons
    const actionsDiv = this.container?.querySelector('#name-change-actions') as HTMLElement;
    if (actionsDiv) {
      actionsDiv.style.display = 'none';
    }

    this.hasUnsavedChanges = false;
  }

  /**
   * Handle logout button click - show confirmation modal
   */
  private handleLogout(): void {
    this.showLogoutConfirmationModal();
  }

  /**
   * Show logout confirmation modal
   */
  private showLogoutConfirmationModal(): void {
    // Create modal overlay
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'cancel-modal-overlay';
    modalOverlay.innerHTML = `
      <div class="cancel-modal">
        <div class="cancel-modal-header">
          <h2>Log out of all devices</h2>
        </div>
        <div class="cancel-modal-body">
          <p class="cancel-modal-description">
            Are you sure you want to log out of all devices?
          </p>
        </div>
        <div class="cancel-modal-footer">
          <button class="btn-secondary" id="logout-modal-cancel-btn">Cancel</button>
          <button class="btn-primary" id="logout-modal-confirm-btn">Log out of all devices</button>
        </div>
      </div>
    `;

    // Add to body
    document.body.appendChild(modalOverlay);

    // Get elements
    const confirmBtn = modalOverlay.querySelector('#logout-modal-confirm-btn');
    const cancelBtn = modalOverlay.querySelector('#logout-modal-cancel-btn');

    // Handle cancel
    const closeModal = () => {
      document.body.removeChild(modalOverlay);
    };

    cancelBtn?.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) closeModal();
    });

    // Handle confirm
    confirmBtn?.addEventListener('click', async () => {
      await this.processLogout();
      closeModal();
    });
  }

  /**
   * Process logout
   */
  private async processLogout(): Promise<void> {
    const result = await signOut();

    if (result.success) {
      // Redirect to home page
      window.location.href = '/';
    } else {
      console.error('Failed to log out:', result.error);
      alert(`Failed to log out: ${result.error || 'Please try again.'}`);
    }
  }

  /**
   * Handle delete account button click - show confirmation modal
   */
  private handleDeleteAccount(): void {
    // Show delete account confirmation modal
    this.showDeleteAccountModal();
  }

  /**
   * Show delete account confirmation modal
   */
  private showDeleteAccountModal(): void {
    // Create modal overlay
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'cancel-modal-overlay';
    modalOverlay.innerHTML = `
      <div class="cancel-modal">
        <div class="cancel-modal-header">
          <h2>Delete Account</h2>
        </div>
        <div class="cancel-modal-body">
          <p class="cancel-modal-description">
            This action will permanently delete your account and all associated data, including:
          </p>
          <ul style="margin: 16px 0; padding-left: 20px; color: var(--text-secondary); font-size: 14px; line-height: 1.6;">
            <li>Saved queries and favorites</li>
            <li>User preferences and settings</li>
            <li>Subscription and billing history</li>
          </ul>
          <p class="cancel-modal-description" style="margin-bottom: 16px;">
            <strong>Your active subscription will be automatically canceled.</strong>
          </p>
          <p class="cancel-modal-description" style="margin-bottom: 16px;">
            This action cannot be undone. To confirm, please type <strong>DELETE</strong> below:
          </p>
          <div class="cancel-form-field">
            <input
              type="text"
              id="delete-confirm-input"
              class="cancel-form-select"
              placeholder="Type DELETE to confirm"
              autocomplete="off"
              style="text-transform: uppercase;"
            />
          </div>
        </div>
        <div class="cancel-modal-footer">
          <button class="btn-secondary" id="delete-modal-cancel-btn">Cancel</button>
          <button class="btn-danger" id="delete-modal-confirm-btn" disabled>Delete Account</button>
        </div>
      </div>
    `;

    // Add to body
    document.body.appendChild(modalOverlay);

    // Get elements
    const confirmInput = modalOverlay.querySelector('#delete-confirm-input') as HTMLInputElement;
    const confirmBtn = modalOverlay.querySelector('#delete-modal-confirm-btn') as HTMLButtonElement;
    const cancelBtn = modalOverlay.querySelector('#delete-modal-cancel-btn');

    // Enable/disable confirm button based on input
    confirmInput?.addEventListener('input', () => {
      const isValid = confirmInput.value.toUpperCase() === 'DELETE';
      confirmBtn.disabled = !isValid;
      confirmBtn.style.opacity = isValid ? '1' : '0.5';
    });

    // Handle cancel
    const closeModal = () => {
      document.body.removeChild(modalOverlay);
    };

    cancelBtn?.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) closeModal();
    });

    // Handle confirm
    confirmBtn?.addEventListener('click', async () => {
      if (confirmInput.value.toUpperCase() === 'DELETE') {
        await this.processAccountDeletion();
        closeModal();
      }
    });
  }

  /**
   * Process account deletion
   */
  private async processAccountDeletion(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/user/account`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        // Import supabase client dynamically
        const { supabase } = await import('../../lib/auth');

        // Sign out
        await supabase.auth.signOut();

        // Show success message
        alert('Your account has been successfully deleted.');

        // Redirect to home page
        window.location.href = '/';
      } else {
        const error = await response.json();
        alert(`Failed to delete account: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to delete account:', error);
      alert('Failed to delete account. Please try again.');
    }
  }

}

// Initialize settings page if on settings route
export function initSettingsPage(containerId: string): void {
  const page = new SettingsPage();
  page.init(containerId);
}
