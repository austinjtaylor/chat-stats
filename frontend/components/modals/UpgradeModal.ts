/**
 * Upgrade Modal Component
 * Shown when users hit their query limit on free tier
 */

import { getSession } from '../../lib/auth';

export class UpgradeModal {
  private modal: HTMLElement | null = null;
  private queryLimit: number = 10;

  constructor() {}

  /**
   * Show the upgrade modal
   */
  show(_queriesUsed: number = 10, queryLimit: number = 10): void {
    this.queryLimit = queryLimit;

    if (this.modal) {
      this.modal.classList.add('active');
      return;
    }

    this.modal = this.createModal();
    document.body.appendChild(this.modal);
    this.modal.classList.add('active');
  }

  /**
   * Hide the upgrade modal
   */
  hide(): void {
    if (this.modal) {
      this.modal.classList.remove('active');
    }
  }

  /**
   * Destroy the modal and remove from DOM
   */
  destroy(): void {
    if (this.modal) {
      this.modal.remove();
      this.modal = null;
    }
  }

  /**
   * Create the modal HTML element
   */
  private createModal(): HTMLElement {
    const modal = document.createElement('div');
    modal.className = 'upgrade-modal';
    modal.innerHTML = `
      <div class="upgrade-modal-overlay"></div>
      <div class="upgrade-modal-content">
        <button class="upgrade-modal-close" aria-label="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        <div class="upgrade-modal-icon">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="32" fill="currentColor" opacity="0.1"/>
            <path d="M32 12v28M32 48h.01M12 32h40" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          </svg>
        </div>

        <h2 class="upgrade-modal-title">You've Reached Your Limit</h2>
        <p class="upgrade-modal-subtitle">
          You've used all ${this.queryLimit} queries on the Free plan this month.
        </p>

        <div class="upgrade-modal-comparison">
          <div class="upgrade-modal-plan">
            <div class="upgrade-modal-plan-header">
              <h3>Free</h3>
              <div class="upgrade-modal-plan-price">$0</div>
            </div>
            <ul class="upgrade-modal-plan-features">
              <li>✓ 10 queries/month</li>
              <li>✓ Basic features</li>
            </ul>
            <div class="upgrade-modal-plan-status">Current Plan</div>
          </div>

          <div class="upgrade-modal-plan upgrade-modal-plan-highlighted">
            <div class="upgrade-modal-plan-badge">Recommended</div>
            <div class="upgrade-modal-plan-header">
              <h3>Pro</h3>
              <div class="upgrade-modal-plan-price">
                $4.99<span>/month</span>
              </div>
            </div>
            <ul class="upgrade-modal-plan-features">
              <li>✓ 200 queries/month</li>
              <li>✓ Priority response times</li>
              <li>✓ Advanced analytics</li>
              <li>✓ Export to CSV</li>
              <li>✓ Email support</li>
            </ul>
            <button class="btn-upgrade-pro" id="upgradeProBtn">
              Upgrade to Pro
            </button>
          </div>
        </div>

        <p class="upgrade-modal-footer">
          Your free queries will reset on the 1st of next month.
          <a href="/pricing" class="upgrade-modal-link">View all plans →</a>
        </p>
      </div>
    `;

    this.attachEventListeners(modal);
    return modal;
  }

  /**
   * Attach event listeners to modal elements
   */
  private attachEventListeners(modal: HTMLElement): void {
    // Close button
    const closeBtn = modal.querySelector('.upgrade-modal-close');
    closeBtn?.addEventListener('click', () => this.hide());

    // Overlay click to close
    const overlay = modal.querySelector('.upgrade-modal-overlay');
    overlay?.addEventListener('click', () => this.hide());

    // Upgrade button
    const upgradeBtn = modal.querySelector('#upgradeProBtn');
    upgradeBtn?.addEventListener('click', () => this.handleUpgrade());

    // ESC key to close
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        this.hide();
      }
    };
    document.addEventListener('keydown', handleEsc);
  }

  /**
   * Handle upgrade button click
   */
  private async handleUpgrade(): Promise<void> {
    const button = this.modal?.querySelector('#upgradeProBtn') as HTMLButtonElement;
    if (!button) return;

    // Show loading state
    const originalText = button.textContent;
    button.textContent = 'Processing...';
    button.disabled = true;

    try {
      const session = await getSession();
      const token = session.session?.access_token;

      if (!token) {
        this.hide();
        window.dispatchEvent(new CustomEvent('show-login-modal'));
        return;
      }

      // Stripe price ID for Pro plan ($5/month)
      const STRIPE_PRO_PRICE_ID = 'price_1SEVEqFQ5wQ0K5wX7rwFg6z2';

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/stripe/create-checkout-session`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          price_id: STRIPE_PRO_PRICE_ID,
          success_url: `${window.location.origin}/?upgrade=success`,
          cancel_url: `${window.location.origin}/?upgrade=cancel`,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Redirect to Stripe checkout
        window.location.href = data.checkout_url;
      } else {
        const error = await response.json().catch(() => ({ detail: 'Failed to create checkout session' }));
        alert(error.detail || 'Failed to create checkout session');

        // Restore button state
        button.textContent = originalText;
        button.disabled = false;
      }
    } catch (error) {
      console.error('Upgrade error:', error);
      alert('An error occurred. Please try again.');

      // Restore button state
      button.textContent = originalText;
      button.disabled = false;
    }
  }
}

// Export singleton instance
let upgradeModalInstance: UpgradeModal | null = null;

export function showUpgradeModal(queriesUsed: number = 10, queryLimit: number = 10): void {
  if (!upgradeModalInstance) {
    upgradeModalInstance = new UpgradeModal();
  }
  upgradeModalInstance.show(queriesUsed, queryLimit);
}

export function hideUpgradeModal(): void {
  upgradeModalInstance?.hide();
}

export function destroyUpgradeModal(): void {
  upgradeModalInstance?.destroy();
  upgradeModalInstance = null;
}
