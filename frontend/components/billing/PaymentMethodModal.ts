/**
 * Payment Method Modal Component
 * Refactored to use modular architecture with Stripe Link integration
 */

import { PaymentMethodModalOptions } from './PaymentMethodTypes';
import { PaymentMethodState } from './PaymentMethodState';
import { PaymentMethodValidator } from './PaymentMethodValidation';
import { PaymentMethodUI } from './PaymentMethodUI';
import { StripePaymentHandler } from './StripePaymentHandler';
import { PaymentMethodEventHandlers } from './PaymentMethodEventHandlers';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Payment Method Modal
 * Manages payment method updates with Stripe Payment Element and Link integration
 */
export class PaymentMethodModal {
  // Core components
  private modal: HTMLElement | null = null;

  // Modules
  private options: PaymentMethodModalOptions;
  private state: PaymentMethodState;
  private validator: PaymentMethodValidator | null = null;
  private ui: PaymentMethodUI;
  private stripeHandler: StripePaymentHandler;

  constructor(options: PaymentMethodModalOptions) {
    this.options = options;
    this.state = new PaymentMethodState(options);
    this.ui = new PaymentMethodUI(options, this.state);
    this.stripeHandler = new StripePaymentHandler(options);
  }

  /**
   * Show the modal
   */
  async show(): Promise<void> {
    this.render();

    // Initialize validator now that modal exists
    if (this.modal) {
      this.validator = new PaymentMethodValidator(this.modal);
    }

    await this.initializeStripe();
    this.attachEventListeners();
  }

  /**
   * Render the modal
   */
  private render(): void {
    const modalHtml = this.ui.generateModalHTML();

    // Add to body
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHtml;
    document.body.appendChild(modalContainer);

    this.modal = modalContainer.querySelector('.payment-modal-overlay');

    // Pre-populate country and state dropdowns from saved billing details
    this.populateBillingDetails();
  }

  /**
   * Populate billing details from saved payment method
   */
  private populateBillingDetails(): void {
    if (!this.options.currentPaymentMethod?.billing_details || !this.modal) {
      return;
    }

    const billingDetails = this.options.currentPaymentMethod.billing_details;

    // Populate country
    const countrySelect = this.modal.querySelector('#country') as HTMLSelectElement;
    if (countrySelect && billingDetails.address?.country) {
      countrySelect.value = billingDetails.address.country;
    }

    // Populate state
    const stateSelect = this.modal.querySelector('#state') as HTMLSelectElement;
    if (stateSelect && billingDetails.address?.state) {
      stateSelect.value = billingDetails.address.state;
    }
  }

  /**
   * Initialize Stripe Payment Element
   */
  private async initializeStripe(): Promise<void> {
    if (!this.state.showNewCardForm) {
      return; // Don't initialize if not showing new card form
    }

    const paymentElementContainer = this.modal?.querySelector('#payment-element');
    if (!paymentElementContainer) {
      console.error('Payment element container not found');
      return;
    }

    // Initialize Stripe handler with callbacks
    const success = await this.stripeHandler.initialize(
      paymentElementContainer as HTMLElement,
      () => this.handlePaymentElementReady(),
      () => this.handleLinkAuthenticationComplete()
    );

    if (!success) {
      console.error('Failed to initialize Stripe Payment Element');
    }
  }

  /**
   * Handle Payment Element ready event
   */
  private handlePaymentElementReady(): void {
    // Remove height restriction from payment element container
    const container = this.modal?.querySelector('#payment-element-container') as HTMLElement;
    if (container) {
      container.style.maxHeight = 'none';
      container.style.overflow = 'visible';
    }
  }

  /**
   * Handle Link authentication completion
   * Automatically submits the Link payment method to backend
   */
  private async handleLinkAuthenticationComplete(): Promise<void> {
    // Prevent duplicate processing
    if (this.state.isProcessingLinkAuth || !this.state.showNewCardForm) {
      return;
    }

    this.state.setProcessingLinkAuth(true);
    console.log('Auto-submitting Link payment method...');

    // Show loading state
    this.setUpdateButtonLoading(true);

    try {
      // Submit the Payment Element
      const submitResult = await this.stripeHandler.submit();
      if (submitResult.error) {
        console.error('Error submitting Payment Element:', submitResult.error);
        return;
      }

      // Create SetupIntent
      const setupResult = await this.stripeHandler.createSetupIntent(this.options.accessToken);
      if (setupResult.error || !setupResult.client_secret) {
        console.error('Failed to create setup intent:', setupResult.error);
        return;
      }

      // Confirm setup and get payment method ID
      const confirmResult = await this.stripeHandler.confirmSetup(setupResult.client_secret);
      if (confirmResult.error || !confirmResult.paymentMethodId) {
        console.error('Error confirming setup:', confirmResult.error);
        return;
      }

      // Update on backend
      const updateResult = await this.stripeHandler.updatePaymentMethod(
        confirmResult.paymentMethodId,
        this.options.accessToken
      );

      if (!updateResult.success) {
        console.error('Failed to update payment method:', updateResult.error);
        return;
      }

      console.log('Successfully updated Link payment method');

      // Wait for Stripe to propagate the change before refreshing
      await new Promise(resolve => setTimeout(resolve, 2000));

      console.log('Refreshing billing page data');

      // Call onSuccess to refresh the billing page
      if (this.options.onSuccess) {
        this.options.onSuccess();
      }

      // Reset button state
      this.setUpdateButtonLoading(false);

    } catch (error) {
      console.error('Error in handleLinkAuthenticationComplete:', error);
      this.setUpdateButtonLoading(false);
    } finally {
      this.state.setProcessingLinkAuth(false);
    }
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    if (!this.modal) return;

    const eventHandlers = new PaymentMethodEventHandlers(this.modal, {
      onClose: () => this.close(),
      onUpdate: () => this.handleUpdate(),
      onEnableEditMode: () => this.enableEditMode(),
      onShowNewCardForm: () => this.showNewCardFormView(),
      onReturnToSavedPayment: () => this.returnToSavedPaymentMethod(),
      onShowCardEdit: () => this.showCardEditForm(),
      onCancelCardEdit: () => this.cancelCardEdit(),
      onCardFieldChange: () => this.handleCardFieldChange(),
      onCardEditUpdate: () => this.handleCardEditUpdate(),
      onRemoveCard: () => this.handleRemoveCard(),
    });

    eventHandlers.attachAll();
  }

  /**
   * Enable edit mode (when Change button is clicked)
   */
  private enableEditMode(): void {
    this.state.enableEditMode();
    if (this.modal) {
      this.ui.updateUI(this.modal);
    }
  }

  /**
   * Show new card form view (when New payment method button is clicked)
   */
  private async showNewCardFormView(): Promise<void> {
    this.state.showNewPaymentForm();

    if (this.modal) {
      this.ui.updateUI(this.modal);
    }

    // Initialize Stripe if not already done
    if (!this.stripeHandler.getElements()) {
      await this.initializeStripe();
    }
  }

  /**
   * Return to saved payment method view
   */
  private returnToSavedPaymentMethod(): void {
    this.state.returnToExistingPayment();

    if (this.modal) {
      this.ui.updateUI(this.modal);
    }
  }

  /**
   * Show card edit form
   */
  private showCardEditForm(): void {
    this.state.showCardEditForm();

    if (this.modal) {
      this.ui.updateUI(this.modal);
    }
  }

  /**
   * Cancel card edit
   */
  private cancelCardEdit(): void {
    this.state.cancelCardEdit();

    if (this.modal) {
      this.ui.updateUI(this.modal);
    }
  }

  /**
   * Handle card field change
   */
  private handleCardFieldChange(): void {
    this.state.markCardFieldsChanged();

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
    if (!this.state.hasCardFieldsChanged) return;

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
    const formError = this.modal?.querySelector('#form-error') as HTMLElement;

    if (!formError) return;

    // Clear previous errors
    formError.style.display = 'none';
    formError.textContent = '';

    // If using new payment method, trigger Stripe validation FIRST
    let stripeValid = true;
    if (!this.state.useExisting) {
      const submitResult = await this.stripeHandler.submit();
      if (submitResult.error) {
        stripeValid = false;
        console.log('Stripe validation failed:', submitResult.error);
        // Stripe automatically shows inline errors in the Payment Element
      }
    }

    // Validate custom form fields (if using new payment)
    let customFieldsValid = true;
    if (!this.state.useExisting && this.validator) {
      const errors = this.validator.validate(true); // Include address fields

      if (errors.size > 0) {
        customFieldsValid = false;
        this.state.showAddressFields();
        this.validator.updateValidationUI(errors);
        this.validator.showAdditionalAddressFields();
      }
    }

    // If either validation failed, stop here
    if (!stripeValid || !customFieldsValid) {
      return;
    }

    // Show loading state
    this.setUpdateButtonLoading(true);

    try {
      let paymentMethodId: string;

      console.log('Update button clicked. useExisting:', this.state.useExisting);

      if (this.state.useExisting && this.options.currentPaymentMethod) {
        // Use existing payment method
        paymentMethodId = this.options.currentPaymentMethod.id;
        console.log('Using existing payment method:', paymentMethodId);
      } else {
        // Create new payment method via SetupIntent
        console.log('Creating new payment method via SetupIntent...');

        // Create SetupIntent
        const setupResult = await this.stripeHandler.createSetupIntent(this.options.accessToken);
        if (setupResult.error || !setupResult.client_secret) {
          throw new Error(setupResult.error || 'Failed to create setup intent');
        }

        // Confirm setup and get payment method ID
        const confirmResult = await this.stripeHandler.confirmSetup(setupResult.client_secret);
        if (confirmResult.error || !confirmResult.paymentMethodId) {
          throw new Error(confirmResult.error || 'No payment method was attached to the setup');
        }

        paymentMethodId = confirmResult.paymentMethodId;
        console.log('Extracted payment method ID from SetupIntent:', paymentMethodId);
      }

      console.log('Calling backend to update payment method:', paymentMethodId);

      // Update on backend
      const updateResult = await this.stripeHandler.updatePaymentMethod(
        paymentMethodId,
        this.options.accessToken
      );

      if (!updateResult.success) {
        throw new Error(updateResult.error || 'Failed to update payment method');
      }

      console.log('Successfully updated payment method on backend');

      // Success - close modal and call callback
      this.close();
      this.options.onSuccess?.();
    } catch (error: any) {
      console.error('Failed to update payment method:', error);
      formError.textContent = error.message || 'Failed to update payment method. Please try again.';
      formError.style.display = 'block';
    } finally {
      this.setUpdateButtonLoading(false);
    }
  }

  /**
   * Set update button loading state
   */
  private setUpdateButtonLoading(isLoading: boolean): void {
    const updateBtn = this.modal?.querySelector('#update-btn') as HTMLButtonElement;
    const updateBtnText = this.modal?.querySelector('#update-btn-text') as HTMLElement;
    const updateBtnSpinner = this.modal?.querySelector('#update-btn-spinner') as HTMLElement;

    if (updateBtn && updateBtnText && updateBtnSpinner) {
      updateBtn.disabled = isLoading;
      updateBtnText.style.display = isLoading ? 'none' : 'inline';
      updateBtnSpinner.style.display = isLoading ? 'inline-block' : 'none';
    }
  }

  /**
   * Close the modal
   */
  close(): void {
    // Clean up Stripe elements
    this.stripeHandler.destroy();

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
