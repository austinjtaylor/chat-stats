/**
 * Filter logic for Game Pass Plot
 */

import type { PassPlotEvent, FilterState, PlayerInfo, FilterCounts } from './game-pass-plot-types';
import { classifyPassType } from './game-pass-plot-stats';

/**
 * Get default filter state
 */
export function getDefaultFilterState(): FilterState {
    return {
        team: 'away',
        throwers: new Set<string>(),
        receivers: new Set<string>(),
        eventTypes: new Set(['throws', 'catches', 'assists', 'goals', 'throwaways', 'drops']),
        lineTypes: new Set(['o-points', 'd-points', 'o-out-of-to', 'd-out-of-to']),
        periods: new Set([1, 2, 3, 4]),
        passTypes: new Set(['huck', 'swing', 'dump', 'gainer', 'dish'])
    };
}

/**
 * Get the number of "actions" an event represents for filter counts.
 * This matches UFA methodology:
 * - Pass = 2 (throw + catch)
 * - Goal = 2 (assist + goal)
 * - Throwaway = 1 (just the turnover, throw not counted separately)
 * - Drop = 2 (throw + drop, since receiver attempted catch)
 * - Stall = 1
 */
export function getActionCount(event: PassPlotEvent): number {
    switch (event.type) {
        case 'pass': return 2;      // throw + catch
        case 'goal': return 2;      // assist + goal
        case 'throwaway': return 1; // just the turnover (UFA methodology)
        case 'drop': return 2;      // throw + drop (UFA methodology)
        case 'stall': return 1;     // stall only
        default: return 0;
    }
}

/**
 * Filter events with one filter dimension excluded (for calculating filter counts)
 */
export function getEventsForFilterCount(
    allEvents: PassPlotEvent[],
    filterState: FilterState,
    excludeFilter: 'thrower' | 'receiver' | 'eventType' | 'lineType' | 'passType' | 'period'
): PassPlotEvent[] {
    return allEvents.filter(event => {
        // Always apply team filter
        if (event.team !== filterState.team) return false;

        // Apply thrower filter (unless excluded or empty = all selected)
        if (excludeFilter !== 'thrower' && filterState.throwers.size > 0 && event.thrower_name) {
            if (!filterState.throwers.has(event.thrower_name)) return false;
        }

        // Apply receiver filter (unless excluded or empty = all selected)
        if (excludeFilter !== 'receiver' && filterState.receivers.size > 0 &&
            event.receiver_name && event.type !== 'drop' && event.type !== 'throwaway') {
            if (!filterState.receivers.has(event.receiver_name)) return false;
        }

        // Apply event type filter (unless excluded or empty = all selected)
        if (excludeFilter !== 'eventType' && filterState.eventTypes.size > 0) {
            let eventTypeMatch = false;
            if (event.type === 'pass') {
                eventTypeMatch = filterState.eventTypes.has('throws') ||
                                filterState.eventTypes.has('catches');
            } else if (event.type === 'goal') {
                eventTypeMatch = filterState.eventTypes.has('goals') ||
                                filterState.eventTypes.has('assists');
            } else if (event.type === 'throwaway') {
                eventTypeMatch = filterState.eventTypes.has('throwaways');
            } else if (event.type === 'drop') {
                eventTypeMatch = filterState.eventTypes.has('drops');
            }
            if (!eventTypeMatch) return false;
        }

        // Apply line type filter (unless excluded or empty = all selected)
        if (excludeFilter !== 'lineType' && filterState.lineTypes.size > 0) {
            let lineTypeMatch = false;
            if (event.line_type === 'O-Line') {
                lineTypeMatch = event.is_after_turnover
                    ? filterState.lineTypes.has('o-out-of-to')
                    : filterState.lineTypes.has('o-points');
            } else if (event.line_type === 'D-Line') {
                lineTypeMatch = event.is_after_turnover
                    ? filterState.lineTypes.has('d-out-of-to')
                    : filterState.lineTypes.has('d-points');
            }
            if (!lineTypeMatch) return false;
        }

        // Apply period filter (unless excluded or empty = all selected)
        if (excludeFilter !== 'period' && filterState.periods.size > 0) {
            if (!filterState.periods.has(event.quarter)) return false;
        }

        // Apply pass type filter (unless excluded or empty = all selected)
        if (excludeFilter !== 'passType' && filterState.passTypes.size > 0) {
            const passType = classifyPassType(event);
            if (passType && !filterState.passTypes.has(passType)) return false;
        }

        return true;
    });
}

/**
 * Build master player lists from ALL team events (unfiltered).
 * This ensures all players remain visible in filter lists even when their count is 0.
 */
export function buildMasterPlayerLists(
    allEvents: PassPlotEvent[],
    team: 'home' | 'away'
): { masterThrowerList: PlayerInfo[]; masterReceiverList: PlayerInfo[] } {
    const teamEvents = allEvents.filter(e => e.team === team);

    // Build master thrower list from ALL team events
    const allThrowers = new Map<string, string>();
    teamEvents.forEach(event => {
        if (event.thrower_name && ['pass', 'goal', 'throwaway'].includes(event.type)) {
            allThrowers.set(event.thrower_name, event.thrower_name);
        }
    });
    const masterThrowerList = Array.from(allThrowers.keys())
        .map(name => ({ id: name, name, count: 0 }))
        .sort((a, b) => a.name.localeCompare(b.name));

    // Build master receiver list from ALL team events
    const allReceivers = new Map<string, string>();
    teamEvents.forEach(event => {
        if (event.receiver_name && ['pass', 'goal', 'drop'].includes(event.type)) {
            allReceivers.set(event.receiver_name, event.receiver_name);
        }
    });
    const masterReceiverList = Array.from(allReceivers.keys())
        .map(name => ({ id: name, name, count: 0 }))
        .sort((a, b) => a.name.localeCompare(b.name));

    return { masterThrowerList, masterReceiverList };
}

/**
 * Compute all filter counts based on current filter state
 */
export function computeFilterCounts(
    allEvents: PassPlotEvent[],
    filterState: FilterState,
    masterThrowerList: PlayerInfo[],
    masterReceiverList: PlayerInfo[]
): FilterCounts {
    // Thrower counts - use master list to keep all players visible
    const eventsForThrowers = getEventsForFilterCount(allEvents, filterState, 'thrower');
    const throwerCounts = new Map<string, number>();
    eventsForThrowers.forEach(event => {
        if (event.thrower_name && ['pass', 'goal', 'throwaway'].includes(event.type)) {
            throwerCounts.set(event.thrower_name, (throwerCounts.get(event.thrower_name) || 0) + 1);
        }
    });
    const throwerList = masterThrowerList.map(p => ({
        ...p,
        count: throwerCounts.get(p.id) || 0
    }));

    // Receiver counts - use master list to keep all players visible
    const eventsForReceivers = getEventsForFilterCount(allEvents, filterState, 'receiver');
    const receiverCounts = new Map<string, number>();
    eventsForReceivers.forEach(event => {
        if (event.receiver_name && ['pass', 'goal', 'drop'].includes(event.type)) {
            receiverCounts.set(event.receiver_name, (receiverCounts.get(event.receiver_name) || 0) + 1);
        }
    });
    const receiverList = masterReceiverList.map(p => ({
        ...p,
        count: receiverCounts.get(p.id) || 0
    }));

    // Event type counts - exclude event type filter
    const eventsForEventTypes = getEventsForFilterCount(allEvents, filterState, 'eventType');
    const eventTypeCounts = {
        throws: eventsForEventTypes.filter(e => e.type === 'pass' || e.type === 'drop').length,
        catches: eventsForEventTypes.filter(e => e.type === 'pass').length,
        assists: eventsForEventTypes.filter(e => e.type === 'goal').length,
        goals: eventsForEventTypes.filter(e => e.type === 'goal').length,
        throwaways: eventsForEventTypes.filter(e => e.type === 'throwaway').length,
        drops: eventsForEventTypes.filter(e => e.type === 'drop').length
    };

    // Line type counts - exclude line type filter
    const eventsForLineTypes = getEventsForFilterCount(allEvents, filterState, 'lineType');
    let oPoints = 0, dPoints = 0, oOutOfTo = 0, dOutOfTo = 0;
    eventsForLineTypes.forEach(e => {
        const actions = getActionCount(e);
        if (e.line_type === 'O-Line' && !e.is_after_turnover) oPoints += actions;
        else if (e.line_type === 'D-Line' && !e.is_after_turnover) dPoints += actions;
        else if (e.line_type === 'O-Line' && e.is_after_turnover) oOutOfTo += actions;
        else if (e.line_type === 'D-Line' && e.is_after_turnover) dOutOfTo += actions;
    });
    const lineTypeCounts = {
        'o-points': oPoints,
        'd-points': dPoints,
        'o-out-of-to': oOutOfTo,
        'd-out-of-to': dOutOfTo
    };

    // Period counts - exclude period filter
    const eventsForPeriods = getEventsForFilterCount(allEvents, filterState, 'period');
    const periodCounts: Record<number, number> = {};
    eventsForPeriods.forEach(event => {
        const actions = getActionCount(event);
        periodCounts[event.quarter] = (periodCounts[event.quarter] || 0) + actions;
    });

    // Pass type counts - exclude pass type filter
    const eventsForPassTypes = getEventsForFilterCount(allEvents, filterState, 'passType');
    const passTypeCounts: Record<string, number> = { huck: 0, swing: 0, dump: 0, gainer: 0, dish: 0 };
    eventsForPassTypes.forEach(event => {
        const passType = classifyPassType(event);
        if (passType && passTypeCounts[passType] !== undefined) {
            passTypeCounts[passType] += 1;
        }
    });

    return {
        throwerList,
        receiverList,
        eventTypeCounts,
        lineTypeCounts,
        periodCounts,
        passTypeCounts
    };
}

/**
 * Get filtered events based on current filter state
 */
export function getFilteredEvents(
    allEvents: PassPlotEvent[],
    filterState: FilterState
): PassPlotEvent[] {
    return allEvents.filter(event => {
        // Team filter
        if (event.team !== filterState.team) return false;

        // Thrower filter (empty = all selected)
        if (filterState.throwers.size > 0 && event.thrower_name) {
            if (!filterState.throwers.has(event.thrower_name)) return false;
        }

        // Receiver filter (empty = all selected, skip for turnovers)
        if (filterState.receivers.size > 0 && event.receiver_name &&
            event.type !== 'drop' && event.type !== 'throwaway') {
            if (!filterState.receivers.has(event.receiver_name)) return false;
        }

        // Event type filter (empty = all selected)
        if (filterState.eventTypes.size > 0) {
            let eventTypeMatch = false;
            if (event.type === 'pass') {
                eventTypeMatch = filterState.eventTypes.has('throws') ||
                                filterState.eventTypes.has('catches');
            } else if (event.type === 'goal') {
                eventTypeMatch = filterState.eventTypes.has('goals') ||
                                filterState.eventTypes.has('assists');
            } else if (event.type === 'throwaway') {
                eventTypeMatch = filterState.eventTypes.has('throwaways');
            } else if (event.type === 'drop') {
                eventTypeMatch = filterState.eventTypes.has('drops');
            }
            if (!eventTypeMatch) return false;
        }

        // Line type filter (empty = all selected)
        if (filterState.lineTypes.size > 0) {
            let lineTypeMatch = false;
            if (event.line_type === 'O-Line') {
                lineTypeMatch = event.is_after_turnover
                    ? filterState.lineTypes.has('o-out-of-to')
                    : filterState.lineTypes.has('o-points');
            } else if (event.line_type === 'D-Line') {
                lineTypeMatch = event.is_after_turnover
                    ? filterState.lineTypes.has('d-out-of-to')
                    : filterState.lineTypes.has('d-points');
            }
            if (!lineTypeMatch) return false;
        }

        // Period filter (empty = all selected)
        if (filterState.periods.size > 0) {
            if (!filterState.periods.has(event.quarter)) return false;
        }

        // Pass type filter (empty = all selected)
        if (filterState.passTypes.size > 0) {
            const passType = classifyPassType(event);
            if (passType && !filterState.passTypes.has(passType)) return false;
        }

        return true;
    });
}
