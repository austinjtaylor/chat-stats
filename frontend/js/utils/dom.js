/**
 * DOM Manipulation Utilities
 */

const DOM = {
    /**
     * Query selector with null check
     */
    $(selector, parent = document) {
        return parent.querySelector(selector);
    },

    /**
     * Query selector all
     */
    $$(selector, parent = document) {
        return Array.from(parent.querySelectorAll(selector));
    },

    /**
     * Create element with optional attributes and children
     */
    createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);

        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = dataValue;
                });
            } else if (key.startsWith('on')) {
                const event = key.substring(2).toLowerCase();
                element.addEventListener(event, value);
            } else {
                element.setAttribute(key, value);
            }
        });

        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Element) {
                element.appendChild(child);
            }
        });

        return element;
    },

    /**
     * Add event listener with delegation support
     */
    on(element, event, selectorOrHandler, handler) {
        if (typeof selectorOrHandler === 'function') {
            element.addEventListener(event, selectorOrHandler);
        } else {
            element.addEventListener(event, (e) => {
                const target = e.target.closest(selectorOrHandler);
                if (target) {
                    handler.call(target, e);
                }
            });
        }
    },

    /**
     * Remove all children from an element
     */
    empty(element) {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    },

    /**
     * Toggle class on element
     */
    toggleClass(element, className, force) {
        if (force !== undefined) {
            return element.classList.toggle(className, force);
        }
        return element.classList.toggle(className);
    },

    /**
     * Show element
     */
    show(element, display = 'block') {
        element.style.display = display;
    },

    /**
     * Hide element
     */
    hide(element) {
        element.style.display = 'none';
    },

    /**
     * Check if element is visible
     */
    isVisible(element) {
        return element.offsetParent !== null;
    },

    /**
     * Scroll element into view
     */
    scrollIntoView(element, options = { behavior: 'smooth', block: 'center' }) {
        element.scrollIntoView(options);
    },

    /**
     * Set multiple styles at once
     */
    setStyles(element, styles) {
        Object.entries(styles).forEach(([key, value]) => {
            element.style[key] = value;
        });
    },

    /**
     * Animate element
     */
    animate(element, keyframes, options = {}) {
        return element.animate(keyframes, {
            duration: 300,
            easing: 'ease',
            ...options
        });
    },

    /**
     * Wait for DOM ready
     */
    ready(callback) {
        if (document.readyState !== 'loading') {
            callback();
        } else {
            document.addEventListener('DOMContentLoaded', callback);
        }
    },

    /**
     * Debounce function
     */
    debounce(func, wait = 300) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    /**
     * Throttle function
     */
    throttle(func, limit = 300) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Parse HTML string
     */
    parseHTML(htmlString) {
        const template = document.createElement('template');
        template.innerHTML = htmlString.trim();
        return template.content.firstChild;
    },

    /**
     * Escape HTML
     */
    escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    /**
     * Get form data as object
     */
    getFormData(form) {
        const formData = new FormData(form);
        const data = {};
        for (const [key, value] of formData.entries()) {
            if (data[key]) {
                if (!Array.isArray(data[key])) {
                    data[key] = [data[key]];
                }
                data[key].push(value);
            } else {
                data[key] = value;
            }
        }
        return data;
    },

    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Failed to copy:', err);
            return false;
        }
    },

    /**
     * Measure element dimensions
     */
    measure(element) {
        const rect = element.getBoundingClientRect();
        return {
            width: rect.width,
            height: rect.height,
            top: rect.top,
            left: rect.left,
            bottom: rect.bottom,
            right: rect.right,
            x: rect.x,
            y: rect.y
        };
    }
};

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.DOM = DOM;
}