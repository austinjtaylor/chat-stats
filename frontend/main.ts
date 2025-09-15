// Main entry point for the application
// This file imports and initializes all necessary modules for the main chat interface

// Import utilities - these are loaded as global scripts
import './js/api/client.js';
import './js/utils/dom.js';
import './js/utils/format.js';
import './js/components/dropdown.js';

// Import main application script
import './script.js';

// Import navigation components
import './components/nav.js';

// Initialize the application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('Chat Stats application initialized');
  });
} else {
  console.log('Chat Stats application initialized');
}