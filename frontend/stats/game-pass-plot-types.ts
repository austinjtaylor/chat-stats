/**
 * Type definitions for Game Pass Plot component
 */

export interface PassPlotEvent {
    type: string;
    thrower_x: number | null;
    thrower_y: number | null;
    receiver_x: number | null;
    receiver_y: number | null;
    turnover_x: number | null;
    turnover_y: number | null;
    thrower_name?: string;
    receiver_name?: string;
    thrower_id?: string;
    receiver_id?: string;
    quarter: number;
    point_number: number;
    line_type: string;
    team: string;
    is_after_turnover: boolean;
}

export interface FilterState {
    team: 'home' | 'away';
    throwers: Set<string>;
    receivers: Set<string>;
    eventTypes: Set<string>;
    lineTypes: Set<string>;
    periods: Set<number>;
    passTypes: Set<string>;
}

export interface PlayByPlayPoint {
    point_number: number;
    quarter: number;
    team: string;
    line_type: string;
    events: RawEvent[];
}

export interface RawEvent {
    type: string;
    thrower_x?: number | null;
    thrower_y?: number | null;
    receiver_x?: number | null;
    receiver_y?: number | null;
    turnover_x?: number | null;
    turnover_y?: number | null;
    thrower_id?: string;
    receiver_id?: string;
    description?: string;
    timeout_line_type?: string;
    out_of_timeout?: boolean;
}

export interface PlayByPlayData {
    points: PlayByPlayPoint[];
}

export interface PlayerInfo {
    id: string;
    name: string;
    count: number;
}

export interface PassPlotStats {
    totalThrows: number;
    completions: number;
    completionsPct: number;
    turnovers: number;
    turnoversPct: number;
    goals: number;
    goalsPct: number;
    avgYardsPerThrow: number;
    avgYardsPerCompletion: number;
    byType: Record<string, { count: number; pct: number }>;
}

export interface FilterCounts {
    throwerList: PlayerInfo[];
    receiverList: PlayerInfo[];
    eventTypeCounts: Record<string, number>;
    lineTypeCounts: Record<string, number>;
    periodCounts: Record<number, number>;
    passTypeCounts: Record<string, number>;
}
