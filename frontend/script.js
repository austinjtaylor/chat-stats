// API client is loaded from js/api/client.js
// const API_URL = '/api'; - No longer needed, using statsAPI

// Global state
let currentSessionId = null;
let queryHistory = [];
let historyIndex = -1;

// DOM elements
let chatMessages, chatInput, sendButton, totalPlayers, totalTeams, totalGames, newChatButton, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements using DOM utility
    chatMessages = DOM.$('#chatMessages');
    chatInput = DOM.$('#chatInput');
    sendButton = DOM.$('#sendButton');
    totalPlayers = DOM.$('#totalPlayers');
    totalTeams = DOM.$('#totalTeams');
    totalGames = DOM.$('#totalGames');
    newChatButton = DOM.$('#newChatButton');
    themeToggle = DOM.$('#themeToggle');
    
    setupEventListeners();
    setupDropdowns();
    // Theme initialization moved to nav.js
    createNewSession();
    loadSportsStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // Query history navigation with arrow keys
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex < queryHistory.length - 1) {
                historyIndex++;
                chatInput.value = queryHistory[queryHistory.length - 1 - historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                chatInput.value = queryHistory[queryHistory.length - 1 - historyIndex];
            } else if (historyIndex === 0) {
                historyIndex = -1;
                chatInput.value = '';
            }
        }
    });
    
    // New chat button
    if (newChatButton) {
        newChatButton.addEventListener('click', startNewChat);
    }
    
    // New chat from menu
    const newChatMenuItem = document.getElementById('newChatMenuItem');
    if (newChatMenuItem) {
        newChatMenuItem.addEventListener('click', startNewChat);
    }
    
    // Theme toggle handled by nav.js
    
    // Suggested questions - handle all suggested items
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
            // Close all dropdowns after selection
            document.querySelectorAll('.suggestions-dropdown').forEach(dropdown => {
                dropdown.classList.remove('active');
            });
        });
    });
}

// Setup dropdown functionality
function setupDropdowns() {
    // Menu dropdown
    const menuWrapper = document.querySelector('.menu-wrapper');
    const menuDropdown = document.getElementById('menuDropdown');
    
    if (menuWrapper && menuDropdown) {
        let menuTimeout;

        menuWrapper.addEventListener('mouseenter', () => {
            clearTimeout(menuTimeout);
            menuDropdown.classList.add('active');
            // Close settings dropdown if open
            const settingsDropdown = document.getElementById('settingsDropdown');
            if (settingsDropdown) {
                settingsDropdown.classList.remove('active');
            }
        });

        menuWrapper.addEventListener('mouseleave', () => {
            menuTimeout = setTimeout(() => {
                menuDropdown.classList.remove('active');
            }, 200);
        });
    }
    
    // Settings dropdown
    const settingsWrapper = document.querySelector('.settings-wrapper');
    const settingsDropdown = document.getElementById('settingsDropdown');
    
    if (settingsWrapper && settingsDropdown) {
        let settingsTimeout;

        settingsWrapper.addEventListener('mouseenter', () => {
            clearTimeout(settingsTimeout);
            settingsDropdown.classList.add('active');
            // Close menu dropdown if open
            if (menuDropdown) {
                menuDropdown.classList.remove('active');
            }
        });

        settingsWrapper.addEventListener('mouseleave', () => {
            settingsTimeout = setTimeout(() => {
                settingsDropdown.classList.remove('active');
            }, 200);
        });
    }
    
    // Try Asking suggestions dropdown - setup for both buttons
    setupTryAskingDropdown('tryAskingButton', 'suggestionsDropdown');
    setupTryAskingDropdown('tryAskingButtonCentered', 'suggestionsDropdownCentered');
}

// Helper function to setup try asking dropdown behavior
function setupTryAskingDropdown(buttonId, dropdownId) {
    const button = document.getElementById(buttonId);
    const dropdown = document.getElementById(dropdownId);

    if (button && dropdown) {
        let timeout;

        // Show dropdown when hovering button
        button.addEventListener('mouseenter', () => {
            clearTimeout(timeout);
            dropdown.classList.add('active');
        });

        // Hide dropdown when leaving button (with delay)
        button.addEventListener('mouseleave', () => {
            timeout = setTimeout(() => {
                dropdown.classList.remove('active');
            }, 200);
        });

        // Keep dropdown open when hovering over it
        dropdown.addEventListener('mouseenter', () => {
            clearTimeout(timeout);
        });

        // Hide dropdown when leaving dropdown
        dropdown.addEventListener('mouseleave', () => {
            timeout = setTimeout(() => {
                dropdown.classList.remove('active');
            }, 200);
        });
    }
    
    // Theme toggle functionality
    const themeToggleItem = document.getElementById('themeToggleItem');
    const themeSwitch = document.getElementById('themeSwitch');
    
    if (themeToggleItem && themeSwitch) {
        // Check current theme
        const currentTheme = localStorage.getItem('theme') || 'dark';
        if (currentTheme === 'light') {
            themeSwitch.classList.add('active');
        }
        
        themeToggleItem.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            if (newTheme === 'light') {
                themeSwitch.classList.add('active');
            } else {
                themeSwitch.classList.remove('active');
            }
        });
    }
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Add to query history
    queryHistory.push(query);
    historyIndex = -1; // Reset history navigation

    // Add chat-active class to transform the layout
    document.body.classList.add('chat-active');

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        // Use the centralized API client
        const data = await statsAPI.query(query, currentSessionId);
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.data);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        // Better error message handling with APIError
        const errorMessage = error instanceof APIError
            ? `Error: ${error.message}`
            : `Error: Unable to process your request. Please try again.`;
        addMessage(errorMessage, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;

    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    let html = `<div class="message-content">${displayContent}`;

    // Add sources inside the message-content div for assistant messages
    if (type === 'assistant' && sources && sources.length > 0) {
        // Force sources to be treated as objects by parsing if needed
        let processedSources = sources;

        // If sources are somehow strings, try to parse them
        if (typeof sources[0] === 'string' && sources[0].includes('[object Object]')) {
            // This shouldn't happen, but let's handle it
            processedSources = [];
        }

        const sourcesHtml = processedSources.map(source => {
            // Ensure we have an object
            if (typeof source === 'object' && source !== null && source.text) {
                if (source.url) {
                    return `<div class="source-item"><a href="${source.url}" target="_blank" rel="noopener noreferrer">${source.text}</a></div>`;
                } else {
                    return `<div class="source-item">${source.text}</div>`;
                }
            } else if (typeof source === 'string') {
                return `<div class="source-item">${source}</div>`;
            } else {
                // Debug: show what we actually received
                return `<div class="source-item">DEBUG: ${JSON.stringify(source)}</div>`;
            }
        }).join('');

        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourcesHtml}</div>
            </details>
        `;
    }

    html += `</div>`;  // Close message-content div

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';

    // Try Asking container now always visible in the input area
}

function startNewChat() {
    // Reset session and clear chat
    currentSessionId = null;
    chatMessages.innerHTML = '';

    // Remove chat-active class to restore centered layout
    document.body.classList.remove('chat-active');

    // Try Asking container now always visible in the input area

    // Re-enable input and focus
    if (chatInput) {
        chatInput.disabled = false;
        chatInput.focus();
    }
    if (sendButton) {
        sendButton.disabled = false;
    }
}

// Load sports statistics
async function loadSportsStats() {
    try {
        console.log('Loading sports stats...');
        // Use the centralized API client
        const data = await statsAPI.getStats();
        console.log('Sports data received:', data);
        
        // Update stats in UI
        if (totalPlayers) {
            totalPlayers.textContent = data.total_players;
        }
        if (totalTeams) {
            totalTeams.textContent = data.total_teams;
        }
        if (totalGames) {
            totalGames.textContent = data.total_games;
        }
        
    } catch (error) {
        console.error('Error loading sports stats:', error);
        // Set default values on error
        if (totalPlayers) totalPlayers.textContent = '0';
        if (totalTeams) totalTeams.textContent = '0';
        if (totalGames) totalGames.textContent = '0';
    }
}

// Theme functions moved to nav.js to avoid conflicts