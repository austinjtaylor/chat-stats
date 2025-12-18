/**
 * Pass Plots Page - Visualizes pass events across games/seasons with filtering
 */

import { MultiSelect } from './components/multi-select';
import type { MultiSelectOption } from './components/multi-select';

// API response interfaces
interface PassEvent {
    game_id: string;
    event_type: number;
    pass_type: string | null;
    thrower_id: string;
    thrower_name: string;
    receiver_id: string;
    receiver_name: string;
    thrower_x: number;
    thrower_y: number;
    receiver_x: number | null;
    receiver_y: number | null;
    turnover_x: number | null;
    turnover_y: number | null;
    result: 'goal' | 'completion' | 'turnover';
    vertical_yards: number | null;
    horizontal_yards: number | null;
    distance: number | null;
    year: number;
}

interface PassEventsStats {
    total_throws: number;
    completions: number;
    completions_pct: number;
    turnovers: number;
    turnovers_pct: number;
    goals: number;
    goals_pct: number;
    total_yards: number;
    completion_yards: number;
    avg_yards_per_throw: number;
    avg_yards_per_completion: number;
    by_type: Record<string, { count: number; pct: number }>;
}

interface PassEventsResponse {
    events: PassEvent[];
    stats: PassEventsStats;
    total: number;
}

interface FilterOptions {
    seasons: number[];
    teams: Array<{ team_id: string; name: string; abbrev: string }>;
    players: Array<{ player_id: string; name: string }>;
    games: Array<{ game_id: string; label: string; year: number; week: number }>;
}

type GraphType = 'throw-lines' | 'origin-heatmap' | 'dest-heatmap';

interface FilterState {
    season: number | null;
    game_id: string | null;
    off_team_id: string | null;
    def_team_id: string | null;
    thrower_id: string | null;
    receiver_id: string | null;
    results: Set<string>;
    pass_types: Set<string>;
    origin_x_min: number;
    origin_x_max: number;
    origin_y_min: number;
    origin_y_max: number;
    dest_x_min: number;
    dest_x_max: number;
    dest_y_min: number;
    dest_y_max: number;
    distance_min: number;
    distance_max: number;
}

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
        this.filterState = this.getDefaultFilterState();
        this.init();
    }

    private getDefaultFilterState(): FilterState {
        return {
            season: null,
            game_id: null,
            off_team_id: null,
            def_team_id: null,
            thrower_id: null,
            receiver_id: null,
            results: new Set(['goal', 'completion', 'turnover']),
            pass_types: new Set(['huck', 'swing', 'dump', 'gainer', 'dish']),
            origin_x_min: -27,
            origin_x_max: 27,
            origin_y_min: 0,
            origin_y_max: 120,
            dest_x_min: -27,
            dest_x_max: 27,
            dest_y_min: 0,
            dest_y_max: 120,
            distance_min: 0,
            distance_max: 100
        };
    }

    private async init(): Promise<void> {
        await this.loadFilterOptions();
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
            const response = await fetch(`/api/pass-events/filters${queryString ? '?' + queryString : ''}`);
            this.filterOptions = await response.json();
        } catch (error) {
            console.error('Failed to load filter options:', error);
        }
    }

    private initializeFilters(): void {
        if (!this.filterOptions) return;

        // Season filter
        const seasonOptions: MultiSelectOption[] = [
            { value: 'all', label: 'All Seasons' },
            ...this.filterOptions.seasons.map(s => ({ value: s, label: String(s) }))
        ];

        this.seasonSelect = new MultiSelect({
            containerId: 'seasonFilter',
            options: seasonOptions,
            selectedValues: ['all'],
            placeholder: 'Select season...',
            allowSelectAll: false,
            exclusiveMode: true,
            exclusiveValues: ['all'],
            onChange: async (values) => {
                const season = values[0] === 'all' ? null : Number(values[0]);
                this.filterState.season = season;

                // Save current selections before reloading options
                const savedOffTeamId = this.filterState.off_team_id;
                const savedDefTeamId = this.filterState.def_team_id;
                const savedThrowerId = this.filterState.thrower_id;
                const savedReceiverId = this.filterState.receiver_id;

                // Reset game (games are season-specific)
                this.filterState.game_id = null;

                // Reload filter options for the selected season
                await this.loadFilterOptions({ season: season ?? undefined });

                // Preserve team/player selections if they exist in new options
                this.preserveOrResetFilters(savedOffTeamId, savedDefTeamId, savedThrowerId, savedReceiverId);

                this.updateDependentFilters();
                this.loadData();
            }
        });

        // Game filter
        this.updateGameSelect();

        // Team filters
        this.updateTeamSelects();

        // Player filters
        this.updatePlayerSelects();
    }

    private updateGameSelect(): void {
        if (!this.filterOptions) return;

        const gameOptions: MultiSelectOption[] = [
            { value: 'all', label: 'All Games' },
            ...this.filterOptions.games.map(g => ({
                value: g.game_id,
                label: `${g.label} (Wk ${g.week})`
            }))
        ];

        if (this.gameSelect) {
            this.gameSelect.updateOptions(gameOptions);
            // Sync visual state with filterState
            this.gameSelect.setSelected([this.filterState.game_id ?? 'all']);
        } else {
            this.gameSelect = new MultiSelect({
                containerId: 'gameFilter',
                options: gameOptions,
                selectedValues: ['all'],
                placeholder: 'Select game...',
                allowSelectAll: false,
                exclusiveMode: true,
                exclusiveValues: ['all'],
                onChange: async (values) => {
                    this.filterState.game_id = values[0] === 'all' ? null : String(values[0]);
                    // Reset player filters when game changes
                    this.filterState.thrower_id = null;
                    this.filterState.receiver_id = null;
                    // Reload player options for the selected game
                    await this.loadFilterOptions({
                        season: this.filterState.season ?? undefined,
                        team_id: this.filterState.off_team_id ?? undefined,
                        game_id: this.filterState.game_id ?? undefined
                    });
                    this.updatePlayerSelects();
                    this.loadData();
                }
            });
        }
    }

    private updateTeamSelects(): void {
        if (!this.filterOptions) return;

        const teamOptions: MultiSelectOption[] = [
            { value: 'all', label: 'All Teams' },
            ...this.filterOptions.teams.map(t => ({
                value: t.team_id,
                label: t.name
            }))
        ];

        if (this.offTeamSelect) {
            this.offTeamSelect.updateOptions(teamOptions);
            // Sync visual state with filterState
            this.offTeamSelect.setSelected([this.filterState.off_team_id ?? 'all']);
        } else {
            this.offTeamSelect = new MultiSelect({
                containerId: 'offTeamFilter',
                options: teamOptions,
                selectedValues: ['all'],
                placeholder: 'Select team...',
                allowSelectAll: false,
                exclusiveMode: true,
                exclusiveValues: ['all'],
                onChange: async (values) => {
                    this.filterState.off_team_id = values[0] === 'all' ? null : String(values[0]);
                    // Reset player filters when team changes
                    this.filterState.thrower_id = null;
                    this.filterState.receiver_id = null;
                    // Reload options for the selected team
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
            this.defTeamSelect.updateOptions(teamOptions);
            // Sync visual state with filterState
            this.defTeamSelect.setSelected([this.filterState.def_team_id ?? 'all']);
        } else {
            this.defTeamSelect = new MultiSelect({
                containerId: 'defTeamFilter',
                options: teamOptions,
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

        const playerOptions: MultiSelectOption[] = [
            { value: 'all', label: 'All Players' },
            ...this.filterOptions.players.map(p => ({
                value: p.player_id,
                label: p.name
            }))
        ];

        if (this.throwerSelect) {
            this.throwerSelect.updateOptions(playerOptions);
            // Sync visual state with filterState
            this.throwerSelect.setSelected([this.filterState.thrower_id ?? 'all']);
        } else {
            this.throwerSelect = new MultiSelect({
                containerId: 'throwerFilter',
                options: playerOptions,
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
            this.receiverSelect.updateOptions(playerOptions);
            // Sync visual state with filterState
            this.receiverSelect.setSelected([this.filterState.receiver_id ?? 'all']);
        } else {
            this.receiverSelect = new MultiSelect({
                containerId: 'receiverFilter',
                options: playerOptions,
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

    private preserveOrResetFilters(
        offTeamId: string | null,
        defTeamId: string | null,
        throwerId: string | null,
        receiverId: string | null
    ): void {
        if (!this.filterOptions) return;

        // Check if offensive team exists in new options
        const offTeamExists = offTeamId && this.filterOptions.teams.some(t => t.team_id === offTeamId);
        this.filterState.off_team_id = offTeamExists ? offTeamId : null;

        // Check if defensive team exists in new options
        const defTeamExists = defTeamId && this.filterOptions.teams.some(t => t.team_id === defTeamId);
        this.filterState.def_team_id = defTeamExists ? defTeamId : null;

        // Check if thrower exists in new options
        const throwerExists = throwerId && this.filterOptions.players.some(p => p.player_id === throwerId);
        this.filterState.thrower_id = throwerExists ? throwerId : null;

        // Check if receiver exists in new options
        const receiverExists = receiverId && this.filterOptions.players.some(p => p.player_id === receiverId);
        this.filterState.receiver_id = receiverExists ? receiverId : null;
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

        // Result checkboxes
        ['Goal', 'Completion', 'Turnover'].forEach(result => {
            const checkbox = document.getElementById(`result${result}`) as HTMLInputElement;
            if (checkbox) {
                checkbox.addEventListener('change', () => {
                    if (checkbox.checked) {
                        this.filterState.results.add(result.toLowerCase());
                    } else {
                        this.filterState.results.delete(result.toLowerCase());
                    }
                    this.loadData();
                });
            }
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
        this.setupRangeSlider('originY', 0, 120, (min, max) => {
            this.filterState.origin_y_min = min;
            this.filterState.origin_y_max = max;
        });
        this.setupRangeSlider('originX', -27, 27, (min, max) => {
            this.filterState.origin_x_min = min;
            this.filterState.origin_x_max = max;
        });
        this.setupRangeSlider('destY', 0, 120, (min, max) => {
            this.filterState.dest_y_min = min;
            this.filterState.dest_y_max = max;
        });
        this.setupRangeSlider('destX', -27, 27, (min, max) => {
            this.filterState.dest_x_min = min;
            this.filterState.dest_x_max = max;
        });
        this.setupRangeSlider('distance', 0, 100, (min, max) => {
            this.filterState.distance_min = min;
            this.filterState.distance_max = max;
        });

        // Reset button
        const resetBtn = document.getElementById('resetFilters');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetFilters());
        }
    }

    private setupRangeSlider(
        id: string,
        _min: number,
        _max: number,
        onChange: (min: number, max: number) => void
    ): void {
        const minInput = document.getElementById(`${id}Min`) as HTMLInputElement;
        const maxInput = document.getElementById(`${id}Max`) as HTMLInputElement;
        const minVal = document.getElementById(`${id}MinVal`);
        const maxVal = document.getElementById(`${id}MaxVal`);

        if (!minInput || !maxInput) return;

        const updateValues = () => {
            const minValue = parseInt(minInput.value);
            const maxValue = parseInt(maxInput.value);

            // Ensure min doesn't exceed max
            if (minValue > maxValue) {
                minInput.value = maxInput.value;
            }

            if (minVal) minVal.textContent = minInput.value;
            if (maxVal) maxVal.textContent = maxInput.value;

            onChange(parseInt(minInput.value), parseInt(maxInput.value));

            // Debounced loadData call
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
        this.filterState = this.getDefaultFilterState();

        // Reset selects
        this.seasonSelect?.setSelected(['all']);
        this.gameSelect?.setSelected(['all']);
        this.offTeamSelect?.setSelected(['all']);
        this.defTeamSelect?.setSelected(['all']);
        this.throwerSelect?.setSelected(['all']);
        this.receiverSelect?.setSelected(['all']);

        // Reset checkboxes
        ['Goal', 'Completion', 'Turnover'].forEach(result => {
            const checkbox = document.getElementById(`result${result}`) as HTMLInputElement;
            if (checkbox) checkbox.checked = true;
        });
        ['Huck', 'Swing', 'Dump', 'Gainer', 'Dish'].forEach(type => {
            const checkbox = document.getElementById(`type${type}`) as HTMLInputElement;
            if (checkbox) checkbox.checked = true;
        });

        // Reset sliders
        this.resetSlider('originY', 0, 120);
        this.resetSlider('originX', -27, 27);
        this.resetSlider('destY', 0, 120);
        this.resetSlider('destX', -27, 27);
        this.resetSlider('distance', 0, 100);

        this.loadData();
    }

    private resetSlider(id: string, min: number, max: number): void {
        const minInput = document.getElementById(`${id}Min`) as HTMLInputElement;
        const maxInput = document.getElementById(`${id}Max`) as HTMLInputElement;
        const minVal = document.getElementById(`${id}MinVal`);
        const maxVal = document.getElementById(`${id}MaxVal`);

        if (minInput) minInput.value = String(min);
        if (maxInput) maxInput.value = String(max);
        if (minVal) minVal.textContent = String(min);
        if (maxVal) maxVal.textContent = String(max);
    }

    private async loadData(): Promise<void> {
        this.showLoading(true);

        try {
            const params = this.buildQueryParams();
            const response = await fetch(`/api/pass-events?${params}`);
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

    private buildQueryParams(): string {
        const params = new URLSearchParams();

        if (this.filterState.season) {
            params.set('season', String(this.filterState.season));
        }
        if (this.filterState.game_id) {
            params.set('game_id', this.filterState.game_id);
        }
        if (this.filterState.off_team_id) {
            params.set('off_team_id', this.filterState.off_team_id);
        }
        if (this.filterState.def_team_id) {
            params.set('def_team_id', this.filterState.def_team_id);
        }
        if (this.filterState.thrower_id) {
            params.set('thrower_id', this.filterState.thrower_id);
        }
        if (this.filterState.receiver_id) {
            params.set('receiver_id', this.filterState.receiver_id);
        }

        // Results filter
        if (this.filterState.results.size > 0 && this.filterState.results.size < 3) {
            params.set('results', Array.from(this.filterState.results).join(','));
        }

        // Pass types filter
        if (this.filterState.pass_types.size > 0 && this.filterState.pass_types.size < 5) {
            params.set('pass_types', Array.from(this.filterState.pass_types).join(','));
        }

        // Coordinate filters (only add if not default)
        if (this.filterState.origin_y_min > 0) {
            params.set('origin_y_min', String(this.filterState.origin_y_min));
        }
        if (this.filterState.origin_y_max < 120) {
            params.set('origin_y_max', String(this.filterState.origin_y_max));
        }
        if (this.filterState.origin_x_min > -27) {
            params.set('origin_x_min', String(this.filterState.origin_x_min));
        }
        if (this.filterState.origin_x_max < 27) {
            params.set('origin_x_max', String(this.filterState.origin_x_max));
        }
        if (this.filterState.dest_y_min > 0) {
            params.set('dest_y_min', String(this.filterState.dest_y_min));
        }
        if (this.filterState.dest_y_max < 120) {
            params.set('dest_y_max', String(this.filterState.dest_y_max));
        }
        if (this.filterState.dest_x_min > -27) {
            params.set('dest_x_min', String(this.filterState.dest_x_min));
        }
        if (this.filterState.dest_x_max < 27) {
            params.set('dest_x_max', String(this.filterState.dest_x_max));
        }
        if (this.filterState.distance_min > 0) {
            params.set('distance_min', String(this.filterState.distance_min));
        }
        if (this.filterState.distance_max < 100) {
            params.set('distance_max', String(this.filterState.distance_max));
        }

        return params.toString();
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

        // Main stats
        this.setStatValue('statTotalThrows', this.stats.total_throws.toLocaleString());
        this.setStatValue('statCompletions',
            `${this.stats.completions.toLocaleString()} <small>(${this.stats.completions_pct}%)</small>`);
        this.setStatValue('statTurnovers',
            `${this.stats.turnovers.toLocaleString()} <small>(${this.stats.turnovers_pct}%)</small>`);
        this.setStatValue('statGoals',
            `${this.stats.goals.toLocaleString()} <small>(${this.stats.goals_pct}%)</small>`);
        this.setStatValue('statAvgYards', String(this.stats.avg_yards_per_throw));
        this.setStatValue('statAvgYardsCompletion', String(this.stats.avg_yards_per_completion));

        // By type stats
        const types = ['huck', 'swing', 'dump', 'gainer', 'dish'];
        const typeLabels: Record<string, string> = {
            huck: 'Hucks',
            swing: 'Swings',
            dump: 'Dumps',
            gainer: 'Gainers',
            dish: 'Dishes'
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

        // Clear existing content (except loading overlay)
        const overlay = container.querySelector('.loading-overlay');
        container.innerHTML = '';
        if (overlay) container.appendChild(overlay);

        if (this.graphType === 'throw-lines') {
            this.renderThrowLines(container);
        } else {
            this.renderHeatmap(container, this.graphType === 'origin-heatmap' ? 'origin' : 'dest');
        }
    }

    private renderThrowLines(container: HTMLElement): void {
        const svg = this.createFieldSVG();
        const eventsGroup = svg.querySelector('#fieldEventsLayer');

        if (eventsGroup) {
            this.events.forEach(event => {
                const element = this.createEventElement(event);
                if (element) {
                    eventsGroup.appendChild(element);
                }
            });
        }

        container.appendChild(svg);
    }

    private createFieldSVG(): SVGSVGElement {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 533 1200');
        svg.classList.add('field-map-svg');
        svg.style.maxWidth = '400px';
        svg.style.height = 'auto';

        svg.innerHTML = `
            <!-- Field background -->
            <rect class="field-grass" x="0" y="0" width="533" height="1200"/>

            <!-- North Endzone (100-120 yards) -->
            <rect class="field-endzone" x="0" y="0" width="533" height="200"/>

            <!-- South Endzone (0-20 yards) -->
            <rect class="field-endzone" x="0" y="1000" width="533" height="200"/>

            <!-- Yard lines -->
            <g class="field-yard-lines">
                ${this.renderYardLines()}
            </g>

            <!-- Yard numbers -->
            <g class="field-yard-numbers">
                ${this.renderYardNumbers()}
            </g>

            <!-- Events layer -->
            <g class="field-events" id="fieldEventsLayer"></g>
        `;

        return svg;
    }

    private renderYardLines(): string {
        const lines: string[] = [];
        for (let yard = 20; yard <= 100; yard += 5) {
            const y = this.fieldYToSVG(yard);
            lines.push(`<line x1="0" y1="${y}" x2="533" y2="${y}"/>`);
        }
        return lines.join('');
    }

    private renderYardNumbers(): string {
        const numbers: string[] = [];
        for (let yard = 30; yard <= 90; yard += 10) {
            const y = this.fieldYToSVG(yard) + 8;
            const displayYard = yard <= 50 ? yard : 100 - yard;
            numbers.push(`<text x="20" y="${y}">${displayYard}</text>`);
            numbers.push(`<text x="513" y="${y}" text-anchor="end">${displayYard}</text>`);
        }
        return numbers.join('');
    }

    private fieldYToSVG(fieldY: number): number {
        return (120 - fieldY) * 10;
    }

    private fieldXToSVG(fieldX: number): number {
        return (fieldX * 10) + 266.5;
    }

    private createEventElement(event: PassEvent): SVGGElement | null {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.classList.add('field-event');

        const color = this.getEventColor(event.result);

        let startX = event.thrower_x;
        let startY = event.thrower_y;
        let endX = event.receiver_x ?? event.turnover_x;
        let endY = event.receiver_y ?? event.turnover_y;

        if (startX === null || startY === null || endX === null || endY === null) {
            return null;
        }

        // Draw line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', String(this.fieldXToSVG(startX)));
        line.setAttribute('y1', String(this.fieldYToSVG(startY)));
        line.setAttribute('x2', String(this.fieldXToSVG(endX)));
        line.setAttribute('y2', String(this.fieldYToSVG(endY)));
        line.setAttribute('stroke', color);
        line.setAttribute('stroke-width', '2');
        line.setAttribute('stroke-opacity', '0.5');
        g.appendChild(line);

        // Draw end marker
        const svgX = this.fieldXToSVG(endX);
        const svgY = this.fieldYToSVG(endY);

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', String(svgX));
        circle.setAttribute('cy', String(svgY));
        circle.setAttribute('r', '4');
        circle.setAttribute('fill', color);
        circle.setAttribute('fill-opacity', '0.7');
        g.appendChild(circle);

        return g;
    }

    private getEventColor(result: string): string {
        switch (result) {
            case 'goal': return '#22C55E';
            case 'completion': return '#3B82F6';
            case 'turnover': return '#EF4444';
            default: return '#9CA3AF';
        }
    }

    private renderHeatmap(container: HTMLElement, type: 'origin' | 'dest'): void {
        const canvas = document.createElement('canvas');
        const width = 533;
        const height = 1200;
        canvas.width = width;
        canvas.height = height;
        canvas.style.maxWidth = '400px';
        canvas.style.height = 'auto';

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Draw field background
        ctx.fillStyle = '#2D5A27';
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = '#1E3F1B';
        ctx.fillRect(0, 0, width, 200);
        ctx.fillRect(0, 1000, width, 200);

        // Collect all points for the heatmap
        const points: Array<{x: number, y: number}> = [];
        this.events.forEach(event => {
            let x: number | null, y: number | null;
            if (type === 'origin') {
                x = event.thrower_x;
                y = event.thrower_y;
            } else {
                x = event.receiver_x ?? event.turnover_x;
                y = event.receiver_y ?? event.turnover_y;
            }
            if (x === null || y === null) return;
            points.push({
                x: this.fieldXToSVG(x),
                y: this.fieldYToSVG(y)
            });
        });

        if (points.length === 0) {
            container.appendChild(canvas);
            this.drawYardLinesAndNumbers(ctx, width, height);
            return;
        }

        // Use floating-point density grid to avoid RGB saturation issues
        // Lower resolution for performance, then render smoothly
        const gridScale = 4; // Each grid cell = 4x4 pixels
        const gridWidth = Math.ceil(width / gridScale);
        const gridHeight = Math.ceil(height / gridScale);
        const density = new Float32Array(gridWidth * gridHeight);

        // Gaussian kernel parameters
        const kernelRadiusPixels = 30;
        const kernelRadius = Math.ceil(kernelRadiusPixels / gridScale);
        const sigma = kernelRadius / 2;

        // Precompute Gaussian kernel weights
        const kernelSize = kernelRadius * 2 + 1;
        const kernel = new Float32Array(kernelSize * kernelSize);
        for (let dy = -kernelRadius; dy <= kernelRadius; dy++) {
            for (let dx = -kernelRadius; dx <= kernelRadius; dx++) {
                const distSq = dx * dx + dy * dy;
                const weight = Math.exp(-distSq / (2 * sigma * sigma));
                kernel[(dy + kernelRadius) * kernelSize + (dx + kernelRadius)] = weight;
            }
        }

        // Add contribution from each point
        for (const point of points) {
            const gx = Math.round(point.x / gridScale);
            const gy = Math.round(point.y / gridScale);

            for (let dy = -kernelRadius; dy <= kernelRadius; dy++) {
                for (let dx = -kernelRadius; dx <= kernelRadius; dx++) {
                    const px = gx + dx;
                    const py = gy + dy;

                    if (px >= 0 && px < gridWidth && py >= 0 && py < gridHeight) {
                        const weight = kernel[(dy + kernelRadius) * kernelSize + (dx + kernelRadius)];
                        density[py * gridWidth + px] += weight;
                    }
                }
            }
        }

        // Find normalization value using percentile on non-zero values
        const nonZeroValues: number[] = [];
        for (let i = 0; i < density.length; i++) {
            if (density[i] > 0.01) {
                nonZeroValues.push(density[i]);
            }
        }

        if (nonZeroValues.length === 0) {
            container.appendChild(canvas);
            this.drawYardLinesAndNumbers(ctx, width, height);
            return;
        }

        // Use 98th percentile for normalization - higher value means more blue/green
        nonZeroValues.sort((a, b) => a - b);
        const percentileIndex = Math.floor(nonZeroValues.length * 0.98);
        const normValue = nonZeroValues[percentileIndex] || nonZeroValues[nonZeroValues.length - 1];

        // Render to canvas with bilinear interpolation for smooth appearance
        const imageData = ctx.createImageData(width, height);
        for (let py = 0; py < height; py++) {
            for (let px = 0; px < width; px++) {
                // Map pixel to grid position
                const gx = px / gridScale;
                const gy = py / gridScale;

                // Bilinear interpolation
                const x0 = Math.floor(gx);
                const x1 = Math.min(x0 + 1, gridWidth - 1);
                const y0 = Math.floor(gy);
                const y1 = Math.min(y0 + 1, gridHeight - 1);
                const fx = gx - x0;
                const fy = gy - y0;

                const v00 = density[y0 * gridWidth + x0];
                const v10 = density[y0 * gridWidth + x1];
                const v01 = density[y1 * gridWidth + x0];
                const v11 = density[y1 * gridWidth + x1];

                const value = v00 * (1 - fx) * (1 - fy) +
                              v10 * fx * (1 - fy) +
                              v01 * (1 - fx) * fy +
                              v11 * fx * fy;

                if (value > 0.005) {
                    // Normalize to percentile
                    const rawIntensity = Math.min(1, value / normValue);
                    // Less compression to preserve more blue in low-density areas
                    const intensity = Math.pow(rawIntensity, 0.8);

                    if (intensity > 0.01) {
                        const color = this.getHeatmapColorRGB(intensity);
                        const i = (py * width + px) * 4;
                        imageData.data[i] = color.r;
                        imageData.data[i + 1] = color.g;
                        imageData.data[i + 2] = color.b;
                        // Linear alpha as requested
                        imageData.data[i + 3] = Math.min(255, Math.floor(intensity * 220 + 30));
                    }
                }
            }
        }
        ctx.putImageData(imageData, 0, 0);

        // Redraw field background behind the heatmap
        ctx.globalCompositeOperation = 'destination-over';
        ctx.fillStyle = '#2D5A27';
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = '#1E3F1B';
        ctx.fillRect(0, 0, width, 200);
        ctx.fillRect(0, 1000, width, 200);
        ctx.globalCompositeOperation = 'source-over';

        // Draw yard lines and numbers on top
        this.drawYardLinesAndNumbers(ctx, width, height);

        container.appendChild(canvas);
    }

    private drawYardLinesAndNumbers(ctx: CanvasRenderingContext2D, width: number, _height: number): void {
        // Draw yard lines
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        for (let yard = 20; yard <= 100; yard += 5) {
            const y = this.fieldYToSVG(yard);
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        // Draw yard numbers
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.font = 'bold 24px sans-serif';
        ctx.textBaseline = 'middle';
        for (let fieldY = 30; fieldY <= 90; fieldY += 10) {
            const y = this.fieldYToSVG(fieldY);
            const displayYard = fieldY <= 50 ? fieldY : 100 - fieldY;
            ctx.textAlign = 'left';
            ctx.fillText(String(displayYard), 20, y);
            ctx.textAlign = 'right';
            ctx.fillText(String(displayYard), 513, y);
        }
    }

    private getHeatmapColorRGB(intensity: number): {r: number, g: number, b: number} {
        // Gradient from blue (cold) -> cyan -> green -> yellow -> orange -> red (hot)
        // Weighted to show more blue/green, with red only for extreme hotspots
        let r: number, g: number, b: number;

        if (intensity < 0.3) {
            // Blue to cyan (0-30%)
            const t = intensity / 0.3;
            r = 0;
            g = Math.round(t * 255);
            b = 255;
        } else if (intensity < 0.5) {
            // Cyan to green (30-50%)
            const t = (intensity - 0.3) / 0.2;
            r = 0;
            g = 255;
            b = Math.round((1 - t) * 255);
        } else if (intensity < 0.7) {
            // Green to yellow (50-70%)
            const t = (intensity - 0.5) / 0.2;
            r = Math.round(t * 255);
            g = 255;
            b = 0;
        } else if (intensity < 0.9) {
            // Yellow to orange (70-90%)
            const t = (intensity - 0.7) / 0.2;
            r = 255;
            g = Math.round(255 - t * 128);
            b = 0;
        } else {
            // Orange to red (90-100%) - only truly extreme hotspots
            const t = (intensity - 0.9) / 0.1;
            r = 255;
            g = Math.round(127 - t * 127);
            b = 0;
        }

        return {r, g, b};
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new PassPlots();
});
