/**
 * SVG field rendering for Game Pass Plot
 */

import type { PassPlotEvent } from './game-pass-plot-types';

/**
 * Convert field Y coordinate to SVG Y coordinate
 * Field y: 0-120 yards -> SVG y: 1200-0 (inverted, north is top)
 */
export function fieldYToSVG(fieldY: number): number {
    return (120 - fieldY) * 10;
}

/**
 * Convert field X coordinate to SVG X coordinate
 * Field x is centered at 0, ranging from about -26.65 to 26.65
 * SVG x: 0-533 (center at 266.5)
 */
export function fieldXToSVG(fieldX: number): number {
    return (fieldX * 10) + 266.5;
}

/**
 * Get color for event type
 */
export function getEventColor(eventType: string): string {
    switch (eventType) {
        case 'pass': return '#3B82F6'; // Blue
        case 'goal': return '#22C55E'; // Green
        case 'drop': return '#EF4444'; // Red
        case 'throwaway': return '#EF4444'; // Red
        case 'stall': return '#8B5CF6'; // Purple
        default: return '#9CA3AF'; // Gray
    }
}

/**
 * Get marker shape for event type
 */
export function getMarkerShape(eventType: string): 'square' | 'circle' {
    return eventType === 'drop' ? 'circle' : 'square';
}

/**
 * Render yard lines HTML
 */
function renderYardLines(): string {
    const lines: string[] = [];
    // Draw lines every 5 yards from 20 to 100 (playable field)
    for (let yard = 20; yard <= 100; yard += 5) {
        const y = fieldYToSVG(yard);
        lines.push(`<line x1="0" y1="${y}" x2="533" y2="${y}"/>`);
    }
    return lines.join('');
}

/**
 * Render yard numbers HTML
 */
function renderYardNumbers(): string {
    const numbers: string[] = [];
    // Show numbers at 10-yard intervals (30, 40, 50, 60, 70, 80, 90)
    for (let yard = 30; yard <= 90; yard += 10) {
        const y = fieldYToSVG(yard) + 8; // Offset for text baseline
        const displayYard = yard <= 50 ? yard : 100 - yard; // Mirror for far side
        numbers.push(`<text x="20" y="${y}">${displayYard}</text>`);
        numbers.push(`<text x="513" y="${y}" text-anchor="end">${displayYard}</text>`);
    }
    return numbers.join('');
}

/**
 * Render the main SVG field HTML
 */
export function renderSVGField(): string {
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
                ${renderYardLines()}
            </g>

            <!-- Yard numbers -->
            <g class="field-yard-numbers">
                ${renderYardNumbers()}
            </g>

            <!-- Events layer -->
            <g class="field-events" id="fieldEventsLayer">
                <!-- Events will be added dynamically -->
            </g>
        </svg>
    `;
}

/**
 * Create SVG element for a single event
 */
export function createEventElement(event: PassPlotEvent): SVGGElement | null {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.classList.add('field-event');

    const color = getEventColor(event.type);
    const markerShape = getMarkerShape(event.type);

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
        line.setAttribute('x1', String(fieldXToSVG(startX)));
        line.setAttribute('y1', String(fieldYToSVG(startY)));
        line.setAttribute('x2', String(fieldXToSVG(endX)));
        line.setAttribute('y2', String(fieldYToSVG(endY)));
        line.setAttribute('stroke', color);
        line.setAttribute('stroke-width', '2');
        line.setAttribute('stroke-opacity', '0.6');
        g.appendChild(line);
    }

    // Draw marker at end position
    if (endX !== null && endY !== null) {
        const svgX = fieldXToSVG(endX);
        const svgY = fieldYToSVG(endY);

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

/**
 * Render events on the field SVG
 */
export function renderEventsOnField(filteredEvents: PassPlotEvent[]): void {
    const eventsLayer = document.getElementById('fieldEventsLayer');
    if (!eventsLayer) return;

    // Clear existing events
    eventsLayer.innerHTML = '';

    // Create SVG elements for each event
    filteredEvents.forEach(event => {
        const element = createEventElement(event);
        if (element) {
            eventsLayer.appendChild(element);
        }
    });
}

/**
 * Render the legend HTML
 */
export function renderLegend(): string {
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
