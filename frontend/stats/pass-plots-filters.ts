/**
 * Filter management utilities for Pass Plots
 */

import { MultiSelect } from './components/multi-select';
import type { MultiSelectOption } from './components/multi-select';
import type { FilterOptions, FilterState } from './pass-plots-types';
import { getDefaultFilterState } from './pass-plots-types';

export interface FilterSelectInstances {
    seasonSelect: MultiSelect | null;
    gameSelect: MultiSelect | null;
    offTeamSelect: MultiSelect | null;
    defTeamSelect: MultiSelect | null;
    throwerSelect: MultiSelect | null;
    receiverSelect: MultiSelect | null;
}

export function createFilterSelectInstances(): FilterSelectInstances {
    return {
        seasonSelect: null,
        gameSelect: null,
        offTeamSelect: null,
        defTeamSelect: null,
        throwerSelect: null,
        receiverSelect: null
    };
}

export function buildSeasonOptions(filterOptions: FilterOptions): MultiSelectOption[] {
    return [
        { value: 'all', label: 'All Seasons' },
        ...filterOptions.seasons.map(s => ({ value: s, label: String(s) }))
    ];
}

export function buildGameOptions(filterOptions: FilterOptions): MultiSelectOption[] {
    return [
        { value: 'all', label: 'All Games' },
        ...filterOptions.games.map(g => ({
            value: g.game_id,
            label: `${g.label} (Wk ${g.week})`
        }))
    ];
}

export function buildTeamOptions(filterOptions: FilterOptions): MultiSelectOption[] {
    return [
        { value: 'all', label: 'All Teams' },
        ...filterOptions.teams.map(t => ({
            value: t.team_id,
            label: t.name
        }))
    ];
}

export function buildPlayerOptions(filterOptions: FilterOptions): MultiSelectOption[] {
    return [
        { value: 'all', label: 'All Players' },
        ...filterOptions.players.map(p => ({
            value: p.player_id,
            label: p.name
        }))
    ];
}

export function preserveOrResetFilters(
    filterOptions: FilterOptions,
    filterState: FilterState,
    offTeamId: string | null,
    defTeamId: string | null,
    throwerId: string | null,
    receiverId: string | null
): void {
    // Check if offensive team exists in new options
    const offTeamExists = offTeamId && filterOptions.teams.some(t => t.team_id === offTeamId);
    filterState.off_team_id = offTeamExists ? offTeamId : null;

    // Check if defensive team exists in new options
    const defTeamExists = defTeamId && filterOptions.teams.some(t => t.team_id === defTeamId);
    filterState.def_team_id = defTeamExists ? defTeamId : null;

    // Check if thrower exists in new options
    const throwerExists = throwerId && filterOptions.players.some(p => p.player_id === throwerId);
    filterState.thrower_id = throwerExists ? throwerId : null;

    // Check if receiver exists in new options
    const receiverExists = receiverId && filterOptions.players.some(p => p.player_id === receiverId);
    filterState.receiver_id = receiverExists ? receiverId : null;
}

export function resetSlider(id: string, min: number, max: number): void {
    const minInput = document.getElementById(`${id}Min`) as HTMLInputElement;
    const maxInput = document.getElementById(`${id}Max`) as HTMLInputElement;
    const minVal = document.getElementById(`${id}MinVal`);
    const maxVal = document.getElementById(`${id}MaxVal`);

    if (minInput) minInput.value = String(min);
    if (maxInput) maxInput.value = String(max);
    if (minVal) minVal.textContent = String(min);
    if (maxVal) maxVal.textContent = String(max);
}

export function resetAllFilters(
    selects: FilterSelectInstances
): void {
    // Reset selects
    selects.seasonSelect?.setSelected(['all']);
    selects.gameSelect?.setSelected(['all']);
    selects.offTeamSelect?.setSelected(['all']);
    selects.defTeamSelect?.setSelected(['all']);
    selects.throwerSelect?.setSelected(['all']);
    selects.receiverSelect?.setSelected(['all']);

    // Reset checkboxes
    ['Goal', 'Completion', 'Turnover'].forEach(result => {
        const checkbox = document.getElementById(`result${result}`) as HTMLInputElement;
        if (checkbox) checkbox.checked = true;
    });
    ['Huck', 'Swing', 'Dump', 'Gainer', 'Dish'].forEach(type => {
        const checkbox = document.getElementById(`type${type}`) as HTMLInputElement;
        if (checkbox) checkbox.checked = true;
    });

    // Reset sliders
    resetSlider('originY', 0, 120);
    resetSlider('originX', -27, 27);
    resetSlider('destY', 0, 120);
    resetSlider('destX', -27, 27);
    resetSlider('distance', 0, 100);
}

export function buildQueryParams(filterState: FilterState): string {
    const params = new URLSearchParams();

    if (filterState.season) {
        params.set('season', String(filterState.season));
    }
    if (filterState.game_id) {
        params.set('game_id', filterState.game_id);
    }
    if (filterState.off_team_id) {
        params.set('off_team_id', filterState.off_team_id);
    }
    if (filterState.def_team_id) {
        params.set('def_team_id', filterState.def_team_id);
    }
    if (filterState.thrower_id) {
        params.set('thrower_id', filterState.thrower_id);
    }
    if (filterState.receiver_id) {
        params.set('receiver_id', filterState.receiver_id);
    }

    // Results filter
    if (filterState.results.size > 0 && filterState.results.size < 3) {
        params.set('results', Array.from(filterState.results).join(','));
    }

    // Pass types filter
    if (filterState.pass_types.size > 0 && filterState.pass_types.size < 5) {
        params.set('pass_types', Array.from(filterState.pass_types).join(','));
    }

    // Coordinate filters (only add if not default)
    if (filterState.origin_y_min > 0) {
        params.set('origin_y_min', String(filterState.origin_y_min));
    }
    if (filterState.origin_y_max < 120) {
        params.set('origin_y_max', String(filterState.origin_y_max));
    }
    if (filterState.origin_x_min > -27) {
        params.set('origin_x_min', String(filterState.origin_x_min));
    }
    if (filterState.origin_x_max < 27) {
        params.set('origin_x_max', String(filterState.origin_x_max));
    }
    if (filterState.dest_y_min > 0) {
        params.set('dest_y_min', String(filterState.dest_y_min));
    }
    if (filterState.dest_y_max < 120) {
        params.set('dest_y_max', String(filterState.dest_y_max));
    }
    if (filterState.dest_x_min > -27) {
        params.set('dest_x_min', String(filterState.dest_x_min));
    }
    if (filterState.dest_x_max < 27) {
        params.set('dest_x_max', String(filterState.dest_x_max));
    }
    if (filterState.distance_min > 0) {
        params.set('distance_min', String(filterState.distance_min));
    }
    if (filterState.distance_max < 100) {
        params.set('distance_max', String(filterState.distance_max));
    }

    return params.toString();
}

export { getDefaultFilterState };
