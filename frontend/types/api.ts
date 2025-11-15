// API response types

import type { Game, PlayerGameStats, PlayerSeasonStats, TeamSeasonStats } from './models';

/**
 * Generic API response wrapper for error handling
 * @template T The type of data returned in the response
 */
export interface APIResponse<T> {
  /** Response data payload */
  data?: T;
  /** Error message if request failed */
  error?: string;
  /** HTTP status code */
  status?: number;
}

/**
 * Dashboard statistics summary response
 * Provides overview data for the main application dashboard
 */
export interface StatsResponse {
  /** Total number of players in the database */
  total_players: number;
  /** Total number of teams in the database */
  total_teams: number;
  /** Total number of games in the database */
  total_games: number;
  /** List of recently played games */
  recent_games: Game[];
  /** Top scoring players for the current/latest season */
  top_scorers: PlayerSeasonStats[];
  /** Current team standings */
  team_standings: TeamSeasonStats[];
}

/**
 * Paginated player statistics response
 * Returns player season statistics with pagination metadata
 */
export interface PlayerStatsResponse {
  /** List of player statistics for the requested page */
  players: PlayerSeasonStats[];
  /** Global percentile rankings for each player's stats (0-100 scale) */
  percentiles: Record<string, Record<string, number>>;
  /** Total number of players matching the query */
  total: number;
  /** Current page number (1-indexed) */
  page: number;
  /** Number of players per page */
  per_page: number;
  /** Total number of pages available */
  total_pages: number;
  /** @deprecated Use total_pages instead - kept for backward compatibility */
  pages?: number;
}

/**
 * Team statistics response
 * Returns team season statistics
 */
export interface TeamStatsResponse {
  /** List of team statistics */
  teams: TeamSeasonStats[];
  /** Total number of teams in the response */
  total: number;
}

/**
 * Paginated game results response
 * Returns game data with pagination
 */
export interface GameStatsResponse {
  /** List of games for the requested page */
  games: Game[];
  /** Total number of games matching the query */
  total: number;
  /** Current page number (1-indexed) */
  page: number;
  /** Total number of pages available */
  pages: number;
}

/**
 * Natural language query request
 * Sends user questions to the AI backend for processing
 */
export interface QueryRequest {
  /** Natural language question about sports statistics */
  query: string;
  /** Optional session ID to maintain conversation context */
  session_id?: string;
}

/**
 * AI-generated query response
 * Contains the natural language answer and supporting data
 */
export interface QueryResponse {
  /** AI-generated natural language answer */
  answer: string;
  /** Supporting data used to generate the answer */
  data?: any;
  /** Session ID for maintaining conversation context */
  session_id: string;
  /** Error message if query processing failed */
  error?: string;
}

/**
 * Player search request parameters
 * Filters for searching players in the database
 */
export interface SearchPlayersRequest {
  /** Search query string (matches player name) */
  q?: string;
  /** Filter by team name */
  team?: string;
  /** Filter by season year */
  season?: number;
  /** Maximum number of results to return */
  limit?: number;
}

/**
 * Team search request parameters
 * Filters for searching teams in the database
 */
export interface SearchTeamsRequest {
  /** Search query string (matches team name or city) */
  q?: string;
  /** Filter by season year */
  season?: number;
  /** Filter by conference (East/West) */
  conference?: string;
  /** Filter by division name */
  division?: string;
}

/**
 * Game details response
 * Complete information about a single game including player statistics
 */
export interface GameDetailsResponse {
  /** Game information */
  game: Game;
  /** Home team player statistics for this game */
  home_stats: PlayerGameStats[];
  /** Away team player statistics for this game */
  away_stats: PlayerGameStats[];
  /** Home team season statistics */
  home_team_stats?: TeamSeasonStats;
  /** Away team season statistics */
  away_team_stats?: TeamSeasonStats;
}