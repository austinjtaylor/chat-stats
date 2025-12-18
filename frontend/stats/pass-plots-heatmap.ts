/**
 * Heatmap rendering utilities for Pass Plots
 */

import type { PassEvent } from './pass-plots-types';
import { fieldXToSVG, fieldYToSVG } from './pass-plots-field';

interface Point {
    x: number;
    y: number;
}

interface RGB {
    r: number;
    g: number;
    b: number;
}

function getHeatmapColorRGB(intensity: number): RGB {
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

    return { r, g, b };
}

function drawYardLinesAndNumbers(ctx: CanvasRenderingContext2D, width: number): void {
    // Draw yard lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    for (let yard = 20; yard <= 100; yard += 5) {
        const y = fieldYToSVG(yard);
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
        const y = fieldYToSVG(fieldY);
        const displayYard = fieldY <= 50 ? fieldY : 100 - fieldY;
        ctx.textAlign = 'left';
        ctx.fillText(String(displayYard), 20, y);
        ctx.textAlign = 'right';
        ctx.fillText(String(displayYard), 513, y);
    }
}

function collectPoints(events: PassEvent[], type: 'origin' | 'dest'): Point[] {
    const points: Point[] = [];

    events.forEach(event => {
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
            x: fieldXToSVG(x),
            y: fieldYToSVG(y)
        });
    });

    return points;
}

function computeDensityGrid(
    points: Point[],
    width: number,
    height: number,
    gridScale: number
): { density: Float32Array; gridWidth: number; gridHeight: number } {
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

    return { density, gridWidth, gridHeight };
}

function findNormalizationValue(density: Float32Array): number {
    // Find normalization value using percentile on non-zero values
    const nonZeroValues: number[] = [];
    for (let i = 0; i < density.length; i++) {
        if (density[i] > 0.01) {
            nonZeroValues.push(density[i]);
        }
    }

    if (nonZeroValues.length === 0) {
        return 1;
    }

    // Use 98th percentile for normalization - higher value means more blue/green
    nonZeroValues.sort((a, b) => a - b);
    const percentileIndex = Math.floor(nonZeroValues.length * 0.98);
    return nonZeroValues[percentileIndex] || nonZeroValues[nonZeroValues.length - 1];
}

function renderDensityToCanvas(
    ctx: CanvasRenderingContext2D,
    density: Float32Array,
    gridWidth: number,
    gridHeight: number,
    gridScale: number,
    width: number,
    height: number,
    normValue: number
): void {
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
                    const color = getHeatmapColorRGB(intensity);
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
}

function drawFieldBackground(ctx: CanvasRenderingContext2D, width: number, height: number): void {
    ctx.globalCompositeOperation = 'destination-over';
    ctx.fillStyle = '#2D5A27';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = '#1E3F1B';
    ctx.fillRect(0, 0, width, 200);
    ctx.fillRect(0, 1000, width, 200);
    ctx.globalCompositeOperation = 'source-over';
}

export function renderHeatmap(
    container: HTMLElement,
    events: PassEvent[],
    type: 'origin' | 'dest'
): void {
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
    const points = collectPoints(events, type);

    if (points.length === 0) {
        container.appendChild(canvas);
        drawYardLinesAndNumbers(ctx, width);
        return;
    }

    // Compute density grid
    const gridScale = 4; // Each grid cell = 4x4 pixels
    const { density, gridWidth, gridHeight } = computeDensityGrid(points, width, height, gridScale);

    // Find normalization value
    const normValue = findNormalizationValue(density);

    if (normValue === 1 && points.length > 0) {
        // Edge case: all density values were filtered out
        container.appendChild(canvas);
        drawYardLinesAndNumbers(ctx, width);
        return;
    }

    // Render density to canvas
    renderDensityToCanvas(ctx, density, gridWidth, gridHeight, gridScale, width, height, normValue);

    // Redraw field background behind the heatmap
    drawFieldBackground(ctx, width, height);

    // Draw yard lines and numbers on top
    drawYardLinesAndNumbers(ctx, width);

    container.appendChild(canvas);
}
