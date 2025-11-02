/**
 * State management for Payment Method Modal
 */

import {
  PaymentMethodModalOptions,
  ModalView,
  ValidationErrors,
  IModalState,
} from './PaymentMethodTypes';

/**
 * Manages the state of the Payment Method Modal
 */
export class PaymentMethodState implements IModalState {
  currentView: ModalView;
  useExisting: boolean;
  isEditingMode: boolean;
  showNewCardForm: boolean;
  isEditingCard: boolean;
  hasCardFieldsChanged: boolean;
  showAdditionalAddressFields: boolean;
  isProcessingLinkAuth: boolean;
  validationErrors: ValidationErrors;

  constructor(options: PaymentMethodModalOptions) {
    this.validationErrors = new Map();
    this.isProcessingLinkAuth = false;

    // Determine initial state based on current payment method
    const hasExistingPayment = this.hasExistingPaymentMethod(options);

    if (hasExistingPayment) {
      // User has existing payment method - show it initially
      this.currentView = ModalView.EXISTING_PAYMENT;
      this.useExisting = true;
      this.isEditingMode = false;
      this.showNewCardForm = false;
      this.isEditingCard = false;
      this.hasCardFieldsChanged = false;
      this.showAdditionalAddressFields = false;
    } else {
      // No existing payment method - show new payment form
      this.currentView = ModalView.NEW_PAYMENT;
      this.useExisting = false;
      this.isEditingMode = true;
      this.showNewCardForm = true;
      this.isEditingCard = false;
      this.hasCardFieldsChanged = false;
      this.showAdditionalAddressFields = true; // Show address fields for new cards
    }
  }

  /**
   * Check if user has an existing payment method
   */
  private hasExistingPaymentMethod(options: PaymentMethodModalOptions): boolean {
    if (!options.currentPaymentMethod) {
      return false;
    }

    const pm = options.currentPaymentMethod;
    // Check if payment method has either card or link details
    return !!(pm.card || pm.link);
  }

  /**
   * Enable edit mode (when Change button is clicked)
   */
  enableEditMode(): void {
    this.isEditingMode = true;
  }

  /**
   * Show new payment form view
   */
  showNewPaymentForm(): void {
    this.currentView = ModalView.NEW_PAYMENT;
    this.showNewCardForm = true;
    this.useExisting = false;
    this.showAdditionalAddressFields = true;
  }

  /**
   * Return to existing payment method view
   */
  returnToExistingPayment(): void {
    this.currentView = ModalView.EXISTING_PAYMENT;
    this.showNewCardForm = false;
    this.useExisting = true;
    this.isEditingMode = true; // Keep in edit mode
  }

  /**
   * Show card edit form
   */
  showCardEditForm(): void {
    this.currentView = ModalView.EDIT_CARD;
    this.isEditingCard = true;
    this.hasCardFieldsChanged = false;
  }

  /**
   * Cancel card edit
   */
  cancelCardEdit(): void {
    this.currentView = ModalView.EXISTING_PAYMENT;
    this.isEditingCard = false;
    this.hasCardFieldsChanged = false;
  }

  /**
   * Mark that card fields have changed
   */
  markCardFieldsChanged(): void {
    this.hasCardFieldsChanged = true;
  }

  /**
   * Set Link authentication processing state
   */
  setProcessingLinkAuth(isProcessing: boolean): void {
    this.isProcessingLinkAuth = isProcessing;
  }

  /**
   * Clear all validation errors
   */
  clearValidationErrors(): void {
    this.validationErrors.clear();
  }

  /**
   * Add a validation error
   */
  addValidationError(field: string, message: string): void {
    this.validationErrors.set(field as any, message);
  }

  /**
   * Check if there are any validation errors
   */
  hasValidationErrors(): boolean {
    return this.validationErrors.size > 0;
  }

  /**
   * Show additional address fields
   */
  showAddressFields(): void {
    this.showAdditionalAddressFields = true;
  }

  /**
   * Get current state as plain object (for debugging)
   */
  toJSON(): object {
    return {
      currentView: this.currentView,
      useExisting: this.useExisting,
      isEditingMode: this.isEditingMode,
      showNewCardForm: this.showNewCardForm,
      isEditingCard: this.isEditingCard,
      hasCardFieldsChanged: this.hasCardFieldsChanged,
      showAdditionalAddressFields: this.showAdditionalAddressFields,
      isProcessingLinkAuth: this.isProcessingLinkAuth,
      validationErrors: Array.from(this.validationErrors.entries()),
    };
  }
}
