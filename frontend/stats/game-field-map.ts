/**
 * Game Field Map Component - Visualizes pass events on a field diagram
 */

import { statsAPI } from '../src/api/client';

export interface FieldMapEvent {
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
    players: Set<string>;
    eventTypes: Set<string>;
    lineTypes: Set<string>;
    periods: Set<number>;
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

export class GameFieldMap {
    private playByPlayData: PlayByPlayData | null = null;
    private allEvents: FieldMapEvent[] = [];
    private filterState: FilterState;

    // Computed counts for filter labels
    private playerList: PlayerInfo[] = [];
    private eventTypeCounts: Record<string, number> = {};
    private lineTypeCounts: Record<string, number> = {};
    private periodCounts: Record<number, number> = {};

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
            players: new Set<string>(),
            eventTypes: new Set(['throws', 'catches', 'assists', 'goals', 'throwaways', 'drops']),
            lineTypes: new Set(['o-points', 'd-points', 'o-out-of-to', 'd-out-of-to']),
            periods: new Set([1, 2, 3, 4])
        };
    }

    public async loadFieldMapData(gameId: string): Promise<void> {
        try {
            this.playByPlayData = await statsAPI.getGamePlayByPlay(gameId);
            this.extractEventsFromPoints();
            this.computeFilterCounts();
        } catch (error) {
            console.error('Failed to load field map data:', error);
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
                // Check if this event is a turnover
                if (['drop', 'throwaway', 'stall', 'block', 'opponent_turnover'].includes(event.type)) {
                    hasSeenTurnover = true;
                    continue; // Skip to processing the turnover event itself
                }

                // Skip events we don't visualize
                if (!['pass', 'goal', 'drop', 'throwaway', 'stall'].includes(event.type)) {
                    continue;
                }

                // Only include events that have coordinates
                const hasCoords = (event.thrower_x !== null && event.thrower_x !== undefined) ||
                                  (event.receiver_x !== null && event.receiver_x !== undefined) ||
                                  (event.turnover_x !== null && event.turnover_x !== undefined);

                if (!hasCoords) continue;

                this.allEvents.push({
                    type: event.type,
                    thrower_x: event.thrower_x ?? null,
                    thrower_y: event.thrower_y ?? null,
                    receiver_x: event.receiver_x ?? null,
                    receiver_y: event.receiver_y ?? null,
                    turnover_x: event.turnover_x ?? null,
                    turnover_y: event.turnover_y ?? null,
                    thrower_name: event.description?.match(/from (\w+)/)?.[1],
                    receiver_name: event.description?.match(/to (\w+)/)?.[1],
                    thrower_id: event.thrower_id,
                    receiver_id: event.receiver_id,
                    quarter: point.quarter,
                    point_number: point.point_number,
                    line_type: point.line_type,
                    team: point.team,
                    is_after_turnover: hasSeenTurnover
                });
            }
        }
    }

    private computeFilterCounts(): void {
        // Filter events by current team first
        const teamEvents = this.allEvents.filter(e => e.team === this.filterState.team);

        // Build player list with counts
        const playerCounts = new Map<string, { name: string; count: number }>();
        teamEvents.forEach(event => {
            // Count throwers
            if (event.thrower_name) {
                const key = event.thrower_name;
                const existing = playerCounts.get(key) || { name: event.thrower_name, count: 0 };
                existing.count++;
                playerCounts.set(key, existing);
            }
            // Count receivers
            if (event.receiver_name && event.type !== 'drop' && event.type !== 'throwaway') {
                const key = event.receiver_name;
                const existing = playerCounts.get(key) || { name: event.receiver_name, count: 0 };
                existing.count++;
                playerCounts.set(key, existing);
            }
        });

        this.playerList = Array.from(playerCounts.entries())
            .map(([id, info]) => ({ id, name: info.name, count: info.count }))
            .sort((a, b) => a.name.localeCompare(b.name));

        // If players filter is empty, select all players
        if (this.filterState.players.size === 0) {
            this.playerList.forEach(p => this.filterState.players.add(p.id));
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
    }

    private getFilteredEvents(): FieldMapEvent[] {
        return this.allEvents.filter(event => {
            // Team filter
            if (event.team !== this.filterState.team) return false;

            // Player filter - check if thrower or receiver is in selected players
            const playerMatch =
                (event.thrower_name && this.filterState.players.has(event.thrower_name)) ||
                (event.receiver_name && this.filterState.players.has(event.receiver_name));
            if (!playerMatch) return false;

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

            return true;
        });
    }

    public renderFieldMap(homeCity?: string, awayCity?: string): void {
        this.container = document.getElementById('field-map');
        if (!this.container) return;

        // Store cities if provided
        if (homeCity !== undefined) this.homeCity = homeCity;
        if (awayCity !== undefined) this.awayCity = awayCity;

        const html = `
            <div class="field-map-container">
                <div class="field-map-filters">
                    ${this.renderTeamFilter()}
                    ${this.renderPlayerFilter()}
                    ${this.renderEventTypeFilter()}
                    ${this.renderLineTypeFilter()}
                    ${this.renderPeriodFilter()}
                </div>
                <div class="field-map-canvas">
                    <div class="field-svg-wrapper">
                        ${this.renderSVGField()}
                    </div>
                    ${this.renderLegend()}
                </div>
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
                    <span class="filter-group-title">Filter by team</span>
                </div>
                <div class="field-map-team-toggle">
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
            <div class="filter-group">
                <div class="filter-group-header">
                    <span class="filter-group-title">Select Player</span>
                    <div class="filter-group-actions">
                        <button class="filter-action-btn select-all-btn" data-filter="players">Select all</button>
                        <button class="filter-action-btn deselect-all-btn" data-filter="players">Deselect all</button>
                    </div>
                </div>
                <div class="filter-checkbox-list player-filter-list">
                    ${this.playerList.map(player => `
                        <div class="filter-checkbox-item">
                            <input type="checkbox" id="player-${player.id}"
                                   data-filter="player" data-value="${player.id}"
                                   ${this.filterState.players.has(player.id) ? 'checked' : ''}>
                            <label for="player-${player.id}">${player.name}</label>
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
            <div class="filter-group">
                <div class="filter-group-header">
                    <span class="filter-group-title">Select Event</span>
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
            <div class="filter-group">
                <div class="filter-group-header">
                    <span class="filter-group-title">Select Line</span>
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
            <div class="filter-group">
                <div class="filter-group-header">
                    <span class="filter-group-title">Select Period</span>
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

    private renderSVGField(): string {
        // SVG viewBox: 533 wide (53.3 yards * 10), 1200 tall (120 yards * 10)
        // Field is oriented with north (attacking) endzone at top
        return `
            <svg viewBox="0 0 533 1200" class="field-map-svg" id="fieldMapSvg">
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

    private createEventElement(event: FieldMapEvent): SVGGElement | null {
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
            <div class="field-map-legend">
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

    private attachEventListeners(): void {
        // Team filter buttons
        document.querySelectorAll('.field-map-team-toggle .team-filter-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const team = (e.target as HTMLElement).dataset.team as 'home' | 'away';
                if (team && team !== this.filterState.team) {
                    this.filterState.team = team;
                    // Reset player selection when team changes
                    this.filterState.players.clear();
                    this.computeFilterCounts();
                    this.renderFieldMap();
                }
            });
        });

        // Player checkboxes
        document.querySelectorAll('[data-filter="player"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const input = e.target as HTMLInputElement;
                const playerId = input.dataset.value!;
                if (input.checked) {
                    this.filterState.players.add(playerId);
                } else {
                    this.filterState.players.delete(playerId);
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
            case 'players':
                this.playerList.forEach(p => this.filterState.players.add(p.id));
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
        }
        this.renderFieldMap();
    }

    private deselectAll(filterType: string): void {
        switch (filterType) {
            case 'players':
                this.filterState.players.clear();
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
        }
        this.renderFieldMap();
    }
}

export default GameFieldMap;
