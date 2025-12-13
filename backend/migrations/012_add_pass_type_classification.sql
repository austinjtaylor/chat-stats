-- Migration: Add pass type classification
-- Adds pass_type column to game_events and pass type count columns to stats tables

-- Add pass_type column to game_events
ALTER TABLE game_events ADD COLUMN IF NOT EXISTS pass_type VARCHAR(10);

-- Create index on pass_type for faster queries
CREATE INDEX IF NOT EXISTS idx_game_events_pass_type ON game_events(pass_type);

-- Add pass type count columns to player_game_stats
ALTER TABLE player_game_stats ADD COLUMN IF NOT EXISTS dish_count INTEGER DEFAULT 0;
ALTER TABLE player_game_stats ADD COLUMN IF NOT EXISTS swing_count INTEGER DEFAULT 0;
ALTER TABLE player_game_stats ADD COLUMN IF NOT EXISTS dump_count INTEGER DEFAULT 0;
ALTER TABLE player_game_stats ADD COLUMN IF NOT EXISTS huck_count INTEGER DEFAULT 0;
ALTER TABLE player_game_stats ADD COLUMN IF NOT EXISTS gainer_count INTEGER DEFAULT 0;

-- Add pass type count columns to player_season_stats
ALTER TABLE player_season_stats ADD COLUMN IF NOT EXISTS total_dish INTEGER DEFAULT 0;
ALTER TABLE player_season_stats ADD COLUMN IF NOT EXISTS total_swing INTEGER DEFAULT 0;
ALTER TABLE player_season_stats ADD COLUMN IF NOT EXISTS total_dump INTEGER DEFAULT 0;
ALTER TABLE player_season_stats ADD COLUMN IF NOT EXISTS total_huck INTEGER DEFAULT 0;
ALTER TABLE player_season_stats ADD COLUMN IF NOT EXISTS total_gainer INTEGER DEFAULT 0;

-- Add pass type count columns to team_season_stats
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS team_dish INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS team_swing INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS team_dump INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS team_huck INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS team_gainer INTEGER DEFAULT 0;
