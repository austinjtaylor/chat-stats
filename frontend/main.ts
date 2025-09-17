// Main entry point for the application
// This file imports and initializes all necessary modules for the main chat interface

// Import utilities - these are loaded as global scripts
import './src/api/client';
import './src/utils/dom';
import './src/utils/format';

// Import dropdown module and its initialization function
import { initDropdowns } from './src/components/dropdown';

// Import main application script
import './script';  // Now TypeScript

// Import navigation components
import './src/components/nav';

// Initialize the application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('Chat Stats application initialized');
    // Initialize the dropdown functionality from dropdown.ts
    initDropdowns();
  });
} else {
  console.log('Chat Stats application initialized');
  // Initialize the dropdown functionality from dropdown.ts
  initDropdowns();
}