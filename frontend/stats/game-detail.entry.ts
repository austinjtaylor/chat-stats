/**
 * Entry point for the game detail page - TypeScript version
 */

import '../styles/main.css';
import { DOM } from '../src/utils/dom';
import { Format } from '../src/utils/format';
import statsAPI from '../src/api/client';

// Make utilities available globally
window.DOM = DOM;
window.Format = Format;
window.statsAPI = statsAPI;

// Import the main game detail script
import './game-detail';

// Initialize when DOM is ready
DOM.ready(() => {
    console.log('Game detail page loaded with Vite');
});