/**
 * Dropdown Component Module
 * Handles all dropdown interactions including menu, settings, and suggestions
 */

// Track currently open dropdown
let currentOpenDropdown: string | null = null;

export function initDropdowns(): void {
    setupMenuDropdown();
    setupSettingsDropdown();
    setupTryAskingDropdown();
    setupThemeToggle();
    setupTooltips();
    setupClickOutsideHandler();
}

function setupMenuDropdown(): void {
    const menuIcon = document.getElementById('menuIcon');
    const menuDropdown = document.getElementById('menuDropdown');

    if (menuIcon && menuDropdown) {
        menuIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown('menuDropdown');
        });

        // Prevent dropdown from closing when clicking inside it
        menuDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }
}

function setupSettingsDropdown(): void {
    const settingsIcon = document.getElementById('settingsIcon');
    const settingsDropdown = document.getElementById('settingsDropdown');

    if (settingsIcon && settingsDropdown) {
        settingsIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown('settingsDropdown');
        });

        // Prevent dropdown from closing when clicking inside it
        settingsDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
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
        // Toggle dropdown on click
        tryAskingButton.addEventListener('click', (e) => {
            e.stopPropagation();

            // Check if this dropdown is already open
            const isOpen = suggestionsDropdown.classList.contains('active');

            // Close all dropdowns first
            closeAllDropdowns();

            // If it wasn't open, open it
            if (!isOpen) {

                // Move dropdown to body for unconstrained positioning
                if (buttonId === 'tryAskingButton') {
                    document.body.appendChild(suggestionsDropdown);
                }

                // Get button position
                const buttonRect = tryAskingButton.getBoundingClientRect();
                const dropdownWidth = 320;
                const dropdownMaxHeight = 300;
                const margin = 8;

                // Calculate horizontal position
                let leftPosition: number;
                const viewportWidth = window.innerWidth;

                if (buttonId === 'tryAskingButton') {
                    leftPosition = buttonRect.left;
                    if (leftPosition < 10) {
                        leftPosition = 10;
                    }
                } else {
                    leftPosition = buttonRect.left + (buttonRect.width / 2) - (dropdownWidth / 2);
                    if (leftPosition < 10) {
                        leftPosition = 10;
                    } else if (leftPosition + dropdownWidth > viewportWidth - 10) {
                        leftPosition = viewportWidth - dropdownWidth - 10;
                    }
                }

                // Calculate vertical position
                let topPosition: number;
                if (buttonId === 'tryAskingButtonCentered') {
                    topPosition = 200;
                } else {
                    topPosition = buttonRect.top - dropdownMaxHeight - margin;
                    const scrollY = window.scrollY || window.pageYOffset;
                    const viewportTop = scrollY;
                    if (topPosition < viewportTop) {
                        topPosition = buttonRect.bottom + margin;
                    }
                }

                // Apply positioning styles
                suggestionsDropdown.classList.remove('suggestions-dropdown-inline');
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

                suggestionsDropdown.classList.add('active');
                currentOpenDropdown = dropdownId;
            }
        });

        // Prevent dropdown from closing when clicking inside it
        suggestionsDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Handle suggested question clicks for this specific dropdown
        suggestionsDropdown.querySelectorAll<HTMLElement>('.suggested-item').forEach(button => {
            button.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                const question = target.getAttribute('data-question');
                const chatInput = document.getElementById('chatInput') as HTMLInputElement | null;
                if (chatInput && question) {
                    chatInput.value = question;
                    const sendButton = document.getElementById('sendButton') as HTMLButtonElement | null;
                    if (sendButton) {
                        sendButton.click();
                    }
                    closeDropdown(dropdownId);
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

        // Update switch state (active = dark mode ON, inactive = light mode)
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

            // Update switch state (active = dark mode ON, inactive = light mode)
            if (newTheme === 'dark') {
                themeSwitch.classList.add('active');
            } else {
                themeSwitch.classList.remove('active');
            }
        });
    }
}

function toggleDropdown(dropdownId: string): void {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;

    const isOpen = dropdown.classList.contains('active');
    closeAllDropdowns();

    if (!isOpen) {
        dropdown.classList.add('active');
        currentOpenDropdown = dropdownId;
    }
}

function closeDropdown(dropdownId: string): void {
    const dropdown = document.getElementById(dropdownId);
    if (dropdown) {
        dropdown.classList.remove('active');
        if (dropdownId === 'suggestionsDropdown' || dropdownId === 'suggestionsDropdownCentered') {
            dropdown.style.visibility = 'hidden';
            dropdown.style.opacity = '0';
            dropdown.style.display = 'none';
        }
        if (currentOpenDropdown === dropdownId) {
            currentOpenDropdown = null;
        }
    }
}

function closeAllDropdowns(): void {
    const dropdownIds = ['menuDropdown', 'settingsDropdown', 'suggestionsDropdown', 'suggestionsDropdownCentered'];
    dropdownIds.forEach(id => closeDropdown(id));
    currentOpenDropdown = null;
}

function setupClickOutsideHandler(): void {
    document.addEventListener('click', (e) => {
        const target = e.target as HTMLElement;

        // Don't close if clicking inside a dropdown or on a trigger button
        const isClickInside = target.closest('.dropdown') ||
                            target.closest('.menu-wrapper') ||
                            target.closest('.settings-wrapper') ||
                            target.closest('.try-asking-button');

        if (!isClickInside) {
            closeAllDropdowns();
        }
    });
}

function setupTooltips(): void {
    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.style.cssText = 'position: fixed; opacity: 0; visibility: hidden; pointer-events: none; z-index: 10001;';
    document.body.appendChild(tooltip);

    // Tooltip configurations
    const tooltipTargets: Array<{selector: string, text: string}> = [
        { selector: '#menuIcon', text: 'Menu' },
        { selector: '#settingsIcon', text: 'Settings' },
        { selector: '#tryAskingButton', text: 'Suggested questions' },
        { selector: '#tryAskingButtonCentered', text: 'Suggested questions' },
        { selector: '#gameSearchIcon', text: 'Game search' }
    ];

    tooltipTargets.forEach(({ selector, text }) => {
        const element = document.querySelector(selector) as HTMLElement;
        if (!element) return;

        let tooltipTimeout: ReturnType<typeof setTimeout> | undefined;

        element.addEventListener('mouseenter', () => {
            // Clear any existing timeout
            clearTimeout(tooltipTimeout);

            // Show tooltip after a short delay
            tooltipTimeout = setTimeout(() => {
                const rect = element.getBoundingClientRect();
                tooltip.textContent = text;

                // Position tooltip below the element
                const tooltipTop = rect.bottom + 8;
                let tooltipLeft = rect.left + rect.width / 2;

                // Temporarily show tooltip to measure width
                tooltip.style.visibility = 'hidden';
                tooltip.style.display = 'block';
                const tooltipWidth = tooltip.offsetWidth;
                tooltip.style.display = '';

                // Check if tooltip would extend beyond left edge
                const halfWidth = tooltipWidth / 2;
                if (tooltipLeft - halfWidth < 10) {
                    // Adjust position to stay within viewport with 10px margin
                    tooltipLeft = halfWidth + 10;
                }

                // Also check right edge
                const viewportWidth = window.innerWidth;
                if (tooltipLeft + halfWidth > viewportWidth - 10) {
                    tooltipLeft = viewportWidth - halfWidth - 10;
                }

                tooltip.style.top = `${tooltipTop}px`;
                tooltip.style.left = `${tooltipLeft}px`;
                tooltip.style.transform = 'translateX(-50%)';
                tooltip.style.opacity = '1';
                tooltip.style.visibility = 'visible';
            }, 300);
        });

        element.addEventListener('mouseleave', () => {
            clearTimeout(tooltipTimeout);
            tooltip.style.opacity = '0';
            tooltip.style.visibility = 'hidden';
        });
    });
}