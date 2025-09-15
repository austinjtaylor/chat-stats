// Core data models matching the backend structure

export interface Player {
  id?: number;
  name: string;
  position: string;
  team?: string;
  team_id?: number;
  height?: number;
  jersey?: string;
  years_played?: number;
  status?: string;
  rookie_year?: number;
}

export interface Team {
  id?: number;
  name: string;
  full_name?: string;
  city?: string;
  division?: string;
  conference?: string;
  founded?: number;
  championships?: number;
  is_current?: boolean;
  last_year?: number;
}

export interface Game {
  id?: number;
  game_id?: string;
  date: string;
  home_team: string;
  home_team_id?: number;
  away_team: string;
  away_team_id?: number;
  home_score: number;
  away_score: number;
  venue?: string;
  attendance?: number;
  season: number;
  game_type?: string;
  week?: number;
}

export interface PlayerGameStats {
  id?: number;
  player_id: number;
  player_name?: string;
  game_id: string;
  team: string;
  opponent?: string;
  goals: number;
  assists: number;
  blocks: number;
  plus_minus: number;
  points_played: number;
  completions?: number;
  throwaways?: number;
  drops?: number;
  stalls?: number;
  callahans?: number;
  pulls?: number;
  ob_pulls?: number;
  o_points_for?: number;
  o_points_against?: number;
  d_points_for?: number;
  d_points_against?: number;
  minutes?: number;
  seconds?: number;
  hockey_assists?: number;
  completion_percentage?: number;
  throw_percentage?: number;
  catch_percentage?: number;
  yards?: number;
  throwing_yards?: number;
  receiving_yards?: number;
  hucks_attempted?: number;
  hucks_completed?: number;
  catches?: number;
  touches?: number;
  calculated_plus_minus?: number;
}

export interface PlayerSeasonStats {
  id?: number;
  player_id: number;
  player_name?: string;
  first_name?: string;
  last_name?: string;
  season: number;
  team: string;
  team_id?: number;
  games_played: number;
  goals: number;
  assists: number;
  blocks: number;
  plus_minus: number;
  points_played?: number;
  completions?: number;
  throwaways?: number;
  drops?: number;
  stalls?: number;
  callahans?: number;
  pulls?: number;
  ob_pulls?: number;
  o_points_for?: number;
  o_points_against?: number;
  d_points_for?: number;
  d_points_against?: number;
  total_minutes?: number;
  hockey_assists?: number;
  completion_percentage?: number;
  throw_percentage?: number;
  catch_percentage?: number;
  yards?: number;
  throwing_yards?: number;
  receiving_yards?: number;
  hucks_attempted?: number;
  hucks_completed?: number;
  huck_percentage?: number;
  catches?: number;
  touches?: number;
  calculated_plus_minus?: number;
}

export interface TeamSeasonStats {
  id?: number;
  team_id: number;
  team_name: string;
  season: number;
  games_played: number;
  wins: number;
  losses: number;
  scores: number;
  scores_against: number;
  completions?: number;
  turnovers?: number;
  blocks?: number;
  hold_percentage?: number;
  break_percentage?: number;
  o_line_conversion?: number;
  d_line_conversion?: number;
  red_zone_conversion?: number;
  hucks_completed?: number;
  huck_percentage?: number;
  completion_percentage?: number;
  is_current?: boolean;
  last_year?: number | string;
}

export interface StatsFilter {
  season?: string | number;
  team?: string;
  position?: string;
  per?: 'total' | 'per-game';
  view?: 'total' | 'per-game';
  perspective?: 'team' | 'opponent';
}

export interface SortConfig {
  key: string;
  direction: 'asc' | 'desc';
}

export interface PaginationConfig {
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalItems: number;
}