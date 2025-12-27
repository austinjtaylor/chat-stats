/**
 * Field SVG rendering utilities for Pass Plots
 */

import type { PassEvent } from './pass-plots-types';

/**
 * Info about which event types are in focus (for solid/hollow styling)
 */
export interface HighlightInfo {
    throwsInFocus: boolean;      // Is "Throws" event type selected?
    catchesInFocus: boolean;     // Is "Catches" event type selected?
    assistsInFocus: boolean;     // Is "Assists" event type selected?
    goalsInFocus: boolean;       // Is "Goals" event type selected?
    throwawaysInFocus: boolean;  // Is "Throwaways" event type selected?
    dropsInFocus: boolean;       // Is "Drops" event type selected?
}

// Coordinate conversion utilities
export function fieldYToSVG(fieldY: number): number {
    return (120 - fieldY) * 10;
}

export function fieldXToSVG(fieldX: number): number {
    return (fieldX * 10) + 266.5;
}

// Color utilities
export function getEventColor(result: string): string {
    switch (result) {
        case 'goal': return '#22C55E';
        case 'completion': return '#3B82F6';
        case 'turnover': return '#EF4444';
        default: return '#9CA3AF';
    }
}

// SVG generation
function renderYardLines(): string {
    const lines: string[] = [];
    for (let yard = 20; yard <= 100; yard += 5) {
        const y = fieldYToSVG(yard);
        lines.push(`<line x1="0" y1="${y}" x2="533" y2="${y}"/>`);
    }
    return lines.join('');
}

function renderYardNumbers(): string {
    const numbers: string[] = [];
    for (let yard = 30; yard <= 90; yard += 10) {
        const y = fieldYToSVG(yard) + 8;
        const displayYard = yard <= 50 ? yard : 100 - yard;
        numbers.push(`<text x="20" y="${y}">${displayYard}</text>`);
        numbers.push(`<text x="513" y="${y}" text-anchor="end">${displayYard}</text>`);
    }
    return numbers.join('');
}

export function createFieldSVG(): SVGSVGElement {
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
            ${renderYardLines()}
        </g>

        <!-- Yard numbers -->
        <g class="field-yard-numbers">
            ${renderYardNumbers()}
        </g>

        <!-- Events layer -->
        <g class="field-events" id="fieldEventsLayer"></g>
    `;

    return svg;
}

// Marker sizes
const SQUARE_HALF_SIZE = 5;
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
 * Format pass type label
 */
function formatPassType(passType: string | null): string {
    if (!passType) return '';
    const labels: Record<string, string> = {
        huck: 'Huck',
        swing: 'Swing',
        dump: 'Dump',
        gainer: 'Gainer',
        dish: 'Dish'
    };
    return labels[passType] || passType;
}

/**
 * Get event type label from event_type number
 */
function getEventTypeLabel(event: PassEvent): string {
    const isDrop = event.event_type === 20;
    const isThrowaway = event.event_type === 22;
    const isGoal = event.result === 'goal';

    if (isGoal) return 'Goal';
    if (isDrop) return 'Drop';
    if (isThrowaway) return 'Throwaway';
    return 'Pass';
}

/**
 * Format tooltip content based on event type
 */
function formatTooltipContent(event: PassEvent): string {
    const thrower = event.thrower_name || 'Unknown';
    const receiver = event.receiver_name || 'Unknown';
    const verticalYards = event.vertical_yards;
    const passType = event.pass_type;

    // Build yards string (e.g., "+15 yds" or "-5 yds")
    const yardsStr = verticalYards !== null
        ? ` (${verticalYards >= 0 ? '+' : ''}${verticalYards} yds)`
        : '';

    // Build pass type string
    const passTypeStr = passType ? ` · ${formatPassType(passType)}` : '';

    const eventType = getEventTypeLabel(event);

    if (event.event_type === 22) {
        // Throwaway - no receiver
        return `${thrower} - Throwaway${yardsStr}${passTypeStr}`;
    } else if (eventType === 'Goal') {
        return `${thrower} → ${receiver} - Goal${yardsStr}${passTypeStr}`;
    } else if (eventType === 'Drop') {
        return `${thrower} → ${receiver} - Drop${yardsStr}${passTypeStr}`;
    } else {
        return `${thrower} → ${receiver}${yardsStr}${passTypeStr}`;
    }
}

export function createEventElement(event: PassEvent, highlightInfo: HighlightInfo): SVGGElement | null {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.classList.add('field-event');

    const eventColor = getEventColor(event.result);

    // Determine if this is a drop (event_type 20) vs throwaway (event_type 22)
    const isDrop = event.event_type === 20;
    const isThrowaway = event.event_type === 22;
    const isGoal = event.result === 'goal';
    const isCompletion = event.result === 'completion';

    // For drops: thrower threw a good pass (blue), receiver dropped it (red)
    const throwerColor = isDrop ? '#3B82F6' : eventColor;
    const receiverColor = eventColor;
    const lineColor = eventColor;

    const startX = event.thrower_x;
    const startY = event.thrower_y;
    const endX = event.receiver_x ?? event.turnover_x;
    const endY = event.receiver_y ?? event.turnover_y;

    if (startX === null || startY === null || endX === null || endY === null) {
        return null;
    }

    const svgStartX = fieldXToSVG(startX);
    const svgStartY = fieldYToSVG(startY);
    const svgEndX = fieldXToSVG(endX);
    const svgEndY = fieldYToSVG(endY);

    // Determine if this event type has an end marker (throwaways don't)
    const hasEndMarker = !isThrowaway;

    // Calculate line endpoints that stop at marker edges
    const dx = svgEndX - svgStartX;
    const dy = svgEndY - svgStartY;
    const length = Math.sqrt(dx * dx + dy * dy);

    if (length > 0) {
        const nx = dx / length;
        const ny = dy / length;

        const lineStartX = svgStartX + nx * SQUARE_HALF_SIZE;
        const lineStartY = svgStartY + ny * SQUARE_HALF_SIZE;
        // Only shorten line end if there's an end marker
        const lineEndX = hasEndMarker ? svgEndX - nx * CIRCLE_RADIUS : svgEndX;
        const lineEndY = hasEndMarker ? svgEndY - ny * CIRCLE_RADIUS : svgEndY;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', String(lineStartX));
        line.setAttribute('y1', String(lineStartY));
        line.setAttribute('x2', String(lineEndX));
        line.setAttribute('y2', String(lineEndY));
        line.setAttribute('stroke', lineColor);
        line.setAttribute('stroke-width', '2');
        line.setAttribute('stroke-opacity', '0.5');
        g.appendChild(line);
    }

    // Helper to create start marker (square)
    const createStartMarker = (): SVGRectElement => {
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', String(svgStartX - SQUARE_HALF_SIZE));
        rect.setAttribute('y', String(svgStartY - SQUARE_HALF_SIZE));
        rect.setAttribute('width', String(SQUARE_HALF_SIZE * 2));
        rect.setAttribute('height', String(SQUARE_HALF_SIZE * 2));

        // Thrower square is filled based on event type focus
        // - Never for drops (focus is on the drop, not the throw)
        const shouldFill = !isDrop && (
            (isCompletion && highlightInfo.throwsInFocus) ||
            (isGoal && highlightInfo.assistsInFocus) ||
            (isThrowaway && highlightInfo.throwawaysInFocus)
        );

        if (shouldFill) {
            rect.setAttribute('fill', throwerColor);
            rect.setAttribute('fill-opacity', '0.7');
        } else {
            rect.setAttribute('fill', 'transparent');
            rect.setAttribute('stroke', throwerColor);
            rect.setAttribute('stroke-width', '1.5');
        }
        return rect;
    };

    // Helper to create end marker (circle)
    const createEndMarker = (): SVGCircleElement => {
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', String(svgEndX));
        circle.setAttribute('cy', String(svgEndY));
        circle.setAttribute('r', String(CIRCLE_RADIUS));

        // Receiver circle is filled based on event type focus
        const shouldFill = (
            isDrop ||  // Drops always focus on receiver
            (isGoal && highlightInfo.goalsInFocus) ||
            (isCompletion && highlightInfo.catchesInFocus)
        );

        if (shouldFill) {
            circle.setAttribute('fill', receiverColor);
            circle.setAttribute('fill-opacity', '0.7');
        } else {
            circle.setAttribute('fill', 'transparent');
            circle.setAttribute('stroke', receiverColor);
            circle.setAttribute('stroke-width', '1.5');
        }
        return circle;
    };

    // Draw markers in correct order based on event type
    // For drops: square first, then circle (red circle overlays blue square at same position)
    // For throwaways: only square (no end marker)
    // For other events: circle first, then square (square overlays circle at same position)
    if (isThrowaway) {
        g.appendChild(createStartMarker());
    } else if (isDrop) {
        g.appendChild(createStartMarker());
        g.appendChild(createEndMarker());
    } else {
        g.appendChild(createEndMarker());
        g.appendChild(createStartMarker());
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

export function renderThrowLines(container: HTMLElement, events: PassEvent[], highlightInfo: HighlightInfo): void {
    const svg = createFieldSVG();
    const eventsGroup = svg.querySelector('#fieldEventsLayer');

    if (eventsGroup) {
        events.forEach(event => {
            const element = createEventElement(event, highlightInfo);
            if (element) {
                eventsGroup.appendChild(element);
            }
        });
    }

    container.appendChild(svg);
}
