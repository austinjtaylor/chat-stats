/**
 * Data loading and event extraction for Game Pass Plot
 */

import type { PassPlotEvent, PlayByPlayData } from './game-pass-plot-types';

/**
 * Extract PassPlotEvents from raw play-by-play data
 */
export function extractEventsFromPoints(playByPlayData: PlayByPlayData): PassPlotEvent[] {
    const allEvents: PassPlotEvent[] = [];

    for (const point of playByPlayData.points) {
        for (const event of point.events) {
            // Skip events we don't visualize
            if (!['pass', 'goal', 'drop', 'throwaway', 'stall'].includes(event.type)) {
                continue;
            }

            // Only include events that have coordinates
            const hasCoords = (event.thrower_x !== null && event.thrower_x !== undefined) ||
                              (event.receiver_x !== null && event.receiver_x !== undefined) ||
                              (event.turnover_x !== null && event.turnover_x !== undefined);

            if (!hasCoords) continue;

            // Extract player names - "from X" for passes, "by X" for turnovers
            const throwerName = event.description?.match(/from (\w+)/)?.[1] ||
                               event.description?.match(/by (\w+)/)?.[1];
            const receiverName = event.description?.match(/to (\w+)/)?.[1];

            allEvents.push({
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
                // Use timeout_line_type for events after timeout (accounts for turnovers)
                // Fall back to point's line_type for normal events
                line_type: event.timeout_line_type || point.line_type,
                team: point.team,
                is_after_turnover: event.out_of_timeout || false  // From backend event
            });
        }
    }

    return allEvents;
}
