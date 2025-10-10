// API client is loaded from js/api/client.js

// Import necessary types
import type { StatsAPI } from './src/api/client';
import type { DOM as DOMType } from './src/utils/dom';

// Declare marked as a global
declare const marked: {
    parse(text: string): string;
};

// Access globals that are made available via imports in main.ts
declare const DOM: typeof DOMType;
declare const statsAPI: StatsAPI;
declare const APIError: any;

// Type definitions
interface MessageSource {
    text: string;
    url?: string;
}

// Global state
let currentSessionId: string | null = null;
let queryHistory: string[] = [];
let historyIndex: number = -1;

// DOM elements
let chatMessages: HTMLElement | null;
let chatInput: HTMLTextAreaElement | null;
let sendButton: HTMLButtonElement | null;
let totalPlayers: HTMLElement | null;
let totalTeams: HTMLElement | null;
let totalGames: HTMLElement | null;
let newChatButton: HTMLElement | null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements using DOM utility
    chatMessages = DOM.$('#chatMessages') as HTMLElement | null;
    chatInput = DOM.$('#chatInput') as HTMLTextAreaElement | null;
    sendButton = DOM.$('#sendButton') as HTMLButtonElement | null;
    totalPlayers = DOM.$('#totalPlayers') as HTMLElement | null;
    totalTeams = DOM.$('#totalTeams') as HTMLElement | null;
    totalGames = DOM.$('#totalGames') as HTMLElement | null;
    newChatButton = DOM.$('#newChatButton') as HTMLElement | null;

    setupEventListeners();
    setupDropdowns();
    // Theme initialization moved to nav.js
    createNewSession();
    loadSportsStats();
});

// Auto-resize textarea based on content
function autoResizeTextarea(textarea: HTMLTextAreaElement): void {
    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';
    // Set height to scrollHeight to fit content
    textarea.style.height = textarea.scrollHeight + 'px';

    // Update chat input area height CSS variable if in active chat mode
    updateChatInputHeight();
}

// Update the CSS variable for chat input height
function updateChatInputHeight(): void {
    const chatInputArea = document.querySelector('.chat-input-area') as HTMLElement;
    if (chatInputArea && document.body.classList.contains('chat-active')) {
        const height = chatInputArea.offsetHeight;
        document.documentElement.style.setProperty('--chat-input-height', `${height}px`);
    }
}

// Event Listeners
function setupEventListeners(): void {
    // Chat functionality
    sendButton?.addEventListener('click', sendMessage);

    // Auto-resize textarea on input
    chatInput?.addEventListener('input', () => {
        if (chatInput) {
            autoResizeTextarea(chatInput);
        }
    });

    chatInput?.addEventListener('keypress', (e) => {
        // Enter sends message, Shift+Enter creates new line
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Query history navigation with arrow keys
    chatInput?.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex < queryHistory.length - 1) {
                historyIndex++;
                if (chatInput) {
                    chatInput.value = queryHistory[queryHistory.length - 1 - historyIndex];
                    autoResizeTextarea(chatInput);
                }
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                if (chatInput) {
                    chatInput.value = queryHistory[queryHistory.length - 1 - historyIndex];
                    autoResizeTextarea(chatInput);
                }
            } else if (historyIndex === 0) {
                historyIndex = -1;
                if (chatInput) {
                    chatInput.value = '';
                    chatInput.style.height = 'auto';
                    updateChatInputHeight();
                }
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

    // Note: Suggested item clicks are now handled in dropdown.ts to avoid duplicate event listeners
}

// Setup dropdown functionality
function setupDropdowns(): void {
    // All dropdown functionality has been moved to dropdown.ts module
    // which handles click-based interactions instead of hover
    // The dropdown.ts module is initialized in main.ts
    // See: src/components/dropdown.ts
}

// Helper function to setup try asking dropdown behavior
// DEPRECATED: This function is no longer used
// All dropdown functionality has been moved to dropdown.ts with click-based interactions
// @ts-ignore - Function is preserved for reference only
function setupTryAskingDropdown(buttonId: string, dropdownId: string): void {
    // This function has been replaced by click-based dropdown handling in dropdown.ts
    return;
}



// Chat Functions
async function sendMessage(): Promise<void> {
    if (!chatInput || !sendButton || !chatMessages) return;

    const query = chatInput.value.trim();
    if (!query) return;

    // Add to query history
    queryHistory.push(query);
    historyIndex = -1; // Reset history navigation

    // Add chat-active class to transform the layout
    document.body.classList.add('chat-active');

    // Disable input and reset height
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Update chat input height after resetting textarea
    updateChatInputHeight();

    // Add user message and store its ID
    const userMessageId = addMessage(query, 'user');

    // Add loading message below the user query
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);

    // Smart scroll to keep messages visible above chat bar
    const userMessageDiv = document.getElementById(`message-${userMessageId}`);
    if (userMessageDiv) {
        // Calculate the maximum scroll to keep message visible above chat bar
        const containerHeight = chatMessages.offsetHeight;
        const messageBottom = userMessageDiv.offsetTop + userMessageDiv.offsetHeight;
        const chatBarHeight = 74; // Height of chat input area from CSS
        const gradientBuffer = 120; // Additional buffer for gradient fade effect

        // Calculate the maximum scroll position that keeps content visible
        // This prevents the bottom of the message from going below the top of the chat bar
        const maxScroll = Math.max(0, messageBottom - containerHeight + chatBarHeight + gradientBuffer);

        // Try to scroll the message to the top, but not beyond the max scroll limit
        const targetScroll = Math.min(userMessageDiv.offsetTop - 32, maxScroll);

        chatMessages.scrollTop = targetScroll;
    }

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

        // After adding assistant message, adjust scroll to keep it fully visible
        if (chatMessages) {
            const assistantMessage = chatMessages.lastElementChild as HTMLElement;
            if (assistantMessage && chatMessages) {
                // Small delay to ensure DOM is updated
                setTimeout(() => {
                    if (!chatMessages) return;
                    const messageBottom = assistantMessage.offsetTop + assistantMessage.offsetHeight;
                    const containerHeight = chatMessages.offsetHeight;
                    const visibleBottom = chatMessages.scrollTop + containerHeight;

                    // If message extends below visible area, scroll to show it
                    // 150px buffer accounts for the gradient fade effect
                    if (messageBottom > visibleBottom - 150) {
                        chatMessages.scrollTo({
                            top: messageBottom - containerHeight + 150,
                            behavior: 'smooth'
                        });
                    }
                }, 50);
            }
        }

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        // Better error message handling with APIError
        let errorMessage: string;
        if (error instanceof APIError) {
            const apiError = error as any;
            // Customize auth error messages
            if (apiError.status === 401 || apiError.message.includes('Not authenticated')) {
                errorMessage = 'Log in to Chat Stats';
            } else {
                errorMessage = `Error: ${apiError.message}`;
            }
        } else {
            errorMessage = `Error: Unable to process your request. Please try again.`;
        }
        addMessage(errorMessage, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage(): HTMLElement {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="thinking-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content: string, type: 'user' | 'assistant', sources: MessageSource[] | null = null, isWelcome: boolean = false): number {
    if (!chatMessages) return 0;

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
        if (typeof sources[0] === 'string' && (sources[0] as string).includes('[object Object]')) {
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

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession(): Promise<void> {
    currentSessionId = null;
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    // Try Asking container now always visible in the input area
}

function startNewChat(): void {
    // Reset session and clear chat
    currentSessionId = null;
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    // Remove chat-active class to restore centered layout
    document.body.classList.remove('chat-active');

    // Try Asking container now always visible in the input area

    // Re-enable input, reset height, and focus
    if (chatInput) {
        chatInput.disabled = false;
        chatInput.style.height = 'auto';
        chatInput.focus();
        updateChatInputHeight();
    }
    if (sendButton) {
        sendButton.disabled = false;
    }
}

// Load sports statistics
async function loadSportsStats(): Promise<void> {
    try {
        console.log('Loading sports stats...');
        // Use the centralized API client
        const data = await statsAPI.getStats();
        console.log('Sports data received:', data);

        // Update stats in UI
        if (totalPlayers) {
            totalPlayers.textContent = data.total_players.toString();
        }
        if (totalTeams) {
            totalTeams.textContent = data.total_teams.toString();
        }
        if (totalGames) {
            totalGames.textContent = data.total_games.toString();
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