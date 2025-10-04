/**
 * Login Modal Component
 * Handles user login with email and password
 */

import { signIn, resetPassword } from '../../lib/auth';

export class LoginModal {
  private modal: HTMLElement | null = null;
  private onSuccess?: () => void;

  constructor(onSuccess?: () => void) {
    this.onSuccess = onSuccess;
  }

  /**
   * Show the login modal
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
      const emailInput = this.modal?.querySelector('#login-email') as HTMLInputElement;
      emailInput?.focus();
    }, 100);
  }

  /**
   * Hide the login modal
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

        <h2 class="auth-modal-title">Welcome Back</h2>
        <p class="auth-modal-subtitle">Sign in to your account</p>

        <form class="auth-form" id="login-form">
          <div class="form-group">
            <label for="login-email">Email</label>
            <input
              type="email"
              id="login-email"
              name="email"
              placeholder="you@example.com"
              required
              autocomplete="email"
            />
          </div>

          <div class="form-group">
            <label for="login-password">Password</label>
            <input
              type="password"
              id="login-password"
              name="password"
              placeholder="Enter your password"
              required
              autocomplete="current-password"
            />
          </div>

          <div class="form-links">
            <a href="#" class="forgot-password-link">Forgot password?</a>
          </div>

          <button type="submit" class="btn-primary btn-full">
            Sign In
          </button>

          <div class="auth-divider">
            <span>Don't have an account?</span>
          </div>

          <button type="button" class="btn-secondary btn-full switch-to-signup">
            Create Account
          </button>
        </form>

        <div class="auth-message" id="login-message"></div>
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
    const form = modal.querySelector('#login-form') as HTMLFormElement;
    form?.addEventListener('submit', (e) => this.handleSubmit(e));

    // Forgot password link
    const forgotLink = modal.querySelector('.forgot-password-link');
    forgotLink?.addEventListener('click', (e) => this.handleForgotPassword(e));

    // Switch to signup
    const signupBtn = modal.querySelector('.switch-to-signup');
    signupBtn?.addEventListener('click', () => {
      this.hide();
      // Dispatch event to show signup modal
      window.dispatchEvent(new CustomEvent('show-signup-modal'));
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

    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]') as HTMLButtonElement;
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Signing in...';
    submitBtn.disabled = true;

    this.showMessage('', 'info');

    try {
      const result = await signIn(email, password);

      if (result.success) {
        this.showMessage('✅ Successfully signed in!', 'success');

        // Call success callback
        setTimeout(() => {
          this.hide();
          if (this.onSuccess) {
            this.onSuccess();
          }
        }, 500);
      } else {
        this.showMessage(`❌ ${result.error || 'Failed to sign in'}`, 'error');
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
   * Handle forgot password link
   */
  private async handleForgotPassword(e: Event): Promise<void> {
    e.preventDefault();

    const emailInput = this.modal?.querySelector('#login-email') as HTMLInputElement;
    const email = emailInput?.value;

    if (!email) {
      this.showMessage('⚠️ Please enter your email address first', 'warning');
      emailInput?.focus();
      return;
    }

    const confirmed = confirm(`Send password reset link to ${email}?`);
    if (!confirmed) return;

    try {
      const result = await resetPassword(email);

      if (result.success) {
        this.showMessage('✅ Password reset email sent! Check your inbox.', 'success');
      } else {
        this.showMessage(`❌ ${result.error || 'Failed to send reset email'}`, 'error');
      }
    } catch (error) {
      this.showMessage('❌ An unexpected error occurred', 'error');
    }
  }

  /**
   * Show a message in the modal
   */
  private showMessage(message: string, type: 'success' | 'error' | 'warning' | 'info'): void {
    const messageEl = this.modal?.querySelector('#login-message');
    if (messageEl) {
      messageEl.textContent = message;
      messageEl.className = `auth-message ${type}`;
    }
  }
}

// Export singleton instance
let loginModalInstance: LoginModal | null = null;

export function showLoginModal(onSuccess?: () => void): void {
  if (!loginModalInstance) {
    loginModalInstance = new LoginModal(onSuccess);
  }
  loginModalInstance.show();
}

export function hideLoginModal(): void {
  loginModalInstance?.hide();
}
