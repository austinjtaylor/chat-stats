/**
 * Dropdown Component Module
 * Handles all dropdown interactions including menu, settings, and suggestions
 */

export function initDropdowns() {
    setupMenuDropdown();
    setupSettingsDropdown();
    setupTryAskingDropdown();
    setupThemeToggle();
}

function setupMenuDropdown() {
    const menuWrapper = document.querySelector('.menu-wrapper');
    const menuDropdown = document.getElementById('menuDropdown');

    if (menuWrapper && menuDropdown) {
        let menuTimeout;

        menuWrapper.addEventListener('mouseenter', () => {
            clearTimeout(menuTimeout);
            menuDropdown.classList.add('active');
            // Close other dropdowns
            closeOtherDropdowns('menuDropdown');
        });

        menuWrapper.addEventListener('mouseleave', () => {
            menuTimeout = setTimeout(() => {
                menuDropdown.classList.remove('active');
            }, 200);
        });

        // Handle new chat menu item click
        const newChatMenuItem = document.getElementById('newChatMenuItem');
        if (newChatMenuItem) {
            newChatMenuItem.addEventListener('click', () => {
                startNewChat();
                menuDropdown.classList.remove('active');
            });
        }
    }
}

function setupSettingsDropdown() {
    const settingsWrapper = document.querySelector('.settings-wrapper');
    const settingsDropdown = document.getElementById('settingsDropdown');

    if (settingsWrapper && settingsDropdown) {
        let settingsTimeout;

        settingsWrapper.addEventListener('mouseenter', () => {
            clearTimeout(settingsTimeout);
            settingsDropdown.classList.add('active');
            // Close other dropdowns
            closeOtherDropdowns('settingsDropdown');
        });

        settingsWrapper.addEventListener('mouseleave', () => {
            settingsTimeout = setTimeout(() => {
                settingsDropdown.classList.remove('active');
            }, 200);
        });
    }
}

function setupTryAskingDropdown() {
    const tryAskingButton = document.getElementById('tryAskingButton');
    const tryAskingContainer = document.querySelector('.try-asking-container');
    const suggestionsDropdown = document.getElementById('suggestionsDropdown');

    if (tryAskingButton && suggestionsDropdown && tryAskingContainer) {
        let suggestionsTimeout;

        // Show dropdown when hovering button
        tryAskingButton.addEventListener('mouseenter', () => {
            clearTimeout(suggestionsTimeout);
            suggestionsDropdown.classList.add('active');
        });

        // Hide dropdown when leaving button (with delay)
        tryAskingButton.addEventListener('mouseleave', () => {
            suggestionsTimeout = setTimeout(() => {
                suggestionsDropdown.classList.remove('active');
            }, 200);
        });

        // Keep dropdown open when hovering over it
        suggestionsDropdown.addEventListener('mouseenter', () => {
            clearTimeout(suggestionsTimeout);
        });

        // Hide dropdown when leaving the dropdown itself
        suggestionsDropdown.addEventListener('mouseleave', () => {
            suggestionsTimeout = setTimeout(() => {
                suggestionsDropdown.classList.remove('active');
            }, 200);
        });

        // Handle suggested question clicks
        document.querySelectorAll('.suggested-item').forEach(button => {
            button.addEventListener('click', (e) => {
                const question = e.target.getAttribute('data-question');
                const chatInput = document.getElementById('chatInput');
                if (chatInput && question) {
                    chatInput.value = question;
                    // Trigger send message if sendButton exists
                    const sendButton = document.getElementById('sendButton');
                    if (sendButton) {
                        sendButton.click();
                    }
                    // Close dropdown after selection
                    suggestionsDropdown.classList.remove('active');
                }
            });
        });
    }
}

function setupThemeToggle() {
    const themeToggleItem = document.getElementById('themeToggleItem');
    const themeSwitch = document.getElementById('themeSwitch');

    if (themeToggleItem && themeSwitch) {
        // Load saved theme or default to dark
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);

        // Update switch state
        if (savedTheme === 'dark') {
            themeSwitch.classList.add('active');
        } else {
            themeSwitch.classList.remove('active');
        }

        // Toggle theme on click
        themeToggleItem.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';

            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);

            // Update switch state
            if (newTheme === 'dark') {
                themeSwitch.classList.add('active');
            } else {
                themeSwitch.classList.remove('active');
            }
        });
    }
}

function closeOtherDropdowns(exceptDropdownId) {
    const dropdownIds = ['menuDropdown', 'settingsDropdown', 'suggestionsDropdown'];
    dropdownIds.forEach(id => {
        if (id !== exceptDropdownId) {
            const dropdown = document.getElementById(id);
            if (dropdown) {
                dropdown.classList.remove('active');
            }
        }
    });
}

function startNewChat() {
    // Clear chat messages
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    // Generate new session ID if needed
    if (window.createNewSession && typeof window.createNewSession === 'function') {
        window.createNewSession();
    }

    // Focus on input
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.focus();
    }
}