/**
 * Pass Plots Page - Visualizes pass events across games/seasons with filtering
 */

import { MultiSelect } from './components/multi-select';
import type {
    PassEvent,
    PassEventsStats,
    PassEventsResponse,
    FilterOptions,
    GraphType,
    FilterState
} from './pass-plots-types';
import {
    buildSeasonOptions,
    buildGameOptions,
    buildTeamOptions,
    buildPlayerOptions,
    preserveOrResetFilters,
    resetAllFilters,
    buildQueryParams,
    getDefaultFilterState
} from './pass-plots-filters';
import { renderThrowLines } from './pass-plots-field';
import { renderHeatmap } from './pass-plots-heatmap';

// Get API base URL from environment
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '';

export class PassPlots {
    private filterOptions: FilterOptions | null = null;
    private events: PassEvent[] = [];
    private stats: PassEventsStats | null = null;
    private graphType: GraphType = 'throw-lines';

    // MultiSelect instances
    private seasonSelect: MultiSelect | null = null;
    private gameSelect: MultiSelect | null = null;
    private offTeamSelect: MultiSelect | null = null;
    private defTeamSelect: MultiSelect | null = null;
    private throwerSelect: MultiSelect | null = null;
    private receiverSelect: MultiSelect | null = null;

    // Filter state
    private filterState: FilterState;

    // Debounce timer for slider changes
    private sliderDebounceTimer: ReturnType<typeof setTimeout> | null = null;

    constructor() {
        this.filterState = getDefaultFilterState();
        this.init();
    }

    private async init(): Promise<void> {
        await this.loadFilterOptions();

        // Default to latest season for faster initial load (instead of all 400k+ events)
        if (this.filterOptions && this.filterOptions.seasons.length > 0) {
            const latestSeason = this.filterOptions.seasons[0]; // Seasons are sorted descending
            this.filterState.season = latestSeason;
            // Reload filter options with season to get season-specific teams/players/games
            await this.loadFilterOptions({ season: latestSeason });
        }

        this.initializeFilters();
        this.attachEventListeners();
        await this.loadData();
    }

    private async loadFilterOptions(options?: { season?: number; team_id?: string; game_id?: string }): Promise<void> {
        try {
            const params = new URLSearchParams();
            if (options?.season) params.set('season', String(options.season));
            if (options?.team_id) params.set('team_id', options.team_id);
            if (options?.game_id) params.set('game_id', options.game_id);
            const queryString = params.toString();
            const response = await fetch(`${API_BASE_URL}/api/pass-events/filters${queryString ? '?' + queryString : ''}`);
            this.filterOptions = await response.json();
        } catch (error) {
            console.error('Failed to load filter options:', error);
        }
    }

    private initializeFilters(): void {
        if (!this.filterOptions) return;

        // Default to current season (set in init) or 'all' if not set
        // Keep as number to match option values (not string)
        const selectedSeason: string | number = this.filterState.season ?? 'all';

        this.seasonSelect = new MultiSelect({
            containerId: 'seasonFilter',
            options: buildSeasonOptions(this.filterOptions),
            selectedValues: [selectedSeason],
            placeholder: 'Select season...',
            allowSelectAll: false,
            exclusiveMode: true,
            exclusiveValues: ['all'],
            onChange: async (values) => {
                const season = values[0] === 'all' ? null : Number(values[0]);
                this.filterState.season = season;

                const savedOffTeamId = this.filterState.off_team_id;
                const savedDefTeamId = this.filterState.def_team_id;
                const savedThrowerId = this.filterState.thrower_id;
                const savedReceiverId = this.filterState.receiver_id;

                this.filterState.game_id = null;
                await this.loadFilterOptions({ season: season ?? undefined });

                if (this.filterOptions) {
                    preserveOrResetFilters(
                        this.filterOptions, this.filterState,
                        savedOffTeamId, savedDefTeamId, savedThrowerId, savedReceiverId
                    );
                }

                this.updateDependentFilters();
                this.loadData();
            }
        });

        this.updateGameSelect();
        this.updateTeamSelects();
        this.updatePlayerSelects();
    }

    private updateGameSelect(): void {
        if (!this.filterOptions) return;

        const options = buildGameOptions(this.filterOptions);

        if (this.gameSelect) {
            this.gameSelect.updateOptions(options);
            this.gameSelect.setSelected([this.filterState.game_id ?? 'all']);
        } else {
            this.gameSelect = new MultiSelect({
                containerId: 'gameFilter',
                options,
                selectedValues: ['all'],
                placeholder: 'Select game...',
                allowSelectAll: false,
                exclusiveMode: true,
                exclusiveValues: ['all'],
                onChange: async (values) => {
                    this.filterState.game_id = values[0] === 'all' ? null : String(values[0]);
                    this.filterState.thrower_id = null;
                    this.filterState.receiver_id = null;
                    await this.loadFilterOptions({
                        season: this.filterState.season ?? undefined,
                        team_id: this.filterState.off_team_id ?? undefined,
                        game_id: this.filterState.game_id ?? undefined
                    });
                    this.updateTeamSelects();
                    this.updatePlayerSelects();
                    this.loadData();
                }
            });
        }
    }

    private updateTeamSelects(): void {
        if (!this.filterOptions) return;

        const options = buildTeamOptions(this.filterOptions);

        if (this.offTeamSelect) {
            this.offTeamSelect.updateOptions(options);
            this.offTeamSelect.setSelected([this.filterState.off_team_id ?? 'all']);
        } else {
            this.offTeamSelect = new MultiSelect({
                containerId: 'offTeamFilter',
                options,
                selectedValues: ['all'],
                placeholder: 'Select team...',
                allowSelectAll: false,
                exclusiveMode: true,
                exclusiveValues: ['all'],
                onChange: async (values) => {
                    this.filterState.off_team_id = values[0] === 'all' ? null : String(values[0]);
                    this.filterState.thrower_id = null;
                    this.filterState.receiver_id = null;
                    await this.loadFilterOptions({
                        season: this.filterState.season ?? undefined,
                        team_id: this.filterState.off_team_id ?? undefined,
                        game_id: this.filterState.game_id ?? undefined
                    });
                    this.updateGameSelect();
                    this.updatePlayerSelects();
                    this.loadData();
                }
            });
        }

        if (this.defTeamSelect) {
            this.defTeamSelect.updateOptions(options);
            this.defTeamSelect.setSelected([this.filterState.def_team_id ?? 'all']);
        } else {
            this.defTeamSelect = new MultiSelect({
                containerId: 'defTeamFilter',
                options,
                selectedValues: ['all'],
                placeholder: 'Select team...',
                allowSelectAll: false,
                exclusiveMode: true,
                exclusiveValues: ['all'],
                onChange: (values) => {
                    this.filterState.def_team_id = values[0] === 'all' ? null : String(values[0]);
                    this.loadData();
                }
            });
        }
    }

    private updatePlayerSelects(): void {
        if (!this.filterOptions) return;

        const options = buildPlayerOptions(this.filterOptions);

        if (this.throwerSelect) {
            this.throwerSelect.updateOptions(options);
            this.throwerSelect.setSelected([this.filterState.thrower_id ?? 'all']);
        } else {
            this.throwerSelect = new MultiSelect({
                containerId: 'throwerFilter',
                options,
                selectedValues: ['all'],
                placeholder: 'Select player...',
                allowSelectAll: false,
                exclusiveMode: true,
                exclusiveValues: ['all'],
                onChange: (values) => {
                    this.filterState.thrower_id = values[0] === 'all' ? null : String(values[0]);
                    this.loadData();
                }
            });
        }

        if (this.receiverSelect) {
            this.receiverSelect.updateOptions(options);
            this.receiverSelect.setSelected([this.filterState.receiver_id ?? 'all']);
        } else {
            this.receiverSelect = new MultiSelect({
                containerId: 'receiverFilter',
                options,
                selectedValues: ['all'],
                placeholder: 'Select player...',
                allowSelectAll: false,
                exclusiveMode: true,
                exclusiveValues: ['all'],
                onChange: (values) => {
                    this.filterState.receiver_id = values[0] === 'all' ? null : String(values[0]);
                    this.loadData();
                }
            });
        }
    }

    private updateDependentFilters(): void {
        this.updateGameSelect();
        this.updateTeamSelects();
        this.updatePlayerSelects();
    }

    private attachEventListeners(): void {
        // Graph type toggle
        document.querySelectorAll('input[name="graphType"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const target = e.target as HTMLInputElement;
                this.graphType = target.value as GraphType;
                this.renderVisualization();
            });
        });

        // Event type checkboxes
        document.querySelectorAll('[data-filter="eventType"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const eventType = input.dataset.value!;
                if (input.checked) {
                    this.filterState.event_types.add(eventType);
                } else {
                    this.filterState.event_types.delete(eventType);
                }
                this.loadData();
            });
        });

        // Event type select all/deselect all
        document.querySelectorAll('[data-filter="eventTypes"].select-all-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                ['throws', 'catches', 'assists', 'goals', 'throwaways', 'drops'].forEach(et => {
                    this.filterState.event_types.add(et);
                    const checkbox = document.querySelector(`[data-filter="eventType"][data-value="${et}"]`) as HTMLInputElement;
                    if (checkbox) checkbox.checked = true;
                });
                this.loadData();
            });
        });

        document.querySelectorAll('[data-filter="eventTypes"].deselect-all-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.filterState.event_types.clear();
                document.querySelectorAll('[data-filter="eventType"]').forEach(checkbox => {
                    (checkbox as HTMLInputElement).checked = false;
                });
                this.loadData();
            });
        });

        // Quarter checkboxes
        document.querySelectorAll('[data-filter="quarter"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const quarter = parseInt(input.dataset.value!);
                if (input.checked) {
                    this.filterState.quarters.add(quarter);
                } else {
                    this.filterState.quarters.delete(quarter);
                }
                this.loadData();
            });
        });

        // Quarter select all/deselect all
        document.querySelectorAll('[data-filter="quarters"].select-all-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                [1, 2, 3, 4, 5].forEach(q => {
                    this.filterState.quarters.add(q);
                    const checkbox = document.querySelector(`[data-filter="quarter"][data-value="${q}"]`) as HTMLInputElement;
                    if (checkbox) checkbox.checked = true;
                });
                this.loadData();
            });
        });

        document.querySelectorAll('[data-filter="quarters"].deselect-all-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.filterState.quarters.clear();
                document.querySelectorAll('[data-filter="quarter"]').forEach(checkbox => {
                    (checkbox as HTMLInputElement).checked = false;
                });
                this.loadData();
            });
        });

        // Pass type checkboxes
        ['Huck', 'Swing', 'Dump', 'Gainer', 'Dish'].forEach(type => {
            const checkbox = document.getElementById(`type${type}`) as HTMLInputElement;
            if (checkbox) {
                checkbox.addEventListener('change', () => {
                    if (checkbox.checked) {
                        this.filterState.pass_types.add(type.toLowerCase());
                    } else {
                        this.filterState.pass_types.delete(type.toLowerCase());
                    }
                    this.loadData();
                });
            }
        });

        // Range sliders
        this.setupRangeSlider('originY', (min, max) => {
            this.filterState.origin_y_min = min;
            this.filterState.origin_y_max = max;
        });
        this.setupRangeSlider('originX', (min, max) => {
            this.filterState.origin_x_min = min;
            this.filterState.origin_x_max = max;
        });
        this.setupRangeSlider('destY', (min, max) => {
            this.filterState.dest_y_min = min;
            this.filterState.dest_y_max = max;
        });
        this.setupRangeSlider('destX', (min, max) => {
            this.filterState.dest_x_min = min;
            this.filterState.dest_x_max = max;
        });
        this.setupRangeSlider('distance', (min, max) => {
            this.filterState.distance_min = min;
            this.filterState.distance_max = max;
        });

        // Reset button
        const resetBtn = document.getElementById('resetFilters');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetFilters());
        }
    }

    private setupRangeSlider(id: string, onChange: (min: number, max: number) => void): void {
        const minInput = document.getElementById(`${id}Min`) as HTMLInputElement;
        const maxInput = document.getElementById(`${id}Max`) as HTMLInputElement;
        const minVal = document.getElementById(`${id}MinVal`);
        const maxVal = document.getElementById(`${id}MaxVal`);

        if (!minInput || !maxInput) return;

        const updateValues = () => {
            const minValue = parseInt(minInput.value);
            const maxValue = parseInt(maxInput.value);

            if (minValue > maxValue) {
                minInput.value = maxInput.value;
            }

            if (minVal) minVal.textContent = minInput.value;
            if (maxVal) maxVal.textContent = maxInput.value;

            onChange(parseInt(minInput.value), parseInt(maxInput.value));

            if (this.sliderDebounceTimer) {
                clearTimeout(this.sliderDebounceTimer);
            }
            this.sliderDebounceTimer = setTimeout(() => {
                this.loadData();
            }, 300);
        };

        minInput.addEventListener('input', updateValues);
        maxInput.addEventListener('input', updateValues);
    }

    private resetFilters(): void {
        this.filterState = getDefaultFilterState();
        resetAllFilters({
            seasonSelect: this.seasonSelect,
            gameSelect: this.gameSelect,
            offTeamSelect: this.offTeamSelect,
            defTeamSelect: this.defTeamSelect,
            throwerSelect: this.throwerSelect,
            receiverSelect: this.receiverSelect
        });
        this.loadData();
    }

    private async loadData(): Promise<void> {
        this.showLoading(true);

        try {
            const params = buildQueryParams(this.filterState);
            const response = await fetch(`${API_BASE_URL}/api/pass-events?${params}`);
            const data: PassEventsResponse = await response.json();

            this.events = data.events;
            this.stats = data.stats;

            this.updateEventCount();
            this.updateStatsPanel();
            this.renderVisualization();
        } catch (error) {
            console.error('Failed to load pass events:', error);
        } finally {
            this.showLoading(false);
        }
    }

    private showLoading(show: boolean): void {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.toggle('hidden', !show);
        }
    }

    private updateEventCount(): void {
        const countEl = document.getElementById('eventCount');
        if (countEl) {
            countEl.textContent = `${this.events.length.toLocaleString()} throws`;
        }
    }

    private updateStatsPanel(): void {
        if (!this.stats) return;

        this.setStatValue('statTotalThrows', this.stats.total_throws.toLocaleString());
        this.setStatValue('statCompletions',
            `${this.stats.completions.toLocaleString()} <small>(${this.stats.completions_pct}%)</small>`);
        this.setStatValue('statTurnovers',
            `${this.stats.turnovers.toLocaleString()} <small>(${this.stats.turnovers_pct}%)</small>`);
        this.setStatValue('statGoals',
            `${this.stats.goals.toLocaleString()} <small>(${this.stats.goals_pct}%)</small>`);
        this.setStatValue('statAvgYards', String(this.stats.avg_yards_per_throw));
        this.setStatValue('statAvgYardsCompletion', String(this.stats.avg_yards_per_completion));

        const types = ['huck', 'swing', 'dump', 'gainer', 'dish'];
        const typeLabels: Record<string, string> = {
            huck: 'Hucks', swing: 'Swings', dump: 'Dumps', gainer: 'Gainers', dish: 'Dishes'
        };

        types.forEach(type => {
            const typeData = this.stats!.by_type[type] || { count: 0, pct: 0 };
            const label = typeLabels[type];
            this.setStatValue(`stat${label}`,
                `${typeData.count.toLocaleString()} <small>(${typeData.pct}%)</small>`);
        });
    }

    private setStatValue(id: string, value: string): void {
        const el = document.getElementById(id);
        if (el) el.innerHTML = value;
    }

    private renderVisualization(): void {
        const container = document.getElementById('fieldContainer');
        if (!container) return;

        const overlay = container.querySelector('.loading-overlay');
        container.innerHTML = '';
        if (overlay) container.appendChild(overlay);

        if (this.graphType === 'throw-lines') {
            renderThrowLines(container, this.events);
        } else {
            renderHeatmap(container, this.events, this.graphType === 'origin-heatmap' ? 'origin' : 'dest');
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new PassPlots();
});
