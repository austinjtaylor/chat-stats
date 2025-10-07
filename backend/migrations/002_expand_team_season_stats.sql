-- Migration: Expand team_season_stats table with UFA-style advanced statistics
-- This adds columns to match the comprehensive team stats displayed in the frontend

-- Add basic game stats
ALTER TABLE team_season_stats ADD COLUMN games_played INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN scores INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN scores_against INTEGER DEFAULT 0;

-- Add completion/turnover stats
ALTER TABLE team_season_stats ADD COLUMN completions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN throw_attempts INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN turnovers INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN completion_percentage DECIMAL(5,2) DEFAULT 0;

-- Add huck stats
ALTER TABLE team_season_stats ADD COLUMN hucks_completed INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN hucks_attempted INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN huck_percentage DECIMAL(5,2) DEFAULT 0;

-- Add defensive stats
ALTER TABLE team_season_stats ADD COLUMN blocks INTEGER DEFAULT 0;

-- Add possession-based stats (calculated from game_events)
ALTER TABLE team_season_stats ADD COLUMN hold_percentage DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN o_line_conversion DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN break_percentage DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN d_line_conversion DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN red_zone_conversion DECIMAL(5,2) DEFAULT 0;

-- Add opponent stats (for opponent perspective view)
ALTER TABLE team_season_stats ADD COLUMN opp_completions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_throw_attempts INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_turnovers INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_completion_percentage DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_hucks_completed INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_hucks_attempted INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_huck_percentage DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_blocks INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_hold_percentage DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_o_line_conversion DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_break_percentage DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_d_line_conversion DECIMAL(5,2) DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN opp_red_zone_conversion DECIMAL(5,2) DEFAULT 0;

-- Add metadata columns
ALTER TABLE team_season_stats ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create index on year for faster filtering
CREATE INDEX IF NOT EXISTS idx_team_season_stats_year ON team_season_stats(year);
