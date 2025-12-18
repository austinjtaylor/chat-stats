/**
 * Type definitions for Pass Plots visualization
 */

// API response interfaces
export interface PassEvent {
    game_id: string;
    event_type: number;
    pass_type: string | null;
    thrower_id: string;
    thrower_name: string;
    receiver_id: string;
    receiver_name: string;
    thrower_x: number;
    thrower_y: number;
    receiver_x: number | null;
    receiver_y: number | null;
    turnover_x: number | null;
    turnover_y: number | null;
    result: 'goal' | 'completion' | 'turnover';
    vertical_yards: number | null;
    horizontal_yards: number | null;
    distance: number | null;
    year: number;
}

export interface PassEventsStats {
    total_throws: number;
    completions: number;
    completions_pct: number;
    turnovers: number;
    turnovers_pct: number;
    goals: number;
    goals_pct: number;
    total_yards: number;
    completion_yards: number;
    avg_yards_per_throw: number;
    avg_yards_per_completion: number;
    by_type: Record<string, { count: number; pct: number }>;
}

export interface PassEventsResponse {
    events: PassEvent[];
    stats: PassEventsStats;
    total: number;
}

export interface FilterOptions {
    seasons: number[];
    teams: Array<{ team_id: string; name: string; abbrev: string }>;
    players: Array<{ player_id: string; name: string }>;
    games: Array<{ game_id: string; label: string; year: number; week: number }>;
}

export type GraphType = 'throw-lines' | 'origin-heatmap' | 'dest-heatmap';

export interface FilterState {
    season: number | null;
    game_id: string | null;
    off_team_id: string | null;
    def_team_id: string | null;
    thrower_id: string | null;
    receiver_id: string | null;
    results: Set<string>;
    pass_types: Set<string>;
    origin_x_min: number;
    origin_x_max: number;
    origin_y_min: number;
    origin_y_max: number;
    dest_x_min: number;
    dest_x_max: number;
    dest_y_min: number;
    dest_y_max: number;
    distance_min: number;
    distance_max: number;
}

export function getDefaultFilterState(): FilterState {
    return {
        season: null,
        game_id: null,
        off_team_id: null,
        def_team_id: null,
        thrower_id: null,
        receiver_id: null,
        results: new Set(['goal', 'completion', 'turnover']),
        pass_types: new Set(['huck', 'swing', 'dump', 'gainer', 'dish']),
        origin_x_min: -27,
        origin_x_max: 27,
        origin_y_min: 0,
        origin_y_max: 120,
        dest_x_min: -27,
        dest_x_max: 27,
        dest_y_min: 0,
        dest_y_max: 120,
        distance_min: 0,
        distance_max: 100
    };
}
