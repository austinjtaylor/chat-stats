/**
 * Entry point for the games stats page
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

// Import the main games script
import './games.js';

// Initialize when DOM is ready
DOM.ready(() => {
    console.log('Games stats page loaded with Vite');
});