/**
 * Signup Modal Component
 * Handles new user registration with email and password
 */

import { signUp } from '../../lib/auth';

export class SignupModal {
  private modal: HTMLElement | null = null;
  private onSuccess?: () => void;

  constructor(onSuccess?: () => void) {
    this.onSuccess = onSuccess;
  }

  /**
   * Show the signup modal
   */
  show(): void {
    if (this.modal) {
      this.modal.classList.add('active');
      return;
    }

    this.modal = this.createModal();
    document.body.appendChild(this.modal);
    this.modal.classList.add('active');

    // Focus email input
    setTimeout(() => {
      const emailInput = this.modal?.querySelector('#signup-email') as HTMLInputElement;
      emailInput?.focus();
    }, 100);
  }

  /**
   * Hide the signup modal
   */
  hide(): void {
    if (this.modal) {
      this.modal.classList.remove('active');
    }
  }

  /**
   * Destroy the modal and remove from DOM
   */
  destroy(): void {
    if (this.modal) {
      this.modal.remove();
      this.modal = null;
    }
  }

  /**
   * Create the modal HTML element
   */
  private createModal(): HTMLElement {
    const modal = document.createElement('div');
    modal.className = 'auth-modal';
    modal.innerHTML = `
      <div class="auth-modal-overlay"></div>
      <div class="auth-modal-content">
        <button class="auth-modal-close" aria-label="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        <h2 class="auth-modal-title">Create Account</h2>
        <p class="auth-modal-subtitle">Start tracking your UFA stats</p>

        <form class="auth-form" id="signup-form">
          <div class="form-group">
            <label for="signup-email">Email</label>
            <input
              type="email"
              id="signup-email"
              name="email"
              placeholder="you@example.com"
              required
              autocomplete="email"
            />
          </div>

          <div class="form-group">
            <label for="signup-password">Password</label>
            <input
              type="password"
              id="signup-password"
              name="password"
              placeholder="At least 6 characters"
              required
              autocomplete="new-password"
              minlength="6"
            />
            <small class="form-help">Minimum 6 characters</small>
          </div>

          <div class="form-group">
            <label for="signup-password-confirm">Confirm Password</label>
            <input
              type="password"
              id="signup-password-confirm"
              name="password-confirm"
              placeholder="Re-enter your password"
              required
              autocomplete="new-password"
              minlength="6"
            />
          </div>

          <button type="submit" class="btn-primary btn-full">
            Create Account
          </button>

          <div class="auth-divider">
            <span>Already have an account?</span>
          </div>

          <button type="button" class="btn-secondary btn-full switch-to-login">
            Sign In
          </button>

          <p class="auth-terms">
            By signing up, you agree to our Terms of Service and Privacy Policy.
            You'll start on the free tier (50 queries/month).
          </p>
        </form>

        <div class="auth-message" id="signup-message"></div>
      </div>
    `;

    // Event listeners
    this.attachEventListeners(modal);

    return modal;
  }

  /**
   * Attach event listeners to modal elements
   */
  private attachEventListeners(modal: HTMLElement): void {
    // Close button
    const closeBtn = modal.querySelector('.auth-modal-close');
    closeBtn?.addEventListener('click', () => this.hide());

    // Overlay click to close
    const overlay = modal.querySelector('.auth-modal-overlay');
    overlay?.addEventListener('click', () => this.hide());

    // Form submission
    const form = modal.querySelector('#signup-form') as HTMLFormElement;
    form?.addEventListener('submit', (e) => this.handleSubmit(e));

    // Switch to login
    const loginBtn = modal.querySelector('.switch-to-login');
    loginBtn?.addEventListener('click', () => {
      this.hide();
      // Dispatch event to show login modal
      window.dispatchEvent(new CustomEvent('show-login-modal'));
    });

    // ESC key to close
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        this.hide();
      }
    };
    document.addEventListener('keydown', handleEsc);
  }

  /**
   * Handle form submission
   */
  private async handleSubmit(e: Event): Promise<void> {
    e.preventDefault();

    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;
    const passwordConfirm = formData.get('password-confirm') as string;

    // Validate passwords match
    if (password !== passwordConfirm) {
      this.showMessage('❌ Passwords do not match', 'error');
      return;
    }

    // Validate password length
    if (password.length < 6) {
      this.showMessage('❌ Password must be at least 6 characters', 'error');
      return;
    }

    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating account...';
    submitBtn.disabled = true;

    this.showMessage('', 'info');

    try {
      const result = await signUp(email, password);

      if (result.success) {
        this.showMessage(
          '✅ Account created! Please check your email to verify your account.',
          'success'
        );

        // Clear form
        form.reset();

        // Close modal after delay
        setTimeout(() => {
          this.hide();
          if (this.onSuccess) {
            this.onSuccess();
          }
        }, 3000);
      } else {
        this.showMessage(`❌ ${result.error || 'Failed to create account'}`, 'error');
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
      }
    } catch (error) {
      this.showMessage('❌ An unexpected error occurred', 'error');
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  }

  /**
   * Show a message in the modal
   */
  private showMessage(message: string, type: 'success' | 'error' | 'warning' | 'info'): void {
    const messageEl = this.modal?.querySelector('#signup-message');
    if (messageEl) {
      messageEl.textContent = message;
      messageEl.className = `auth-message ${type}`;
    }
  }
}

// Export singleton instance
let signupModalInstance: SignupModal | null = null;

export function showSignupModal(onSuccess?: () => void): void {
  if (!signupModalInstance) {
    signupModalInstance = new SignupModal(onSuccess);
  }
  signupModalInstance.show();
}

export function hideSignupModal(): void {
  signupModalInstance?.hide();
}
