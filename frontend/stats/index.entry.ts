/**
 * Unified Stats Page Entry Point
 * Handles tab navigation for Players, Teams, and Games
 */

import { initSidebar } from '../components/navigation/Sidebar';

/**
 * Initialize tab navigation
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
    });
  });
}

/**
 * Initialize the page
 */
async function init() {
  // Initialize sidebar
  await initSidebar();

  // Initialize tabs
  initTabs();

  console.log('Unified Stats page initialized');
}

// Run initialization
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
