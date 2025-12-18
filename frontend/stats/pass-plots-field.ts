/**
 * Field SVG rendering utilities for Pass Plots
 */

import type { PassEvent } from './pass-plots-types';

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

export function createEventElement(event: PassEvent): SVGGElement | null {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.classList.add('field-event');

    const color = getEventColor(event.result);

    const startX = event.thrower_x;
    const startY = event.thrower_y;
    const endX = event.receiver_x ?? event.turnover_x;
    const endY = event.receiver_y ?? event.turnover_y;

    if (startX === null || startY === null || endX === null || endY === null) {
        return null;
    }

    // Draw line
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', String(fieldXToSVG(startX)));
    line.setAttribute('y1', String(fieldYToSVG(startY)));
    line.setAttribute('x2', String(fieldXToSVG(endX)));
    line.setAttribute('y2', String(fieldYToSVG(endY)));
    line.setAttribute('stroke', color);
    line.setAttribute('stroke-width', '2');
    line.setAttribute('stroke-opacity', '0.5');
    g.appendChild(line);

    // Draw end marker
    const svgX = fieldXToSVG(endX);
    const svgY = fieldYToSVG(endY);

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', String(svgX));
    circle.setAttribute('cy', String(svgY));
    circle.setAttribute('r', '4');
    circle.setAttribute('fill', color);
    circle.setAttribute('fill-opacity', '0.7');
    g.appendChild(circle);

    return g;
}

export function renderThrowLines(container: HTMLElement, events: PassEvent[]): void {
    const svg = createFieldSVG();
    const eventsGroup = svg.querySelector('#fieldEventsLayer');

    if (eventsGroup) {
        events.forEach(event => {
            const element = createEventElement(event);
            if (element) {
                eventsGroup.appendChild(element);
            }
        });
    }

    container.appendChild(svg);
}
