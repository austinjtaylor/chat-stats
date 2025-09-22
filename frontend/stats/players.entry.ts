/**
 * Entry point for the players stats page - TypeScript version
 */

import '../styles/main.css';
import { DOM } from '../src/utils/dom';
import { Format } from '../src/utils/format';
import statsAPI from '../src/api/client';

// Make utilities available globally for existing code
window.DOM = DOM;
window.Format = Format;
window.statsAPI = statsAPI;

// Import the shared utilities
import './shared';

// Import the dropdown functionality with tooltips
import { initDropdowns } from '../src/components/dropdown';

// Import the main players script
import './players';

// Initialize when DOM is ready
DOM.ready(() => {
    console.log('Players stats page loaded with Vite');
    // Initialize dropdowns and tooltips
    initDropdowns();
});