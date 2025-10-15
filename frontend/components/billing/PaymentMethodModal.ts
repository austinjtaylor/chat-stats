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
  private isEditingMode: boolean = false;
  private showNewCardForm: boolean = false;
  private isEditingCard: boolean = false;
  private hasCardFieldsChanged: boolean = false;

  constructor(options: PaymentMethodModalOptions) {
    this.options = options;
    // If no current payment method, force new card entry
    if (!options.currentPaymentMethod) {
      this.useExisting = false;
      this.isEditingMode = true;
      this.showNewCardForm = true;
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
                  <div class="payment-option ${this.isEditingMode ? 'editing' : ''}" id="existing-payment-box">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                      <line x1="1" y1="10" x2="23" y2="10"></line>
                    </svg>
                    <div class="payment-option-content">
                      <div class="payment-option-title">Use ${this.options.currentPaymentMethod.card.brand} •••• ${this.options.currentPaymentMethod.card.last4}</div>
                      <div class="payment-option-subtitle">Expires ${this.options.currentPaymentMethod.card.exp_month}/${this.options.currentPaymentMethod.card.exp_year}</div>
                    </div>
                    <button type="button" class="payment-option-change-btn" id="change-btn" style="display: ${!this.isEditingMode ? 'block' : 'none'};">
                      Change
                    </button>
                    <div class="stripe-link-logo" id="payment-link-logo" style="display: none;">
                      <img src="/images/link-logo.png" alt="Link" width="60" height="30" />
                    </div>
                    <div class="payment-actions-container" id="payment-actions-container" style="display: ${this.isEditingMode ? 'flex' : 'none'};">
                      <button type="button" class="payment-action-btn payment-action-btn-remove" id="remove-card-btn" style="display: none;">
                        Remove
                      </button>
                      <button type="button" class="payment-action-btn" id="update-card-btn" style="display: none;">
                        Update
                      </button>
                      <button type="button" class="stripe-link-menu-button" id="payment-menu-btn">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" style="color: #5e8d90;">
                          <circle cx="8" cy="3" r="1.5"></circle>
                          <circle cx="8" cy="8" r="1.5"></circle>
                          <circle cx="8" cy="13" r="1.5"></circle>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <!-- New Payment Method Button (shown when editing) -->
                  <button
                    type="button"
                    class="payment-method-add-new"
                    id="add-new-btn"
                    style="display: ${this.isEditingMode ? 'flex' : 'none'};"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                      <line x1="12" y1="8" x2="12" y2="16"></line>
                      <line x1="8" y1="12" x2="16" y2="12"></line>
                    </svg>
                    <span>New payment method</span>
                  </button>

                  <!-- Log out of Link Button (shown when editing) -->
                  <button
                    type="button"
                    class="payment-method-link-button"
                    id="logout-link-btn-main"
                    style="display: ${this.isEditingMode ? 'inline-block' : 'none'};"
                  >
                    Log out of Link
                  </button>
                ` : ''}
              </div>

              <!-- Card Element (shown when adding new card) -->
              <div id="card-element-container" style="display: ${this.showNewCardForm ? 'block' : 'none'};">
                <div class="form-field">
                  <label>Card information</label>
                  <div id="card-element" class="stripe-card-element"></div>
                  <div id="card-errors" class="card-errors"></div>
                </div>

                <!-- Disclaimer -->
                <div class="payment-method-disclaimer">
                  By continuing, you agree to save your payment method with Link.
                </div>

                <!-- Use Saved Payment Method Button (shown when viewing new card form) -->
                ${this.options.currentPaymentMethod ? `
                  <button
                    type="button"
                    class="payment-method-link-button"
                    id="use-saved-btn"
                  >
                    Use a saved payment method
                  </button>
                ` : ''}
              </div>

              <!-- Card Edit Form (shown when editing existing card) -->
              <div id="card-edit-container" style="display: ${this.isEditingCard ? 'block' : 'none'};">
                <div class="form-field">
                  <label>Card number</label>
                  <input
                    type="text"
                    id="edit-card-number"
                    class="form-input"
                    value="•••• •••• •••• ${this.options.currentPaymentMethod?.card.last4 || ''}"
                    readonly
                    style="background-color: #1f1f1f; cursor: not-allowed;"
                  />
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                  <div class="form-field">
                    <label>Expiration (MM/YY)</label>
                    <input
                      type="text"
                      id="edit-expiration"
                      class="form-input"
                      value="${this.options.currentPaymentMethod ? String(this.options.currentPaymentMethod.card.exp_month).padStart(2, '0') + ' / ' + String(this.options.currentPaymentMethod.card.exp_year).slice(-2) : ''}"
                      placeholder="MM / YY"
                      maxlength="7"
                    />
                  </div>

                  <div class="form-field">
                    <label>Security code</label>
                    <input
                      type="text"
                      id="edit-security-code"
                      class="form-input"
                      placeholder="CVC"
                      maxlength="4"
                    />
                  </div>
                </div>

                <div class="form-field">
                  <label>Nickname (optional)</label>
                  <input
                    type="text"
                    id="edit-nickname"
                    class="form-input"
                    placeholder="Nickname (optional)"
                  />
                </div>

                <div style="display: flex; gap: 12px; margin-top: 20px;">
                  <button type="button" class="payment-method-link-button" id="card-edit-update-btn" disabled style="opacity: 0.5; cursor: not-allowed;">
                    Update
                  </button>
                  <button type="button" class="payment-method-link-button" id="card-edit-cancel-btn">
                    Cancel
                  </button>
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
    if (!this.showNewCardForm) return; // Don't initialize if not showing new card form

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

    // Change button (enables edit mode)
    const changeBtn = this.modal.querySelector('#change-btn');
    changeBtn?.addEventListener('click', () => this.enableEditMode());

    // Add new payment method button
    const addNewBtn = this.modal.querySelector('#add-new-btn');
    addNewBtn?.addEventListener('click', () => this.showNewCardFormView());

    // Use saved payment method button
    const useSavedBtn = this.modal.querySelector('#use-saved-btn');
    useSavedBtn?.addEventListener('click', () => this.returnToSavedPaymentMethod());

    // Payment menu button - toggles visibility of Update/Remove buttons and Link logo
    const paymentMenuBtn = this.modal.querySelector('#payment-menu-btn');
    const updateCardBtn = this.modal.querySelector('#update-card-btn') as HTMLElement;
    const removeCardBtn = this.modal.querySelector('#remove-card-btn') as HTMLElement;
    const paymentLinkLogo = this.modal.querySelector('#payment-link-logo') as HTMLElement;

    paymentMenuBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      if (updateCardBtn && removeCardBtn) {
        const isVisible = updateCardBtn.style.display === 'flex';
        updateCardBtn.style.display = isVisible ? 'none' : 'flex';
        removeCardBtn.style.display = isVisible ? 'none' : 'flex';

        // Toggle Link logo (opposite of buttons)
        if (paymentLinkLogo) {
          paymentLinkLogo.style.display = isVisible ? 'flex' : 'none';
        }
      }
    });

    // Update card button
    updateCardBtn?.addEventListener('click', () => {
      this.showCardEditForm();
      // Only restore Link logo if buttons were actually visible
      const buttonsWereVisible = updateCardBtn.style.display === 'flex';
      // Hide buttons after clicking
      updateCardBtn.style.display = 'none';
      removeCardBtn.style.display = 'none';
      // Restore Link logo only if buttons were visible
      if (paymentLinkLogo && buttonsWereVisible) paymentLinkLogo.style.display = 'flex';
    });

    // Remove card button
    removeCardBtn?.addEventListener('click', () => {
      this.handleRemoveCard();
      // Only restore Link logo if buttons were actually visible
      const buttonsWereVisible = updateCardBtn.style.display === 'flex';
      // Hide buttons after clicking
      updateCardBtn.style.display = 'none';
      removeCardBtn.style.display = 'none';
      // Restore Link logo only if buttons were visible
      if (paymentLinkLogo && buttonsWereVisible) paymentLinkLogo.style.display = 'flex';
    });

    // Close payment buttons when clicking outside
    document.addEventListener('click', (e) => {
      const actionsContainer = this.modal.querySelector('#payment-actions-container');
      if (actionsContainer && !actionsContainer.contains(e.target as Node)) {
        // Only restore Link logo if buttons were actually visible
        const buttonsWereVisible = updateCardBtn && updateCardBtn.style.display === 'flex';
        if (updateCardBtn) updateCardBtn.style.display = 'none';
        if (removeCardBtn) removeCardBtn.style.display = 'none';
        // Restore Link logo only if buttons were visible
        if (paymentLinkLogo && buttonsWereVisible) paymentLinkLogo.style.display = 'flex';
      }
    });

    // Card edit form buttons
    const cardEditUpdateBtn = this.modal.querySelector('#card-edit-update-btn');
    cardEditUpdateBtn?.addEventListener('click', () => this.handleCardEditUpdate());

    const cardEditCancelBtn = this.modal.querySelector('#card-edit-cancel-btn');
    cardEditCancelBtn?.addEventListener('click', () => this.cancelCardEdit());

    // Card field change detection
    const editExpiration = this.modal.querySelector('#edit-expiration') as HTMLInputElement;
    const editSecurityCode = this.modal.querySelector('#edit-security-code') as HTMLInputElement;
    const editNickname = this.modal.querySelector('#edit-nickname') as HTMLInputElement;

    [editExpiration, editSecurityCode, editNickname].forEach(field => {
      field?.addEventListener('input', () => this.handleCardFieldChange());
    });

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

    // Log out of Link button (in dropdown)
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

    // Log out of Link button (main button shown when editing)
    const logoutLinkBtnMain = this.modal.querySelector('#logout-link-btn-main');
    logoutLinkBtnMain?.addEventListener('click', () => {
      // For now, just hide the Link section
      // In a real implementation, you would call Stripe API to disconnect Link
      const linkSection = this.modal?.querySelector('.stripe-link-section') as HTMLElement;
      if (linkSection) {
        linkSection.style.display = 'none';
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
   * Enable edit mode (when Change button is clicked)
   */
  private enableEditMode(): void {
    this.isEditingMode = true;

    // Update UI
    const existingPaymentBox = this.modal?.querySelector('#existing-payment-box');
    const changeBtn = this.modal?.querySelector('#change-btn') as HTMLElement;
    const paymentLinkLogo = this.modal?.querySelector('#payment-link-logo') as HTMLElement;
    const paymentActionsContainer = this.modal?.querySelector('#payment-actions-container') as HTMLElement;
    const addNewBtn = this.modal?.querySelector('#add-new-btn') as HTMLElement;
    const logoutLinkBtnMain = this.modal?.querySelector('#logout-link-btn-main') as HTMLElement;

    if (existingPaymentBox) {
      existingPaymentBox.classList.add('editing');
    }

    if (changeBtn) {
      changeBtn.style.display = 'none';
    }

    if (paymentLinkLogo) {
      paymentLinkLogo.style.display = 'flex';
    }

    if (paymentActionsContainer) {
      paymentActionsContainer.style.display = 'flex';
    }

    if (addNewBtn) {
      addNewBtn.style.display = 'flex';
    }

    if (logoutLinkBtnMain) {
      logoutLinkBtnMain.style.display = 'inline-block';
    }
  }

  /**
   * Show new card form view (when New payment method button is clicked)
   */
  private async showNewCardFormView(): Promise<void> {
    this.showNewCardForm = true;
    this.useExisting = false;

    // Update UI
    const cardElementContainer = this.modal?.querySelector('#card-element-container') as HTMLElement;
    const addNewBtn = this.modal?.querySelector('#add-new-btn') as HTMLElement;
    const logoutLinkBtnMain = this.modal?.querySelector('#logout-link-btn-main') as HTMLElement;

    if (cardElementContainer) {
      cardElementContainer.style.display = 'block';
    }

    if (addNewBtn) {
      addNewBtn.style.display = 'none';
    }

    if (logoutLinkBtnMain) {
      logoutLinkBtnMain.style.display = 'none';
    }

    // Initialize Stripe if not already done
    if (!this.cardElement) {
      await this.initializeStripe();
    }
  }

  /**
   * Return to saved payment method view (when Use a saved payment method button is clicked)
   */
  private returnToSavedPaymentMethod(): void {
    this.showNewCardForm = false;
    this.useExisting = true;
    this.isEditingMode = true; // Keep in edit mode

    // Update UI
    const cardElementContainer = this.modal?.querySelector('#card-element-container') as HTMLElement;
    const addNewBtn = this.modal?.querySelector('#add-new-btn') as HTMLElement;
    const logoutLinkBtnMain = this.modal?.querySelector('#logout-link-btn-main') as HTMLElement;

    if (cardElementContainer) {
      cardElementContainer.style.display = 'none';
    }

    if (addNewBtn) {
      addNewBtn.style.display = 'flex';
    }

    if (logoutLinkBtnMain) {
      logoutLinkBtnMain.style.display = 'inline-block';
    }
  }

  /**
   * Show card edit form (when Update is clicked from dropdown)
   */
  private showCardEditForm(): void {
    this.isEditingCard = true;
    this.hasCardFieldsChanged = false;

    // Hide other sections
    const existingPaymentBox = this.modal?.querySelector('#existing-payment-box') as HTMLElement;
    const addNewBtn = this.modal?.querySelector('#add-new-btn') as HTMLElement;
    const logoutLinkBtnMain = this.modal?.querySelector('#logout-link-btn-main') as HTMLElement;
    const cardEditContainer = this.modal?.querySelector('#card-edit-container') as HTMLElement;

    if (existingPaymentBox) {
      existingPaymentBox.style.display = 'none';
    }

    if (addNewBtn) {
      addNewBtn.style.display = 'none';
    }

    if (logoutLinkBtnMain) {
      logoutLinkBtnMain.style.display = 'none';
    }

    if (cardEditContainer) {
      cardEditContainer.style.display = 'block';
    }
  }

  /**
   * Cancel card edit (return to edit mode)
   */
  private cancelCardEdit(): void {
    this.isEditingCard = false;
    this.hasCardFieldsChanged = false;

    // Show edit mode sections
    const existingPaymentBox = this.modal?.querySelector('#existing-payment-box') as HTMLElement;
    const addNewBtn = this.modal?.querySelector('#add-new-btn') as HTMLElement;
    const logoutLinkBtnMain = this.modal?.querySelector('#logout-link-btn-main') as HTMLElement;
    const cardEditContainer = this.modal?.querySelector('#card-edit-container') as HTMLElement;

    if (existingPaymentBox) {
      existingPaymentBox.style.display = 'flex';
    }

    if (addNewBtn) {
      addNewBtn.style.display = 'flex';
    }

    if (logoutLinkBtnMain) {
      logoutLinkBtnMain.style.display = 'inline-block';
    }

    if (cardEditContainer) {
      cardEditContainer.style.display = 'none';
    }
  }

  /**
   * Handle card field change (enable Update button)
   */
  private handleCardFieldChange(): void {
    this.hasCardFieldsChanged = true;

    const updateBtn = this.modal?.querySelector('#card-edit-update-btn') as HTMLButtonElement;
    if (updateBtn) {
      updateBtn.disabled = false;
      updateBtn.style.opacity = '1';
      updateBtn.style.cursor = 'pointer';
    }
  }

  /**
   * Handle card edit update
   */
  private async handleCardEditUpdate(): Promise<void> {
    if (!this.hasCardFieldsChanged) return;

    // For now, just close the edit form
    // In a real implementation, you would update the card details via Stripe API
    console.log('Updating card details...');
    this.cancelCardEdit();
  }

  /**
   * Handle remove card
   */
  private async handleRemoveCard(): Promise<void> {
    // Confirm before removing
    if (!confirm('Are you sure you want to remove this payment method?')) {
      return;
    }

    try {
      // Call backend to remove payment method
      const response = await fetch(`${API_BASE_URL}/api/stripe/remove-payment-method`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.options.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payment_method_id: this.options.currentPaymentMethod?.id,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to remove payment method');
      }

      // Success - close modal and refresh
      this.close();
      this.options.onSuccess?.();
    } catch (error: any) {
      console.error('Failed to remove payment method:', error);
      alert('Failed to remove payment method. Please try again.');
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
