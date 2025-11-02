/**
 * UI template generation for Payment Method Modal
 */

import {
  PaymentMethodModalOptions,
  CurrentPaymentMethod,
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
   * Generate payment method options section
   */
  private generatePaymentMethodSection(): string {
    if (!this.options.currentPaymentMethod) {
      return '';
    }

    return `
      <div class="payment-method-options">
        ${this.generateExistingPaymentBox()}
        ${this.generateAddNewButton()}
      </div>
    `;
  }

  /**
   * Generate existing payment method box
   */
  private generateExistingPaymentBox(): string {
    const pm = this.options.currentPaymentMethod;
    if (!pm) return '';

    const isLinkPayment = pm.type === 'link' || pm.link;
    const hasCard = !!pm.card;

    return `
      <div class="payment-option ${this.state.isEditingMode ? 'editing' : ''}" id="existing-payment-box">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
          <line x1="1" y1="10" x2="23" y2="10"></line>
        </svg>
        <div class="payment-option-content">
          ${this.generatePaymentMethodDetails(pm)}
        </div>
        <button type="button" class="payment-option-change-btn" id="change-btn" style="display: ${!this.state.isEditingMode ? 'block' : 'none'};">
          Change
        </button>
        ${isLinkPayment ? `
        <div class="stripe-link-logo" id="payment-link-logo" style="display: ${this.state.isEditingMode ? 'flex' : 'none'};">
          <img src="/images/link-logo.png" alt="Link" width="60" height="30" />
        </div>
        ` : ''}
        <div class="payment-actions-container" id="payment-actions-container" style="display: ${this.state.isEditingMode ? 'flex' : 'none'};">
          ${hasCard ? `
          <button type="button" class="payment-action-btn payment-action-btn-remove" id="remove-card-btn" style="display: none;">
            Remove
          </button>
          <button type="button" class="payment-action-btn" id="update-card-btn" style="display: none;">
            Update
          </button>
          ` : ''}
          <button type="button" class="stripe-link-menu-button" id="payment-menu-btn">
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
   * Generate payment method details (card or Link)
   */
  private generatePaymentMethodDetails(pm: CurrentPaymentMethod): string {
    if (pm.card) {
      return `
        <div class="payment-option-title">Use ${pm.card.brand} •••• ${pm.card.last4}</div>
        <div class="payment-option-subtitle">Expires ${pm.card.exp_month}/${pm.card.exp_year}</div>
      `;
    } else if (pm.link) {
      return `
        <div class="payment-option-title">${pm.link.email}</div>
        <div class="payment-option-subtitle">Payment method via Link</div>
      `;
    } else {
      return `
        <div class="payment-option-title">Payment method</div>
        <div class="payment-option-subtitle">Managed through Stripe</div>
      `;
    }
  }

  /**
   * Generate "Add new payment method" button
   */
  private generateAddNewButton(): string {
    return `
      <button
        type="button"
        class="payment-method-add-new"
        id="add-new-btn"
        style="display: ${this.state.isEditingMode && this.options.currentPaymentMethod ? 'flex' : 'none'};"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="12" y1="8" x2="12" y2="16"></line>
          <line x1="8" y1="12" x2="16" y2="12"></line>
        </svg>
        <span>New payment method</span>
      </button>
    `;
  }

  /**
   * Generate Payment Element section
   */
  private generatePaymentElementSection(): string {
    return `
      <div id="payment-element-container" style="display: ${this.state.showNewCardForm ? 'block' : 'none'};">
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
