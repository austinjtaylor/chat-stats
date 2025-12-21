/**
 * Game Pass Plot Component - Visualizes pass events on a field diagram
 */

import { statsAPI } from '../src/api/client';

export interface PassPlotEvent {
    type: string;
    thrower_x: number | null;
    thrower_y: number | null;
    receiver_x: number | null;
    receiver_y: number | null;
    turnover_x: number | null;
    turnover_y: number | null;
    thrower_name?: string;
    receiver_name?: string;
    thrower_id?: string;
    receiver_id?: string;
    quarter: number;
    point_number: number;
    line_type: string;
    team: string;
    is_after_turnover: boolean;
}

interface FilterState {
    team: 'home' | 'away';
    throwers: Set<string>;
    receivers: Set<string>;
    eventTypes: Set<string>;
    lineTypes: Set<string>;
    periods: Set<number>;
    passTypes: Set<string>;
}

interface PlayByPlayPoint {
    point_number: number;
    quarter: number;
    team: string;
    line_type: string;
    events: any[];
}

interface PlayByPlayData {
    points: PlayByPlayPoint[];
}

interface PlayerInfo {
    id: string;
    name: string;
    count: number;
}

export class GamePassPlot {
    private playByPlayData: PlayByPlayData | null = null;
    private allEvents: PassPlotEvent[] = [];
    private filterState: FilterState;

    // Computed counts for filter labels
    private throwerList: PlayerInfo[] = [];
    private receiverList: PlayerInfo[] = [];
    private eventTypeCounts: Record<string, number> = {};
    private lineTypeCounts: Record<string, number> = {};
    private periodCounts: Record<number, number> = {};
    private passTypeCounts: Record<string, number> = {};

    // DOM references
    private container: HTMLElement | null = null;

    // City info for labels
    private homeCity: string = '';
    private awayCity: string = '';
    private getCityAbbreviation: (city: string) => string;

    constructor(getCityAbbreviation: (city: string) => string) {
        this.getCityAbbreviation = getCityAbbreviation;
        this.filterState = this.getDefaultFilterState();
    }

    private getDefaultFilterState(): FilterState {
        return {
            team: 'home',
            throwers: new Set<string>(),
            receivers: new Set<string>(),
            eventTypes: new Set(['throws', 'catches', 'assists', 'goals', 'throwaways', 'drops']),
            lineTypes: new Set(['o-points', 'd-points', 'o-out-of-to', 'd-out-of-to']),
            periods: new Set([1, 2, 3, 4]),
            passTypes: new Set(['huck', 'swing', 'dump', 'gainer', 'dish'])
        };
    }

    public async loadPassPlotData(gameId: string): Promise<void> {
        try {
            this.playByPlayData = await statsAPI.getGamePlayByPlay(gameId);
            this.extractEventsFromPoints();
            this.computeFilterCounts();
        } catch (error) {
            console.error('Failed to load pass plot data:', error);
        }
    }

    public setPlayByPlayData(data: PlayByPlayData): void {
        this.playByPlayData = data;
        this.extractEventsFromPoints();
        this.computeFilterCounts();
    }

    private extractEventsFromPoints(): void {
        if (!this.playByPlayData) return;

        this.allEvents = [];

        for (const point of this.playByPlayData.points) {
            // Track if we've seen a turnover in this point (for detecting "out of turnover" scenarios)
            let hasSeenTurnover = false;

            for (const event of point.events) {
                // Skip events we don't visualize, but track turnovers for "out of turnover" marking
                if (!['pass', 'goal', 'drop', 'throwaway', 'stall'].includes(event.type)) {
                    // Mark that a turnover occurred (block, opponent_turnover, etc.)
                    if (['block', 'opponent_turnover'].includes(event.type)) {
                        hasSeenTurnover = true;
                    }
                    continue;
                }

                // Only include events that have coordinates
                const hasCoords = (event.thrower_x !== null && event.thrower_x !== undefined) ||
                                  (event.receiver_x !== null && event.receiver_x !== undefined) ||
                                  (event.turnover_x !== null && event.turnover_x !== undefined);

                if (!hasCoords) continue;

                // Capture whether this event happened after a turnover (before marking current event as turnover)
                const isAfterTurnover = hasSeenTurnover;

                // Extract player names - "from X" for passes, "by X" for turnovers
                const throwerName = event.description?.match(/from (\w+)/)?.[1] ||
                                   event.description?.match(/by (\w+)/)?.[1];
                const receiverName = event.description?.match(/to (\w+)/)?.[1];

                this.allEvents.push({
                    type: event.type,
                    thrower_x: event.thrower_x ?? null,
                    thrower_y: event.thrower_y ?? null,
                    receiver_x: event.receiver_x ?? null,
                    receiver_y: event.receiver_y ?? null,
                    turnover_x: event.turnover_x ?? null,
                    turnover_y: event.turnover_y ?? null,
                    thrower_name: throwerName,
                    receiver_name: receiverName,
                    thrower_id: event.thrower_id,
                    receiver_id: event.receiver_id,
                    quarter: point.quarter,
                    point_number: point.point_number,
                    line_type: point.line_type,
                    team: point.team,
                    is_after_turnover: isAfterTurnover
                });

                // Mark turnover AFTER adding the event so the turnover itself isn't marked as "after turnover"
                if (['drop', 'throwaway', 'stall'].includes(event.type)) {
                    hasSeenTurnover = true;
                }
            }
        }
    }

    private computeFilterCounts(): void {
        // Filter events by current team first
        const teamEvents = this.allEvents.filter(e => e.team === this.filterState.team);

        // Build separate thrower and receiver lists with counts
        const throwerCounts = new Map<string, { name: string; count: number }>();
        const receiverCounts = new Map<string, { name: string; count: number }>();

        teamEvents.forEach(event => {
            // Count throwers
            if (event.thrower_name) {
                const key = event.thrower_name;
                const existing = throwerCounts.get(key) || { name: event.thrower_name, count: 0 };
                existing.count++;
                throwerCounts.set(key, existing);
            }
            // Count receivers
            if (event.receiver_name && event.type !== 'drop' && event.type !== 'throwaway') {
                const key = event.receiver_name;
                const existing = receiverCounts.get(key) || { name: event.receiver_name, count: 0 };
                existing.count++;
                receiverCounts.set(key, existing);
            }
        });

        this.throwerList = Array.from(throwerCounts.entries())
            .map(([id, info]) => ({ id, name: info.name, count: info.count }))
            .sort((a, b) => a.name.localeCompare(b.name));

        this.receiverList = Array.from(receiverCounts.entries())
            .map(([id, info]) => ({ id, name: info.name, count: info.count }))
            .sort((a, b) => a.name.localeCompare(b.name));

        // If throwers filter is empty, select all throwers
        if (this.filterState.throwers.size === 0) {
            this.throwerList.forEach(p => this.filterState.throwers.add(p.id));
        }
        // If receivers filter is empty, select all receivers
        if (this.filterState.receivers.size === 0) {
            this.receiverList.forEach(p => this.filterState.receivers.add(p.id));
        }

        // Event type counts
        this.eventTypeCounts = {
            throws: teamEvents.filter(e => ['pass', 'goal', 'throwaway'].includes(e.type)).length,
            catches: teamEvents.filter(e => ['pass', 'goal'].includes(e.type)).length,
            assists: teamEvents.filter(e => e.type === 'goal').length,
            goals: teamEvents.filter(e => e.type === 'goal').length,
            throwaways: teamEvents.filter(e => e.type === 'throwaway').length,
            drops: teamEvents.filter(e => e.type === 'drop').length
        };

        // Line type counts
        this.lineTypeCounts = {
            'o-points': teamEvents.filter(e => e.line_type === 'O-Line' && !e.is_after_turnover).length,
            'd-points': teamEvents.filter(e => e.line_type === 'D-Line' && !e.is_after_turnover).length,
            'o-out-of-to': teamEvents.filter(e => e.line_type === 'O-Line' && e.is_after_turnover).length,
            'd-out-of-to': teamEvents.filter(e => e.line_type === 'D-Line' && e.is_after_turnover).length
        };

        // Period counts
        this.periodCounts = {};
        teamEvents.forEach(event => {
            this.periodCounts[event.quarter] = (this.periodCounts[event.quarter] || 0) + 1;
        });

        // Update periods filter to include any quarters that exist
        const existingQuarters = Object.keys(this.periodCounts).map(Number);
        existingQuarters.forEach(q => this.filterState.periods.add(q));

        // Pass type counts
        this.passTypeCounts = {
            huck: 0,
            swing: 0,
            dump: 0,
            gainer: 0,
            dish: 0
        };
        teamEvents.forEach(event => {
            const passType = this.classifyPassType(event);
            if (passType && this.passTypeCounts[passType] !== undefined) {
                this.passTypeCounts[passType]++;
            }
        });
    }

    private getFilteredEvents(): PassPlotEvent[] {
        return this.allEvents.filter(event => {
            // Team filter
            if (event.team !== this.filterState.team) return false;

            // Thrower filter - check if thrower is in selected throwers
            if (event.thrower_name && !this.filterState.throwers.has(event.thrower_name)) return false;

            // Receiver filter - check if receiver is in selected receivers (skip for turnovers)
            if (event.receiver_name && event.type !== 'drop' && event.type !== 'throwaway') {
                if (!this.filterState.receivers.has(event.receiver_name)) return false;
            }

            // Event type filter
            let eventTypeMatch = false;
            if (event.type === 'pass') {
                eventTypeMatch = this.filterState.eventTypes.has('throws') ||
                                this.filterState.eventTypes.has('catches');
            } else if (event.type === 'goal') {
                eventTypeMatch = this.filterState.eventTypes.has('goals') ||
                                this.filterState.eventTypes.has('assists');
            } else if (event.type === 'throwaway') {
                eventTypeMatch = this.filterState.eventTypes.has('throwaways');
            } else if (event.type === 'drop') {
                eventTypeMatch = this.filterState.eventTypes.has('drops');
            }
            if (!eventTypeMatch) return false;

            // Line type filter
            let lineTypeMatch = false;
            if (event.line_type === 'O-Line') {
                lineTypeMatch = event.is_after_turnover
                    ? this.filterState.lineTypes.has('o-out-of-to')
                    : this.filterState.lineTypes.has('o-points');
            } else if (event.line_type === 'D-Line') {
                lineTypeMatch = event.is_after_turnover
                    ? this.filterState.lineTypes.has('d-out-of-to')
                    : this.filterState.lineTypes.has('d-points');
            }
            if (!lineTypeMatch) return false;

            // Period filter
            if (!this.filterState.periods.has(event.quarter)) return false;

            // Pass type filter
            const passType = this.classifyPassType(event);
            if (passType && !this.filterState.passTypes.has(passType)) return false;

            return true;
        });
    }

    public renderPassPlot(homeCity?: string, awayCity?: string): void {
        this.container = document.getElementById('pass-plot');
        if (!this.container) return;

        // Store cities if provided
        if (homeCity !== undefined) this.homeCity = homeCity;
        if (awayCity !== undefined) this.awayCity = awayCity;

        const html = `
            <div class="game-pass-plot-container">
                <div class="game-pass-plot-filters">
                    <div class="filters-section">
                        ${this.renderTeamFilter()}
                        ${this.renderPlayerFilter()}
                        ${this.renderEventTypeFilter()}
                        ${this.renderLineTypeFilter()}
                        ${this.renderPassTypeFilter()}
                        ${this.renderPeriodFilter()}
                    </div>
                </div>
                <div class="game-pass-plot-canvas">
                    <div class="field-svg-wrapper">
                        ${this.renderSVGField()}
                    </div>
                    ${this.renderLegend()}
                </div>
                ${this.renderStatsPanel()}
            </div>
        `;

        this.container.innerHTML = html;
        this.renderEventsOnField();
        this.attachEventListeners();
    }

    private renderTeamFilter(): string {
        const awayAbbrev = this.awayCity ? this.getCityAbbreviation(this.awayCity) : 'AWAY';
        const homeAbbrev = this.homeCity ? this.getCityAbbreviation(this.homeCity) : 'HOME';

        return `
            <div class="filter-group">
                <div class="filter-group-header">
                    <span class="filter-group-title">Team</span>
                </div>
                <div class="game-pass-plot-team-toggle">
                    <button class="team-filter-btn ${this.filterState.team === 'away' ? 'active' : ''}"
                            data-team="away">${awayAbbrev}</button>
                    <button class="team-filter-btn ${this.filterState.team === 'home' ? 'active' : ''}"
                            data-team="home">${homeAbbrev}</button>
                </div>
            </div>
        `;
    }

    private renderPlayerFilter(): string {
        return `
            <h3 class="filter-section-title">Players</h3>
            <div class="filter-group">
                <div class="filter-group-header">
                    <span class="filter-subgroup-title">Thrower</span>
                    <div class="filter-group-actions">
                        <button class="filter-action-btn select-all-btn" data-filter="throwers">Select all</button>
                        <button class="filter-action-btn deselect-all-btn" data-filter="throwers">Deselect all</button>
                    </div>
                </div>
                <div class="filter-checkbox-list player-filter-list">
                    ${this.throwerList.map(player => `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="thrower-${player.id}"
                                   data-filter="thrower" data-value="${player.id}"
                                   ${this.filterState.throwers.has(player.id) ? 'checked' : ''}>
                            <label for="thrower-${player.id}">${player.name}</label>
                            <span class="count">(${player.count})</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="filter-group">
                <div class="filter-group-header">
                    <span class="filter-subgroup-title">Receiver</span>
                    <div class="filter-group-actions">
                        <button class="filter-action-btn select-all-btn" data-filter="receivers">Select all</button>
                        <button class="filter-action-btn deselect-all-btn" data-filter="receivers">Deselect all</button>
                    </div>
                </div>
                <div class="filter-checkbox-list player-filter-list">
                    ${this.receiverList.map(player => `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="receiver-${player.id}"
                                   data-filter="receiver" data-value="${player.id}"
                                   ${this.filterState.receivers.has(player.id) ? 'checked' : ''}>
                            <label for="receiver-${player.id}">${player.name}</label>
                            <span class="count">(${player.count})</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    private renderEventTypeFilter(): string {
        const eventTypes = [
            { id: 'throws', label: 'Throws', count: this.eventTypeCounts.throws || 0 },
            { id: 'catches', label: 'Catches', count: this.eventTypeCounts.catches || 0 },
            { id: 'assists', label: 'Assists', count: this.eventTypeCounts.assists || 0 },
            { id: 'goals', label: 'Goals', count: this.eventTypeCounts.goals || 0 },
            { id: 'throwaways', label: 'Throwaways', count: this.eventTypeCounts.throwaways || 0 },
            { id: 'drops', label: 'Drops', count: this.eventTypeCounts.drops || 0 }
        ];

        return `
            <h3 class="filter-section-title">Event Type</h3>
            <div class="filter-group">
                <div class="filter-group-header">
                    <div class="filter-group-actions">
                        <button class="filter-action-btn select-all-btn" data-filter="eventTypes">Select all</button>
                        <button class="filter-action-btn deselect-all-btn" data-filter="eventTypes">Deselect all</button>
                    </div>
                </div>
                <div class="filter-checkbox-list">
                    ${eventTypes.map(et => `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="event-${et.id}"
                                   data-filter="eventType" data-value="${et.id}"
                                   ${this.filterState.eventTypes.has(et.id) ? 'checked' : ''}>
                            <label for="event-${et.id}">${et.label}</label>
                            <span class="count">(${et.count})</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    private renderLineTypeFilter(): string {
        const lineTypes = [
            { id: 'o-points', label: 'O points', count: this.lineTypeCounts['o-points'] || 0 },
            { id: 'd-points', label: 'D points', count: this.lineTypeCounts['d-points'] || 0 },
            { id: 'o-out-of-to', label: 'O out of TO', count: this.lineTypeCounts['o-out-of-to'] || 0 },
            { id: 'd-out-of-to', label: 'D out of TO', count: this.lineTypeCounts['d-out-of-to'] || 0 }
        ];

        return `
            <h3 class="filter-section-title">Line Type</h3>
            <div class="filter-group">
                <div class="filter-group-header">
                    <div class="filter-group-actions">
                        <button class="filter-action-btn select-all-btn" data-filter="lineTypes">Select all</button>
                        <button class="filter-action-btn deselect-all-btn" data-filter="lineTypes">Deselect all</button>
                    </div>
                </div>
                <div class="filter-checkbox-list">
                    ${lineTypes.map(lt => `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="line-${lt.id}"
                                   data-filter="lineType" data-value="${lt.id}"
                                   ${this.filterState.lineTypes.has(lt.id) ? 'checked' : ''}>
                            <label for="line-${lt.id}">${lt.label}</label>
                            <span class="count">(${lt.count})</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    private renderPeriodFilter(): string {
        const periods = [
            { id: 1, label: 'First quarter' },
            { id: 2, label: 'Second quarter' },
            { id: 3, label: 'Third quarter' },
            { id: 4, label: 'Fourth quarter' }
        ];

        // Add overtime if it exists
        if (this.periodCounts[5]) {
            periods.push({ id: 5, label: 'Overtime' });
        }

        return `
            <h3 class="filter-section-title">Quarter</h3>
            <div class="filter-group">
                <div class="filter-group-header">
                    <div class="filter-group-actions">
                        <button class="filter-action-btn select-all-btn" data-filter="periods">Select all</button>
                        <button class="filter-action-btn deselect-all-btn" data-filter="periods">Deselect all</button>
                    </div>
                </div>
                <div class="filter-checkbox-list">
                    ${periods.map(p => `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="period-${p.id}"
                                   data-filter="period" data-value="${p.id}"
                                   ${this.filterState.periods.has(p.id) ? 'checked' : ''}>
                            <label for="period-${p.id}">${p.label}</label>
                            <span class="count">(${this.periodCounts[p.id] || 0})</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    private renderPassTypeFilter(): string {
        const passTypes = [
            { id: 'huck', label: 'Hucks', count: this.passTypeCounts.huck || 0 },
            { id: 'swing', label: 'Swings', count: this.passTypeCounts.swing || 0 },
            { id: 'dump', label: 'Dumps', count: this.passTypeCounts.dump || 0 },
            { id: 'gainer', label: 'Gainers', count: this.passTypeCounts.gainer || 0 },
            { id: 'dish', label: 'Dishes', count: this.passTypeCounts.dish || 0 }
        ];

        return `
            <h3 class="filter-section-title">Pass Type</h3>
            <div class="filter-group">
                <div class="filter-group-header">
                    <div class="filter-group-actions">
                        <button class="filter-action-btn select-all-btn" data-filter="passTypes">Select all</button>
                        <button class="filter-action-btn deselect-all-btn" data-filter="passTypes">Deselect all</button>
                    </div>
                </div>
                <div class="filter-checkbox-list">
                    ${passTypes.map(pt => `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="passType-${pt.id}"
                                   data-filter="passType" data-value="${pt.id}"
                                   ${this.filterState.passTypes.has(pt.id) ? 'checked' : ''}>
                            <label for="passType-${pt.id}">${pt.label}</label>
                            <span class="count">(${pt.count})</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    private renderSVGField(): string {
        // SVG viewBox: 533 wide (53.3 yards * 10), 1200 tall (120 yards * 10)
        // Field is oriented with north (attacking) endzone at top
        return `
            <svg viewBox="0 0 533 1200" class="game-pass-plot-svg" id="passPlotSvg">
                <!-- Field background -->
                <rect class="field-grass" x="0" y="0" width="533" height="1200"/>

                <!-- North Endzone (100-120 yards, attacking) -->
                <rect class="field-endzone field-endzone-north" x="0" y="0" width="533" height="200"/>

                <!-- South Endzone (0-20 yards, defending) -->
                <rect class="field-endzone field-endzone-south" x="0" y="1000" width="533" height="200"/>

                <!-- Yard lines -->
                <g class="field-yard-lines">
                    ${this.renderYardLines()}
                </g>

                <!-- Yard numbers -->
                <g class="field-yard-numbers">
                    ${this.renderYardNumbers()}
                </g>

                <!-- Events layer -->
                <g class="field-events" id="fieldEventsLayer">
                    <!-- Events will be added dynamically -->
                </g>
            </svg>
        `;
    }

    private renderYardLines(): string {
        const lines: string[] = [];
        // Draw lines every 5 yards from 20 to 100 (playable field)
        for (let yard = 20; yard <= 100; yard += 5) {
            const y = this.fieldYToSVG(yard);
            lines.push(`<line x1="0" y1="${y}" x2="533" y2="${y}"/>`);
        }
        return lines.join('');
    }

    private renderYardNumbers(): string {
        const numbers: string[] = [];
        // Show numbers at 10-yard intervals (30, 40, 50, 60, 70, 80, 90)
        for (let yard = 30; yard <= 90; yard += 10) {
            const y = this.fieldYToSVG(yard) + 8; // Offset for text baseline
            const displayYard = yard <= 50 ? yard : 100 - yard; // Mirror for far side
            numbers.push(`<text x="20" y="${y}">${displayYard}</text>`);
            numbers.push(`<text x="513" y="${y}" text-anchor="end">${displayYard}</text>`);
        }
        return numbers.join('');
    }

    private fieldYToSVG(fieldY: number): number {
        // Field y: 0-120 yards -> SVG y: 1200-0 (inverted, north is top)
        return (120 - fieldY) * 10;
    }

    private fieldXToSVG(fieldX: number): number {
        // Field x is centered at 0, ranging from about -26.65 to 26.65
        // SVG x: 0-533 (center at 266.5)
        return (fieldX * 10) + 266.5;
    }

    private renderEventsOnField(): void {
        const eventsLayer = document.getElementById('fieldEventsLayer');
        if (!eventsLayer) return;

        // Clear existing events
        eventsLayer.innerHTML = '';

        const filteredEvents = this.getFilteredEvents();

        // Create SVG elements for each event
        filteredEvents.forEach(event => {
            const element = this.createEventElement(event);
            if (element) {
                eventsLayer.appendChild(element);
            }
        });
    }

    private createEventElement(event: PassPlotEvent): SVGGElement | null {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.classList.add('field-event');

        const color = this.getEventColor(event.type);
        const markerShape = this.getMarkerShape(event.type);

        // Determine start and end positions
        let startX: number | null = null;
        let startY: number | null = null;
        let endX: number | null = null;
        let endY: number | null = null;

        if (event.type === 'pass' || event.type === 'goal') {
            startX = event.thrower_x;
            startY = event.thrower_y;
            endX = event.receiver_x;
            endY = event.receiver_y;
        } else if (event.type === 'throwaway' || event.type === 'drop') {
            startX = event.thrower_x;
            startY = event.thrower_y;
            endX = event.turnover_x ?? event.thrower_x;
            endY = event.turnover_y ?? event.thrower_y;
        } else if (event.type === 'stall') {
            endX = event.turnover_x;
            endY = event.turnover_y;
        }

        // Draw line if we have start and end positions
        if (startX !== null && startY !== null && endX !== null && endY !== null) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', String(this.fieldXToSVG(startX)));
            line.setAttribute('y1', String(this.fieldYToSVG(startY)));
            line.setAttribute('x2', String(this.fieldXToSVG(endX)));
            line.setAttribute('y2', String(this.fieldYToSVG(endY)));
            line.setAttribute('stroke', color);
            line.setAttribute('stroke-width', '2');
            line.setAttribute('stroke-opacity', '0.6');
            g.appendChild(line);
        }

        // Draw marker at end position
        if (endX !== null && endY !== null) {
            const svgX = this.fieldXToSVG(endX);
            const svgY = this.fieldYToSVG(endY);

            if (markerShape === 'circle') {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', String(svgX));
                circle.setAttribute('cy', String(svgY));
                circle.setAttribute('r', '5');
                circle.setAttribute('fill', color);
                g.appendChild(circle);
            } else {
                const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                rect.setAttribute('x', String(svgX - 4));
                rect.setAttribute('y', String(svgY - 4));
                rect.setAttribute('width', '8');
                rect.setAttribute('height', '8');
                rect.setAttribute('fill', color);
                g.appendChild(rect);
            }
        }

        return g;
    }

    private getEventColor(eventType: string): string {
        switch (eventType) {
            case 'pass': return '#3B82F6'; // Blue
            case 'goal': return '#22C55E'; // Green
            case 'drop': return '#EF4444'; // Red
            case 'throwaway': return '#EF4444'; // Red
            case 'stall': return '#8B5CF6'; // Purple
            default: return '#9CA3AF'; // Gray
        }
    }

    private getMarkerShape(eventType: string): 'square' | 'circle' {
        return eventType === 'drop' ? 'circle' : 'square';
    }

    private renderLegend(): string {
        const legendItems = [
            { type: 'pass', label: 'Pass', color: '#3B82F6', shape: 'square' },
            { type: 'drop', label: 'Drop', color: '#EF4444', shape: 'circle' },
            { type: 'throwaway', label: 'Throwaway', color: '#EF4444', shape: 'square' },
            { type: 'stall', label: 'Stall', color: '#8B5CF6', shape: 'square' },
            { type: 'goal', label: 'Score', color: '#22C55E', shape: 'square' }
        ];

        return `
            <div class="game-pass-plot-legend">
                ${legendItems.map(item => `
                    <div class="legend-item">
                        <span class="legend-line" style="background: ${item.color};"></span>
                        <span class="legend-marker ${item.shape}" style="background: ${item.color};"></span>
                        <span class="legend-label">${item.label}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    private renderStatsPanel(): string {
        const stats = this.computeStats();
        return `
            <aside class="game-pass-plot-stats">
                <h3 class="stats-title">Statistics</h3>

                <div class="stats-summary">
                    <div class="stat-row">
                        <span class="stat-label">Total Throws</span>
                        <span class="stat-value">${stats.totalThrows}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Completions</span>
                        <span class="stat-value">${stats.completions} <small>(${stats.completionsPct}%)</small></span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Turnovers</span>
                        <span class="stat-value">${stats.turnovers} <small>(${stats.turnoversPct}%)</small></span>
                    </div>
                    <div class="stat-row highlight">
                        <span class="stat-label">Goals</span>
                        <span class="stat-value">${stats.goals} <small>(${stats.goalsPct}%)</small></span>
                    </div>
                </div>

                <div class="stats-divider"></div>

                <div class="stats-summary">
                    <div class="stat-row">
                        <span class="stat-label">Avg Yards/Throw</span>
                        <span class="stat-value">${stats.avgYardsPerThrow.toFixed(1)}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Avg Yards/Completion</span>
                        <span class="stat-value">${stats.avgYardsPerCompletion.toFixed(1)}</span>
                    </div>
                </div>

                <div class="stats-divider"></div>

                <h4 class="stats-subtitle">By Pass Type</h4>
                <div class="stats-by-type">
                    <div class="stat-row">
                        <span class="stat-label">Hucks</span>
                        <span class="stat-value">${stats.byType.huck.count} <small>(${stats.byType.huck.pct}%)</small></span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Swings</span>
                        <span class="stat-value">${stats.byType.swing.count} <small>(${stats.byType.swing.pct}%)</small></span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Dumps</span>
                        <span class="stat-value">${stats.byType.dump.count} <small>(${stats.byType.dump.pct}%)</small></span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Gainers</span>
                        <span class="stat-value">${stats.byType.gainer.count} <small>(${stats.byType.gainer.pct}%)</small></span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Dishes</span>
                        <span class="stat-value">${stats.byType.dish.count} <small>(${stats.byType.dish.pct}%)</small></span>
                    </div>
                </div>

                <div class="stats-divider"></div>

                <div class="type-definitions">
                    <h4 class="stats-subtitle">Definitions</h4>
                    <div class="definition"><strong>Huck:</strong> 40+ yard throw</div>
                    <div class="definition"><strong>Swing:</strong> Lateral throw</div>
                    <div class="definition"><strong>Dump:</strong> Short backward throw</div>
                    <div class="definition"><strong>Gainer:</strong> Short-medium forward</div>
                    <div class="definition"><strong>Dish:</strong> Under 5 yards</div>
                </div>
            </aside>
        `;
    }

    private computeStats(): {
        totalThrows: number;
        completions: number;
        completionsPct: number;
        turnovers: number;
        turnoversPct: number;
        goals: number;
        goalsPct: number;
        avgYardsPerThrow: number;
        avgYardsPerCompletion: number;
        byType: Record<string, { count: number; pct: number }>;
    } {
        const filteredEvents = this.getFilteredEvents();

        let totalThrows = 0;
        let completions = 0;
        let turnovers = 0;
        let goals = 0;
        let totalYards = 0;
        let completionYards = 0;

        const byType: Record<string, { count: number; pct: number }> = {
            huck: { count: 0, pct: 0 },
            swing: { count: 0, pct: 0 },
            dump: { count: 0, pct: 0 },
            gainer: { count: 0, pct: 0 },
            dish: { count: 0, pct: 0 },
        };

        for (const event of filteredEvents) {
            // Count throws (pass, goal, throwaway events)
            if (['pass', 'goal', 'throwaway'].includes(event.type)) {
                totalThrows++;

                // Calculate yards
                const yards = this.calculateYards(event);
                if (yards !== null) {
                    totalYards += yards;
                }

                // Classify pass type and count
                const passType = this.classifyPassType(event);
                if (passType && byType[passType]) {
                    byType[passType].count++;
                }
            }

            // Count results
            if (event.type === 'goal') {
                goals++;
                completions++;
                const yards = this.calculateYards(event);
                if (yards !== null) {
                    completionYards += yards;
                }
            } else if (event.type === 'pass') {
                completions++;
                const yards = this.calculateYards(event);
                if (yards !== null) {
                    completionYards += yards;
                }
            } else if (['throwaway', 'drop', 'stall'].includes(event.type)) {
                turnovers++;
            }
        }

        // Calculate percentages
        const completionsPct = totalThrows > 0 ? Math.round(completions / totalThrows * 100) : 0;
        const turnoversPct = totalThrows > 0 ? Math.round(turnovers / totalThrows * 100) : 0;
        const goalsPct = totalThrows > 0 ? Math.round(goals / totalThrows * 100) : 0;
        const avgYardsPerThrow = totalThrows > 0 ? totalYards / totalThrows : 0;
        const avgYardsPerCompletion = completions > 0 ? completionYards / completions : 0;

        // Calculate pass type percentages
        for (const type in byType) {
            byType[type].pct = totalThrows > 0 ? Math.round(byType[type].count / totalThrows * 100) : 0;
        }

        return {
            totalThrows,
            completions,
            completionsPct,
            turnovers,
            turnoversPct,
            goals,
            goalsPct,
            avgYardsPerThrow,
            avgYardsPerCompletion,
            byType,
        };
    }

    private calculateYards(event: PassPlotEvent): number | null {
        const destY = event.receiver_y ?? event.turnover_y;
        if (event.thrower_y === null || destY === null) {
            return null;
        }
        return destY - event.thrower_y;
    }

    private classifyPassType(event: PassPlotEvent): string | null {
        const destX = event.receiver_x ?? event.turnover_x;
        const destY = event.receiver_y ?? event.turnover_y;

        if (event.thrower_x === null || event.thrower_y === null || destX === null || destY === null) {
            return null;
        }

        const verticalYards = destY - event.thrower_y;
        const horizontalYards = Math.abs(destX - event.thrower_x);
        const distance = Math.sqrt(verticalYards ** 2 + horizontalYards ** 2);

        // Huck: 40+ yards forward
        if (verticalYards >= 40) {
            return 'huck';
        }

        // Dish: Under 5 yards total distance
        if (distance < 5) {
            return 'dish';
        }

        // Dump: Short backward throw (negative yards)
        if (verticalYards < 0 && distance < 15) {
            return 'dump';
        }

        // Swing: Lateral throw (more horizontal than vertical, or slightly negative)
        if (horizontalYards > Math.abs(verticalYards) || (verticalYards <= 0 && horizontalYards > 5)) {
            return 'swing';
        }

        // Gainer: Short-medium forward throw
        if (verticalYards > 0 && verticalYards < 40) {
            return 'gainer';
        }

        return null;
    }

    private attachEventListeners(): void {
        // Team filter buttons
        document.querySelectorAll('.game-pass-plot-team-toggle .team-filter-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const team = (e.target as HTMLElement).dataset.team as 'home' | 'away';
                if (team && team !== this.filterState.team) {
                    this.filterState.team = team;
                    // Reset player selection when team changes
                    this.filterState.throwers.clear();
                    this.filterState.receivers.clear();
                    this.computeFilterCounts();
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
                this.renderEventsOnField();
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
                this.renderEventsOnField();
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
                this.renderEventsOnField();
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
                this.renderEventsOnField();
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
                this.renderEventsOnField();
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
                this.renderEventsOnField();
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
                this.throwerList.forEach(p => this.filterState.throwers.add(p.id));
                break;
            case 'receivers':
                this.receiverList.forEach(p => this.filterState.receivers.add(p.id));
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
        this.renderPassPlot();
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
        this.renderPassPlot();
    }
}

export default GamePassPlot;
