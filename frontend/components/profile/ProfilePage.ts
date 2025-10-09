/**
 * Profile Page Component
 * Displays user profile, subscription, and usage information
 */

import { getSession, type SessionInfo } from '../../lib/auth';

interface SubscriptionData {
  tier: string;
  status: string;
  queries_this_month: number;
  query_limit: number;
  current_period_end?: string;
  stripe_customer_id?: string;
}

export class ProfilePage {
  private container: HTMLElement | null = null;
  private session: SessionInfo | null = null;
  private subscription: SubscriptionData | null = null;

  /**
   * Initialize and render the profile page
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

    // Fetch subscription data
    await this.fetchSubscription();

    // Render profile
    this.render();
  }

  /**
   * Fetch user subscription data from API
   */
  private async fetchSubscription(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch('/api/subscription/status', {
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
   * Render unauthenticated state
   */
  private renderUnauthenticated(): void {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="profile-container">
        <div class="profile-unauthenticated">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <h2>Sign in to view your profile</h2>
          <p>Create an account or sign in to access your profile, subscription, and usage statistics.</p>
          <button class="btn-primary" id="profile-signin-btn">Sign In</button>
        </div>
      </div>
    `;

    // Attach event listener
    const signinBtn = this.container.querySelector('#profile-signin-btn');
    signinBtn?.addEventListener('click', () => {
      window.dispatchEvent(new CustomEvent('show-login-modal'));
    });
  }

  /**
   * Render the profile page
   */
  private render(): void {
    if (!this.container || !this.session || !this.subscription) return;

    const user = this.session.user;
    const sub = this.subscription;

    // Calculate usage percentage
    const usagePercentage = (sub.queries_this_month / sub.query_limit) * 100;
    const isNearLimit = usagePercentage >= 80;

    // Format tier name
    const tierName = sub.tier.charAt(0).toUpperCase() + sub.tier.slice(1);

    // Format renewal date
    const renewalDate = sub.current_period_end
      ? new Date(sub.current_period_end).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        })
      : 'N/A';

    this.container.innerHTML = `
      <div class="profile-container">
        <div class="profile-header">
          <h1>Profile</h1>
        </div>

        <!-- Account Information -->
        <div class="profile-section">
          <h2 class="profile-section-title">Account Information</h2>
          <div class="profile-card">
            <div class="profile-field">
              <label>Email</label>
              <div class="profile-value">${user?.email || 'N/A'}</div>
            </div>
            <div class="profile-field">
              <label>User ID</label>
              <div class="profile-value profile-value-mono">${user?.id || 'N/A'}</div>
            </div>
            <div class="profile-field">
              <label>Account Created</label>
              <div class="profile-value">
                ${user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
              </div>
            </div>
          </div>
        </div>

        <!-- Subscription -->
        <div class="profile-section">
          <h2 class="profile-section-title">Subscription</h2>
          <div class="profile-card">
            <div class="subscription-header">
              <div>
                <div class="subscription-tier">
                  <span class="tier-badge tier-${sub.tier}">${tierName} Plan</span>
                  <span class="subscription-status status-${sub.status}">${sub.status}</span>
                </div>
                <div class="subscription-limit">${sub.query_limit} queries per month</div>
              </div>
              ${sub.tier !== 'free' ? `
                <button class="btn-secondary" id="manage-billing-btn">
                  Manage Billing
                </button>
              ` : `
                <button class="btn-primary" id="upgrade-btn">
                  Upgrade Plan
                </button>
              `}
            </div>

            ${sub.tier !== 'free' && sub.current_period_end ? `
              <div class="profile-field" style="margin-top: 16px;">
                <label>Next Billing Date</label>
                <div class="profile-value">${renewalDate}</div>
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Usage -->
        <div class="profile-section">
          <h2 class="profile-section-title">Usage This Month</h2>
          <div class="profile-card">
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
                <span>You're approaching your monthly limit. Consider upgrading to continue asking questions.</span>
              </div>
            ` : ''}
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="profile-section">
          <h2 class="profile-section-title">Quick Actions</h2>
          <div class="profile-actions">
            <a href="/" class="profile-action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              <div class="profile-action-content">
                <div class="profile-action-title">Ask a Question</div>
                <div class="profile-action-description">Query UFA statistics</div>
              </div>
            </a>

            <a href="/pricing" class="profile-action-card">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 6v6l4 2"></path>
              </svg>
              <div class="profile-action-content">
                <div class="profile-action-title">View Plans</div>
                <div class="profile-action-description">Compare subscription tiers</div>
              </div>
            </a>

            <button class="profile-action-card" id="refresh-data-btn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
              <div class="profile-action-content">
                <div class="profile-action-title">Refresh Data</div>
                <div class="profile-action-description">Update usage statistics</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    `;

    // Attach event listeners
    this.attachEventListeners();
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    // Manage billing button
    const manageBillingBtn = this.container?.querySelector('#manage-billing-btn');
    manageBillingBtn?.addEventListener('click', () => this.handleManageBilling());

    // Upgrade button
    const upgradeBtn = this.container?.querySelector('#upgrade-btn');
    upgradeBtn?.addEventListener('click', () => {
      window.location.href = '/pricing';
    });

    // Refresh data button
    const refreshBtn = this.container?.querySelector('#refresh-data-btn');
    refreshBtn?.addEventListener('click', () => this.handleRefresh());
  }

  /**
   * Handle manage billing click
   */
  private async handleManageBilling(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch('/api/stripe/create-billing-portal-session', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          return_url: window.location.href,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        window.location.href = data.portal_url;
      } else {
        alert('Failed to open billing portal');
      }
    } catch (error) {
      console.error('Failed to open billing portal:', error);
      alert('Failed to open billing portal');
    }
  }

  /**
   * Handle refresh data
   */
  private async handleRefresh(): Promise<void> {
    await this.fetchSubscription();
    this.render();
  }
}

// Initialize profile page if on profile route
export function initProfilePage(containerId: string): void {
  const page = new ProfilePage();
  page.init(containerId);
}
