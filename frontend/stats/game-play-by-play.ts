/**
 * Game Play-by-Play Component - Handles play-by-play rendering
 */

export interface PlayByPlayEvent {
    type: string;
    description: string;
    yard_line: number | null;
    direction?: number;  // Angle in degrees for pass direction
}

export interface PlayByPlayPoint {
    point_number: number;
    quarter: number;
    score: string;
    home_score: number;
    away_score: number;
    team: string;
    line_type: string;
    start_time: number;
    duration_seconds: number;
    duration: string;
    time: string;
    players: string[];
    pulling_team: string;
    receiving_team: string;
    scoring_team: string | null;
    events: PlayByPlayEvent[];
}

export interface PlayByPlayData {
    points: PlayByPlayPoint[];
}

export class GamePlayByPlay {
    private playByPlayData: PlayByPlayData | null = null;
    private expandedPoints: Set<number> = new Set();
    private playByPlayFilter: 'home' | 'away' = 'home';

    // City abbreviations cache
    private getCityAbbreviation: (city: string) => string;

    constructor(getCityAbbreviation: (city: string) => string) {
        this.getCityAbbreviation = getCityAbbreviation;
    }

    public async loadPlayByPlay(gameId: string): Promise<void> {
        try {
            const response = await fetch(`/api/games/${gameId}/play-by-play`);
            this.playByPlayData = await response.json();
            this.renderPlayByPlay();
        } catch (error) {
            console.error('Failed to load play-by-play:', error);
        }
    }

    public renderPlayByPlay(homeCity?: string, awayCity?: string): void {
        const container = document.getElementById('play-by-play');
        if (!container || !this.playByPlayData) return;

        // Filter points based on team filter
        let points = this.playByPlayData.points;
        points = points.filter(point => point.team === this.playByPlayFilter);

        // Group points by quarter
        const quarters = new Map<number, PlayByPlayPoint[]>();
        points.forEach(point => {
            if (!quarters.has(point.quarter)) {
                quarters.set(point.quarter, []);
            }
            quarters.get(point.quarter)!.push(point);
        });

        const html = `
            <div class="play-by-play-container">
                <div class="play-by-play-header">
                    <div class="filter-section">
                        <span>Filter by team</span>
                        <div class="team-filter-buttons">
                            <button class="team-filter-btn ${this.playByPlayFilter === 'away' ? 'active' : ''}"
                                    data-team="away">${awayCity ? this.getCityAbbreviation(awayCity) : 'AWAY'}</button>
                            <button class="team-filter-btn ${this.playByPlayFilter === 'home' ? 'active' : ''}"
                                    data-team="home">${homeCity ? this.getCityAbbreviation(homeCity) : 'HOME'}</button>
                        </div>
                    </div>
                    <div class="control-section">
                        <button class="expand-all-btn" id="expandAllBtn">Expand all</button>
                        <button class="collapse-all-btn" id="collapseAllBtn">Collapse all</button>
                    </div>
                </div>

                <div class="points-list">
                    ${Array.from(quarters.entries()).map(([quarter, quarterPoints]) => `
                        <div class="quarter-section">
                            <h3 class="quarter-header">${this.getQuarterName(quarter)}</h3>
                            ${quarterPoints.map(point => this.renderPoint(point)).join('')}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        container.innerHTML = html;
        this.attachPlayByPlayListeners();
    }

    private renderPoint(point: PlayByPlayPoint): string {
        const isExpanded = this.expandedPoints.has(point.point_number);
        const isHomePoint = point.team === 'home';

        // Determine point color based on scoring team
        let pointClass = 'point-item';
        if (point.scoring_team === 'home' && isHomePoint) {
            pointClass += ' point-scored';  // Green for team score
        } else if (point.scoring_team === 'away' && !isHomePoint) {
            pointClass += ' point-scored';  // Green for team score
        } else if (point.scoring_team && point.scoring_team !== point.team) {
            pointClass += ' point-conceded';  // Red for opponent score
        } else if (point.home_score === point.away_score) {
            pointClass += ' point-tie';  // Blue for tie
        }

        return `
            <div class="${pointClass}" data-point="${point.point_number}">
                <div class="point-header" data-point="${point.point_number}">
                    <span class="expand-icon">${isExpanded ? '▼' : '▶'}</span>
                    <span class="point-score">${point.score}</span>
                    <span class="point-line-type">${point.line_type}</span>
                    <span class="point-time">${point.time}</span>
                    <span class="point-duration">${point.duration}</span>
                    <span class="point-players">${point.players.join(', ')}</span>
                </div>
                ${isExpanded ? `
                    <div class="point-details">
                        ${point.events.map(event => this.renderEvent(event)).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }

    private renderEvent(event: PlayByPlayEvent): string {
        // Determine icon based on event type and description
        let iconHtml = '<span class="event-icon">•</span>';

        if (event.type === 'pull') {
            iconHtml = '<span class="event-icon">↗</span>';
        } else if (event.type === 'pass' || event.type === 'goal') {
            // Use SVG arrow with rotation for passes and goals
            if (event.direction !== undefined) {
                // Adjust angle: 0° is East, we want 0° to be North (up)
                // So we subtract 90 degrees
                const rotationAngle = event.direction - 90;

                iconHtml = `
                    <span class="event-icon" style="display: inline-block; transform: rotate(${rotationAngle}deg);">
                        ↑
                    </span>
                `;
            } else {
                // Fallback for passes without direction
                if (event.type === 'goal') {
                    iconHtml = '<span class="event-icon">⚑</span>';
                } else {
                    const description = event.description.toLowerCase();
                    if (description.includes('dump')) {
                        iconHtml = '<span class="event-icon">↙</span>';
                    } else if (description.includes('huck')) {
                        iconHtml = '<span class="event-icon">↗</span>';
                    } else {
                        iconHtml = '<span class="event-icon">→</span>';
                    }
                }
            }
        } else if (event.type === 'block') {
            iconHtml = '<span class="event-icon">🛡</span>';
        } else if (event.type === 'drop') {
            iconHtml = '<span class="event-icon">↓</span>';
        } else if (event.type === 'throwaway') {
            // Use direction if available for throwaways, similar to passes
            if (event.direction !== undefined) {
                const rotationAngle = event.direction - 90;
                iconHtml = `
                    <span class="event-icon" style="display: inline-block; transform: rotate(${rotationAngle}deg);">
                        ↑
                    </span>
                `;
            } else {
                iconHtml = '<span class="event-icon">↘</span>';
            }
        } else if (event.type === 'stall') {
            iconHtml = '<span class="event-icon">⏱</span>';
        }

        const yardLine = event.yard_line !== null ? `${event.yard_line}y` : '';

        return `
            <div class="event-item">
                ${iconHtml}
                <span class="event-yard">${yardLine}</span>
                <span class="event-description">${event.description}</span>
            </div>
        `;
    }

    private attachPlayByPlayListeners(): void {
        // Team filter buttons
        document.querySelectorAll('.team-filter-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const team = (e.target as HTMLElement).dataset.team as 'home' | 'away';
                if (team) {
                    this.playByPlayFilter = team;
                    // Re-render with current game data
                    this.renderPlayByPlay();
                }
            });
        });

        // Expand/Collapse all buttons
        const expandAllBtn = document.getElementById('expandAllBtn');
        const collapseAllBtn = document.getElementById('collapseAllBtn');

        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', () => {
                this.playByPlayData?.points.forEach(point => {
                    this.expandedPoints.add(point.point_number);
                });
                this.renderPlayByPlay();
            });
        }

        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', () => {
                this.expandedPoints.clear();
                this.renderPlayByPlay();
            });
        }

        // Point expand/collapse
        document.querySelectorAll('.point-header').forEach(header => {
            header.addEventListener('click', (e) => {
                const pointNumber = parseInt((e.currentTarget as HTMLElement).dataset.point || '0');
                if (this.expandedPoints.has(pointNumber)) {
                    this.expandedPoints.delete(pointNumber);
                } else {
                    this.expandedPoints.add(pointNumber);
                }
                this.renderPlayByPlay();
            });
        });
    }

    private getQuarterName(quarter: number): string {
        switch (quarter) {
            case 1: return 'First Quarter';
            case 2: return 'Second Quarter';
            case 3: return 'Third Quarter';
            case 4: return 'Fourth Quarter';
            case 5: return 'Overtime';
            default: return `Quarter ${quarter}`;
        }
    }
}

export default GamePlayByPlay;