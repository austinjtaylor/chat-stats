/**
 * Entry point for the games stats page - TypeScript version
 */

import '../styles/main.css';
import { DOM } from '../js/utils/dom';
import { Format } from '../js/utils/format';
import statsAPI from '../js/api/client';

// Make utilities available globally for existing code
window.DOM = DOM;
window.Format = Format;
window.statsAPI = statsAPI;

// Import the shared utilities
import './shared';

// Import the main games script
import './games';

// Initialize when DOM is ready
DOM.ready(() => {
    console.log('Games stats page loaded with Vite');
});