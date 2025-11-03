/**
 * Settings Page Component
 * Displays user settings with tabbed interface: Profile, Billing, Usage
 */

import { getSession, type SessionInfo } from '../../lib/auth';
import { showPaymentMethodModal } from '../billing/PaymentMethodModal';
import { showCancelSubscriptionModal } from './CancelSubscriptionModal';

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

type TabName = 'profile' | 'billing' | 'usage';

export class SettingsPage {
  private container: HTMLElement | null = null;
  private session: SessionInfo | null = null;
  private subscription: SubscriptionData | null = null;
  private profile: UserProfile | null = null;
  private paymentMethod: PaymentMethod | null = null;
  private invoices: Invoice[] = [];
  private activeTab: TabName = 'profile';
  private saveTimeout: number | null = null;

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

    // Fetch subscription data, profile, payment method, and invoices
    await Promise.all([
      this.fetchSubscription(),
      this.fetchProfile(),
      this.fetchPaymentMethod(),
      this.fetchInvoices(),
    ]);

    // Check URL hash for tab
    const hash = window.location.hash.slice(1) as TabName;
    if (hash && ['profile', 'billing', 'usage'].includes(hash)) {
      this.activeTab = hash;
    }

    // Render settings
    this.render();
    this.setupHashNavigation();
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
      const hash = window.location.hash.slice(1) as TabName;
      if (hash && ['profile', 'billing', 'usage'].includes(hash)) {
        this.switchTab(hash);
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
          <button class="settings-tab-button ${this.activeTab === 'profile' ? 'active' : ''}" data-tab="profile">
            Profile
          </button>
          <button class="settings-tab-button ${this.activeTab === 'billing' ? 'active' : ''}" data-tab="billing">
            Billing
          </button>
          <button class="settings-tab-button ${this.activeTab === 'usage' ? 'active' : ''}" data-tab="usage">
            Usage
          </button>
        </div>

        <!-- Profile Tab -->
        <div class="settings-tab-content ${this.activeTab === 'profile' ? 'active' : ''}" data-tab="profile">
          ${this.renderProfileTab(user)}
        </div>

        <!-- Billing Tab -->
        <div class="settings-tab-content ${this.activeTab === 'billing' ? 'active' : ''}" data-tab="billing">
          ${this.renderBillingTab(sub)}
        </div>

        <!-- Usage Tab -->
        <div class="settings-tab-content ${this.activeTab === 'usage' ? 'active' : ''}" data-tab="usage">
          ${this.renderUsageTab(sub)}
        </div>
      </div>
    `;

    // Attach event listeners
    this.attachEventListeners();
  }

  /**
   * Render Profile tab content
   */
  private renderProfileTab(user: any): string {
    const savedTheme = localStorage.getItem('theme') || 'dark';

    return `
      <!-- Account Information -->
      <div class="settings-section">
        <h2 class="settings-section-title">Account Information</h2>
        <div class="settings-card">
          <div class="settings-field">
            <label>Name</label>
            <input
              type="text"
              id="full-name-input"
              class="settings-value settings-value-mono"
              placeholder="Your name here"
              value="${this.profile?.full_name || ''}"
              autocomplete="off"
            />
          </div>
          <div class="settings-field">
            <label>Email</label>
            <div class="settings-value">${user?.email || 'N/A'}</div>
          </div>
        </div>
      </div>

      <!-- Color Mode -->
      <div class="settings-section">
        <h2 class="settings-section-title">Color mode</h2>
        <div class="settings-card">
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

    // Full name input with auto-save
    const fullNameInput = this.container?.querySelector('#full-name-input') as HTMLInputElement;
    fullNameInput?.addEventListener('input', (e) => {
      const target = e.target as HTMLInputElement;
      this.handleFullNameInput(target.value);
    });

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
   * Handle full name input with debouncing
   */
  private handleFullNameInput(value: string): void {
    // Clear existing timeout
    if (this.saveTimeout !== null) {
      window.clearTimeout(this.saveTimeout);
    }

    // Set new timeout to save after 500ms
    this.saveTimeout = window.setTimeout(async () => {
      await this.saveFullName(value);
    }, 500);
  }

  /**
   * Save full name to API
   */
  private async saveFullName(fullName: string): Promise<void> {
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

        // Dispatch event to update user menu initials
        window.dispatchEvent(new CustomEvent('profile-updated', {
          detail: { full_name: fullName.trim() },
        }));
      }
    } catch (error) {
      console.error('Failed to save full name:', error);
    }
  }

}

// Initialize settings page if on settings route
export function initSettingsPage(containerId: string): void {
  const page = new SettingsPage();
  page.init(containerId);
}
