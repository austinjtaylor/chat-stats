/**
 * Filter UI rendering for Game Pass Plot
 */

import type { FilterState, FilterCounts } from './game-pass-plot-types';

/**
 * Render team filter toggle buttons
 */
export function renderTeamFilter(
    filterState: FilterState,
    homeCity: string,
    awayCity: string,
    getCityAbbreviation: (city: string) => string
): string {
    const awayAbbrev = awayCity ? getCityAbbreviation(awayCity) : 'AWAY';
    const homeAbbrev = homeCity ? getCityAbbreviation(homeCity) : 'HOME';

    return `
        <div class="filter-group">
            <div class="filter-group-header">
                <span class="filter-group-title">Team</span>
            </div>
            <div class="game-pass-plot-team-toggle">
                <button class="team-filter-btn ${filterState.team === 'away' ? 'active' : ''}"
                        data-team="away">${awayAbbrev}</button>
                <button class="team-filter-btn ${filterState.team === 'home' ? 'active' : ''}"
                        data-team="home">${homeAbbrev}</button>
            </div>
        </div>
    `;
}

/**
 * Render player filter (thrower and receiver checkboxes)
 */
export function renderPlayerFilter(
    filterState: FilterState,
    filterCounts: FilterCounts
): string {
    return `
        <h3 class="filter-section-title">Players</h3>
        <div class="filter-group">
            <div class="filter-group-header">
                <span class="filter-subgroup-title">Thrower</span>
                <div class="filter-group-actions">
                    <button class="filter-action-btn select-all-btn" data-filter="throwers">Select all</button>
                    <button class="filter-action-btn deselect-all-btn" data-filter="throwers">Deselect all</button>
                </div>
            </div>
            <div class="filter-checkbox-list player-filter-list">
                ${filterCounts.throwerList.map(player => `
                    <div class="filter-checkbox-item">
                        <input type="checkbox" id="thrower-${player.id}"
                               data-filter="thrower" data-value="${player.id}"
                               ${filterState.throwers.has(player.id) ? 'checked' : ''}>
                        <label for="thrower-${player.id}">${player.name}</label>
                        <span class="count">(${player.count})</span>
                    </div>
                `).join('')}
            </div>
        </div>
        <div class="filter-group">
            <div class="filter-group-header">
                <span class="filter-subgroup-title">Receiver</span>
                <div class="filter-group-actions">
                    <button class="filter-action-btn select-all-btn" data-filter="receivers">Select all</button>
                    <button class="filter-action-btn deselect-all-btn" data-filter="receivers">Deselect all</button>
                </div>
            </div>
            <div class="filter-checkbox-list player-filter-list">
                ${filterCounts.receiverList.map(player => `
                    <div class="filter-checkbox-item">
                        <input type="checkbox" id="receiver-${player.id}"
                               data-filter="receiver" data-value="${player.id}"
                               ${filterState.receivers.has(player.id) ? 'checked' : ''}>
                        <label for="receiver-${player.id}">${player.name}</label>
                        <span class="count">(${player.count})</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

/**
 * Render event type filter checkboxes
 */
export function renderEventTypeFilter(
    filterState: FilterState,
    filterCounts: FilterCounts
): string {
    const eventTypes = [
        { id: 'throws', label: 'Throws', count: filterCounts.eventTypeCounts.throws || 0 },
        { id: 'catches', label: 'Catches', count: filterCounts.eventTypeCounts.catches || 0 },
        { id: 'assists', label: 'Assists', count: filterCounts.eventTypeCounts.assists || 0 },
        { id: 'goals', label: 'Goals', count: filterCounts.eventTypeCounts.goals || 0 },
        { id: 'throwaways', label: 'Throwaways', count: filterCounts.eventTypeCounts.throwaways || 0 },
        { id: 'drops', label: 'Drops', count: filterCounts.eventTypeCounts.drops || 0 }
    ];

    return `
        <h3 class="filter-section-title">Event Type</h3>
        <div class="filter-group">
            <div class="filter-group-header">
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
                               ${filterState.eventTypes.has(et.id) ? 'checked' : ''}>
                        <label for="event-${et.id}">${et.label}</label>
                        <span class="count">(${et.count})</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

/**
 * Render line type filter checkboxes
 */
export function renderLineTypeFilter(
    filterState: FilterState,
    filterCounts: FilterCounts
): string {
    const lineTypes = [
        { id: 'o-points', label: 'O points', count: filterCounts.lineTypeCounts['o-points'] || 0 },
        { id: 'd-points', label: 'D points', count: filterCounts.lineTypeCounts['d-points'] || 0 },
        { id: 'o-out-of-to', label: 'O out of TO', count: filterCounts.lineTypeCounts['o-out-of-to'] || 0 },
        { id: 'd-out-of-to', label: 'D out of TO', count: filterCounts.lineTypeCounts['d-out-of-to'] || 0 }
    ];

    return `
        <h3 class="filter-section-title">Line Type</h3>
        <div class="filter-group">
            <div class="filter-group-header">
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
                               ${filterState.lineTypes.has(lt.id) ? 'checked' : ''}>
                        <label for="line-${lt.id}">${lt.label}</label>
                        <span class="count">(${lt.count})</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

/**
 * Render period/quarter filter checkboxes
 */
export function renderPeriodFilter(
    filterState: FilterState,
    filterCounts: FilterCounts
): string {
    const periods = [
        { id: 1, label: 'First quarter' },
        { id: 2, label: 'Second quarter' },
        { id: 3, label: 'Third quarter' },
        { id: 4, label: 'Fourth quarter' }
    ];

    // Add overtime if it exists
    if (filterCounts.periodCounts[5]) {
        periods.push({ id: 5, label: 'Overtime' });
    }

    return `
        <h3 class="filter-section-title">Quarter</h3>
        <div class="filter-group">
            <div class="filter-group-header">
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
                               ${filterState.periods.has(p.id) ? 'checked' : ''}>
                        <label for="period-${p.id}">${p.label}</label>
                        <span class="count">(${filterCounts.periodCounts[p.id] || 0})</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

/**
 * Render pass type filter checkboxes
 */
export function renderPassTypeFilter(
    filterState: FilterState,
    filterCounts: FilterCounts
): string {
    const passTypes = [
        { id: 'huck', label: 'Hucks', count: filterCounts.passTypeCounts.huck || 0 },
        { id: 'swing', label: 'Swings', count: filterCounts.passTypeCounts.swing || 0 },
        { id: 'dump', label: 'Dumps', count: filterCounts.passTypeCounts.dump || 0 },
        { id: 'gainer', label: 'Gainers', count: filterCounts.passTypeCounts.gainer || 0 },
        { id: 'dish', label: 'Dishes', count: filterCounts.passTypeCounts.dish || 0 }
    ];

    return `
        <h3 class="filter-section-title">Pass Type</h3>
        <div class="filter-group">
            <div class="filter-group-header">
                <div class="filter-group-actions">
                    <button class="filter-action-btn select-all-btn" data-filter="passTypes">Select all</button>
                    <button class="filter-action-btn deselect-all-btn" data-filter="passTypes">Deselect all</button>
                </div>
            </div>
            <div class="filter-checkbox-list">
                ${passTypes.map(pt => `
                    <div class="filter-checkbox-item">
                        <input type="checkbox" id="passType-${pt.id}"
                               data-filter="passType" data-value="${pt.id}"
                               ${filterState.passTypes.has(pt.id) ? 'checked' : ''}>
                        <label for="passType-${pt.id}">${pt.label}</label>
                        <span class="count">(${pt.count})</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}
