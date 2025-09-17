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
    // Setup both inline and centered dropdowns
    setupDropdownPair('tryAskingButton', 'suggestionsDropdown');
    setupDropdownPair('tryAskingButtonCentered', 'suggestionsDropdownCentered');
}

function setupDropdownPair(buttonId: string, dropdownId: string): void {
    const tryAskingButton = document.getElementById(buttonId);
    const suggestionsDropdown = document.getElementById(dropdownId) as HTMLElement;


    if (tryAskingButton && suggestionsDropdown) {
        let suggestionsTimeout: TimeoutHandle | undefined;
        let originalParent = suggestionsDropdown.parentElement; // Store original parent

        // Show dropdown when hovering button
        tryAskingButton.addEventListener('mouseenter', () => {
            clearTimeout(suggestionsTimeout);

            // Move dropdown to body for unconstrained positioning
            if (buttonId === 'tryAskingButton') {
                document.body.appendChild(suggestionsDropdown);
            }

            // Get button position
            const buttonRect = tryAskingButton.getBoundingClientRect();
            const dropdownWidth = 320;
            const dropdownMaxHeight = 300;
            const margin = 8; // Normal margin spacing

            // Calculate horizontal position
            let leftPosition: number;
            const viewportWidth = window.innerWidth;

            // For inline dropdown (right-side button), position dropdown to the left of button
            if (buttonId === 'tryAskingButton') {
                // Position dropdown to the left of the button
                leftPosition = buttonRect.left - dropdownWidth - 10;

                // If that would go off the left edge, position it just inside the viewport
                if (leftPosition < 10) {
                    leftPosition = 10;
                }

            } else {
                // For centered button, center the dropdown on the button
                leftPosition = buttonRect.left + (buttonRect.width / 2) - (dropdownWidth / 2);

                // Keep within viewport bounds
                if (leftPosition < 10) {
                    leftPosition = 10;
                } else if (leftPosition + dropdownWidth > viewportWidth - 10) {
                    leftPosition = viewportWidth - dropdownWidth - 10;
                }

            }

            // Calculate vertical position
            let topPosition = buttonRect.top - dropdownMaxHeight - margin;

            // Check if dropdown would go above viewport
            const scrollY = window.scrollY || window.pageYOffset;
            const viewportTop = scrollY;

            // If dropdown would be above viewport, position it below button instead
            if (topPosition < viewportTop) {
                topPosition = buttonRect.bottom + margin;
            }


            // Remove any interfering classes
            suggestionsDropdown.classList.remove('suggestions-dropdown-inline');

            // Apply styles using setProperty for !important
            suggestionsDropdown.style.setProperty('position', 'fixed', 'important');
            suggestionsDropdown.style.setProperty('left', `${leftPosition}px`, 'important');
            suggestionsDropdown.style.setProperty('top', `${topPosition}px`, 'important');
            suggestionsDropdown.style.setProperty('right', 'auto', 'important');
            suggestionsDropdown.style.setProperty('bottom', 'auto', 'important');
            suggestionsDropdown.style.setProperty('transform', 'none', 'important');
            suggestionsDropdown.style.setProperty('width', `${dropdownWidth}px`, 'important');
            suggestionsDropdown.style.setProperty('min-width', `${dropdownWidth}px`, 'important');
            suggestionsDropdown.style.setProperty('max-width', `${dropdownWidth}px`, 'important');
            suggestionsDropdown.style.setProperty('height', 'auto', 'important');
            suggestionsDropdown.style.setProperty('min-height', '172px', 'important');
            suggestionsDropdown.style.setProperty('max-height', `${dropdownMaxHeight}px`, 'important');
            suggestionsDropdown.style.setProperty('visibility', 'visible', 'important');
            suggestionsDropdown.style.setProperty('opacity', '1', 'important');
            suggestionsDropdown.style.setProperty('display', 'block', 'important');
            suggestionsDropdown.style.setProperty('z-index', '10000', 'important');

            // Remove any temporary debug styles
            suggestionsDropdown.style.removeProperty('border');
            suggestionsDropdown.style.removeProperty('background-color');
            suggestionsDropdown.style.removeProperty('color');

            // Add active class after setting styles
            suggestionsDropdown.classList.add('active');

        });

        // Hide dropdown when leaving button (with delay)
        tryAskingButton.addEventListener('mouseleave', () => {
            suggestionsTimeout = setTimeout(() => {
                suggestionsDropdown.classList.remove('active');
                // Don't clear all styles, just hide it
                suggestionsDropdown.style.visibility = 'hidden';
                suggestionsDropdown.style.opacity = '0';
                suggestionsDropdown.style.display = 'none';

                // Return dropdown to original parent if it was moved
                if (buttonId === 'tryAskingButton' && originalParent && suggestionsDropdown.parentElement === document.body) {
                    originalParent.appendChild(suggestionsDropdown);
                }
            }, 200);
        });

        // Keep dropdown open when hovering over it
        suggestionsDropdown.addEventListener('mouseenter', () => {
            clearTimeout(suggestionsTimeout);
            // Just maintain visibility, position is already set
            suggestionsDropdown.style.visibility = 'visible';
            suggestionsDropdown.style.opacity = '1';
            suggestionsDropdown.style.display = 'block';
        });

        // Hide dropdown when leaving the dropdown itself
        suggestionsDropdown.addEventListener('mouseleave', () => {
            suggestionsTimeout = setTimeout(() => {
                suggestionsDropdown.classList.remove('active');
                // Don't clear all styles, just hide it
                suggestionsDropdown.style.visibility = 'hidden';
                suggestionsDropdown.style.opacity = '0';
                suggestionsDropdown.style.display = 'none';

                // Return dropdown to original parent if it was moved
                if (buttonId === 'tryAskingButton' && originalParent && suggestionsDropdown.parentElement === document.body) {
                    originalParent.appendChild(suggestionsDropdown);
                }
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