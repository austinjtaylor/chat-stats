/**
 * DOM Manipulation Utilities - TypeScript version
 */

/**
 * Attributes for creating or modifying DOM elements
 */
interface DOMAttributes {
    /** CSS class name(s) to apply */
    className?: string;
    /** Data attributes (data-*) as key-value pairs */
    dataset?: Record<string, string>;
    /** Additional element properties */
    [key: string]: any;
}

/**
 * Options for element animations
 * Extends standard KeyframeAnimationOptions
 */
interface AnimateOptions extends KeyframeAnimationOptions {
    /** Animation duration in milliseconds */
    duration?: number;
    /** CSS easing function */
    easing?: string;
}

/**
 * Element position and size information
 * Matches DOMRect interface structure
 */
interface ElementDimensions {
    /** Element width in pixels */
    width: number;
    /** Element height in pixels */
    height: number;
    /** Distance from top of viewport */
    top: number;
    /** Distance from left of viewport */
    left: number;
    /** Distance from bottom of viewport */
    bottom: number;
    /** Distance from right of viewport */
    right: number;
    /** Horizontal position (same as left) */
    x: number;
    /** Vertical position (same as top) */
    y: number;
}

const DOM = {
    /**
     * Query selector with null check
     */
    $<T extends Element = Element>(selector: string, parent: Document | Element = document): T | null {
        return parent.querySelector<T>(selector);
    },

    /**
     * Query selector all
     */
    $$<T extends Element = Element>(selector: string, parent: Document | Element = document): T[] {
        return Array.from(parent.querySelectorAll<T>(selector));
    },

    /**
     * Create element with optional attributes and children
     */
    createElement<K extends keyof HTMLElementTagNameMap>(
        tag: K,
        attributes: DOMAttributes = {},
        children: (string | Element)[] = []
    ): HTMLElementTagNameMap[K] {
        const element = document.createElement(tag);

        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = String(dataValue);
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
    on<K extends keyof HTMLElementEventMap>(
        element: Element,
        event: K,
        selectorOrHandler: string | EventListener,
        handler?: EventListener
    ): void {
        if (typeof selectorOrHandler === 'function') {
            element.addEventListener(event, selectorOrHandler as EventListener);
        } else {
            element.addEventListener(event, (e: Event) => {
                const target = (e.target as Element).closest(selectorOrHandler);
                if (target && handler) {
                    handler.call(target, e);
                }
            });
        }
    },

    /**
     * Remove all children from an element
     */
    empty(element: Element): void {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    },

    /**
     * Toggle class on element
     */
    toggleClass(element: Element, className: string, force?: boolean): boolean {
        if (force !== undefined) {
            return element.classList.toggle(className, force);
        }
        return element.classList.toggle(className);
    },

    /**
     * Show element
     */
    show(element: HTMLElement, display: string = 'block'): void {
        element.style.display = display;
    },

    /**
     * Hide element
     */
    hide(element: HTMLElement): void {
        element.style.display = 'none';
    },

    /**
     * Check if element is visible
     */
    isVisible(element: HTMLElement): boolean {
        return element.offsetParent !== null;
    },

    /**
     * Scroll element into view
     */
    scrollIntoView(element: Element, options: ScrollIntoViewOptions = { behavior: 'smooth', block: 'center' }): void {
        element.scrollIntoView(options);
    },

    /**
     * Set multiple styles at once
     */
    setStyles(element: HTMLElement, styles: Partial<CSSStyleDeclaration>): void {
        Object.entries(styles).forEach(([key, value]) => {
            (element.style as any)[key] = value;
        });
    },

    /**
     * Animate element
     */
    animate(element: Element, keyframes: Keyframe[] | PropertyIndexedKeyframes, options: AnimateOptions = {}): Animation {
        return element.animate(keyframes, {
            duration: 300,
            easing: 'ease',
            ...options
        });
    },

    /**
     * Wait for DOM ready
     */
    ready(callback: () => void): void {
        if (document.readyState !== 'loading') {
            callback();
        } else {
            document.addEventListener('DOMContentLoaded', callback);
        }
    },

    /**
     * Debounce function
     */
    debounce<T extends (...args: any[]) => any>(func: T, wait: number = 300): (...args: Parameters<T>) => void {
        let timeout: ReturnType<typeof setTimeout> | undefined;
        return function(this: any, ...args: Parameters<T>) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    /**
     * Throttle function
     */
    throttle<T extends (...args: any[]) => any>(func: T, limit: number = 300): (...args: Parameters<T>) => void {
        let inThrottle: boolean = false;
        return function(this: any, ...args: Parameters<T>) {
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
    parseHTML(htmlString: string): ChildNode | null {
        const template = document.createElement('template');
        template.innerHTML = htmlString.trim();
        return template.content.firstChild;
    },

    /**
     * Escape HTML
     */
    escapeHTML(str: string): string {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    /**
     * Get form data as object
     */
    getFormData(form: HTMLFormElement): Record<string, FormDataEntryValue | FormDataEntryValue[]> {
        const formData = new FormData(form);
        const data: Record<string, FormDataEntryValue | FormDataEntryValue[]> = {};
        for (const [key, value] of formData.entries()) {
            if (data[key]) {
                if (!Array.isArray(data[key])) {
                    data[key] = [data[key] as FormDataEntryValue];
                }
                (data[key] as FormDataEntryValue[]).push(value);
            } else {
                data[key] = value;
            }
        }
        return data;
    },

    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text: string): Promise<boolean> {
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
    measure(element: Element): ElementDimensions {
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

// ES Module exports
export { DOM };
export default DOM;

// Also export individual functions for convenience
export const { $, $$, createElement, on, empty, toggleClass, show, hide, isVisible, scrollIntoView, setStyles, animate, ready, debounce, throttle, parseHTML, escapeHTML, getFormData, copyToClipboard, measure } = DOM;

// For backward compatibility with script tags
if (typeof window !== 'undefined') {
    (window as any).DOM = DOM;
}