/**
 * Pricing Page Component
 * Displays subscription tiers and handles Stripe checkout
 */

import { getSession, isAuthenticated } from '../../lib/auth';

interface PricingTier {
  name: string;
  price: number;
  queries: number;
  features: string[];
  highlighted?: boolean;
}

const PRICING_TIERS: PricingTier[] = [
  {
    name: 'Free',
    price: 0,
    queries: 10,
    features: [
      '10 AI queries per month',
      'Access to all UFA statistics',
      'Save favorite players and teams',
      'Basic query history',
    ],
  },
  {
    name: 'Pro',
    price: 4.99,
    queries: 200,
    features: [
      '200 AI queries per month',
      'Priority response times',
      'Advanced analytics',
      'Export data to CSV',
      'Extended query history',
      'Email support',
    ],
    highlighted: true,
  },
];

export class PricingPage {
  private container: HTMLElement | null = null;
  private currentTier: string = 'free';

  /**
   * Initialize and render the pricing page
   */
  async init(containerId: string): Promise<void> {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    // Get user's current tier if authenticated
    const authenticated = await isAuthenticated();
    if (authenticated) {
      await this.fetchCurrentTier();
    }

    this.render();
  }

  /**
   * Fetch user's current subscription tier
   */
  private async fetchCurrentTier(): Promise<void> {
    try {
      const session = await getSession();
      const token = session.session?.access_token;
      if (!token) return;

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/subscription/status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        this.currentTier = data.tier || 'free';
      }
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
    }
  }

  /**
   * Render the pricing page
   */
  private render(): void {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="pricing-container">
        <div class="pricing-header">
          <h1>Choose Your Plan</h1>
          <p class="pricing-subtitle">
            Get instant access to comprehensive UFA statistics with our AI-powered chat interface
          </p>
        </div>

        <div class="pricing-tiers">
          ${PRICING_TIERS.map(tier => this.renderTier(tier)).join('')}
        </div>

        <div class="pricing-faq">
          <h2>Frequently Asked Questions</h2>

          <div class="faq-item">
            <h3>Can I change my plan later?</h3>
            <p>Yes! You can upgrade or downgrade your plan at any time from your profile page.</p>
          </div>

          <div class="faq-item">
            <h3>What happens when I reach my query limit?</h3>
            <p>On the Free plan, you'll be prompted to upgrade. Your limit resets on the 1st of each month.</p>
          </div>

          <div class="faq-item">
            <h3>How do I cancel my subscription?</h3>
            <p>You can cancel anytime from your profile page. You'll continue to have access until the end of your billing period.</p>
          </div>

          <div class="faq-item">
            <h3>Do you offer refunds?</h3>
            <p>We offer a 30-day money-back guarantee on all Pro subscriptions. No questions asked.</p>
          </div>
        </div>
      </div>
    `;

    this.attachEventListeners();
  }

  /**
   * Render a single pricing tier card
   */
  private renderTier(tier: PricingTier): string {
    const isCurrentTier = tier.name.toLowerCase() === this.currentTier;
    const isFree = tier.price === 0;

    return `
      <div class="pricing-tier ${tier.highlighted ? 'pricing-tier-highlighted' : ''} ${isCurrentTier ? 'pricing-tier-current' : ''}">
        ${tier.highlighted ? '<div class="pricing-tier-badge">Most Popular</div>' : ''}
        ${isCurrentTier ? '<div class="pricing-tier-current-badge">Current Plan</div>' : ''}

        <div class="pricing-tier-header">
          <h3 class="pricing-tier-name">${tier.name}</h3>
          <div class="pricing-tier-price">
            <span class="pricing-tier-price-amount">$${tier.price.toFixed(2)}</span>
            ${!isFree ? '<span class="pricing-tier-price-period">/month</span>' : '<span class="pricing-tier-price-period">forever</span>'}
          </div>
          <p class="pricing-tier-queries">${tier.queries} queries per month</p>
        </div>

        <ul class="pricing-tier-features">
          ${tier.features.map(feature => `
            <li class="pricing-tier-feature">
              <svg class="pricing-tier-checkmark" width="20" height="20" viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="10" fill="currentColor" opacity="0.1"/>
                <path d="M6 10l2.5 2.5L14 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>${feature}</span>
            </li>
          `).join('')}
        </ul>

        <div class="pricing-tier-cta">
          ${this.renderCTAButton(tier, isCurrentTier)}
        </div>
      </div>
    `;
  }

  /**
   * Render the call-to-action button for a tier
   */
  private renderCTAButton(tier: PricingTier, isCurrentTier: boolean): string {
    if (isCurrentTier) {
      return `
        <button class="btn-pricing btn-pricing-current" disabled>
          Current Plan
        </button>
      `;
    }

    if (tier.price === 0) {
      return `
        <a href="/" class="btn-pricing btn-pricing-secondary">
          Get Started Free
        </a>
      `;
    }

    return `
      <button class="btn-pricing btn-pricing-primary" data-tier="${tier.name.toLowerCase()}" data-action="upgrade">
        Upgrade to ${tier.name}
      </button>
    `;
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    // Upgrade buttons
    const upgradeButtons = this.container?.querySelectorAll('[data-action="upgrade"]');
    upgradeButtons?.forEach(button => {
      button.addEventListener('click', (e) => {
        const tier = (e.target as HTMLElement).getAttribute('data-tier');
        if (tier) {
          this.handleUpgrade(tier);
        }
      });
    });
  }

  /**
   * Handle upgrade button click
   */
  private async handleUpgrade(tier: string): Promise<void> {
    const authenticated = await isAuthenticated();

    if (!authenticated) {
      // Show login modal
      window.dispatchEvent(new CustomEvent('show-login-modal'));
      return;
    }

    // Stripe price IDs for each tier
    const STRIPE_PRICE_IDS: Record<string, string> = {
      'pro': 'price_1SHunhFDSSUl9V6nc8jPnWX7', // Pro plan: $5/month
    };

    const priceId = STRIPE_PRICE_IDS[tier];
    if (!priceId) {
      console.error(`No price ID found for tier: ${tier}`);
      alert('Unable to process upgrade. Please contact support.');
      return;
    }

    try {
      const session = await getSession();
      const token = session.session?.access_token;
      if (!token) {
        window.dispatchEvent(new CustomEvent('show-login-modal'));
        return;
      }

      // Show loading state
      const button = this.container?.querySelector(`[data-tier="${tier}"]`) as HTMLButtonElement;
      if (button) {
        button.disabled = true;
        button.textContent = 'Processing...';
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/stripe/create-checkout-session`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          price_id: priceId,
          success_url: `${window.location.origin}/profile?upgrade=success`,
          cancel_url: `${window.location.origin}/pricing?upgrade=cancel`,
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
        if (button) {
          button.disabled = false;
          button.textContent = `Upgrade to ${tier.charAt(0).toUpperCase() + tier.slice(1)}`;
        }
      }
    } catch (error) {
      console.error('Upgrade error:', error);
      alert('An error occurred. Please try again.');

      // Restore button state
      const button = this.container?.querySelector(`[data-tier="${tier}"]`) as HTMLButtonElement;
      if (button) {
        button.disabled = false;
        button.textContent = `Upgrade to ${tier.charAt(0).toUpperCase() + tier.slice(1)}`;
      }
    }
  }
}

// Initialize pricing page if on pricing route
export function initPricingPage(containerId: string): void {
  const page = new PricingPage();
  page.init(containerId);
}
