// Main entry point for the application
// This file imports and initializes all necessary modules for the main chat interface

// Import utilities - these are loaded as global scripts
import './js/api/client';
import './js/utils/dom';
import './js/utils/format';
import './js/components/dropdown.js';  // Still JS, needs conversion

// Import main application script
import './script.js';  // Still JS, needs conversion

// Import navigation components
import './js/components/nav.js';  // Still JS, needs conversion

// Initialize the application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('Chat Stats application initialized');
  });
} else {
  console.log('Chat Stats application initialized');
}