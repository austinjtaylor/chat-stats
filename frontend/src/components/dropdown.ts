/**
 * Dropdown Component Module
 * Handles all dropdown interactions including menu, settings, and suggestions
 */

// Type for timeout handles
type TimeoutHandle = ReturnType<typeof setTimeout>;

export function initDropdowns(): void {
    setupMenuDropdown();
    setupSettingsDropdown();
    setupTryAskingDropdown();
    setupThemeToggle();
}

function setupMenuDropdown(): void {
    const menuWrapper = document.querySelector('.menu-wrapper');
    const menuDropdown = document.getElementById('menuDropdown');

    if (menuWrapper && menuDropdown) {
        let menuTimeout: TimeoutHandle | undefined;

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

function setupSettingsDropdown(): void {
    const settingsWrapper = document.querySelector('.settings-wrapper');
    const settingsDropdown = document.getElementById('settingsDropdown');

    if (settingsWrapper && settingsDropdown) {
        let settingsTimeout: TimeoutHandle | undefined;

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

function setupTryAskingDropdown(): void {
    const tryAskingButton = document.getElementById('tryAskingButton');
    const tryAskingContainer = document.querySelector('.try-asking-container');
    const suggestionsDropdown = document.getElementById('suggestionsDropdown');

    if (tryAskingButton && suggestionsDropdown && tryAskingContainer) {
        let suggestionsTimeout: TimeoutHandle | undefined;

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
        document.querySelectorAll<HTMLElement>('.suggested-item').forEach(button => {
            button.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                const question = target.getAttribute('data-question');
                const chatInput = document.getElementById('chatInput') as HTMLInputElement | null;
                if (chatInput && question) {
                    chatInput.value = question;
                    // Trigger send message if sendButton exists
                    const sendButton = document.getElementById('sendButton') as HTMLButtonElement | null;
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

function setupThemeToggle(): void {
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

function closeOtherDropdowns(exceptDropdownId: string): void {
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

function startNewChat(): void {
    // Clear chat messages
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    // Generate new session ID if needed
    if ((window as any).createNewSession && typeof (window as any).createNewSession === 'function') {
        (window as any).createNewSession();
    }

    // Focus on input
    const chatInput = document.getElementById('chatInput') as HTMLInputElement | null;
    if (chatInput) {
        chatInput.focus();
    }
}