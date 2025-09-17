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
    const tryAskingButton = document.getElementById('tryAskingButton');  // Back to the inline button
    const tryAskingContainer = document.querySelector('.try-asking-container');
    const suggestionsDropdown = document.getElementById('suggestionsDropdown');  // Back to the inline dropdown

    console.log('Setting up dropdown - Button:', !!tryAskingButton, 'Dropdown:', !!suggestionsDropdown, 'Container:', !!tryAskingContainer);

    if (tryAskingButton && suggestionsDropdown && tryAskingContainer) {
        let suggestionsTimeout: TimeoutHandle | undefined;

        // Show dropdown when hovering button
        tryAskingButton.addEventListener('mouseenter', () => {
            clearTimeout(suggestionsTimeout);

            // Calculate position from viewport edge
            const viewportWidth = window.innerWidth;
            const dropdownWidth = 320;
            const rightMargin = 20;
            const leftPosition = viewportWidth - dropdownWidth - rightMargin;

            // Log for debugging
            console.log('Dropdown position - Left:', leftPosition, 'Viewport Width:', viewportWidth);

            // Remove any interfering classes
            suggestionsDropdown.classList.remove('suggestions-dropdown-inline');

            // Apply styles using setProperty for !important
            suggestionsDropdown.style.setProperty('position', 'fixed', 'important');
            suggestionsDropdown.style.setProperty('left', `${leftPosition}px`, 'important');
            suggestionsDropdown.style.setProperty('top', '300px', 'important');
            suggestionsDropdown.style.setProperty('right', 'auto', 'important');
            suggestionsDropdown.style.setProperty('bottom', 'auto', 'important');
            suggestionsDropdown.style.setProperty('transform', 'none', 'important');
            suggestionsDropdown.style.setProperty('width', '320px', 'important');
            suggestionsDropdown.style.setProperty('min-width', '320px', 'important');
            suggestionsDropdown.style.setProperty('max-width', '320px', 'important');
            suggestionsDropdown.style.setProperty('height', 'auto', 'important');
            suggestionsDropdown.style.setProperty('min-height', '172px', 'important');
            suggestionsDropdown.style.setProperty('max-height', '300px', 'important');
            suggestionsDropdown.style.setProperty('visibility', 'visible', 'important');
            suggestionsDropdown.style.setProperty('opacity', '1', 'important');
            suggestionsDropdown.style.setProperty('display', 'block', 'important');
            suggestionsDropdown.style.setProperty('z-index', '10000', 'important');

            // Add active class after setting styles
            suggestionsDropdown.classList.add('active');

            // Verify styles were applied
            console.log('Applied styles - top:', suggestionsDropdown.style.top, 'left:', suggestionsDropdown.style.left);
        });

        // Hide dropdown when leaving button (with delay)
        tryAskingButton.addEventListener('mouseleave', () => {
            suggestionsTimeout = setTimeout(() => {
                suggestionsDropdown.classList.remove('active');
                // Don't clear all styles, just hide it
                suggestionsDropdown.style.visibility = 'hidden';
                suggestionsDropdown.style.opacity = '0';
                suggestionsDropdown.style.display = 'none';
            }, 200);
        });

        // Keep dropdown open when hovering over it
        suggestionsDropdown.addEventListener('mouseenter', () => {
            clearTimeout(suggestionsTimeout);
            // Maintain position while hovering
            requestAnimationFrame(() => {
                // Calculate position from viewport edge
                const viewportWidth = window.innerWidth;
                const dropdownWidth = 320;
                const rightMargin = 20;
                const leftPosition = viewportWidth - dropdownWidth - rightMargin;

                // Remove any existing properties
                suggestionsDropdown.style.removeProperty('right');
                suggestionsDropdown.style.removeProperty('transform');

                // Maintain position with calculated left value
                suggestionsDropdown.style.position = 'fixed';
                suggestionsDropdown.style.setProperty('right', 'auto', 'important');  // Override CSS right property
                suggestionsDropdown.style.left = `${leftPosition}px`;
                suggestionsDropdown.style.top = '300px';  // Position in middle-upper area
                suggestionsDropdown.style.bottom = '';  // Clear bottom
                suggestionsDropdown.style.transform = 'none';

                // Enforce width and height
                suggestionsDropdown.style.width = '320px';
                suggestionsDropdown.style.minWidth = '320px';
                suggestionsDropdown.style.maxWidth = '320px';
                suggestionsDropdown.style.height = 'auto';
                suggestionsDropdown.style.minHeight = '172px';
                suggestionsDropdown.style.maxHeight = '300px';
                suggestionsDropdown.style.boxSizing = 'border-box';

                // Force visibility
                suggestionsDropdown.style.visibility = 'visible';
                suggestionsDropdown.style.opacity = '1';
                suggestionsDropdown.style.display = 'block';
                suggestionsDropdown.style.zIndex = '10000';
            });
        });

        // Hide dropdown when leaving the dropdown itself
        suggestionsDropdown.addEventListener('mouseleave', () => {
            suggestionsTimeout = setTimeout(() => {
                suggestionsDropdown.classList.remove('active');
                // Don't clear all styles, just hide it
                suggestionsDropdown.style.visibility = 'hidden';
                suggestionsDropdown.style.opacity = '0';
                suggestionsDropdown.style.display = 'none';
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
                    // Don't clear all styles, just hide it
                    suggestionsDropdown.style.visibility = 'hidden';
                    suggestionsDropdown.style.opacity = '0';
                    suggestionsDropdown.style.display = 'none';
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