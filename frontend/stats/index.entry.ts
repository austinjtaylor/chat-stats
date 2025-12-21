/**
 * Unified Stats Page Entry Point
 * Handles tab navigation for Players, Teams, and Games
 */

import { initSidebar } from '../components/navigation/Sidebar';
import { onAuthStateChange, getSession } from '../lib/auth';
import { showLoginModal } from '../components/auth/LoginModal';
import { showSignupModal } from '../components/auth/SignupModal';
import { initUserMenu, destroyUserMenu } from '../components/auth/UserMenu';
import type { Session } from '@supabase/supabase-js';

/**
 * Initialize tab navigation with lazy loading for iframes
 */
function initTabs(): void {
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabName = button.getAttribute('data-tab');
      if (!tabName) return;

      // Remove active class from all buttons and panes
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabPanes.forEach(pane => pane.classList.remove('active'));

      // Add active class to clicked button and corresponding pane
      button.classList.add('active');
      const activePane = document.getElementById(`${tabName}-tab`);
      activePane?.classList.add('active');

      // Lazy load iframe if it has data-src
      if (activePane) {
        const iframe = activePane.querySelector('iframe[data-src]') as HTMLIFrameElement;
        if (iframe && iframe.dataset.src && !iframe.src) {
          iframe.src = iframe.dataset.src;
          delete iframe.dataset.src;
        }
      }
    });
  });
}

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
    // Dispatch custom event for sidebar to listen
    window.dispatchEvent(new CustomEvent('auth-state-changed'));
  });

  // Set up event listeners for auth buttons
  const loginButton = document.getElementById('loginButton');
  loginButton?.addEventListener('click', () => {
    showLoginModal(async () => {
      const session = await getSession();
      await updateUIForAuthState(session.session);
      // Reload page to ensure full state refresh
      window.location.reload();
    });
  });

  const signupButton = document.getElementById('signupButton');
  signupButton?.addEventListener('click', () => {
    showSignupModal(async () => {
      const session = await getSession();
      await updateUIForAuthState(session.session);
      // Reload page to ensure full state refresh
      window.location.reload();
    });
  });
}

/**
 * Update UI based on authentication state
 */
async function updateUIForAuthState(session: Session | null) {
  const isAuthenticated = !!session;

  // Show/hide auth buttons wrapper based on auth state
  const authButtonsWrapper = document.querySelector('.auth-buttons-wrapper') as HTMLElement;
  if (authButtonsWrapper) {
    if (isAuthenticated) {
      authButtonsWrapper.classList.add('hidden');
    } else {
      authButtonsWrapper.classList.remove('hidden');
    }
  }

  // Manage user menu
  if (isAuthenticated) {
    // Initialize user menu if authenticated
    await initUserMenu('userMenuContainer');
  } else {
    // Destroy user menu if not authenticated
    destroyUserMenu();
  }
}

/**
 * Initialize the page
 */
async function init() {
  // Initialize sidebar
  await initSidebar();

  // Initialize tabs
  initTabs();

  // Initialize authentication
  await initAuth();

  console.log('Unified Stats page initialized');
}

// Run initialization
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
