// Player statistics page functionality - TypeScript version

import type { PlayerSeasonStats, SortConfig } from '../types/models';
import type { PlayerStatsResponse } from '../types/api';
import { initializeTableTooltips, playerColumnDescriptions } from '../src/utils/table-tooltips';
import { MultiSelect } from './components/multi-select';
import type { MultiSelectOption } from './components/multi-select';

interface TeamInfo {
    id: string | number;
    name: string;
    is_current?: boolean;
    last_year?: number | string;
}

interface PlayerColumn {
    key: string;
    label: string;
    sortable: boolean;
}

interface CustomFilter {
    field: string;
    operator: '>' | '<' | '>=' | '<=' | '=';
    value: number;
}

interface PlayerFilters {
    season: (string | number)[]; // Changed to array for multi-select
    per: 'total' | 'game' | 'possession';
    team: string[]; // Changed to array for multi-select
    customFilters: CustomFilter[];
    careerMode: boolean; // Track if career mode is active
    sort?: string;
    order?: 'asc' | 'desc';
    page?: number;
    per_page?: number;
}

interface FilterableField {
    key: string;
    label: string;
    dataType: 'number' | 'percentage' | 'ratio';
    minYear?: number; // If undefined, available for all years
    description?: string;
}

// Filterable fields configuration
const FILTERABLE_FIELDS: FilterableField[] = [
    // Core stats
    { key: 'games_played', label: 'Games Played', dataType: 'number', description: 'GP' },
    { key: 'total_points_played', label: 'Points Played', dataType: 'number', description: 'PP' },
    { key: 'possessions', label: 'Possessions', dataType: 'number', description: 'POS' },
    { key: 'total_o_points_played', label: 'O-Points Played', dataType: 'number', description: 'OPP' },
    { key: 'total_d_points_played', label: 'D-Points Played', dataType: 'number', description: 'DPP' },
    { key: 'minutes_played', label: 'Minutes Played', dataType: 'number', description: 'MP' },

    // Scoring stats
    { key: 'score_total', label: 'Score Total', dataType: 'number', description: 'S (Goals + Assists)' },
    { key: 'total_goals', label: 'Goals', dataType: 'number', description: 'G' },
    { key: 'total_assists', label: 'Assists', dataType: 'number', description: 'A' },
    { key: 'total_hockey_assists', label: 'Hockey Assists', dataType: 'number', description: 'HA', minYear: 2014 },
    { key: 'total_blocks', label: 'Blocks', dataType: 'number', description: 'B' },
    { key: 'total_callahans', label: 'Callahans', dataType: 'number', description: 'CAL' },
    { key: 'calculated_plus_minus', label: 'Plus/Minus', dataType: 'number', description: '+/-' },

    // Throwing stats
    { key: 'total_completions', label: 'Completions', dataType: 'number', description: 'C' },
    { key: 'total_throw_attempts', label: 'Throw Attempts', dataType: 'number', description: 'Attempts' },
    { key: 'completion_percentage', label: 'Completion %', dataType: 'percentage', description: 'C%' },
    { key: 'total_throwaways', label: 'Throwaways', dataType: 'number', description: 'T' },
    { key: 'total_stalls', label: 'Stalls', dataType: 'number', description: 'S' },
    { key: 'total_drops', label: 'Drops', dataType: 'number', description: 'D' },
    { key: 'total_pulls', label: 'Pulls', dataType: 'number', description: 'P' },

    // Advanced stats (2021+)
    { key: 'total_yards', label: 'Total Yards', dataType: 'number', description: 'Y', minYear: 2021 },
    { key: 'total_yards_thrown', label: 'Throwing Yards', dataType: 'number', description: 'TY', minYear: 2021 },
    { key: 'total_yards_received', label: 'Receiving Yards', dataType: 'number', description: 'RY', minYear: 2021 },
    { key: 'total_hucks_completed', label: 'Hucks Completed', dataType: 'number', description: 'H', minYear: 2021 },
    { key: 'total_hucks_attempted', label: 'Hucks Attempted', dataType: 'number', description: 'HA', minYear: 2021 },
    { key: 'total_hucks_received', label: 'Hucks Received', dataType: 'number', description: 'HR', minYear: 2021 },
    { key: 'huck_percentage', label: 'Huck %', dataType: 'percentage', description: 'H%', minYear: 2021 },

    // Ratio stats
    { key: 'offensive_efficiency', label: 'Offensive Efficiency', dataType: 'percentage', description: 'OEFF' },
    { key: 'assists_per_turnover', label: 'Assists per Turnover', dataType: 'ratio', description: 'AST/T' },
    { key: 'yards_per_turn', label: 'Yards per Turnover', dataType: 'ratio', description: 'Y/T', minYear: 2021 },
    { key: 'yards_per_completion', label: 'Yards per Completion', dataType: 'ratio', description: 'TY/C', minYear: 2021 },
    { key: 'yards_per_reception', label: 'Yards per Reception', dataType: 'ratio', description: 'RY/R', minYear: 2021 }
];

class PlayerStats {
    currentPage: number;
    pageSize: number;
    currentSort: SortConfig;
    filters: PlayerFilters;
    players: PlayerSeasonStats[];
    percentiles: Record<string, Record<string, number>>;
    totalPages: number;
    totalPlayers: number;
    teams: TeamInfo[];
    cache: Map<string, { data: any; timestamp: number }>;
    seasonMultiSelect: MultiSelect | null = null;
    perMultiSelect: MultiSelect | null = null;
    teamMultiSelect: MultiSelect | null = null;

    constructor() {
        this.currentPage = 1;
        this.pageSize = 20;
        this.currentSort = { key: 'calculated_plus_minus', direction: 'desc' };
        this.filters = {
            season: ['career'],
            per: 'total',
            team: ['all'],
            customFilters: [],
            careerMode: true
        };
        this.players = [];
        this.percentiles = {};
        this.totalPages = 0;
        this.totalPlayers = 0;
        this.teams = [];
        this.cache = new Map();

        this.init();
    }

    async init(): Promise<void> {
        this.initializeSeasonMultiSelect();
        this.initializePerMultiSelect();
        this.initializeTeamMultiSelect(); // Initialize with just "All" option immediately
        this.setupEventListeners();
        this.setupModalEventListeners();
        this.renderTableHeaders();
        // Run both API calls in parallel for faster initial load
        await Promise.all([
            this.loadTeams(),
            this.loadPlayerStats()
        ]);
    }

    private initializeSeasonMultiSelect(): void {
        const seasonOptions: MultiSelectOption[] = [
            { value: 'career', label: 'All' },
            { value: 2025, label: '2025' },
            { value: 2024, label: '2024' },
            { value: 2023, label: '2023' },
            { value: 2022, label: '2022' },
            { value: 2021, label: '2021' },
            { value: 2019, label: '2019' },
            { value: 2018, label: '2018' },
            { value: 2017, label: '2017' },
            { value: 2016, label: '2016' },
            { value: 2015, label: '2015' },
            { value: 2014, label: '2014' },
            { value: 2013, label: '2013' },
            { value: 2012, label: '2012' }
        ];

        this.seasonMultiSelect = new MultiSelect({
            containerId: 'seasonFilter',
            options: seasonOptions,
            selectedValues: ['career'],  // Default to All
            placeholder: 'Select seasons...',
            allowSelectAll: false,  // Don't allow "Select All" when Career is an option
            searchable: false,
            exclusiveValues: ['career'],  // Career clears all other selections
            onChange: (selected) => this.handleSeasonChange(selected)
        });
    }

    private initializePerMultiSelect(): void {
        const perOptions: MultiSelectOption[] = [
            { value: 'total', label: 'Total' },
            { value: 'game', label: 'Per Game' },
            { value: 'possession', label: 'Per 100 Poss' }
        ];

        this.perMultiSelect = new MultiSelect({
            containerId: 'perFilter',
            options: perOptions,
            selectedValues: ['total'],  // Default to Total
            placeholder: 'Select...',
            allowSelectAll: false,
            searchable: false,
            exclusiveMode: true,  // Only one option can be selected at a time
            onChange: (selected) => this.handlePerChange(selected)
        });
    }

    private initializeTeamMultiSelect(): void {
        const teamOptions: MultiSelectOption[] = [
            { value: 'all', label: 'All' }
        ];

        // Add current teams
        const currentTeams = this.teams.filter(t => t.is_current);
        if (currentTeams.length > 0) {
            currentTeams.forEach(team => {
                teamOptions.push({
                    value: team.id,
                    label: team.name,
                    group: 'Current Teams'
                });
            });
        }

        // Add historical teams
        const historicalTeams = this.teams.filter(t => !t.is_current);
        if (historicalTeams.length > 0) {
            historicalTeams.forEach(team => {
                teamOptions.push({
                    value: team.id,
                    label: team.name,
                    group: 'Historical Teams'
                });
            });
        }

        // If teamMultiSelect already exists, update its options
        if (this.teamMultiSelect) {
            this.teamMultiSelect.updateOptions(teamOptions);
        } else {
            // Create new MultiSelect instance
            this.teamMultiSelect = new MultiSelect({
                containerId: 'teamFilter',
                options: teamOptions,
                selectedValues: ['all'],
                placeholder: 'Select teams...',
                allowSelectAll: true,
                searchable: true,
                exclusiveValues: ['all'],  // "All" clears all other selections
                onChange: (selected) => this.handleTeamChange(selected)
            });
        }
    }

    private handleSeasonChange(selected: (string | number)[]): void {
        // Update filters based on selection (exclusive logic handled in handleOptionChange)
        if (selected.includes('career')) {
            this.filters.season = ['career'];
            this.filters.careerMode = true;
        } else {
            this.filters.season = selected;
            this.filters.careerMode = false;
        }

        this.currentPage = 1;
        this.clearCache();
        this.renderTableHeaders();
        this.loadPlayerStats();
    }

    private handlePerChange(selected: (string | number)[]): void {
        // Update filters based on selection (exclusive mode - only one value)
        const value = selected[0] || 'total';
        this.filters.per = value as 'total' | 'game' | 'possession';

        this.currentPage = 1;
        this.clearCache();
        this.loadPlayerStats();
    }

    private handleTeamChange(selected: (string | number)[]): void {
        // Update filters based on selection (exclusive logic handled in handleOptionChange)
        if (selected.includes('all')) {
            this.filters.team = ['all'];
        } else {
            this.filters.team = selected.filter(v => v !== 'all') as string[];
        }

        this.currentPage = 1;
        this.clearCache();
        this.loadPlayerStats();
    }

    async loadTeams(): Promise<void> {
        try {
            // Use lightweight teams/dropdown endpoint instead of heavy /stats endpoint
            const teams = await window.ufaStats.fetchData<TeamInfo[]>('/teams/dropdown');
            if (teams && Array.isArray(teams)) {
                this.teams = teams;
                this.initializeTeamMultiSelect();
            }
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    // Removed old populateTeamFilter method - replaced by initializeTeamMultiSelect

    private clearCache(): void {
        this.cache.clear();
    }

    setupEventListeners(): void {
        // Removed old season, per, and team filter listeners - now handled by MultiSelect onChange

        // Table header click handlers for sorting
        const tableHeaders = document.getElementById('tableHeaders');
        if (tableHeaders) {
            tableHeaders.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                if (target.tagName === 'TH' && target.hasAttribute('data-sort')) {
                    const sortKey = target.getAttribute('data-sort')!;
                    this.currentSort = window.ufaStats.handleTableSort(
                        document.getElementById('playersTable')!,
                        sortKey,
                        this.currentSort
                    );
                    this.currentPage = 1;
                    this.loadPlayerStats();
                }
            });
        }
    }

    setupModalEventListeners(): void {
        const advancedFiltersBtn = document.getElementById('advancedFiltersBtn');
        const closeModalBtn = document.getElementById('closeModalBtn');
        const cancelFiltersBtn = document.getElementById('cancelFiltersBtn');
        const applyFiltersBtn = document.getElementById('applyFiltersBtn');
        const clearFiltersBtn = document.getElementById('clearFiltersBtn');
        const addFilterBtn = document.getElementById('addFilterBtn');
        const modal = document.getElementById('advancedFiltersModal');

        if (advancedFiltersBtn) {
            advancedFiltersBtn.addEventListener('click', () => this.openModal());
        }

        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => this.closeModal());
        }

        if (cancelFiltersBtn) {
            cancelFiltersBtn.addEventListener('click', () => this.closeModal());
        }

        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => this.applyFilters());
        }

        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => this.clearAllFilters());
        }

        if (addFilterBtn) {
            addFilterBtn.addEventListener('click', () => this.addFilterRow());
        }

        // Close modal when clicking on the modal background (not the content)
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const modal = document.getElementById('advancedFiltersModal');
                if (modal && !modal.classList.contains('hidden')) {
                    this.closeModal();
                }
            }
        });
    }

    openModal(): void {
        const modal = document.getElementById('advancedFiltersModal');
        if (modal) {
            modal.classList.remove('hidden');
            this.renderFilterRows();
        }
    }

    closeModal(): void {
        const modal = document.getElementById('advancedFiltersModal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    getAvailableFields(): FilterableField[] {
        const season = this.filters.season;

        // Filter fields based on season availability
        return FILTERABLE_FIELDS.filter(field => {
            if (!field.minYear) return true; // Available for all years

            // Check if season includes 'career' or 'all'
            if (season.includes('career') || season.includes('all')) return true;

            // For specific seasons, check if any selected season meets the minimum year
            const seasons = season.map(s => parseInt(String(s))).filter(y => !isNaN(y));
            return seasons.length === 0 || seasons.some(y => y >= (field.minYear || 0));
        });
    }

    renderFilterRows(): void {
        const filtersList = document.getElementById('filtersList');
        if (!filtersList) return;

        const availableFields = this.getAvailableFields();

        if (this.filters.customFilters.length === 0) {
            filtersList.innerHTML = '<div class="no-filters">No filters added yet. Click "Add Filter" to create one.</div>';
            return;
        }

        filtersList.innerHTML = this.filters.customFilters.map((filter, index) => {
            const fieldOptions = availableFields.map(field =>
                `<option value="${field.key}" ${filter.field === field.key ? 'selected' : ''}>${field.label}</option>`
            ).join('');

            return `
                <div class="filter-row" data-index="${index}">
                    <select class="field-select" data-index="${index}">
                        ${fieldOptions}
                    </select>
                    <select class="operator-select" data-index="${index}">
                        <option value=">" ${filter.operator === '>' ? 'selected' : ''}>&gt;</option>
                        <option value="<" ${filter.operator === '<' ? 'selected' : ''}>&lt;</option>
                        <option value=">=" ${filter.operator === '>=' ? 'selected' : ''}>&gt;=</option>
                        <option value="<=" ${filter.operator === '<=' ? 'selected' : ''}>&lt;=</option>
                        <option value="=" ${filter.operator === '=' ? 'selected' : ''}>=</option>
                    </select>
                    <input type="number" class="value-input" data-index="${index}" value="${filter.value}" step="any" />
                    <button class="remove-filter-btn" data-index="${index}" aria-label="Remove filter">
                        <span>&times;</span>
                    </button>
                </div>
            `;
        }).join('');

        // Add event listeners for filter row controls
        this.attachFilterRowListeners();
    }

    attachFilterRowListeners(): void {
        const filtersList = document.getElementById('filtersList');
        if (!filtersList) return;

        // Field select listeners
        filtersList.querySelectorAll('.field-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const index = parseInt((e.target as HTMLSelectElement).getAttribute('data-index')!);
                const value = (e.target as HTMLSelectElement).value;
                this.filters.customFilters[index].field = value;
            });
        });

        // Operator select listeners
        filtersList.querySelectorAll('.operator-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const index = parseInt((e.target as HTMLSelectElement).getAttribute('data-index')!);
                const value = (e.target as HTMLSelectElement).value as '>' | '<' | '>=' | '<=' | '=';
                this.filters.customFilters[index].operator = value;
            });
        });

        // Value input listeners
        filtersList.querySelectorAll('.value-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const index = parseInt((e.target as HTMLInputElement).getAttribute('data-index')!);
                const value = parseFloat((e.target as HTMLInputElement).value);
                this.filters.customFilters[index].value = value;
            });
        });

        // Remove button listeners
        filtersList.querySelectorAll('.remove-filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt((e.target as HTMLElement).closest('button')!.getAttribute('data-index')!);
                this.removeFilterRow(index);
            });
        });
    }

    addFilterRow(): void {
        const availableFields = this.getAvailableFields();
        if (availableFields.length === 0) {
            alert('No fields available for filtering in the selected season.');
            return;
        }

        // Add a new filter with default values
        this.filters.customFilters.push({
            field: availableFields[0].key,
            operator: '>=',
            value: 0
        });

        this.renderFilterRows();
    }

    removeFilterRow(index: number): void {
        this.filters.customFilters.splice(index, 1);
        this.renderFilterRows();
        this.updateFilterBadge();
    }

    applyFilters(): void {
        this.closeModal();
        this.updateFilterBadge();
        this.currentPage = 1; // Reset to first page
        this.loadPlayerStats();
    }

    clearAllFilters(): void {
        this.filters.customFilters = [];
        this.renderFilterRows();
        this.updateFilterBadge();
    }

    updateFilterBadge(): void {
        const badge = document.getElementById('filterCount');
        if (badge) {
            const count = this.filters.customFilters.length;
            badge.textContent = String(count);

            if (count > 0) {
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }

    getColumnsForSeason(season: (string | number)[] | string | number): PlayerColumn[] {
        // Handle array input by using the earliest numeric season for column filtering
        const effectiveSeason = Array.isArray(season)
            ? (season.includes('career') || season.includes('all')
                ? 'career'
                : Math.min(...season.map(s => parseInt(String(s))).filter(n => !isNaN(n))))
            : season;
        // Base columns available for all years
        const baseColumns: PlayerColumn[] = [
            { key: 'full_name', label: 'Player', sortable: true },
            { key: 'games_played', label: 'GP', sortable: true },
            { key: 'total_points_played', label: 'PP', sortable: true },
            { key: 'possessions', label: 'POS', sortable: true },
            { key: 'score_total', label: 'S', sortable: true },
            { key: 'total_assists', label: 'A', sortable: true },
            { key: 'total_goals', label: 'G', sortable: true },
            { key: 'total_blocks', label: 'B', sortable: true },
            { key: 'calculated_plus_minus', label: '+/-', sortable: true },
            { key: 'total_completions', label: 'C', sortable: true },
            { key: 'completion_percentage', label: 'C%', sortable: true }
        ];

        // Advanced stats added in 2021
        const advancedStats2021: PlayerColumn[] = [
            { key: 'total_yards', label: 'Y', sortable: true },
            { key: 'total_yards_thrown', label: 'TY', sortable: true },
            { key: 'total_yards_received', label: 'RY', sortable: true }
        ];

        // OEFF available for all years
        const oeffColumn: PlayerColumn[] = [{ key: 'offensive_efficiency', label: 'OEFF', sortable: true }];

        // Hockey assists available from 2014
        const hockeyAssistColumn: PlayerColumn[] = [{ key: 'total_hockey_assists', label: 'HA', sortable: true }];

        // Other base columns
        const otherBaseColumns: PlayerColumn[] = [
            { key: 'total_throwaways', label: 'T', sortable: true }
        ];

        // Y/T available from 2021 (when yards data exists)
        const yardsPerTurnColumn: PlayerColumn[] = [
            { key: 'yards_per_turn', label: 'Y/T', sortable: true }
        ];

        // TY/C and RY/R available from 2021 (when yards data exists)
        const yardsRatiosColumns: PlayerColumn[] = [
            { key: 'yards_per_completion', label: 'TY/C', sortable: true },
            { key: 'yards_per_reception', label: 'RY/R', sortable: true }
        ];

        // AST/T available for all years
        const assistTurnoverRatioColumn: PlayerColumn[] = [
            { key: 'assists_per_turnover', label: 'AST/T', sortable: true }
        ];

        // Rest of base columns
        const restBaseColumns: PlayerColumn[] = [
            { key: 'total_stalls', label: 'S', sortable: true },
            { key: 'total_drops', label: 'D', sortable: true },
            { key: 'total_callahans', label: 'CAL', sortable: true }
        ];

        // Huck stats available from 2021
        const huckStats2021: PlayerColumn[] = [
            { key: 'total_hucks_completed', label: 'H', sortable: true },
            { key: 'total_hucks_received', label: 'HR', sortable: true },
            { key: 'huck_percentage', label: 'H%', sortable: true }
        ];

        // Final columns
        const finalColumns: PlayerColumn[] = [
            { key: 'total_pulls', label: 'P', sortable: true },
            { key: 'total_o_points_played', label: 'OPP', sortable: true },
            { key: 'total_d_points_played', label: 'DPP', sortable: true },
            { key: 'minutes_played', label: 'MP', sortable: true }
        ];

        // Build column list based on season
        let columns = [...baseColumns];

        // For career stats or 2021+, show all columns
        if (effectiveSeason === 'career' || (effectiveSeason && parseInt(String(effectiveSeason)) >= 2021)) {
            columns.push(...advancedStats2021);
        }

        columns.push(...oeffColumn);

        // Hockey assists available from 2014
        if (effectiveSeason === 'career' || (effectiveSeason && parseInt(String(effectiveSeason)) >= 2014)) {
            columns.push(...hockeyAssistColumn);
        }

        columns.push(...otherBaseColumns);

        // AST/T available for all years - right after T (turnovers)
        columns.push(...assistTurnoverRatioColumn);

        // Y/T from 2021 (when yards data is available)
        if (effectiveSeason === 'career' || (effectiveSeason && parseInt(String(effectiveSeason)) >= 2021)) {
            columns.push(...yardsPerTurnColumn);
            columns.push(...yardsRatiosColumns);
        }

        columns.push(...restBaseColumns);

        // Huck stats from 2021
        if (effectiveSeason === 'career' || (effectiveSeason && parseInt(String(effectiveSeason)) >= 2021)) {
            columns.push(...huckStats2021);
        }

        columns.push(...finalColumns);

        return columns;
    }

    renderTableHeaders(): void {
        const headerRow = document.getElementById('tableHeaders');
        if (!headerRow) return;

        // Get columns based on current season filter
        const columns = this.getColumnsForSeason(this.filters.season);

        headerRow.innerHTML = '';
        columns.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col.label;
            // Use different class for Player column (left-aligned) vs numeric columns (center-aligned)
            th.className = col.key === 'full_name' ? 'player-name' : 'numeric';

            if (col.sortable) {
                th.setAttribute('data-sort', col.key);
                th.classList.add('sortable');

                if (this.currentSort.key === col.key) {
                    th.classList.add(this.currentSort.direction);
                }
            }

            headerRow.appendChild(th);
        });

        // Initialize tooltips for the headers
        setTimeout(() => {
            initializeTableTooltips('playersTable', playerColumnDescriptions);
        }, 0);
    }

    async loadPlayerStats(): Promise<void> {
        try {
            // Sort arrays for consistent cache keys
            const sortedSeasons = [...this.filters.season].sort();
            const sortedTeams = [...this.filters.team].sort();

            // Generate cache key with sorted arrays
            const cacheKey = JSON.stringify({
                season: sortedSeasons,
                team: sortedTeams,
                per: this.filters.per,
                customFilters: this.filters.customFilters,
                page: this.currentPage,
                per_page: this.pageSize,
                sort: this.currentSort.key,
                order: this.currentSort.direction
            });

            // Check cache (5 minute TTL)
            const cached = this.cache.get(cacheKey);
            if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
                this.players = cached.data.players || [];
                this.percentiles = cached.data.percentiles || {};
                this.totalPlayers = cached.data.total || 0;
                this.totalPages = cached.data.total_pages || cached.data.pages || 0;

                this.renderPlayersTable();
                this.renderPagination();
                this.updatePlayerCount();

                // Prefetch adjacent pages in background
                this.prefetchPages();
                return;
            }

            window.ufaStats.showLoading('#playersTableBody', 'Loading player statistics...');

            // Serialize arrays as comma-separated values for API
            const seasonParam = this.filters.careerMode ? 'career' : sortedSeasons.join(',');
            const teamParam = sortedTeams.includes('all') ? 'all' : sortedTeams.join(',');

            // Prepare query params
            const queryParams: any = {
                season: seasonParam,
                team: teamParam,
                per: this.filters.per,
                page: this.currentPage,
                per_page: this.pageSize,
                sort: this.currentSort.key,
                order: this.currentSort.direction,
                include_percentiles: true  // Include percentiles in single request
            };

            // Add custom filters if present
            if (this.filters.customFilters.length > 0) {
                queryParams.custom_filters = JSON.stringify(this.filters.customFilters);
            }

            // Fetch player stats with percentiles
            const response = await window.ufaStats.fetchData<PlayerStatsResponse>('/players/stats', queryParams);

            if (response) {
                this.players = response.players || [];
                this.percentiles = response.percentiles || {};
                this.totalPlayers = response.total || 0;
                this.totalPages = response.total_pages || 0;

                // Fallback: calculate totalPages if not provided
                if (!this.totalPages && this.totalPlayers > 0) {
                    this.totalPages = Math.ceil(this.totalPlayers / this.pageSize);
                }

                // Store in cache
                this.cache.set(cacheKey, {
                    data: response,
                    timestamp: Date.now()
                });
            } else {
                this.players = [];
                this.percentiles = {};
                this.totalPlayers = 0;
                this.totalPages = 0;
            }

            this.renderPlayersTable();
            this.renderPagination();
            this.updatePlayerCount();

            // Prefetch adjacent pages in background
            this.prefetchPages();

        } catch (error) {
            console.error('Failed to load player stats:', error);
            const tbody = document.getElementById('playersTableBody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="26" class="error">Failed to load player statistics</td></tr>';
            }
        }
    }

    getPercentile(playerName: string, statKey: string): number | null {
        if (!this.percentiles || !this.percentiles[playerName]) {
            return null;
        }
        return this.percentiles[playerName][statKey] ?? null;
    }

    formatCellWithPercentile(value: string, playerName: string, statKey: string): string {
        const percentile = this.getPercentile(playerName, statKey);
        if (percentile !== null && percentile !== undefined) {
            return `<div class="stat-cell"><div class="stat-value">${value}</div><div class="stat-percentile">${percentile}%</div></div>`;
        }
        return value;
    }

    renderPlayersTable(): void {
        const tbody = document.getElementById('playersTableBody');
        if (!tbody) return;

        if (this.players.length === 0) {
            tbody.innerHTML = '<tr><td colspan="26" class="no-data">No players found</td></tr>';
            return;
        }

        // Get columns for current season to match headers
        const columns = this.getColumnsForSeason(this.filters.season);

        tbody.innerHTML = this.players.map(player => {
            const playerName = player.player_name || `${player.first_name || ''} ${player.last_name || ''}`.trim();

            const cells = columns.map(col => {
                let value: number | string;
                let displayValue: string;

                switch (col.key) {
                    case 'full_name':
                        return `<td class="player-name">${playerName}</td>`;
                    case 'total_points_played':
                        value = player.total_points_played || 0;
                        displayValue = this.formatValue(value);
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'score_total':
                        value = player.score_total || 0;
                        displayValue = this.formatValue(value);
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'calculated_plus_minus':
                        displayValue = this.formatValue(player[col.key as keyof PlayerSeasonStats] || 0, false);
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'completion_percentage':
                        // Backend already returns this as a percentage value (e.g., 95.79)
                        const compPct = player[col.key as keyof PlayerSeasonStats] as number;
                        displayValue = compPct ? compPct.toFixed(1) : '-';
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'huck_percentage':
                        // Require minimum 10 huck attempts to display H%
                        const huckAttempts = (player as any).total_hucks_attempted || 0;
                        if (huckAttempts < 10) {
                            return `<td class="numeric">-</td>`;
                        }
                        const huckPct = player.huck_percentage || this.calculateHuckPercentage(player);
                        displayValue = huckPct ? huckPct.toFixed(1) : '-';
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'yards_per_turn':
                        const yPerTurn = player.yards_per_turn;
                        displayValue = yPerTurn !== null && yPerTurn !== undefined ? yPerTurn.toFixed(1) : '-';
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'yards_per_completion':
                        const yPerComp = player.yards_per_completion;
                        displayValue = yPerComp !== null && yPerComp !== undefined ? yPerComp.toFixed(1) : '-';
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'yards_per_reception':
                        const yPerRecep = player.yards_per_reception;
                        displayValue = yPerRecep !== null && yPerRecep !== undefined ? yPerRecep.toFixed(1) : '-';
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    case 'assists_per_turnover':
                        const astPerTO = player.assists_per_turnover;
                        displayValue = astPerTO !== null && astPerTO !== undefined ? astPerTO.toFixed(2) : '-';
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                    default:
                        const fieldValue = player[col.key as keyof PlayerSeasonStats];
                        displayValue = this.formatValue(fieldValue || 0);
                        return `<td class="numeric">${this.formatCellWithPercentile(displayValue, playerName, col.key)}</td>`;
                }
            });

            return `<tr>${cells.join('')}</tr>`;
        }).join('');
    }

    calculateHuckPercentage(player: PlayerSeasonStats): number {
        // Use the correct field names from the API response
        const attempted = player.hucks_attempted || 0;
        const completed = player.hucks_completed || 0;

        if (!attempted || attempted === 0) return 0;
        return (completed / attempted) * 100;
    }

    formatValue(value: any, showSign: boolean = false): string {
        if (value === null || value === undefined) return '-';
        const num = parseFloat(String(value));
        if (isNaN(num)) return '-';

        if (showSign && num > 0) {
            return `+${num}`;
        }
        return num.toString();
    }

    formatPercentage(value: number | null | undefined): string {
        // Use Format utility if available
        if (window.Format && window.Format.percentage) {
            return window.Format.percentage(value, 1);
        }
        if (value === null || value === undefined || isNaN(value)) return '-';
        return parseFloat(String(value)).toFixed(1);
    }

    renderPagination(): void {
        const container = document.getElementById('paginationContainer');
        if (!container) {
            console.error('Pagination container not found');
            return;
        }

        console.log('Rendering pagination:', {
            totalPages: this.totalPages,
            currentPage: this.currentPage,
            totalPlayers: this.totalPlayers
        });

        if (this.totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        const pagination = window.ufaStats.createPagination({
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            onPageChange: (page: number) => {
                this.currentPage = page;
                this.loadPlayerStats();
            }
        });

        container.innerHTML = '';
        container.appendChild(pagination);
    }

    updatePlayerCount(): void {
        const countElement = document.getElementById('playerCount');
        if (countElement) {
            countElement.textContent = window.Format ? window.Format.number(this.totalPlayers) : this.totalPlayers.toLocaleString();
        }
    }

    async prefetchPages(): Promise<void> {
        // Prefetch next and previous pages in the background
        const pagesToPrefetch = [];

        if (this.currentPage > 1) {
            pagesToPrefetch.push(this.currentPage - 1);
        }
        if (this.currentPage < this.totalPages) {
            pagesToPrefetch.push(this.currentPage + 1);
        }

        // Prefetch each page silently
        for (const page of pagesToPrefetch) {
            const cacheKey = JSON.stringify({
                season: this.filters.season,
                team: this.filters.team,
                per: this.filters.per,
                customFilters: this.filters.customFilters,
                page: page,
                per_page: this.pageSize,
                sort: this.currentSort.key,
                order: this.currentSort.direction
            });

            // Skip if already cached
            if (this.cache.has(cacheKey)) {
                continue;
            }

            // Prepare query params - explicitly skip percentiles for faster prefetch
            const queryParams: any = {
                season: this.filters.careerMode ? 'career' : [...this.filters.season].sort().join(','),
                team: this.filters.team.includes('all') ? 'all' : [...this.filters.team].sort().join(','),
                per: this.filters.per,
                page: page,
                per_page: this.pageSize,
                sort: this.currentSort.key,
                order: this.currentSort.direction,
                include_percentiles: false  // Skip percentiles for prefetch
            };

            // Add custom filters if present
            if (this.filters.customFilters.length > 0) {
                queryParams.custom_filters = JSON.stringify(this.filters.customFilters);
            }

            // Fetch in background without awaiting
            window.ufaStats.fetchData<PlayerStatsResponse>('/players/stats', queryParams).then(response => {
                if (response) {
                    this.cache.set(cacheKey, {
                        data: response,
                        timestamp: Date.now()
                    });
                }
            }).catch(err => {
                // Silently ignore prefetch errors
                console.debug('Prefetch failed:', err);
            });
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.ufaStats) {
        new PlayerStats();
    } else {
        // Wait for shared.js to load
        setTimeout(() => new PlayerStats(), 100);
    }
});

// Export for module usage
export { PlayerStats };
export default PlayerStats;