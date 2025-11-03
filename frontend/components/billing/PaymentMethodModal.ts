/**
 * Simple Payment Method Modal
 * Uses Stripe Payment Element with SetupIntent following Stripe best practices
 */

import { loadStripe, Stripe, StripeElements } from '@stripe/stripe-js';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '';

// Type definitions
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
  billing_details?: {
    name?: string;
    email?: string;
    phone?: string;
    address?: {
      line1?: string;
      line2?: string;
      city?: string;
      state?: string;
      postal_code?: string;
      country?: string;
    };
  };
}

interface ModalOptions {
  currentPaymentMethod: PaymentMethod | null;
  userEmail: string;
  userName: string;
  accessToken: string;
  onSuccess: () => void;
  onCancel: () => void;
}

/**
 * Show the payment method modal
 */
export async function showPaymentMethodModal(options: ModalOptions): Promise<void> {
  const modal = new PaymentMethodModal(options);
  await modal.show();
}

/**
 * Payment Method Modal Class
 */
class PaymentMethodModal {
  private options: ModalOptions;
  private modal: HTMLElement | null = null;
  private stripe: Stripe | null = null;
  private elements: StripeElements | null = null;
  private setupIntentClientSecret: string | null = null;

  constructor(options: ModalOptions) {
    this.options = options;
  }

  /**
   * Show the modal
   */
  async show(): Promise<void> {
    this.renderModal();
    await this.initializeStripe();
    this.attachEventListeners();
  }

  /**
   * Render modal HTML
   */
  private renderModal(): void {
    const html = `
      <div class="payment-modal-overlay">
        <div class="payment-modal">
          <div class="payment-modal-header">
            <h2>Payment Method</h2>
          </div>

          <div class="payment-modal-body">
            <div class="form-field">
              <label>Payment Method</label>
              <div id="payment-element-container">
                <div id="payment-element"></div>
              </div>
            </div>

            <div id="error-message" class="form-error" style="display: none;"></div>
          </div>

          <div class="payment-modal-footer">
            <button type="button" class="btn-secondary" id="cancel-button">
              Cancel
            </button>
            <button type="button" class="btn-primary" id="submit-button">
              <span id="button-text">Update</span>
              <div class="spinner" id="button-spinner" style="display: none;"></div>
            </button>
          </div>
        </div>
      </div>
    `;

    const container = document.createElement('div');
    container.innerHTML = html;
    document.body.appendChild(container);
    this.modal = container.querySelector('.payment-modal-overlay');
  }

  /**
   * Initialize Stripe Payment Element with SetupIntent
   */
  private async initializeStripe(): Promise<void> {
    try {
      // Load Stripe
      this.stripe = await loadStripe(STRIPE_PUBLISHABLE_KEY);

      if (!this.stripe) {
        this.showError('Failed to load Stripe');
        return;
      }

      // Create SetupIntent
      const response = await fetch(`${API_BASE_URL}/api/stripe/create-setup-intent`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.options.accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to create setup intent');
      }

      const data = await response.json();
      this.setupIntentClientSecret = data.client_secret;

      // Ensure we have a client secret
      if (!this.setupIntentClientSecret) {
        throw new Error('No client secret received');
      }

      // Create Payment Element
      this.elements = this.stripe.elements({
        clientSecret: this.setupIntentClientSecret,
        appearance: {
          theme: 'night',
          variables: {
            colorPrimary: '#5e8d90',
            colorBackground: '#2a2e36',
            colorText: '#fafafa',
            colorDanger: '#ef4444',
            fontFamily: 'system-ui, sans-serif',
            spacingUnit: '4px',
            borderRadius: '6px',
          },
        },
      });

      const paymentElement = this.elements.create('payment', {
        layout: 'tabs',
      });

      paymentElement.mount('#payment-element');

    } catch (error) {
      console.error('Error initializing Stripe:', error);
      this.showError('Failed to initialize payment form');
    }
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    if (!this.modal) return;

    // Cancel button
    const cancelButton = this.modal.querySelector('#cancel-button');
    cancelButton?.addEventListener('click', () => this.close());

    // Submit button
    const submitButton = this.modal.querySelector('#submit-button');
    submitButton?.addEventListener('click', () => this.handleSubmit());

    // Close on overlay click
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.close();
      }
    });

    // ESC key to close
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        this.close();
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
  }

  /**
   * Handle form submission
   */
  private async handleSubmit(): Promise<void> {
    if (!this.stripe || !this.elements) {
      this.showError('Payment system not initialized');
      return;
    }

    this.setLoading(true);
    this.hideError();

    try {
      // Confirm the setup with Stripe
      const { error, setupIntent } = await this.stripe.confirmSetup({
        elements: this.elements,
        confirmParams: {
          return_url: window.location.href, // Not actually used, but required by Stripe
        },
        redirect: 'if_required', // Don't redirect, handle in-page
      });

      if (error) {
        this.showError(error.message || 'Payment setup failed');
        this.setLoading(false);
        return;
      }

      if (setupIntent?.payment_method) {
        // Update payment method on backend
        await this.updatePaymentMethod(setupIntent.payment_method as string);
      } else {
        this.showError('No payment method received');
        this.setLoading(false);
      }

    } catch (error) {
      console.error('Error submitting payment:', error);
      this.showError('An error occurred. Please try again.');
      this.setLoading(false);
    }
  }

  /**
   * Update payment method on backend
   */
  private async updatePaymentMethod(paymentMethodId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stripe/update-payment-method`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.options.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ payment_method_id: paymentMethodId }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update payment method');
      }

      // Success!
      this.close();
      this.options.onSuccess();

    } catch (error) {
      console.error('Error updating payment method:', error);
      this.showError(error instanceof Error ? error.message : 'Failed to update payment method');
      this.setLoading(false);
    }
  }

  /**
   * Show error message
   */
  private showError(message: string): void {
    const errorElement = this.modal?.querySelector('#error-message');
    if (errorElement) {
      errorElement.textContent = message;
      (errorElement as HTMLElement).style.display = 'block';
    }
  }

  /**
   * Hide error message
   */
  private hideError(): void {
    const errorElement = this.modal?.querySelector('#error-message');
    if (errorElement) {
      (errorElement as HTMLElement).style.display = 'none';
    }
  }

  /**
   * Set loading state
   */
  private setLoading(loading: boolean): void {
    const button = this.modal?.querySelector('#submit-button') as HTMLButtonElement;
    const buttonText = this.modal?.querySelector('#button-text') as HTMLElement;
    const spinner = this.modal?.querySelector('#button-spinner') as HTMLElement;

    if (button && buttonText && spinner) {
      button.disabled = loading;
      buttonText.style.display = loading ? 'none' : 'inline';
      spinner.style.display = loading ? 'inline-block' : 'none';
    }
  }

  /**
   * Close the modal
   */
  private close(): void {
    if (this.modal?.parentElement) {
      this.modal.parentElement.remove();
    }
    this.options.onCancel();
  }
}
