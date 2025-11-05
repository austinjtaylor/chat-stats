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

// Import sidebar component
import { initSidebar, getSidebar } from './components/navigation/Sidebar';

// Import authentication modules
import { onAuthStateChange, getSession } from './lib/auth';
import { showLoginModal } from './components/auth/LoginModal';
import { showSignupModal } from './components/auth/SignupModal';
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
    // Dispatch custom event for sidebar to listen
    window.dispatchEvent(new CustomEvent('auth-state-changed'));
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

  // If user just logged in, start a new chat
  if (isAuthenticated) {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages && chatMessages.children.length === 0) {
      document.body.classList.remove('chat-active');
    }
  }

  // Update sidebar user plan if authenticated
  if (isAuthenticated) {
    // Fetch subscription status and update sidebar
    const sidebar = getSidebar();
    if (sidebar) {
      try {
        const token = session.access_token;
        const API_BASE_URL = import.meta.env.VITE_API_URL || '';
        const response = await fetch(`${API_BASE_URL}/api/subscription/status`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const subscription = await response.json();
          sidebar.updateUserPlan(subscription.tier);
        }
      } catch (error) {
        console.error('Failed to fetch subscription:', error);
      }
    }
  }
}

// Initialize the application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', async () => {
    console.log('Chat Stats application initialized');
    // Initialize the sidebar
    await initSidebar();
    // Initialize the dropdown functionality from dropdown.ts
    initDropdowns();
    // Initialize the interactive logo animation
    initLogoAnimation();
    // Initialize authentication
    await initAuth();
  });
} else {
  (async () => {
    console.log('Chat Stats application initialized');
    // Initialize the sidebar
    await initSidebar();
    // Initialize the dropdown functionality from dropdown.ts
    initDropdowns();
    // Initialize the interactive logo animation
    initLogoAnimation();
    // Initialize authentication
    await initAuth();
  })();
}