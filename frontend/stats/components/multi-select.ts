/**
 * MultiSelect Component - Reusable dropdown with checkboxes
 * Extracted from players.ts for shared use across tabs
 */

export interface MultiSelectOption {
    value: string | number;
    label: string;
    group?: string; // For grouping (e.g., "Current Teams" vs "Historical Teams")
}

export interface MultiSelectConfig {
    containerId: string;
    options: MultiSelectOption[];
    selectedValues: (string | number)[];
    placeholder?: string;
    onChange: (selected: (string | number)[]) => void;
    allowSelectAll?: boolean;
    searchable?: boolean;
    exclusiveMode?: boolean; // If true, selecting one value clears others (single-select mode)
    exclusiveValues?: (string | number)[]; // Values that clear all others when selected (e.g., "career", "all")
}

export class MultiSelect {
    private config: MultiSelectConfig;
    private container: HTMLElement | null;
    private dropdown: HTMLElement | null;
    private isOpen: boolean = false;
    private searchInput: HTMLInputElement | null = null;
    private lastToggleTime: number = 0;

    constructor(config: MultiSelectConfig) {
        this.config = config;
        this.container = document.getElementById(config.containerId);
        this.dropdown = null;
        this.init();
    }

    private init(): void {
        if (!this.container) {
            console.error(`MultiSelect: Container ${this.config.containerId} not found`);
            return;
        }

        this.render();
        this.setupClickOutsideListener();
    }

    private render(): void {
        if (!this.container) return;

        this.container.innerHTML = '';
        this.container.className = 'multi-select-container';

        // Create toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'multi-select-toggle';
        toggleBtn.type = 'button';
        toggleBtn.innerHTML = this.getToggleButtonText();
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });

        // Create dropdown
        const dropdown = document.createElement('div');
        dropdown.className = 'multi-select-dropdown' + (this.isOpen ? '' : ' hidden');
        this.dropdown = dropdown;

        // Add search if enabled
        if (this.config.searchable) {
            const searchContainer = document.createElement('div');
            searchContainer.className = 'multi-select-search';
            this.searchInput = document.createElement('input');
            this.searchInput.type = 'text';
            this.searchInput.placeholder = 'Search...';
            this.searchInput.className = 'multi-select-search-input';
            this.searchInput.addEventListener('input', () => this.filterOptions());
            searchContainer.appendChild(this.searchInput);
            dropdown.appendChild(searchContainer);
        }

        // Add select all/clear all buttons (only for multi-select mode)
        if (this.config.allowSelectAll && !this.config.exclusiveMode) {
            const actionsRow = document.createElement('div');
            actionsRow.className = 'multi-select-actions';

            const selectAllBtn = document.createElement('button');
            selectAllBtn.textContent = 'Select All';
            selectAllBtn.className = 'multi-select-action-btn';
            selectAllBtn.type = 'button';
            selectAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectAll();
            });

            const clearAllBtn = document.createElement('button');
            clearAllBtn.textContent = 'Clear All';
            clearAllBtn.className = 'multi-select-action-btn';
            clearAllBtn.type = 'button';
            clearAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearAll();
            });

            actionsRow.appendChild(selectAllBtn);
            actionsRow.appendChild(clearAllBtn);
            dropdown.appendChild(actionsRow);
        }

        // Add options list
        const optionsList = document.createElement('div');
        optionsList.className = 'multi-select-options';
        this.renderOptions(optionsList);
        dropdown.appendChild(optionsList);

        this.container.appendChild(toggleBtn);
        this.container.appendChild(dropdown);
    }

    private renderOptions(container: HTMLElement): void {
        container.innerHTML = '';

        const filteredOptions = this.getFilteredOptions();
        let currentGroup = '';

        filteredOptions.forEach(option => {
            // Add group header if needed
            if (option.group && option.group !== currentGroup) {
                const groupHeader = document.createElement('div');
                groupHeader.className = 'multi-select-group-header';
                groupHeader.textContent = option.group;
                container.appendChild(groupHeader);
                currentGroup = option.group;
            }

            const optionDiv = document.createElement('div');
            optionDiv.className = 'multi-select-option';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `${this.config.containerId}-${option.value}`;
            checkbox.value = String(option.value);
            checkbox.checked = this.config.selectedValues.includes(option.value);
            checkbox.addEventListener('change', () => this.handleOptionChange(option.value));

            const label = document.createElement('label');
            label.htmlFor = checkbox.id;
            label.textContent = option.label;

            optionDiv.appendChild(checkbox);
            optionDiv.appendChild(label);
            container.appendChild(optionDiv);
        });

        if (filteredOptions.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'multi-select-no-results';
            noResults.textContent = 'No results found';
            container.appendChild(noResults);
        }
    }

    private getFilteredOptions(): MultiSelectOption[] {
        if (!this.searchInput || !this.searchInput.value.trim()) {
            return this.config.options;
        }

        const searchTerm = this.searchInput.value.toLowerCase();
        return this.config.options.filter(option =>
            option.label.toLowerCase().includes(searchTerm)
        );
    }

    private filterOptions(): void {
        const optionsList = this.dropdown?.querySelector('.multi-select-options');
        if (optionsList) {
            this.renderOptions(optionsList as HTMLElement);
        }
    }

    private getToggleButtonText(): string {
        const count = this.config.selectedValues.length;

        if (count === 0) {
            return this.config.placeholder || 'Select...';
        }

        if (count === 1) {
            const selected = this.config.options.find(opt => opt.value === this.config.selectedValues[0]);
            return selected ? selected.label : `${count} selected`;
        }

        if (count === this.config.options.length) {
            return 'All';
        }

        return `${count} selected`;
    }

    private handleOptionChange(value: string | number): void {
        let newSelected: (string | number)[];
        const exclusiveValues = this.config.exclusiveValues || [];

        // Check if this value is an exclusive value
        const isExclusiveValue = exclusiveValues.includes(value);
        // Check if current selection includes any exclusive values
        const hasExclusiveSelected = this.config.selectedValues.some(v => exclusiveValues.includes(v));

        if (this.config.exclusiveMode) {
            // In exclusive mode, selecting one clears all others (single-select)
            newSelected = [value];
        } else if (isExclusiveValue) {
            // Selecting an exclusive value clears all others
            newSelected = [value];
        } else if (hasExclusiveSelected) {
            // Clicking any non-exclusive value when exclusive is selected removes the exclusive
            newSelected = [value];
        } else {
            // Normal toggle behavior for multi-select
            if (this.config.selectedValues.includes(value)) {
                newSelected = this.config.selectedValues.filter(v => v !== value);
            } else {
                newSelected = [...this.config.selectedValues, value];
            }
        }

        this.updateSelected(newSelected);
    }

    private selectAll(): void {
        // Filter out exclusive values when selecting all
        const exclusiveValues = this.config.exclusiveValues || [];
        const allValues = this.getFilteredOptions()
            .filter(opt => !exclusiveValues.includes(opt.value))
            .map(opt => opt.value);
        this.updateSelected(allValues);
    }

    private clearAll(): void {
        this.updateSelected([]);
    }

    private updateSelected(newSelected: (string | number)[]): void {
        this.config.selectedValues = newSelected;
        this.config.onChange(newSelected);

        // Update UI
        const toggleBtn = this.container?.querySelector('.multi-select-toggle');
        if (toggleBtn) {
            toggleBtn.innerHTML = this.getToggleButtonText();
        }

        // Update checkboxes
        const checkboxes = this.dropdown?.querySelectorAll('input[type="checkbox"]');
        checkboxes?.forEach((checkbox: Element) => {
            const cb = checkbox as HTMLInputElement;
            cb.checked = this.config.selectedValues.includes(cb.value) || this.config.selectedValues.includes(Number(cb.value));
        });
    }

    private toggleDropdown(): void {
        // Debounce rapid double-clicks (can happen with multiple event listeners)
        const now = Date.now();
        if (now - this.lastToggleTime < 50) {
            return;
        }
        this.lastToggleTime = now;

        this.isOpen = !this.isOpen;

        if (this.dropdown) {
            if (this.isOpen) {
                this.dropdown.classList.remove('hidden');
                if (this.searchInput) {
                    this.searchInput.focus();
                }
            } else {
                this.dropdown.classList.add('hidden');
                if (this.searchInput) {
                    this.searchInput.value = '';
                    this.filterOptions();
                }
            }
        }
    }

    private setupClickOutsideListener(): void {
        document.addEventListener('click', (e) => {
            if (this.isOpen && this.container && !this.container.contains(e.target as Node)) {
                this.closeDropdown();
            }
        });

        // Close when clicking outside the iframe (parent document)
        window.addEventListener('blur', () => {
            if (this.isOpen) {
                this.closeDropdown();
            }
        });

        // Handle ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeDropdown();
            }
        });
    }

    private closeDropdown(): void {
        this.isOpen = false;
        if (this.dropdown) {
            this.dropdown.classList.add('hidden');
        }
        if (this.searchInput) {
            this.searchInput.value = '';
            this.filterOptions();
        }
    }

    // Public methods
    public updateOptions(options: MultiSelectOption[]): void {
        this.config.options = options;
        this.render();
    }

    public getSelected(): (string | number)[] {
        return this.config.selectedValues;
    }

    public setSelected(values: (string | number)[]): void {
        this.config.selectedValues = values;

        // Update UI without full re-render (avoids issues when called after updateOptions)
        const toggleBtn = this.container?.querySelector('.multi-select-toggle');
        if (toggleBtn) {
            toggleBtn.innerHTML = this.getToggleButtonText();
        }

        // Update checkboxes
        const checkboxes = this.dropdown?.querySelectorAll('input[type="checkbox"]');
        checkboxes?.forEach((checkbox: Element) => {
            const cb = checkbox as HTMLInputElement;
            cb.checked = this.config.selectedValues.includes(cb.value) || this.config.selectedValues.includes(Number(cb.value));
        });
    }

    public destroy(): void {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

export default MultiSelect;
