/**
 * Cancel Subscription Modal Component
 * Allows users to cancel their subscription with reason collection
 */

interface CancelSubscriptionModalOptions {
  endDate: string;
  onConfirm: (reason: string, feedback: string) => void;
  onCancel: () => void;
}

export class CancelSubscriptionModal {
  private modal: HTMLElement | null = null;
  private options: CancelSubscriptionModalOptions;

  constructor(options: CancelSubscriptionModalOptions) {
    this.options = options;
  }

  /**
   * Show the modal
   */
  show(): void {
    this.render();
    this.attachEventListeners();
  }

  /**
   * Render the modal
   */
  private render(): void {
    const modalHtml = `
      <div class="cancel-modal-overlay">
        <div class="cancel-modal">
          <div class="cancel-modal-header">
            <h2>Cancel plan</h2>
          </div>

          <div class="cancel-modal-body">
            <p class="cancel-modal-description">
              Cancel to stop recurring billing. You can still use Chat Stats until ${this.options.endDate}.
            </p>

            <form id="cancel-form">
              <!-- Cancellation Reason Dropdown -->
              <div class="cancel-form-field">
                <label for="cancellation-reason">What is your main reason for canceling?</label>
                <select id="cancellation-reason" class="cancel-form-select" required>
                  <option value="">Select option</option>
                  <option value="too-expensive">Too expensive</option>
                  <option value="not-using-enough">Not using it enough</option>
                  <option value="missing-features">Missing features I need</option>
                  <option value="found-alternative">Found a better alternative</option>
                  <option value="technical-issues">Technical issues</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <!-- Feedback Textarea -->
              <div class="cancel-form-field">
                <label for="cancellation-feedback">Please briefly describe what led to this decision.</label>
                <textarea
                  id="cancellation-feedback"
                  class="cancel-form-textarea"
                  placeholder="e.g., reasons for cancellation"
                  maxlength="500"
                  rows="4"
                ></textarea>
                <div class="cancel-form-char-count">
                  <span id="char-count">0</span>/500
                </div>
              </div>
            </form>
          </div>

          <div class="cancel-modal-footer">
            <button type="button" class="btn-secondary" id="go-back-btn">Go back</button>
            <button type="button" class="btn-danger" id="confirm-cancel-btn">
              Cancel plan
            </button>
          </div>
        </div>
      </div>
    `;

    // Add to body
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHtml;
    document.body.appendChild(modalContainer);

    this.modal = modalContainer.querySelector('.cancel-modal-overlay');
  }

  /**
   * Attach event listeners
   */
  private attachEventListeners(): void {
    if (!this.modal) return;

    // Go back button
    const goBackBtn = this.modal.querySelector('#go-back-btn');
    goBackBtn?.addEventListener('click', () => this.close());

    // Confirm cancel button
    const confirmBtn = this.modal.querySelector('#confirm-cancel-btn');
    confirmBtn?.addEventListener('click', () => this.handleConfirm());

    // Character count
    const feedbackTextarea = this.modal.querySelector('#cancellation-feedback') as HTMLTextAreaElement;
    const charCount = this.modal.querySelector('#char-count');
    feedbackTextarea?.addEventListener('input', () => {
      if (charCount) {
        charCount.textContent = feedbackTextarea.value.length.toString();
      }
    });

    // Close on overlay click
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.close();
      }
    });

    // Close on Escape key
    const escapeHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        this.close();
        document.removeEventListener('keydown', escapeHandler);
      }
    };
    document.addEventListener('keydown', escapeHandler);
  }

  /**
   * Handle confirm button click
   */
  private handleConfirm(): void {
    const reasonSelect = this.modal?.querySelector('#cancellation-reason') as HTMLSelectElement;
    const feedbackTextarea = this.modal?.querySelector('#cancellation-feedback') as HTMLTextAreaElement;

    const reason = reasonSelect?.value || '';
    const feedback = feedbackTextarea?.value || '';

    if (!reason) {
      alert('Please select a reason for cancellation');
      return;
    }

    // Call confirm callback
    this.options.onConfirm(reason, feedback);
    this.close();
  }

  /**
   * Close the modal
   */
  close(): void {
    // Remove modal from DOM
    this.modal?.parentElement?.remove();
    this.modal = null;

    // Call cancel callback
    this.options.onCancel();
  }
}

/**
 * Show cancel subscription modal
 */
export function showCancelSubscriptionModal(options: CancelSubscriptionModalOptions): void {
  const modal = new CancelSubscriptionModal(options);
  modal.show();
}
