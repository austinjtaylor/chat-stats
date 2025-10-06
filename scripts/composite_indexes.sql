-- Composite indexes to optimize player stats queries
-- Run these in Supabase SQL Editor or via Railway CLI

-- Player game stats - optimize JOINs on player_id, year, team_id
CREATE INDEX IF NOT EXISTS idx_player_game_stats_composite ON player_game_stats(player_id, year, team_id);

-- Player season stats - optimize queries filtering by player, year, team
CREATE INDEX IF NOT EXISTS idx_player_season_stats_composite ON player_season_stats(player_id, year, team_id);

-- Player season stats - optimize career queries (all years for a player)
CREATE INDEX IF NOT EXISTS idx_player_season_stats_player_year ON player_season_stats(player_id, year);

-- Games - optimize year-based filtering in JOINs
CREATE INDEX IF NOT EXISTS idx_games_year_teams ON games(year, home_team_id, away_team_id);
