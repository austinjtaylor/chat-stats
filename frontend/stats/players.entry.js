/**
 * Entry point for the players stats page
 */

import '../styles/main.css';
import { DOM } from '../js/utils/dom.js';
import { Format } from '../js/utils/format.js';
import statsAPI from '../js/api/client.js';

// Make utilities available globally for existing code
window.DOM = DOM;
window.Format = Format;
window.statsAPI = statsAPI;

// Import the shared utilities
import './shared.js';

// Import the main players script
import './players.js';

// Initialize when DOM is ready
DOM.ready(() => {
    console.log('Players stats page loaded with Vite');
});