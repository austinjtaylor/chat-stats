/**
 * Payment Method Modal Component
 * Allows users to update their payment method with Stripe Payment Element
 */

import { StripePaymentElement, StripeElements } from '@stripe/stripe-js';
import { createStripeElements, createPaymentElement } from '../../lib/stripe';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface PaymentMethodModalOptions {
  currentPaymentMethod?: {
    id: string;
    card: {
      brand: string;
      last4: string;
      exp_month: number;
      exp_year: number;
    } | null;
  } | null;
  userEmail: string;
  userName?: string;
  accessToken: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export class PaymentMethodModal {
  private modal: HTMLElement | null = null;
  private paymentElement: StripePaymentElement | null = null;
  private elements: StripeElements | null = null;
  private options: PaymentMethodModalOptions;
  private useExisting: boolean = true;
  private isEditingMode: boolean = false;
  private showNewCardForm: boolean = false;
  private isEditingCard: boolean = false;
  private hasCardFieldsChanged: boolean = false;
  private validationErrors: Map<string, string> = new Map();
  private showAdditionalAddressFields: boolean = false;

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
                  class="form-input ${this.validationErrors.has('cardholder-name') ? 'input-error' : ''}"
                  value="${this.options.userName || ''}"
                  placeholder="Full name"
                  autocomplete="name"
                  required
                />
                ${this.validationErrors.has('cardholder-name') ? `<div class="field-error">${this.validationErrors.get('cardholder-name')}</div>` : ''}
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

              <!-- Address Line 1 -->
              <div class="form-field">
                <label for="address-line1" id="address-line1-label">${this.showAdditionalAddressFields ? 'Address line 1' : 'Address'}</label>
                <input
                  type="text"
                  id="address-line1"
                  class="form-input ${this.validationErrors.has('address-line1') ? 'input-error' : ''}"
                  placeholder=""
                  autocomplete="address-line1"
                  required
                />
                ${this.validationErrors.has('address-line1') ? `<div class="field-error">${this.validationErrors.get('address-line1')}</div>` : ''}
              </div>

              <!-- Additional Address Fields (shown when entering card manually) -->
              <div id="additional-address-fields" style="display: ${this.showAdditionalAddressFields ? 'block' : 'none'};">
                <!-- Address Line 2 -->
                <div class="form-field">
                  <label for="address-line2">Address line 2</label>
                  <input
                    type="text"
                    id="address-line2"
                    class="form-input"
                    placeholder="Apt., suite, unit number, etc. (optional)"
                    autocomplete="address-line2"
                  />
                </div>

                <!-- City -->
                <div class="form-field">
                  <label for="city">City</label>
                  <input
                    type="text"
                    id="city"
                    class="form-input ${this.validationErrors.has('city') ? 'input-error' : ''}"
                    placeholder="City"
                    autocomplete="address-level2"
                    required
                  />
                  ${this.validationErrors.has('city') ? `<div class="field-error">${this.validationErrors.get('city')}</div>` : ''}
                </div>

                <!-- State -->
                <div class="form-field">
                  <label for="state">State</label>
                  <select id="state" class="form-select ${this.validationErrors.has('state') ? 'input-error' : ''}" autocomplete="address-level1" required>
                  <option value="" selected>Select</option>
                  <option value="AL">Alabama</option>
                  <option value="AK">Alaska</option>
                  <option value="AZ">Arizona</option>
                  <option value="AR">Arkansas</option>
                  <option value="CA">California</option>
                  <option value="CO">Colorado</option>
                  <option value="CT">Connecticut</option>
                  <option value="DE">Delaware</option>
                  <option value="FL">Florida</option>
                  <option value="GA">Georgia</option>
                  <option value="HI">Hawaii</option>
                  <option value="ID">Idaho</option>
                  <option value="IL">Illinois</option>
                  <option value="IN">Indiana</option>
                  <option value="IA">Iowa</option>
                  <option value="KS">Kansas</option>
                  <option value="KY">Kentucky</option>
                  <option value="LA">Louisiana</option>
                  <option value="ME">Maine</option>
                  <option value="MD">Maryland</option>
                  <option value="MA">Massachusetts</option>
                  <option value="MI">Michigan</option>
                  <option value="MN">Minnesota</option>
                  <option value="MS">Mississippi</option>
                  <option value="MO">Missouri</option>
                  <option value="MT">Montana</option>
                  <option value="NE">Nebraska</option>
                  <option value="NV">Nevada</option>
                  <option value="NH">New Hampshire</option>
                  <option value="NJ">New Jersey</option>
                  <option value="NM">New Mexico</option>
                  <option value="NY">New York</option>
                  <option value="NC">North Carolina</option>
                  <option value="ND">North Dakota</option>
                  <option value="OH">Ohio</option>
                  <option value="OK">Oklahoma</option>
                  <option value="OR">Oregon</option>
                  <option value="PA">Pennsylvania</option>
                  <option value="RI">Rhode Island</option>
                  <option value="SC">South Carolina</option>
                  <option value="SD">South Dakota</option>
                  <option value="TN">Tennessee</option>
                  <option value="TX">Texas</option>
                  <option value="UT">Utah</option>
                  <option value="VT">Vermont</option>
                  <option value="VA">Virginia</option>
                  <option value="WA">Washington</option>
                  <option value="WV">West Virginia</option>
                  <option value="WI">Wisconsin</option>
                  <option value="WY">Wyoming</option>
                </select>
                ${this.validationErrors.has('state') ? `<div class="field-error">${this.validationErrors.get('state')}</div>` : ''}
              </div>

                <!-- ZIP Code -->
                <div class="form-field">
                  <label for="zip-code">ZIP code</label>
                  <input
                    type="text"
                    id="zip-code"
                    class="form-input ${this.validationErrors.has('zip-code') ? 'input-error' : ''}"
                    placeholder="ZIP code"
                    autocomplete="postal-code"
                    required
                  />
                  ${this.validationErrors.has('zip-code') ? `<div class="field-error">${this.validationErrors.get('zip-code')}</div>` : ''}
                </div>
              </div>

              <!-- Payment Method Options -->
              <div class="payment-method-options">
                ${this.options.currentPaymentMethod && this.options.currentPaymentMethod.card ? `
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

              <!-- Payment Element (shown when adding new card) -->
              <div id="payment-element-container" style="display: ${this.showNewCardForm ? 'block' : 'none'};">
                <div id="payment-element" class="payment-element"></div>

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
                    value="•••• •••• •••• ${this.options.currentPaymentMethod?.card?.last4 || ''}"
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
                      value="${this.options.currentPaymentMethod && this.options.currentPaymentMethod.card ? String(this.options.currentPaymentMethod.card.exp_month).padStart(2, '0') + ' / ' + String(this.options.currentPaymentMethod.card.exp_year).slice(-2) : ''}"
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
   * Initialize Stripe Payment Element
   */
  private async initializeStripe(): Promise<void> {
    if (!this.showNewCardForm) {
      return; // Don't initialize if not showing new card form
    }

    // Create Elements instance
    this.elements = await createStripeElements(this.options.userEmail, this.options.userName);
    if (!this.elements) {
      console.error('Failed to initialize Stripe Elements');
      return;
    }

    // Create and mount Payment Element
    this.paymentElement = createPaymentElement(this.elements, {
      defaultValues: {
        billingDetails: {
          name: this.options.userName || '',
          email: this.options.userEmail || '',
        },
      },
    });

    const paymentElementContainer = this.modal?.querySelector('#payment-element');
    if (paymentElementContainer) {
      this.paymentElement.mount('#payment-element');

      // Listen for when the Payment Element is ready
      this.paymentElement.on('ready', () => {
        // Remove height restriction from payment element container
        const container = this.modal?.querySelector('#payment-element-container') as HTMLElement;
        if (container) {
          container.style.maxHeight = 'none';
          container.style.overflow = 'visible';
        }
      });

      // Listen for payment method selection changes
      this.paymentElement.on('change', (event) => {
        // Show additional fields only when Card tab is selected
        // Hide them when Link is selected (Link already has billing info)
        if (event.value?.type === 'card') {
          this.showAdditionalAddressFields = true;
          this.updateAdditionalFieldsVisibility();
        } else if (event.value?.type === 'link') {
          this.showAdditionalAddressFields = false;
          this.updateAdditionalFieldsVisibility();
        }
      });
    }
  }

  /**
   * Update visibility of additional address fields
   */
  private updateAdditionalFieldsVisibility(): void {
    const additionalFields = this.modal?.querySelector('#additional-address-fields') as HTMLElement;
    if (additionalFields) {
      additionalFields.style.display = this.showAdditionalAddressFields ? 'block' : 'none';
    }

    // Update Address line 1 label
    const addressLabel = this.modal?.querySelector('#address-line1-label') as HTMLLabelElement;
    if (addressLabel) {
      addressLabel.textContent = this.showAdditionalAddressFields ? 'Address line 1' : 'Address';
    }
  }


  /**
   * Validate form fields
   */
  private validateForm(): boolean {
    this.validationErrors.clear();

    // Validate full name
    const nameInput = this.modal?.querySelector('#cardholder-name') as HTMLInputElement;
    if (nameInput && !nameInput.value.trim()) {
      this.validationErrors.set('cardholder-name', 'This field is incomplete.');
    }

    // Validate address line 1
    const addressLine1Input = this.modal?.querySelector('#address-line1') as HTMLInputElement;
    if (addressLine1Input && !addressLine1Input.value.trim()) {
      this.validationErrors.set('address-line1', 'This field is incomplete.');
    }

    // Only validate additional fields if they're visible (Card payment method)
    if (this.showAdditionalAddressFields) {
      // Validate city
      const cityInput = this.modal?.querySelector('#city') as HTMLInputElement;
      if (cityInput && !cityInput.value.trim()) {
        this.validationErrors.set('city', 'This field is incomplete.');
      }

      // Validate state
      const stateSelect = this.modal?.querySelector('#state') as HTMLSelectElement;
      if (stateSelect && !stateSelect.value) {
        this.validationErrors.set('state', 'This field is incomplete.');
      }

      // Validate ZIP code
      const zipInput = this.modal?.querySelector('#zip-code') as HTMLInputElement;
      if (zipInput && !zipInput.value.trim()) {
        this.validationErrors.set('zip-code', 'This field is incomplete.');
      }
    }

    return this.validationErrors.size === 0;
  }

  /**
   * Re-render form with validation errors
   */
  private reRenderWithErrors(): void {
    // Re-render the modal with errors
    const oldModal = this.modal?.parentElement;
    if (oldModal) {
      oldModal.remove();
    }

    this.render();

    // Restore Stripe elements if they were initialized
    if (this.showNewCardForm && this.paymentElement) {
      this.initializeStripe();
    }

    this.attachEventListeners();
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
      const actionsContainer = this.modal?.querySelector('#payment-actions-container');
      if (actionsContainer && e.target && !actionsContainer.contains(e.target as Node)) {
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
    const paymentElementContainer = this.modal?.querySelector('#payment-element-container') as HTMLElement;
    const addNewBtn = this.modal?.querySelector('#add-new-btn') as HTMLElement;
    const logoutLinkBtnMain = this.modal?.querySelector('#logout-link-btn-main') as HTMLElement;

    if (paymentElementContainer) {
      paymentElementContainer.style.display = 'block';
    }

    if (addNewBtn) {
      addNewBtn.style.display = 'none';
    }

    if (logoutLinkBtnMain) {
      logoutLinkBtnMain.style.display = 'none';
    }

    // Initialize Stripe if not already done
    if (!this.paymentElement) {
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
    const paymentElementContainer = this.modal?.querySelector('#payment-element-container') as HTMLElement;
    const addNewBtn = this.modal?.querySelector('#add-new-btn') as HTMLElement;
    const logoutLinkBtnMain = this.modal?.querySelector('#logout-link-btn-main') as HTMLElement;

    if (paymentElementContainer) {
      paymentElementContainer.style.display = 'none';
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

    // Validate form before proceeding
    if (!this.validateForm()) {
      this.reRenderWithErrors();
      return;
    }

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
        // Use Payment Element - submit and create SetupIntent
        if (!this.elements || !this.paymentElement) {
          throw new Error('Payment Element not initialized');
        }

        // Submit the form to validate
        const { error: submitError } = await this.elements.submit();
        if (submitError) {
          throw new Error(submitError.message);
        }

        // Create SetupIntent on backend
        const setupResponse = await fetch(`${API_BASE_URL}/api/stripe/create-setup-intent`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.options.accessToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (!setupResponse.ok) {
          throw new Error('Failed to create setup intent');
        }

        const { client_secret } = await setupResponse.json();

        // TODO: Confirm setup - this needs to be completed
        // For now, we'll just close and show success
        // In a full implementation, you'd use stripe.confirmSetup() here
        console.warn('Payment Element integration incomplete - needs confirmSetup implementation');

        // Temporary: just use the existing payment method flow
        throw new Error('Payment Element not fully integrated yet - please contact support');
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
    // Clean up Stripe elements
    if (this.paymentElement) {
      this.paymentElement.destroy();
      this.paymentElement = null;
    }
    if (this.elements) {
      // Elements instance doesn't need explicit cleanup
      this.elements = null;
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
