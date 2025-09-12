// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
let queryHistory = [];
let historyIndex = -1;

// DOM elements
let chatMessages, chatInput, sendButton, totalPlayers, totalTeams, totalGames, newChatButton, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalPlayers = document.getElementById('totalPlayers');
    totalTeams = document.getElementById('totalTeams');
    totalGames = document.getElementById('totalGames');
    newChatButton = document.getElementById('newChatButton');
    themeToggle = document.getElementById('themeToggle');
    
    setupEventListeners();
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
    newChatButton.addEventListener('click', startNewChat);
    
    // Theme toggle handled by nav.js
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Add to query history
    queryHistory.push(query);
    historyIndex = -1; // Reset history navigation
    
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
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
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
        addMessage(`Error: ${error.message}`, 'assistant');
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
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
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
    addMessage('Welcome to the UFA Stats Assistant! I can help you with questions about player stats, team performance, and game results. What would you like to know?', 'assistant', null, true);
}

function startNewChat() {
    // Reset session and clear chat
    currentSessionId = null;
    chatMessages.innerHTML = '';
    
    // Add welcome message
    addMessage('Welcome to the UFA Stats Assistant! I can help you with questions about player stats, team performance, and game results. What would you like to know?', 'assistant', null, true);
    
    // Focus on chat input for immediate use
    if (chatInput) {
        chatInput.focus();
    }
}

// Load sports statistics
async function loadSportsStats() {
    try {
        console.log('Loading sports stats...');
        const response = await fetch(`${API_URL}/stats`);
        if (!response.ok) throw new Error('Failed to load sports stats');
        
        const data = await response.json();
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