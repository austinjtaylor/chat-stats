/**
 * SVG field rendering for Game Pass Plot
 */

import type { PassPlotEvent } from './game-pass-plot-types';

/**
 * Info about which players are selected in filters (for solid/hollow styling)
 */
export interface HighlightInfo {
    selectedThrowers: Set<string>;
    selectedReceivers: Set<string>;
}

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

// Marker sizes
const SQUARE_HALF_SIZE = 5;  // Square is 10x10, slightly larger than circle
const CIRCLE_RADIUS = 5;

/**
 * Get or create the tooltip element
 */
function getOrCreateTooltip(): HTMLElement {
    let tooltip = document.querySelector('.pass-plot-tooltip') as HTMLElement;
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.className = 'pass-plot-tooltip';
        document.body.appendChild(tooltip);
    }
    return tooltip;
}

/**
 * Format tooltip content based on event type
 */
function formatTooltipContent(event: PassPlotEvent): string {
    const thrower = event.thrower_name || 'Unknown';
    const receiver = event.receiver_name || 'Unknown';

    switch (event.type) {
        case 'pass':
            return `${thrower} → ${receiver}`;
        case 'goal':
            return `${thrower} → ${receiver} - Goal`;
        case 'drop':
            return `${thrower} → ${receiver} - Drop`;
        case 'throwaway':
            return `${thrower} - Throwaway`;
        case 'stall':
            return `${thrower} - Stall`;
        default:
            return `${thrower} → ${receiver}`;
    }
}

/**
 * Create SVG element for a single event
 */
export function createEventElement(event: PassPlotEvent, highlightInfo: HighlightInfo): SVGGElement | null {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.classList.add('field-event');

    const color = getEventColor(event.type);

    // Determine if thrower/receiver are highlighted (selected in filters)
    // Use thrower_name/receiver_name since that's what the filter uses as IDs
    const throwerHighlighted = highlightInfo.selectedThrowers.has(event.thrower_name || '');
    const receiverHighlighted = highlightInfo.selectedReceivers.has(event.receiver_name || '');

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

    // Calculate line endpoints that stop at marker edges
    if (startX !== null && startY !== null && endX !== null && endY !== null) {
        const svgStartX = fieldXToSVG(startX);
        const svgStartY = fieldYToSVG(startY);
        const svgEndX = fieldXToSVG(endX);
        const svgEndY = fieldYToSVG(endY);

        // Calculate line direction and length
        const dx = svgEndX - svgStartX;
        const dy = svgEndY - svgStartY;
        const length = Math.sqrt(dx * dx + dy * dy);

        if (length > 0) {
            // Normalize direction
            const nx = dx / length;
            const ny = dy / length;

            // Shorten line by marker sizes at each end
            const lineStartX = svgStartX + nx * SQUARE_HALF_SIZE;
            const lineStartY = svgStartY + ny * SQUARE_HALF_SIZE;
            const lineEndX = svgEndX - nx * CIRCLE_RADIUS;
            const lineEndY = svgEndY - ny * CIRCLE_RADIUS;

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', String(lineStartX));
            line.setAttribute('y1', String(lineStartY));
            line.setAttribute('x2', String(lineEndX));
            line.setAttribute('y2', String(lineEndY));
            line.setAttribute('stroke', color);
            line.setAttribute('stroke-width', '2');
            line.setAttribute('stroke-opacity', '0.6');
            g.appendChild(line);
        }
    }

    // Draw end marker (circle) FIRST so square overlays it when at same position
    if (endX !== null && endY !== null) {
        const svgX = fieldXToSVG(endX);
        const svgY = fieldYToSVG(endY);

        // For passes and goals, use circle at end; for turnovers use square
        const usesCircleEnd = event.type === 'pass' || event.type === 'goal' || event.type === 'drop';

        if (usesCircleEnd) {
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', String(svgX));
            circle.setAttribute('cy', String(svgY));
            circle.setAttribute('r', String(CIRCLE_RADIUS));

            if (receiverHighlighted) {
                circle.setAttribute('fill', color);
                circle.setAttribute('fill-opacity', '0.8');
            } else {
                circle.setAttribute('fill', 'transparent');
                circle.setAttribute('stroke', color);
                circle.setAttribute('stroke-width', '1.5');
            }
            g.appendChild(circle);
        } else {
            // Throwaway and stall use square at end
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', String(svgX - SQUARE_HALF_SIZE));
            rect.setAttribute('y', String(svgY - SQUARE_HALF_SIZE));
            rect.setAttribute('width', String(SQUARE_HALF_SIZE * 2));
            rect.setAttribute('height', String(SQUARE_HALF_SIZE * 2));

            // For turnovers, the end marker inherits thrower's highlight state
            if (throwerHighlighted) {
                rect.setAttribute('fill', color);
                rect.setAttribute('fill-opacity', '0.8');
            } else {
                rect.setAttribute('fill', 'transparent');
                rect.setAttribute('stroke', color);
                rect.setAttribute('stroke-width', '1.5');
            }
            g.appendChild(rect);
        }
    }

    // Draw start marker (square) LAST so it overlays circle when at same position
    if (startX !== null && startY !== null) {
        const svgX = fieldXToSVG(startX);
        const svgY = fieldYToSVG(startY);
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', String(svgX - SQUARE_HALF_SIZE));
        rect.setAttribute('y', String(svgY - SQUARE_HALF_SIZE));
        rect.setAttribute('width', String(SQUARE_HALF_SIZE * 2));
        rect.setAttribute('height', String(SQUARE_HALF_SIZE * 2));

        if (throwerHighlighted) {
            rect.setAttribute('fill', color);
            rect.setAttribute('fill-opacity', '0.8');
        } else {
            rect.setAttribute('fill', 'transparent');
            rect.setAttribute('stroke', color);
            rect.setAttribute('stroke-width', '1.5');
        }
        g.appendChild(rect);
    }

    // Add hover event listeners for tooltip
    g.addEventListener('mouseenter', (e: MouseEvent) => {
        const tooltip = getOrCreateTooltip();
        tooltip.textContent = formatTooltipContent(event);
        tooltip.classList.add('visible');

        // Position tooltip near cursor
        tooltip.style.left = `${e.clientX + 12}px`;
        tooltip.style.top = `${e.clientY + 12}px`;
    });

    g.addEventListener('mousemove', (e: MouseEvent) => {
        const tooltip = getOrCreateTooltip();
        tooltip.style.left = `${e.clientX + 12}px`;
        tooltip.style.top = `${e.clientY + 12}px`;
    });

    g.addEventListener('mouseleave', () => {
        const tooltip = getOrCreateTooltip();
        tooltip.classList.remove('visible');
    });

    return g;
}

/**
 * Render events on the field SVG
 */
export function renderEventsOnField(filteredEvents: PassPlotEvent[], highlightInfo: HighlightInfo): void {
    const eventsLayer = document.getElementById('fieldEventsLayer');
    if (!eventsLayer) return;

    // Clear existing events
    eventsLayer.innerHTML = '';

    // Create SVG elements for each event
    filteredEvents.forEach(event => {
        const element = createEventElement(event, highlightInfo);
        if (element) {
            eventsLayer.appendChild(element);
        }
    });
}

/**
 * Render the legend HTML
 */
export function renderLegend(): string {
    // Legend items with start/end marker info
    // startShape: 'square' | null, endShape: 'square' | 'circle'
    const legendItems = [
        { label: 'Pass', color: '#3B82F6', startShape: 'square', endShape: 'circle' },
        { label: 'Drop', color: '#EF4444', startShape: 'square', endShape: 'circle' },
        { label: 'Throwaway', color: '#EF4444', startShape: 'square', endShape: 'square' },
        { label: 'Stall', color: '#8B5CF6', startShape: null, endShape: 'square' },
        { label: 'Score', color: '#22C55E', startShape: 'square', endShape: 'circle' }
    ];

    return `
        <div class="game-pass-plot-legend">
            ${legendItems.map(item => `
                <div class="legend-item">
                    ${item.startShape ? `<span class="legend-marker square" style="background: ${item.color};"></span>` : ''}
                    <span class="legend-line" style="background: ${item.color};"></span>
                    <span class="legend-marker ${item.endShape}" style="background: ${item.color};"></span>
                    <span class="legend-label">${item.label}</span>
                </div>
            `).join('')}
        </div>
    `;
}
