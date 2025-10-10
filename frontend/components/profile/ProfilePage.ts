/**
 * Profile Page Component
 * Displays user profile, subscription, and usage information
 */

import { getSession, type SessionInfo } from '../../lib/auth';

// Get API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface SubscriptionData {
  tier: string;
  status: string;
  queries_this_month: number;
  query_limit: number;
  current_period_end?: string;
  stripe_customer_id?: string;
}

interface UserProfile {
  full_name: string | null;
  theme: string;
  default_season: number | null;
  notifications_enabled: boolean;
  email_digest_frequency: string;
  favorite_stat_categories: string[];
}

export class ProfilePage {
  private container: HTMLElement | null = null;
  private session: SessionInfo | null = null;
  private subscription: SubscriptionData | null = null;
  private profile: UserProfile | null = null;

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

    // Fetch subscription data and profile
    await Promise.all([
      this.fetchSubscription(),
      this.fetchProfile(),
    ]);

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
    if (!this.container || !this.session || !this.subscription || !this.profile) return;

    const user = this.session.user;
    const sub = this.subscription;
    const profile = this.profile;

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
              <label>Full Name</label>
              <div class="profile-field-editable">
                <input
                  type="text"
                  id="full-name-input"
                  class="profile-input"
                  placeholder="Enter your full name"
                  value="${profile.full_name || ''}"
                />
                <button class="btn-primary btn-small" id="save-name-btn">Save</button>
              </div>
              <div class="profile-field-hint">Used to generate your initials in the user menu</div>
            </div>
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
      </div>
    `;

    // Attach event listeners
    this.attachEventListeners();
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    // Save full name button
    const saveNameBtn = this.container?.querySelector('#save-name-btn');
    saveNameBtn?.addEventListener('click', () => this.handleSaveFullName());

    // Manage billing button
    const manageBillingBtn = this.container?.querySelector('#manage-billing-btn');
    manageBillingBtn?.addEventListener('click', () => this.handleManageBilling());

    // Upgrade button
    const upgradeBtn = this.container?.querySelector('#upgrade-btn');
    upgradeBtn?.addEventListener('click', () => {
      window.location.href = '/pricing';
    });
  }

  /**
   * Handle save full name
   */
  private async handleSaveFullName(): Promise<void> {
    const input = this.container?.querySelector('#full-name-input') as HTMLInputElement;
    const saveBtn = this.container?.querySelector('#save-name-btn') as HTMLButtonElement;

    if (!input || !saveBtn) return;

    const fullName = input.value.trim();

    // Update button state
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
      const token = this.session?.session?.access_token;
      if (!token) {
        alert('Not authenticated');
        return;
      }

      const response = await fetch(`${API_BASE_URL}/api/user/profile`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: fullName || null,
        }),
      });

      if (response.ok) {
        this.profile = await response.json();
        saveBtn.textContent = 'Saved!';

        // Dispatch event to update user menu initials
        window.dispatchEvent(new CustomEvent('profile-updated', {
          detail: { full_name: fullName },
        }));

        // Reset button after delay
        setTimeout(() => {
          saveBtn.textContent = 'Save';
          saveBtn.disabled = false;
        }, 2000);
      } else {
        alert('Failed to save full name');
        saveBtn.textContent = 'Save';
        saveBtn.disabled = false;
      }
    } catch (error) {
      console.error('Failed to save full name:', error);
      alert('Failed to save full name');
      saveBtn.textContent = 'Save';
      saveBtn.disabled = false;
    }
  }

  /**
   * Handle manage billing click
   */
  private async handleManageBilling(): Promise<void> {
    try {
      const token = this.session?.session?.access_token;
      if (!token) return;

      const response = await fetch(`${API_BASE_URL}/api/stripe/create-billing-portal-session`, {
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
}

// Initialize profile page if on profile route
export function initProfilePage(containerId: string): void {
  const page = new ProfilePage();
  page.init(containerId);
}
