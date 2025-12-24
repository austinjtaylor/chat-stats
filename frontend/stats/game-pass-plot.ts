/**
 * Game Pass Plot Component - Visualizes pass events on a field diagram
 */

import { statsAPI } from '../src/api/client';
import type {
    PassPlotEvent,
    FilterState,
    PlayByPlayData,
    PlayerInfo,
    FilterCounts
} from './game-pass-plot-types';
import { extractEventsFromPoints } from './game-pass-plot-data';
import {
    getDefaultFilterState,
    buildMasterPlayerLists,
    computeFilterCounts,
    getFilteredEvents
} from './game-pass-plot-filters';
import {
    renderSVGField,
    renderEventsOnField,
    renderLegend,
    type HighlightInfo
} from './game-pass-plot-field';
import { computeStats, renderStatsPanel } from './game-pass-plot-stats';
import {
    renderTeamFilter,
    renderPlayerFilter,
    renderEventTypeFilter,
    renderLineTypeFilter,
    renderPeriodFilter,
    renderPassTypeFilter
} from './game-pass-plot-ui';

// Re-export types for external use
export type { PassPlotEvent } from './game-pass-plot-types';

export class GamePassPlot {
    private playByPlayData: PlayByPlayData | null = null;
    private allEvents: PassPlotEvent[] = [];
    private filterState: FilterState;

    // Computed counts for filter labels
    private filterCounts: FilterCounts = {
        throwerList: [],
        receiverList: [],
        eventTypeCounts: {},
        lineTypeCounts: {},
        periodCounts: {},
        passTypeCounts: {}
    };

    // Master lists of all players on the team (unfiltered)
    private masterThrowerList: PlayerInfo[] = [];
    private masterReceiverList: PlayerInfo[] = [];

    // Track if filters have been initialized
    private filtersInitialized = false;

    // DOM references
    private container: HTMLElement | null = null;

    // City info for labels
    private homeCity: string = '';
    private awayCity: string = '';
    private getCityAbbreviation: (city: string) => string;

    constructor(getCityAbbreviation: (city: string) => string) {
        this.getCityAbbreviation = getCityAbbreviation;
        this.filterState = getDefaultFilterState();
    }

    public async loadPassPlotData(gameId: string): Promise<void> {
        try {
            this.playByPlayData = await statsAPI.getGamePlayByPlay(gameId);
            if (this.playByPlayData) {
                this.allEvents = extractEventsFromPoints(this.playByPlayData);
                this.updateFilterCounts();
            }
        } catch (error) {
            console.error('Failed to load pass plot data:', error);
        }
    }

    public setPlayByPlayData(data: PlayByPlayData): void {
        this.playByPlayData = data;
        this.allEvents = extractEventsFromPoints(this.playByPlayData);
        this.updateFilterCounts();
    }

    private updateFilterCounts(): void {
        // Build master player lists on first load
        if (!this.filtersInitialized) {
            const { masterThrowerList, masterReceiverList } = buildMasterPlayerLists(
                this.allEvents,
                this.filterState.team
            );
            this.masterThrowerList = masterThrowerList;
            this.masterReceiverList = masterReceiverList;
        }

        // Compute filter counts
        this.filterCounts = computeFilterCounts(
            this.allEvents,
            this.filterState,
            this.masterThrowerList,
            this.masterReceiverList
        );

        // Auto-select all players on first load
        if (!this.filtersInitialized) {
            if (this.filterState.throwers.size === 0) {
                this.filterCounts.throwerList.forEach(p => this.filterState.throwers.add(p.id));
            }
            if (this.filterState.receivers.size === 0) {
                this.filterCounts.receiverList.forEach(p => this.filterState.receivers.add(p.id));
            }
            // Auto-select periods that exist
            if (this.filterState.periods.size === 0) {
                const existingQuarters = Object.keys(this.filterCounts.periodCounts).map(Number);
                existingQuarters.forEach(q => this.filterState.periods.add(q));
            }
            this.filtersInitialized = true;
        }
    }

    public renderPassPlot(homeCity?: string, awayCity?: string): void {
        this.container = document.getElementById('pass-plot');
        if (!this.container) return;

        // Store cities if provided
        if (homeCity !== undefined) this.homeCity = homeCity;
        if (awayCity !== undefined) this.awayCity = awayCity;

        const filteredEvents = getFilteredEvents(this.allEvents, this.filterState);
        const stats = computeStats(filteredEvents);

        const html = `
            <div class="game-pass-plot-container">
                <div class="game-pass-plot-filters">
                    <div class="filters-section">
                        ${renderTeamFilter(this.filterState, this.homeCity, this.awayCity, this.getCityAbbreviation)}
                        ${renderPlayerFilter(this.filterState, this.filterCounts)}
                        ${renderEventTypeFilter(this.filterState, this.filterCounts)}
                        ${renderLineTypeFilter(this.filterState, this.filterCounts)}
                        ${renderPassTypeFilter(this.filterState, this.filterCounts)}
                        ${renderPeriodFilter(this.filterState, this.filterCounts)}
                    </div>
                </div>
                <div class="game-pass-plot-canvas">
                    <div class="field-svg-wrapper">
                        ${renderSVGField()}
                    </div>
                    ${renderLegend()}
                </div>
                ${renderStatsPanel(stats)}
            </div>
        `;

        this.container.innerHTML = html;

        // Pass highlight info for solid/hollow marker styling
        const highlightInfo: HighlightInfo = {
            selectedThrowers: this.filterState.throwers,
            selectedReceivers: this.filterState.receivers
        };
        renderEventsOnField(filteredEvents, highlightInfo);
        this.attachEventListeners();
    }

    private onFilterChange(): void {
        // Save scroll position before re-render
        const filtersPanel = document.querySelector('.game-pass-plot-filters');
        const scrollTop = filtersPanel?.scrollTop ?? 0;

        // Recalculate all filter counts based on current selections
        this.updateFilterCounts();
        // Re-render the entire pass plot with updated counts
        this.renderPassPlot();

        // Restore scroll position after re-render
        const newFiltersPanel = document.querySelector('.game-pass-plot-filters');
        if (newFiltersPanel) {
            newFiltersPanel.scrollTop = scrollTop;
        }
    }

    private attachEventListeners(): void {
        // Team filter buttons
        document.querySelectorAll('.game-pass-plot-team-toggle .team-filter-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const team = (e.target as HTMLElement).dataset.team as 'home' | 'away';
                if (team && team !== this.filterState.team) {
                    this.filterState.team = team;
                    // Reset player selection and rebuild master lists when team changes
                    this.filterState.throwers.clear();
                    this.filterState.receivers.clear();
                    this.filtersInitialized = false;
                    this.updateFilterCounts();
                    this.renderPassPlot();
                }
            });
        });

        // Thrower checkboxes
        document.querySelectorAll('[data-filter="thrower"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const playerId = input.dataset.value!;
                if (input.checked) {
                    this.filterState.throwers.add(playerId);
                } else {
                    this.filterState.throwers.delete(playerId);
                }
                this.onFilterChange();
            });
        });

        // Receiver checkboxes
        document.querySelectorAll('[data-filter="receiver"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const playerId = input.dataset.value!;
                if (input.checked) {
                    this.filterState.receivers.add(playerId);
                } else {
                    this.filterState.receivers.delete(playerId);
                }
                this.onFilterChange();
            });
        });

        // Event type checkboxes
        document.querySelectorAll('[data-filter="eventType"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const eventType = input.dataset.value!;
                if (input.checked) {
                    this.filterState.eventTypes.add(eventType);
                } else {
                    this.filterState.eventTypes.delete(eventType);
                }
                this.onFilterChange();
            });
        });

        // Line type checkboxes
        document.querySelectorAll('[data-filter="lineType"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const lineType = input.dataset.value!;
                if (input.checked) {
                    this.filterState.lineTypes.add(lineType);
                } else {
                    this.filterState.lineTypes.delete(lineType);
                }
                this.onFilterChange();
            });
        });

        // Period checkboxes
        document.querySelectorAll('[data-filter="period"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const period = parseInt(input.dataset.value!);
                if (input.checked) {
                    this.filterState.periods.add(period);
                } else {
                    this.filterState.periods.delete(period);
                }
                this.onFilterChange();
            });
        });

        // Pass type checkboxes
        document.querySelectorAll('[data-filter="passType"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const passType = input.dataset.value!;
                if (input.checked) {
                    this.filterState.passTypes.add(passType);
                } else {
                    this.filterState.passTypes.delete(passType);
                }
                this.onFilterChange();
            });
        });

        // Select all buttons
        document.querySelectorAll('.select-all-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const filterType = (e.target as HTMLElement).dataset.filter!;
                this.selectAll(filterType);
            });
        });

        // Deselect all buttons
        document.querySelectorAll('.deselect-all-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const filterType = (e.target as HTMLElement).dataset.filter!;
                this.deselectAll(filterType);
            });
        });
    }

    private selectAll(filterType: string): void {
        switch (filterType) {
            case 'throwers':
                this.filterCounts.throwerList.forEach(p => this.filterState.throwers.add(p.id));
                break;
            case 'receivers':
                this.filterCounts.receiverList.forEach(p => this.filterState.receivers.add(p.id));
                break;
            case 'eventTypes':
                ['throws', 'catches', 'assists', 'goals', 'throwaways', 'drops'].forEach(et =>
                    this.filterState.eventTypes.add(et));
                break;
            case 'lineTypes':
                ['o-points', 'd-points', 'o-out-of-to', 'd-out-of-to'].forEach(lt =>
                    this.filterState.lineTypes.add(lt));
                break;
            case 'periods':
                [1, 2, 3, 4, 5].forEach(p => this.filterState.periods.add(p));
                break;
            case 'passTypes':
                ['huck', 'swing', 'dump', 'gainer', 'dish'].forEach(pt =>
                    this.filterState.passTypes.add(pt));
                break;
        }
        this.onFilterChange();
    }

    private deselectAll(filterType: string): void {
        switch (filterType) {
            case 'throwers':
                this.filterState.throwers.clear();
                break;
            case 'receivers':
                this.filterState.receivers.clear();
                break;
            case 'eventTypes':
                this.filterState.eventTypes.clear();
                break;
            case 'lineTypes':
                this.filterState.lineTypes.clear();
                break;
            case 'periods':
                this.filterState.periods.clear();
                break;
            case 'passTypes':
                this.filterState.passTypes.clear();
                break;
        }
        this.onFilterChange();
    }
}

export default GamePassPlot;
