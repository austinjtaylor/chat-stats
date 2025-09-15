// API response types

import type { Game, PlayerGameStats, PlayerSeasonStats, TeamSeasonStats } from './models';

export interface APIResponse<T> {
  data?: T;
  error?: string;
  status?: number;
}

export interface StatsResponse {
  total_players: number;
  total_teams: number;
  total_games: number;
  recent_games: Game[];
  top_scorers: PlayerSeasonStats[];
  team_standings: TeamSeasonStats[];
}

export interface PlayerStatsResponse {
  players: PlayerSeasonStats[];
  total: number;
  page: number;
  pages: number;
}

export interface TeamStatsResponse {
  teams: TeamSeasonStats[];
  total: number;
}

export interface GameStatsResponse {
  games: Game[];
  total: number;
  page: number;
  pages: number;
}

export interface QueryRequest {
  query: string;
  session_id?: string;
}

export interface QueryResponse {
  response: string;
  data?: any;
  session_id: string;
  error?: string;
}

export interface SearchPlayersRequest {
  q?: string;
  team?: string;
  season?: number;
  limit?: number;
}

export interface SearchTeamsRequest {
  q?: string;
  season?: number;
  conference?: string;
  division?: string;
}

export interface GameDetailsResponse {
  game: Game;
  home_stats: PlayerGameStats[];
  away_stats: PlayerGameStats[];
  home_team_stats?: TeamSeasonStats;
  away_team_stats?: TeamSeasonStats;
}