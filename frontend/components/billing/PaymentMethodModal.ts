/**
 * Payment Method Modal Component
 * Allows users to update their payment method with Stripe Elements
 */

import { StripeCardElement } from '@stripe/stripe-js';
import { createStripeElements, createPaymentMethod, cardElementOptions } from '../../lib/stripe';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface PaymentMethodModalOptions {
  currentPaymentMethod?: {
    id: string;
    card: {
      brand: string;
      last4: string;
      exp_month: number;
      exp_year: number;
    };
  } | null;
  userEmail: string;
  userName?: string;
  accessToken: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export class PaymentMethodModal {
  private modal: HTMLElement | null = null;
  private cardElement: StripeCardElement | null = null;
  private options: PaymentMethodModalOptions;
  private useExisting: boolean = true;

  constructor(options: PaymentMethodModalOptions) {
    this.options = options;
    // If no current payment method, force new card entry
    if (!options.currentPaymentMethod) {
      this.useExisting = false;
    }
  }

  /**
   * Show the modal
   */
  async show(): Promise<void> {
    this.render();
    await this.initializeStripe();
    this.attachEventListeners();
  }

  /**
   * Render the modal
   */
  private render(): void {
    const modalHtml = `
      <div class="payment-modal-overlay">
        <div class="payment-modal">
          <div class="payment-modal-header">
            <h2>Payment method</h2>
          </div>

          <div class="payment-modal-body">
            <form id="payment-form">
              <!-- Full Name -->
              <div class="form-field">
                <label for="cardholder-name">Full name</label>
                <input
                  type="text"
                  id="cardholder-name"
                  class="form-input"
                  value="${this.options.userName || ''}"
                  placeholder="Full name"
                  autocomplete="name"
                  required
                />
              </div>

              <!-- Country/Region -->
              <div class="form-field">
                <label for="country">Country or region</label>
                <select id="country" class="form-select" autocomplete="country" required>
                  <option value="US" selected>United States</option>
                  <option value="CA">Canada</option>
                  <option value="GB">United Kingdom</option>
                  <option value="AU">Australia</option>
                  <option value="NZ">New Zealand</option>
                  <option value="IE">Ireland</option>
                  <option value="DE">Germany</option>
                  <option value="FR">France</option>
                  <option value="ES">Spain</option>
                  <option value="IT">Italy</option>
                  <option value="NL">Netherlands</option>
                  <option value="BE">Belgium</option>
                  <option value="CH">Switzerland</option>
                  <option value="AT">Austria</option>
                  <option value="SE">Sweden</option>
                  <option value="NO">Norway</option>
                  <option value="DK">Denmark</option>
                  <option value="FI">Finland</option>
                  <option value="PL">Poland</option>
                  <option value="CZ">Czech Republic</option>
                  <option value="JP">Japan</option>
                  <option value="SG">Singapore</option>
                  <option value="HK">Hong Kong</option>
                  <option value="KR">South Korea</option>
                  <option value="IN">India</option>
                  <option value="BR">Brazil</option>
                  <option value="MX">Mexico</option>
                  <option value="AR">Argentina</option>
                  <option value="CL">Chile</option>
                  <option value="CO">Colombia</option>
                </select>
              </div>

              <!-- Address -->
              <div class="form-field">
                <label for="address">Address</label>
                <input
                  type="text"
                  id="address"
                  class="form-input"
                  placeholder="Address"
                  autocomplete="street-address"
                />
              </div>

              <!-- Stripe Link Section -->
              ${this.options.userEmail ? `
                <div class="stripe-link-section">
                  <span class="stripe-link-email">${this.options.userEmail}</span>
                  <div class="stripe-link-logo">
                    <img src="/images/link-logo.png" alt="Link" width="60" height="30" />
                  </div>
                  <div class="stripe-link-menu-container">
                    <button type="button" class="stripe-link-menu-button" id="link-menu-btn">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <circle cx="8" cy="3" r="1.5"></circle>
                        <circle cx="8" cy="8" r="1.5"></circle>
                        <circle cx="8" cy="13" r="1.5"></circle>
                      </svg>
                    </button>
                    <div class="stripe-link-dropdown" id="link-dropdown" style="display: none;">
                      <button type="button" class="stripe-link-dropdown-item" id="logout-link-btn">
                        Log out of Link
                      </button>
                    </div>
                  </div>
                </div>
              ` : ''}

              <!-- Payment Method Options -->
              <div class="payment-method-options">
                ${this.options.currentPaymentMethod ? `
                  <button
                    type="button"
                    class="payment-option ${this.useExisting ? 'active' : ''}"
                    id="use-existing-btn"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                      <line x1="1" y1="10" x2="23" y2="10"></line>
                    </svg>
                    <div class="payment-option-content">
                      <div class="payment-option-title">Use ${this.options.currentPaymentMethod.card.brand} •••• ${this.options.currentPaymentMethod.card.last4}</div>
                      <div class="payment-option-subtitle">Expires ${this.options.currentPaymentMethod.card.exp_month}/${this.options.currentPaymentMethod.card.exp_year}</div>
                    </div>
                  </button>
                ` : ''}

                <button
                  type="button"
                  class="payment-option ${!this.useExisting ? 'active' : ''}"
                  id="add-new-btn"
                >
                  <span>Pay another way</span>
                </button>
              </div>

              <!-- Card Element (shown when adding new card) -->
              <div id="card-element-container" style="display: ${!this.useExisting ? 'block' : 'none'};">
                <div class="form-field">
                  <label>Card information</label>
                  <div id="card-element" class="stripe-card-element"></div>
                  <div id="card-errors" class="card-errors"></div>
                </div>
              </div>

              <!-- Form Error -->
              <div id="form-error" class="form-error" style="display: none;"></div>
            </form>
          </div>

          <div class="payment-modal-footer">
            <button type="button" class="btn-secondary" id="cancel-btn">Cancel</button>
            <button type="button" class="btn-primary" id="update-btn">
              <span id="update-btn-text">Update</span>
              <span id="update-btn-spinner" class="spinner" style="display: none;"></span>
            </button>
          </div>
        </div>
      </div>
    `;

    // Add to body
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHtml;
    document.body.appendChild(modalContainer);

    this.modal = modalContainer.querySelector('.payment-modal-overlay');
  }

  /**
   * Initialize Stripe Elements
   */
  private async initializeStripe(): Promise<void> {
    if (this.useExisting) return; // Don't initialize if using existing

    const elements = await createStripeElements();
    if (!elements) {
      console.error('Failed to initialize Stripe Elements');
      return;
    }

    // Create card element
    this.cardElement = elements.create('card', cardElementOptions);
    const cardElementContainer = this.modal?.querySelector('#card-element');
    if (cardElementContainer) {
      this.cardElement.mount('#card-element');

      // Handle errors
      this.cardElement.on('change', (event) => {
        const displayError = this.modal?.querySelector('#card-errors');
        if (displayError) {
          displayError.textContent = event.error ? event.error.message : '';
        }
      });
    }
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    if (!this.modal) return;

    // Cancel button
    const cancelBtn = this.modal.querySelector('#cancel-btn');
    cancelBtn?.addEventListener('click', () => this.close());

    // Update button
    const updateBtn = this.modal.querySelector('#update-btn');
    updateBtn?.addEventListener('click', () => this.handleUpdate());

    // Use existing payment method button
    const useExistingBtn = this.modal.querySelector('#use-existing-btn');
    useExistingBtn?.addEventListener('click', () => this.togglePaymentMethod(true));

    // Add new payment method button
    const addNewBtn = this.modal.querySelector('#add-new-btn');
    addNewBtn?.addEventListener('click', () => this.togglePaymentMethod(false));

    // Link menu button
    const linkMenuBtn = this.modal.querySelector('#link-menu-btn');
    const linkDropdown = this.modal.querySelector('#link-dropdown') as HTMLElement;

    linkMenuBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      if (linkDropdown) {
        const isVisible = linkDropdown.style.display === 'block';
        linkDropdown.style.display = isVisible ? 'none' : 'block';
      }
    });

    // Log out of Link button
    const logoutLinkBtn = this.modal.querySelector('#logout-link-btn');
    logoutLinkBtn?.addEventListener('click', () => {
      // For now, just hide the Link section
      // In a real implementation, you would call Stripe API to disconnect Link
      const linkSection = this.modal?.querySelector('.stripe-link-section') as HTMLElement;
      if (linkSection) {
        linkSection.style.display = 'none';
      }
      if (linkDropdown) {
        linkDropdown.style.display = 'none';
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (linkDropdown && !linkMenuBtn?.contains(e.target as Node)) {
        linkDropdown.style.display = 'none';
      }
    });

    // Close on overlay click
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.close();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.close();
        if (linkDropdown) {
          linkDropdown.style.display = 'none';
        }
      }
    });
  }

  /**
   * Toggle between existing and new payment method
   */
  private async togglePaymentMethod(useExisting: boolean): Promise<void> {
    this.useExisting = useExisting;

    // Update button states
    const useExistingBtn = this.modal?.querySelector('#use-existing-btn');
    const addNewBtn = this.modal?.querySelector('#add-new-btn');
    const cardElementContainer = this.modal?.querySelector('#card-element-container') as HTMLElement;

    if (useExisting) {
      useExistingBtn?.classList.add('active');
      addNewBtn?.classList.remove('active');
      if (cardElementContainer) cardElementContainer.style.display = 'none';
    } else {
      useExistingBtn?.classList.remove('active');
      addNewBtn?.classList.add('active');
      if (cardElementContainer) cardElementContainer.style.display = 'block';

      // Initialize Stripe if not already done
      if (!this.cardElement) {
        await this.initializeStripe();
      }
    }
  }

  /**
   * Handle update button click
   */
  private async handleUpdate(): Promise<void> {
    const updateBtn = this.modal?.querySelector('#update-btn') as HTMLButtonElement;
    const updateBtnText = this.modal?.querySelector('#update-btn-text') as HTMLElement;
    const updateBtnSpinner = this.modal?.querySelector('#update-btn-spinner') as HTMLElement;
    const formError = this.modal?.querySelector('#form-error') as HTMLElement;

    if (!updateBtn) return;

    // Clear errors
    formError.style.display = 'none';
    formError.textContent = '';

    // Show loading state
    updateBtn.disabled = true;
    updateBtnText.style.display = 'none';
    updateBtnSpinner.style.display = 'inline-block';

    try {
      let paymentMethodId: string;

      if (this.useExisting && this.options.currentPaymentMethod) {
        // Use existing payment method
        paymentMethodId = this.options.currentPaymentMethod.id;
      } else {
        // Create new payment method
        if (!this.cardElement) {
          throw new Error('Card element not initialized');
        }

        const nameInput = this.modal?.querySelector('#cardholder-name') as HTMLInputElement;
        const addressInput = this.modal?.querySelector('#address') as HTMLInputElement;
        const countrySelect = this.modal?.querySelector('#country') as HTMLSelectElement;

        const { paymentMethod, error } = await createPaymentMethod(this.cardElement, {
          name: nameInput?.value || '',
          email: this.options.userEmail,
          address: {
            line1: addressInput?.value || undefined,
            country: countrySelect?.value || 'US',
          },
        });

        if (error) {
          throw new Error(error.message);
        }

        if (!paymentMethod) {
          throw new Error('Failed to create payment method');
        }

        paymentMethodId = paymentMethod.id;
      }

      // Send to backend to update
      await this.updatePaymentMethodOnBackend(paymentMethodId);

      // Success - close modal and call callback
      this.close();
      this.options.onSuccess?.();
    } catch (error: any) {
      console.error('Failed to update payment method:', error);
      formError.textContent = error.message || 'Failed to update payment method. Please try again.';
      formError.style.display = 'block';
    } finally {
      // Reset button state
      updateBtn.disabled = false;
      updateBtnText.style.display = 'inline';
      updateBtnSpinner.style.display = 'none';
    }
  }

  /**
   * Update payment method on backend
   */
  private async updatePaymentMethodOnBackend(paymentMethodId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/stripe/update-payment-method`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.options.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        payment_method_id: paymentMethodId,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update payment method');
    }
  }

  /**
   * Close the modal
   */
  close(): void {
    // Clean up Stripe element
    if (this.cardElement) {
      this.cardElement.destroy();
      this.cardElement = null;
    }

    // Remove modal from DOM
    this.modal?.parentElement?.remove();
    this.modal = null;

    // Call cancel callback
    this.options.onCancel?.();
  }
}

/**
 * Show payment method modal
 */
export function showPaymentMethodModal(options: PaymentMethodModalOptions): void {
  const modal = new PaymentMethodModal(options);
  modal.show();
}
