// Main entry point for the application
// This file imports and initializes all necessary modules for the main chat interface

// Import utilities - these are loaded as global scripts
import './src/api/client';
import './src/utils/dom';
import './src/utils/format';

// Import dropdown module and its initialization function
import { initDropdowns } from './src/components/dropdown';

// Import logo animation
import { initLogoAnimation } from './src/components/logo-animation';

// Import main application script
import './script';  // Now TypeScript

// Import navigation components
import './src/components/nav';

// Import authentication modules
import { onAuthStateChange, getSession } from './lib/auth';
import { showLoginModal } from './components/auth/LoginModal';
import { showSignupModal } from './components/auth/SignupModal';
import { initUserMenu, destroyUserMenu } from './components/auth/UserMenu';
import type { Session } from '@supabase/supabase-js';

/**
 * Initialize authentication state management
 */
async function initAuth() {
  // Check current auth state
  const session = await getSession();
  await updateUIForAuthState(session.session);

  // Listen for auth state changes
  onAuthStateChange(async (session) => {
    await updateUIForAuthState(session);
  });

  // Set up event listeners for auth buttons
  const loginButton = document.getElementById('loginButton');
  loginButton?.addEventListener('click', () => {
    showLoginModal(async () => {
      // Refresh auth state after successful login
      const session = await getSession();
      await updateUIForAuthState(session.session);
    });
  });

  const signupButton = document.getElementById('signupButton');
  signupButton?.addEventListener('click', () => {
    showSignupModal(async () => {
      // Refresh auth state after successful signup
      const session = await getSession();
      await updateUIForAuthState(session.session);
    });
  });

  // Set up event listeners for auth modals (from other components)
  window.addEventListener('show-login-modal', () => {
    showLoginModal(async () => {
      // Refresh auth state after successful login
      const session = await getSession();
      await updateUIForAuthState(session.session);
    });
  });

  window.addEventListener('show-signup-modal', () => {
    showSignupModal(async () => {
      // Refresh auth state after successful signup
      const session = await getSession();
      await updateUIForAuthState(session.session);
    });
  });

  // Handle auth-required events (from API client when 401 errors occur)
  window.addEventListener('auth-required', () => {
    showLoginModal(async () => {
      // Refresh auth state after successful login
      const session = await getSession();
      await updateUIForAuthState(session.session);
    });
  });
}

/**
 * Update UI based on authentication state
 */
async function updateUIForAuthState(session: Session | null) {
  const isAuthenticated = !!session;

  // Show/hide login button
  const loginButton = document.getElementById('loginButton');
  if (loginButton) {
    loginButton.style.display = isAuthenticated ? 'none' : 'flex';
  }

  // Show/hide signup button
  const signupButton = document.getElementById('signupButton');
  if (signupButton) {
    signupButton.style.display = isAuthenticated ? 'none' : 'flex';
  }

  // Initialize or destroy user menu
  if (isAuthenticated) {
    await initUserMenu('userMenuContainer', async () => {
      // Callback after logout
      await updateUIForAuthState(null);
    });
  } else {
    destroyUserMenu();
  }
}

// Initialize the application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', async () => {
    console.log('Chat Stats application initialized');
    // Initialize the dropdown functionality from dropdown.ts
    initDropdowns();
    // Initialize the interactive logo animation
    initLogoAnimation();
    // Initialize authentication
    await initAuth();
  });
} else {
  console.log('Chat Stats application initialized');
  // Initialize the dropdown functionality from dropdown.ts
  initDropdowns();
  // Initialize the interactive logo animation
  initLogoAnimation();
  // Initialize authentication
  initAuth();
}