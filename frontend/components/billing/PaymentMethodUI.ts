/**
 * UI template generation for Payment Method Modal
 */

import {
  PaymentMethodModalOptions,
} from './PaymentMethodTypes';
import { PaymentMethodState } from './PaymentMethodState';

/**
 * Generates HTML templates for the Payment Method Modal
 */
export class PaymentMethodUI {
  private options: PaymentMethodModalOptions;
  private state: PaymentMethodState;

  constructor(options: PaymentMethodModalOptions, state: PaymentMethodState) {
    this.options = options;
    this.state = state;
  }

  /**
   * Generate the complete modal HTML
   */
  generateModalHTML(): string {
    return `
      <div class="payment-modal-overlay">
        <div class="payment-modal">
          <div class="payment-modal-header">
            <h2>Payment method</h2>
          </div>

          <div class="payment-modal-body">
            <form id="payment-form">
              ${this.generateBillingFields()}
              ${this.generatePaymentMethodSection()}
              ${this.generatePaymentElementSection()}
              ${this.generateCardEditSection()}
              ${this.generateFormError()}
            </form>
          </div>

          ${this.generateModalFooter()}
        </div>
      </div>
    `;
  }

  /**
   * Generate billing fields (always shown at top)
   */
  private generateBillingFields(): string {
    const pm = this.options.currentPaymentMethod;
    const billingDetails = pm?.billing_details;

    return `
      <!-- Manual Billing Fields - Always Shown -->
      <div class="form-field">
        <label for="cardholder-name">Full name</label>
        <input
          type="text"
          id="cardholder-name"
          class="form-input"
          value="${billingDetails?.name || this.options.userName || ''}"
          placeholder="Full name"
          autocomplete="name"
          required
        />
      </div>

      <div class="form-field">
        <label for="country">Country or region</label>
        <select id="country" class="form-select" autocomplete="country" required>
          <option value="US" ${billingDetails?.address?.country === 'US' || !billingDetails?.address?.country ? 'selected' : ''}>United States</option>
          <option value="CA" ${billingDetails?.address?.country === 'CA' ? 'selected' : ''}>Canada</option>
          <option value="GB" ${billingDetails?.address?.country === 'GB' ? 'selected' : ''}>United Kingdom</option>
          <option value="AU" ${billingDetails?.address?.country === 'AU' ? 'selected' : ''}>Australia</option>
        </select>
      </div>

      <div class="form-field">
        <label for="address-line1">Address</label>
        <input
          type="text"
          id="address-line1"
          class="form-input"
          value="${billingDetails?.address?.line1 || ''}"
          placeholder=""
          autocomplete="address-line1"
          required
        />
      </div>
    `;
  }

  /**
   * Generate payment method options section
   */
  private generatePaymentMethodSection(): string {
    if (!this.options.currentPaymentMethod) {
      return '';
    }

    const pm = this.options.currentPaymentMethod;
    const isLinkPayment = pm.type === 'link' || pm.link;
    const userEmail = pm.billing_details?.email || pm.link?.email || this.options.userEmail;

    return `
      <div class="payment-method-options">
        ${isLinkPayment && userEmail ? this.generateEmailField(userEmail) : ''}
        ${this.generateExistingPaymentBox()}
        ${this.generateAddNewButton()}
      </div>
    `;
  }

  /**
   * Generate email field with Link logo
   */
  private generateEmailField(email: string): string {
    return `
      <div class="form-field" style="position: relative;">
        <input
          type="email"
          id="link-email"
          class="form-input"
          value="${email}"
          readonly
          style="padding-right: 100px;"
        />
        <div style="position: absolute; right: 12px; top: 50%; transform: translateY(-50%); display: flex; align-items: center; gap: 8px;">
          <svg width="60" height="30" viewBox="0 0 60 30" fill="none">
            <text x="5" y="20" font-family="Arial, sans-serif" font-size="16" font-weight="600" fill="#00D66F">link</text>
          </svg>
          <button type="button" class="stripe-link-menu-button" id="link-menu-btn" style="padding: 4px;">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <circle cx="8" cy="3" r="1.5"></circle>
              <circle cx="8" cy="8" r="1.5"></circle>
              <circle cx="8" cy="13" r="1.5"></circle>
            </svg>
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Generate existing payment method box
   */
  private generateExistingPaymentBox(): string {
    const pm = this.options.currentPaymentMethod;
    if (!pm) return '';

    // Show card box if we have card details OR if we have Link (which may have associated cards)
    if (!pm.card && !pm.link) return '';

    // Determine what to display
    let displayText = '';
    let iconType = 'card'; // 'card' or 'link'

    if (pm.card) {
      displayText = `${pm.card.brand} •••• ${pm.card.last4}`;
      iconType = 'card';
    } else if (pm.link) {
      displayText = 'Linked Payment Method';
      iconType = 'link';
    } else {
      return '';
    }

    // Choose appropriate icon based on type
    const icon = iconType === 'link' ? `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
      </svg>
    ` : `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
        <line x1="1" y1="10" x2="23" y2="10"></line>
      </svg>
    `;

    return `
      <div class="payment-option" id="existing-payment-box">
        ${icon}
        <div class="payment-option-content">
          <div class="payment-option-title">${displayText}</div>
        </div>
        <button type="button" class="payment-option-change-btn" id="change-btn">
          Change
        </button>
      </div>
    `;
  }

  /**
   * Generate "Add new payment method" button
   */
  private generateAddNewButton(): string {
    // Don't show Add New button for now - user can click Change
    return '';
  }

  /**
   * Generate Payment Element section
   */
  private generatePaymentElementSection(): string {
    return `
      <div id="payment-element-container" style="display: ${this.state.showNewCardForm ? 'block' : 'none'};">
        <!-- Additional Address Fields (shown when validation fails) -->
        <div id="additional-address-fields" style="display: ${this.state.showAdditionalAddressFields ? 'block' : 'none'};">
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

          <div class="form-field">
            <label for="city">City</label>
            <input
              type="text"
              id="city"
              class="form-input"
              placeholder="City"
              autocomplete="address-level2"
              required
            />
          </div>

          <div class="form-field">
            <label for="state">State</label>
            <select id="state" class="form-select" autocomplete="address-level1" required>
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
          </div>

          <div class="form-field">
            <label for="zip-code">ZIP code</label>
            <input
              type="text"
              id="zip-code"
              class="form-input"
              placeholder="ZIP code"
              autocomplete="postal-code"
              required
            />
          </div>
        </div>

        <!-- Stripe Payment Element (Card + Link) -->
        <div id="payment-element" class="payment-element"></div>

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
    `;
  }

  /**
   * Generate card edit section
   */
  private generateCardEditSection(): string {
    const pm = this.options.currentPaymentMethod;
    if (!pm || !pm.card) {
      return '<div id="card-edit-container" style="display: none;"></div>';
    }

    return `
      <div id="card-edit-container" style="display: ${this.state.isEditingCard ? 'block' : 'none'};">
        <div class="form-field">
          <label>Card number</label>
          <input
            type="text"
            id="edit-card-number"
            class="form-input"
            value="•••• •••• •••• ${pm.card.last4}"
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
              value="${String(pm.card.exp_month).padStart(2, '0')} / ${String(pm.card.exp_year).slice(-2)}"
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
    `;
  }

  /**
   * Generate form error div
   */
  private generateFormError(): string {
    return '<div id="form-error" class="form-error" style="display: none;"></div>';
  }

  /**
   * Generate modal footer
   */
  private generateModalFooter(): string {
    return `
      <div class="payment-modal-footer">
        <button type="button" class="btn-secondary" id="cancel-btn">Cancel</button>
        <button type="button" class="btn-primary" id="update-btn">
          <span id="update-btn-text">Update</span>
          <span id="update-btn-spinner" class="spinner" style="display: none;"></span>
        </button>
      </div>
    `;
  }

  /**
   * Update UI to reflect current state
   * Used when state changes without full re-render
   */
  updateUI(modal: HTMLElement): void {
    // Update existing payment box visibility
    const existingPaymentBox = modal.querySelector('#existing-payment-box') as HTMLElement;
    if (existingPaymentBox) {
      if (this.state.isEditingMode) {
        existingPaymentBox.classList.add('editing');
      } else {
        existingPaymentBox.classList.remove('editing');
      }
      existingPaymentBox.style.display = this.state.isEditingCard ? 'none' : 'flex';
    }

    // Update change button visibility
    const changeBtn = modal.querySelector('#change-btn') as HTMLElement;
    if (changeBtn) {
      changeBtn.style.display = !this.state.isEditingMode ? 'block' : 'none';
    }

    // Update Link logo visibility
    const linkLogo = modal.querySelector('#payment-link-logo') as HTMLElement;
    if (linkLogo) {
      linkLogo.style.display = this.state.isEditingMode ? 'flex' : 'none';
    }

    // Update payment actions container
    const actionsContainer = modal.querySelector('#payment-actions-container') as HTMLElement;
    if (actionsContainer) {
      actionsContainer.style.display = this.state.isEditingMode ? 'flex' : 'none';
    }

    // Update add new button visibility
    const addNewBtn = modal.querySelector('#add-new-btn') as HTMLElement;
    if (addNewBtn) {
      addNewBtn.style.display = this.state.isEditingMode && this.options.currentPaymentMethod ? 'flex' : 'none';
    }

    // Update payment element container
    const paymentElementContainer = modal.querySelector('#payment-element-container') as HTMLElement;
    if (paymentElementContainer) {
      paymentElementContainer.style.display = this.state.showNewCardForm ? 'block' : 'none';
    }

    // Update card edit container
    const cardEditContainer = modal.querySelector('#card-edit-container') as HTMLElement;
    if (cardEditContainer) {
      cardEditContainer.style.display = this.state.isEditingCard ? 'block' : 'none';
    }
  }
}
