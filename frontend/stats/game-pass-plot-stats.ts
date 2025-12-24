/**
 * Statistics calculation for Game Pass Plot
 */

import type { PassPlotEvent, PassPlotStats } from './game-pass-plot-types';

/**
 * Calculate yards gained/lost for a pass event
 */
export function calculateYards(event: PassPlotEvent): number | null {
    const destY = event.receiver_y ?? event.turnover_y;
    if (event.thrower_y === null || destY === null) {
        return null;
    }
    return destY - event.thrower_y;
}

/**
 * Classify pass type based on coordinates
 * - Huck: 40+ yards forward
 * - Dish: Under 5 yards total distance
 * - Dump: Short backward throw
 * - Swing: Lateral throw (more horizontal than vertical)
 * - Gainer: Short-medium forward throw
 */
export function classifyPassType(event: PassPlotEvent): string | null {
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

/**
 * Compute aggregated statistics from filtered events
 */
export function computeStats(filteredEvents: PassPlotEvent[]): PassPlotStats {
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
        // Count throws (pass, goal, throwaway, drop events)
        if (['pass', 'goal', 'throwaway', 'drop'].includes(event.type)) {
            totalThrows++;

            // Calculate yards
            const yards = calculateYards(event);
            if (yards !== null) {
                totalYards += yards;
            }

            // Classify pass type and count (includes turnovers)
            const passType = classifyPassType(event);
            if (passType && byType[passType]) {
                byType[passType].count++;
            }
        }

        // Count results
        if (event.type === 'goal') {
            goals++;
            completions++;
            const yards = calculateYards(event);
            if (yards !== null) {
                completionYards += yards;
            }
        } else if (event.type === 'pass') {
            completions++;
            const yards = calculateYards(event);
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

/**
 * Render the stats panel HTML
 */
export function renderStatsPanel(stats: PassPlotStats): string {
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
