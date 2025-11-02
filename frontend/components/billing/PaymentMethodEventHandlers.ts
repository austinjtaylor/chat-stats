/**
 * Event handlers for Payment Method Modal
 */

/**
 * Callback type for event handlers
 */
export interface ModalCallbacks {
  onClose: () => void;
  onUpdate: () => Promise<void>;
  onEnableEditMode: () => void;
  onShowNewCardForm: () => Promise<void>;
  onReturnToSavedPayment: () => void;
  onShowCardEdit: () => void;
  onCancelCardEdit: () => void;
  onCardFieldChange: () => void;
  onCardEditUpdate: () => Promise<void>;
  onRemoveCard: () => Promise<void>;
}

/**
 * Attaches all event listeners to the modal
 */
export class PaymentMethodEventHandlers {
  private modal: HTMLElement;
  private callbacks: ModalCallbacks;

  constructor(modal: HTMLElement, callbacks: ModalCallbacks) {
    this.modal = modal;
    this.callbacks = callbacks;
  }

  /**
   * Attach all event listeners
   */
  attachAll(): void {
    this.attachBasicButtons();
    this.attachPaymentMenuListeners();
    this.attachCardEditListeners();
    this.attachOverlayCloseListeners();
    this.attachKeyboardListeners();
  }

  /**
   * Attach basic button listeners
   */
  private attachBasicButtons(): void {
    // Cancel button
    const cancelBtn = this.modal.querySelector('#cancel-btn');
    cancelBtn?.addEventListener('click', () => this.callbacks.onClose());

    // Update button
    const updateBtn = this.modal.querySelector('#update-btn');
    updateBtn?.addEventListener('click', () => this.callbacks.onUpdate());

    // Change button (enables edit mode)
    const changeBtn = this.modal.querySelector('#change-btn');
    changeBtn?.addEventListener('click', () => this.callbacks.onEnableEditMode());

    // Add new payment method button
    const addNewBtn = this.modal.querySelector('#add-new-btn');
    addNewBtn?.addEventListener('click', () => this.callbacks.onShowNewCardForm());

    // Use saved payment method button
    const useSavedBtn = this.modal.querySelector('#use-saved-btn');
    useSavedBtn?.addEventListener('click', () => this.callbacks.onReturnToSavedPayment());
  }

  /**
   * Attach payment menu listeners (3-dot menu)
   */
  private attachPaymentMenuListeners(): void {
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
      this.callbacks.onShowCardEdit();
      const buttonsWereVisible = updateCardBtn.style.display === 'flex';
      updateCardBtn.style.display = 'none';
      removeCardBtn.style.display = 'none';
      if (paymentLinkLogo && buttonsWereVisible) paymentLinkLogo.style.display = 'flex';
    });

    // Remove card button
    removeCardBtn?.addEventListener('click', () => {
      this.callbacks.onRemoveCard();
      const buttonsWereVisible = updateCardBtn.style.display === 'flex';
      updateCardBtn.style.display = 'none';
      removeCardBtn.style.display = 'none';
      if (paymentLinkLogo && buttonsWereVisible) paymentLinkLogo.style.display = 'flex';
    });

    // Close payment buttons when clicking outside
    document.addEventListener('click', (e) => {
      const actionsContainer = this.modal.querySelector('#payment-actions-container');
      if (actionsContainer && e.target && !actionsContainer.contains(e.target as Node)) {
        const buttonsWereVisible = updateCardBtn && updateCardBtn.style.display === 'flex';
        if (updateCardBtn) updateCardBtn.style.display = 'none';
        if (removeCardBtn) removeCardBtn.style.display = 'none';
        if (paymentLinkLogo && buttonsWereVisible) paymentLinkLogo.style.display = 'flex';
      }
    });
  }

  /**
   * Attach card edit listeners
   */
  private attachCardEditListeners(): void {
    const cardEditUpdateBtn = this.modal.querySelector('#card-edit-update-btn');
    cardEditUpdateBtn?.addEventListener('click', () => this.callbacks.onCardEditUpdate());

    const cardEditCancelBtn = this.modal.querySelector('#card-edit-cancel-btn');
    cardEditCancelBtn?.addEventListener('click', () => this.callbacks.onCancelCardEdit());

    // Card field change detection
    const editExpiration = this.modal.querySelector('#edit-expiration') as HTMLInputElement;
    const editSecurityCode = this.modal.querySelector('#edit-security-code') as HTMLInputElement;
    const editNickname = this.modal.querySelector('#edit-nickname') as HTMLInputElement;

    [editExpiration, editSecurityCode, editNickname].forEach(field => {
      field?.addEventListener('input', () => this.callbacks.onCardFieldChange());
    });
  }

  /**
   * Attach overlay close listeners
   */
  private attachOverlayCloseListeners(): void {
    // Close on overlay click
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.callbacks.onClose();
      }
    });
  }

  /**
   * Attach keyboard listeners
   */
  private attachKeyboardListeners(): void {
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.callbacks.onClose();
      }
    });
  }
}
