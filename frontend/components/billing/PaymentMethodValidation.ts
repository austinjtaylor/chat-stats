/**
 * Validation logic for Payment Method Modal
 */

import { ValidationErrors, ValidationErrorField } from './PaymentMethodTypes';

/**
 * Handles validation for payment method forms
 */
export class PaymentMethodValidator {
  private modal: HTMLElement;

  constructor(modal: HTMLElement) {
    this.modal = modal;
  }

  /**
   * Validate all required billing fields
   * @param includeAddressFields - Whether to validate city, state, zip (for new cards)
   * @returns Map of validation errors
   */
  validate(includeAddressFields: boolean = false): ValidationErrors {
    const errors: ValidationErrors = new Map();

    // Validate full name
    const nameInput = this.getInput('cardholder-name');
    if (nameInput && !nameInput.value.trim()) {
      errors.set('cardholder-name', 'This field is incomplete.');
    }

    // Validate address line 1
    const addressLine1Input = this.getInput('address-line1');
    if (addressLine1Input && !addressLine1Input.value.trim()) {
      errors.set('address-line1', 'This field is incomplete.');
    }

    // Validate additional fields when using new payment method
    if (includeAddressFields) {
      // Validate city
      const cityInput = this.getInput('city');
      if (cityInput && !cityInput.value.trim()) {
        errors.set('city', 'This field is incomplete.');
      }

      // Validate state
      const stateSelect = this.getSelect('state');
      if (stateSelect && !stateSelect.value) {
        errors.set('state', 'This field is incomplete.');
      }

      // Validate ZIP code
      const zipInput = this.getInput('zip-code');
      if (zipInput && !zipInput.value.trim()) {
        errors.set('zip-code', 'This field is incomplete.');
      }
    }

    return errors;
  }

  /**
   * Update validation errors in the UI
   * @param errors - Map of validation errors
   */
  updateValidationUI(errors: ValidationErrors): void {
    // First, clear all existing error states
    this.clearValidationUI();

    // Then, apply new error states
    errors.forEach((message, fieldName) => {
      this.showFieldError(fieldName, message);
    });
  }

  /**
   * Clear all validation errors from the UI
   */
  clearValidationUI(): void {
    // Remove error classes from all inputs
    const allInputs = this.modal.querySelectorAll('.input-error');
    allInputs.forEach(input => {
      input.classList.remove('input-error');
    });

    // Remove all error messages
    const allErrors = this.modal.querySelectorAll('.field-error');
    allErrors.forEach(error => {
      error.remove();
    });
  }

  /**
   * Show error for a specific field
   */
  private showFieldError(fieldName: ValidationErrorField, message: string): void {
    const input = this.modal.querySelector(`#${fieldName}`) as HTMLInputElement | HTMLSelectElement;
    if (!input) return;

    // Add error class
    input.classList.add('input-error');

    // Add or update error message
    const existingError = input.parentElement?.querySelector('.field-error');
    if (existingError) {
      existingError.textContent = message;
    } else {
      const errorDiv = document.createElement('div');
      errorDiv.className = 'field-error';
      errorDiv.textContent = message;
      input.parentElement?.appendChild(errorDiv);
    }
  }

  /**
   * Get input element by ID
   */
  private getInput(id: string): HTMLInputElement | null {
    return this.modal.querySelector(`#${id}`) as HTMLInputElement | null;
  }

  /**
   * Get select element by ID
   */
  private getSelect(id: string): HTMLSelectElement | null {
    return this.modal.querySelector(`#${id}`) as HTMLSelectElement | null;
  }

  /**
   * Show additional address fields if needed
   */
  showAdditionalAddressFields(): void {
    const additionalFields = this.modal.querySelector('#additional-address-fields') as HTMLElement;
    if (additionalFields) {
      additionalFields.style.display = 'block';
    }

    // Update Address line 1 label
    const addressLabel = this.modal.querySelector('#address-line1-label') as HTMLLabelElement;
    if (addressLabel) {
      addressLabel.textContent = 'Address line 1';
    }
  }
}
