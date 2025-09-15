/**
 * Main entry point for the chat page
 */

import './styles/main.css';
import { DOM, $, $$, debounce, scrollIntoView } from './js/utils/dom.js';
import { Format } from './js/utils/format.js';
import statsAPI from './js/api/client.js';
import { initDropdowns } from './js/components/dropdown.js';

// Make utilities available globally for legacy code
window.DOM = DOM;
window.Format = Format;
window.statsAPI = statsAPI;

// Initialize marked if available
if (window.marked) {
    marked.setOptions({
        highlight: function(code, lang) {
            if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(code, { language: lang }).value;
                } catch (err) {}
            }
            return code;
        },
        breaks: true,
        gfm: true
    });
}

// Chat functionality
let sessionId = generateSessionId();
let isLoading = false;
let currentController = null;

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

async function sendMessage(retry = false) {
    const input = $('#messageInput');
    const message = input.value.trim();

    if (!message || isLoading) return;

    // Clear input immediately for better UX
    if (!retry) {
        input.value = '';
        addMessage(message, 'user');
    }

    isLoading = true;
    updateButtonState();

    // Show thinking message
    const thinkingMessage = addThinkingMessage();

    try {
        currentController = new AbortController();
        const response = await statsAPI.query(message, sessionId);

        // Remove thinking message
        thinkingMessage.remove();

        // Add bot response
        addMessage(response.response, 'bot');

        // Update stats if available
        if (response.stats) {
            updateStats(response.stats);
        }
    } catch (error) {
        thinkingMessage.remove();

        if (error.name === 'AbortError') {
            console.log('Query was cancelled');
        } else {
            console.error('Error:', error);
            const errorMessage = error.message || 'Sorry, I encountered an error processing your request.';
            addMessage(errorMessage, 'error');
        }
    } finally {
        isLoading = false;
        currentController = null;
        updateButtonState();
        input.focus();
    }
}

function cancelQuery() {
    if (currentController) {
        currentController.abort();
        currentController = null;
    }
}

function addMessage(content, type = 'user') {
    const messagesContainer = $('#messages');
    const messageDiv = DOM.createElement('div', {
        className: `message ${type}-message`
    });

    const contentDiv = DOM.createElement('div', {
        className: 'message-content'
    });

    if (type === 'bot' && window.marked) {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // Auto-scroll to the new message
    scrollIntoView(messageDiv);

    return messageDiv;
}

function addThinkingMessage() {
    const messagesContainer = $('#messages');
    const thinkingDiv = DOM.createElement('div', {
        className: 'message bot-message thinking-message'
    });

    thinkingDiv.innerHTML = `
        <div class="message-content">
            <div class="thinking-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

    messagesContainer.appendChild(thinkingDiv);
    scrollIntoView(thinkingDiv);

    return thinkingDiv;
}

function updateButtonState() {
    const sendButton = $('#sendButton');
    const cancelButton = $('#cancelButton');
    const input = $('#messageInput');

    if (isLoading) {
        DOM.hide(sendButton);
        DOM.show(cancelButton, 'flex');
        input.disabled = true;
    } else {
        DOM.show(sendButton, 'flex');
        DOM.hide(cancelButton);
        input.disabled = false;
    }
}

function clearChat() {
    if (confirm('Are you sure you want to start a new chat? This will clear the current conversation.')) {
        sessionId = generateSessionId();
        const messagesContainer = $('#messages');
        DOM.empty(messagesContainer);
        $('#messageInput').focus();
    }
}

// Make clearChat available globally for dropdown module
window.createNewSession = () => {
    sessionId = generateSessionId();
    const messagesContainer = $('#messages');
    if (messagesContainer) {
        DOM.empty(messagesContainer);
    }
};

async function updateStats(stats) {
    // Update stats display if provided
    if (stats) {
        const elements = {
            totalPlayers: $('#totalPlayers'),
            totalTeams: $('#totalTeams'),
            totalGames: $('#totalGames'),
            topScorers: $('#topScorers')
        };

        if (elements.totalPlayers && stats.total_players !== undefined) {
            elements.totalPlayers.textContent = Format.number(stats.total_players);
        }
        if (elements.totalTeams && stats.total_teams !== undefined) {
            elements.totalTeams.textContent = Format.number(stats.total_teams);
        }
        if (elements.totalGames && stats.total_games !== undefined) {
            elements.totalGames.textContent = Format.number(stats.total_games);
        }
    }
}

async function loadInitialStats() {
    try {
        const stats = await statsAPI.getStats();
        updateStats(stats);

        // Update top scorers list
        if (stats.top_scorers) {
            const topScorersContainer = $('#topScorers');
            if (topScorersContainer) {
                DOM.empty(topScorersContainer);
                stats.top_scorers.forEach(player => {
                    const item = DOM.createElement('div', {
                        className: 'scorer-item'
                    });
                    item.innerHTML = `
                        <span class="scorer-name">${Format.playerName(player.first_name, player.last_name)}</span>
                        <span class="scorer-points">${player.total_goals || 0}</span>
                    `;
                    topScorersContainer.appendChild(item);
                });
            }
        }
    } catch (error) {
        console.error('Failed to load initial stats:', error);
    }
}

function setupEventListeners() {
    // Send button
    const sendButton = $('#sendButton');
    if (sendButton) {
        DOM.on(sendButton, 'click', () => sendMessage());
    }

    // Cancel button
    const cancelButton = $('#cancelButton');
    if (cancelButton) {
        DOM.on(cancelButton, 'click', cancelQuery);
    }

    // Input field
    const input = $('#messageInput');
    if (input) {
        DOM.on(input, 'keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // New chat menu item
    const newChatMenuItem = $('#newChatMenuItem');
    if (newChatMenuItem) {
        DOM.on(newChatMenuItem, 'click', clearChat);
    }

    // Try Asking button
    const tryAskingBtn = $('#tryAskingBtn');
    const suggestedQuestions = $('#suggestedQuestions');
    if (tryAskingBtn && suggestedQuestions) {
        DOM.on(tryAskingBtn, 'click', () => {
            DOM.toggle(suggestedQuestions);
        });

        // Handle suggested question clicks
        DOM.on(suggestedQuestions, 'click', '.question-item', function() {
            const question = this.textContent.trim();
            const input = $('#messageInput');
            if (input) {
                input.value = question;
                DOM.hide(suggestedQuestions);
                sendMessage();
            }
        });
    }
}

// Initialize when DOM is ready
DOM.ready(() => {
    setupEventListeners();
    initDropdowns();
    loadInitialStats();

    // Focus on input
    const input = $('#messageInput');
    if (input) {
        input.focus();
    }
});