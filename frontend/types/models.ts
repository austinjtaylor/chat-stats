// Core data models matching the backend structure

/**
 * Player entity representing an Ultimate Frisbee player
 */
export interface Player {
  /** Unique player ID in database */
  id?: number;
  /** Full player name */
  name: string;
  /** Player position (Handler/Cutter/Hybrid) */
  position: string;
  /** Current team name */
  team?: string;
  /** Current team ID */
  team_id?: number;
  /** Height in inches */
  height?: number;
  /** Jersey number */
  jersey?: string;
  /** Total years played in the league */
  years_played?: number;
  /** Player status (Active/Inactive/Retired) */
  status?: string;
  /** First year in the league */
  rookie_year?: number;
}

/**
 * Team entity representing a UFA franchise
 */
export interface Team {
  /** Unique team ID in database */
  id?: number;
  /** Team short name/abbreviation */
  name: string;
  /** Full team name including city */
  full_name?: string;
  /** Team city/location */
  city?: string;
  /** Division name (Atlantic/Central/South/West) */
  division?: string;
  /** Conference name (East/West) */
  conference?: string;
  /** Year team was founded */
  founded?: number;
  /** Number of championships won */
  championships?: number;
  /** Whether team is currently active */
  is_current?: boolean;
  /** Last year team played (if inactive) */
  last_year?: number;
}

/**
 * Game record for a single Ultimate Frisbee match
 */
export interface Game {
  /** Unique game ID in database */
  id?: number;
  /** External game identifier from UFA */
  game_id?: string;
  /** Game date (YYYY-MM-DD format) */
  date: string;
  /** Home team name */
  home_team: string;
  /** Home team ID */
  home_team_id?: number;
  /** Away team name */
  away_team: string;
  /** Away team ID */
  away_team_id?: number;
  /** Home team final score */
  home_score: number;
  /** Away team final score */
  away_score: number;
  /** Game venue/stadium name */
  venue?: string;
  /** Number of attendees */
  attendance?: number;
  /** Season year */
  season: number;
  /** Type of game (Regular/Playoff/Championship) */
  game_type?: string;
  /** Week number in the season */
  week?: number;
}

/**
 * Individual player statistics for a single game
 */
export interface PlayerGameStats {
  /** Unique record ID */
  id?: number;
  /** Player ID reference */
  player_id: number;
  /** Player display name */
  player_name?: string;
  /** Game identifier */
  game_id: string;
  /** Player's team name */
  team: string;
  /** Opposing team name */
  opponent?: string;
  /** Goals scored */
  goals: number;
  /** Assists (goal throws) */
  assists: number;
  /** Defensive blocks */
  blocks: number;
  /** Plus/minus differential */
  plus_minus: number;
  /** Total points played */
  points_played: number;
  /** Successful completions */
  completions?: number;
  /** Throwing turnovers */
  throwaways?: number;
  /** Dropped catches */
  drops?: number;
  /** Stall violations */
  stalls?: number;
  /** Callahan goals (defensive score) */
  callahans?: number;
  /** Total pulls */
  pulls?: number;
  /** Out-of-bounds pulls */
  ob_pulls?: number;
  /** Offensive points scored */
  o_points_for?: number;
  /** Offensive points conceded */
  o_points_against?: number;
  /** Defensive points scored */
  d_points_for?: number;
  /** Defensive points conceded */
  d_points_against?: number;
  /** Minutes played */
  minutes?: number;
  /** Additional seconds played */
  seconds?: number;
  /** Hockey assists (assist to the assister) - Available from 2014 onwards */
  hockey_assists?: number;
  /** Completion percentage (completions/attempts) */
  completion_percentage?: number;
  /** Throwing percentage (completions/throws) */
  throw_percentage?: number;
  /** Catching percentage (catches/targets) */
  catch_percentage?: number;
  /** Total yards gained - Available from 2021 onwards */
  yards?: number;
  /** Yards gained by throwing - Available from 2021 onwards */
  throwing_yards?: number;
  /** Yards gained by receiving - Available from 2021 onwards */
  receiving_yards?: number;
  /** Long throws attempted - Available from 2021 onwards */
  hucks_attempted?: number;
  /** Long throws completed - Available from 2021 onwards */
  hucks_completed?: number;
  /** Long throws received (caught) - Available from 2021 onwards */
  hucks_received?: number;
  /** Total catches */
  catches?: number;
  /** Total disc touches */
  touches?: number;
  /** Calculated plus/minus (may differ from reported) */
  calculated_plus_minus?: number;
  /** Yards per turn ((yards_thrown + yards_received) / (throwaways + stalls + drops)) - Available from 2021 onwards */
  yards_per_turn?: number | null;
}

/**
 * Aggregated player statistics for an entire season
 */
export interface PlayerSeasonStats {
  /** Unique record ID */
  id?: number;
  /** Player ID reference */
  player_id: number;
  /** Player full name */
  player_name?: string;
  /** Player first name */
  first_name?: string;
  /** Player last name */
  last_name?: string;
  /** Season year */
  season: number;
  /** Team name for this season */
  team: string;
  /** Team ID for this season */
  team_id?: number;
  /** Number of games played */
  games_played: number;
  /** Total goals scored */
  goals: number;
  /** Total assists */
  assists: number;
  /** Total blocks */
  blocks: number;
  /** Season plus/minus differential */
  plus_minus: number;
  /** Total points played */
  points_played?: number;
  /** Total completions */
  completions?: number;
  /** Total throwaways */
  throwaways?: number;
  /** Total drops */
  drops?: number;
  /** Total stalls */
  stalls?: number;
  /** Total Callahan goals */
  callahans?: number;
  /** Total pulls */
  pulls?: number;
  /** Total out-of-bounds pulls */
  ob_pulls?: number;
  /** Offensive points scored */
  o_points_for?: number;
  /** Offensive points conceded */
  o_points_against?: number;
  /** Defensive points scored */
  d_points_for?: number;
  /** Defensive points conceded */
  d_points_against?: number;
  /** Total minutes played */
  total_minutes?: number;
  /** Total hockey assists - Available from 2014 onwards */
  hockey_assists?: number;
  /** Season completion percentage */
  completion_percentage?: number;
  /** Season throwing percentage */
  throw_percentage?: number;
  /** Season catching percentage */
  catch_percentage?: number;
  /** Total yards - Available from 2021 onwards */
  yards?: number;
  /** Total throwing yards - Available from 2021 onwards */
  throwing_yards?: number;
  /** Total receiving yards - Available from 2021 onwards */
  receiving_yards?: number;
  /** Total hucks attempted - Available from 2021 onwards */
  hucks_attempted?: number;
  /** Total hucks completed - Available from 2021 onwards */
  hucks_completed?: number;
  /** Total hucks received (caught) - Available from 2021 onwards */
  hucks_received?: number;
  /** Huck completion percentage - Available from 2021 onwards */
  huck_percentage?: number;
  /** Total catches */
  catches?: number;
  /** Total disc touches */
  touches?: number;
  /** Calculated season plus/minus */
  calculated_plus_minus?: number;
  /** Yards per turn ((total_yards_thrown + total_yards_received) / (total_throwaways + total_stalls + total_drops)) - Available from 2021 onwards */
  yards_per_turn?: number | null;
}

/**
 * Team statistics and standings for a season
 */
export interface TeamSeasonStats {
  /** Unique record ID */
  id?: number;
  /** Team ID reference */
  team_id: number;
  /** Team name */
  team_name: string;
  /** API returns this as 'name' */
  name?: string;
  /** Season year */
  season: number;
  /** Games played this season */
  games_played: number;
  /** Games won */
  wins: number;
  /** Games lost */
  losses: number;
  /** Total points scored */
  scores: number;
  /** Total points conceded */
  scores_against: number;
  /** Total completions */
  completions?: number;
  /** Total turnovers */
  turnovers?: number;
  /** Total blocks */
  blocks?: number;
  /** O-line success rate (O-line scores/O-line points) */
  hold_percentage?: number;
  /** D-line success rate (D-line scores/D-line points) */
  break_percentage?: number;
  /** O-line conversion rate (O-line scores/O-line possessions) */
  o_line_conversion?: number;
  /** D-line conversion rate (D-line scores/D-line possessions) */
  d_line_conversion?: number;
  /** Red zone (20-40 yards) conversion rate */
  red_zone_conversion?: number;
  /** Total hucks completed */
  hucks_completed?: number;
  /** Huck completion percentage */
  huck_percentage?: number;
  /** Overall completion percentage */
  completion_percentage?: number;
  /** Whether team is currently active */
  is_current?: boolean;
  /** Last year of operation (if inactive) */
  last_year?: number | string;
}

/**
 * Filter options for statistics queries
 */
export interface StatsFilter {
  /** Filter by season year */
  season?: string | number;
  /** Filter by team name */
  team?: string;
  /** Filter by player position */
  position?: string;
  /** @deprecated Use 'view' instead */
  per?: 'total' | 'per-game';
  /** Statistics view mode (total or per-game averages) */
  view?: 'total' | 'per-game';
  /** Team or opponent perspective for statistics */
  perspective?: 'team' | 'opponent';
}

/**
 * Table sorting configuration
 */
export interface SortConfig {
  /** Column key to sort by */
  key: string;
  /** Sort direction */
  direction: 'asc' | 'desc';
}

/**
 * Pagination configuration for data tables
 */
export interface PaginationConfig {
  /** Current page number (1-indexed) */
  currentPage: number;
  /** Number of items per page */
  pageSize: number;
  /** Total number of pages available */
  totalPages: number;
  /** Total number of items across all pages */
  totalItems: number;
}