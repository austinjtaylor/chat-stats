-- Migration: Add possession statistics raw count columns to team_season_stats
-- This migration adds the raw count columns needed to calculate possession percentages
-- for both team and opponent perspectives

-- Add team possession raw count columns
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS o_line_points INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS o_line_scores INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS o_line_possessions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS d_line_points INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS d_line_scores INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS d_line_possessions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS redzone_possessions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS redzone_goals INTEGER DEFAULT 0;

-- Add opponent possession raw count columns
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_o_line_points INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_o_line_scores INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_o_line_possessions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_d_line_points INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_d_line_scores INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_d_line_possessions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_redzone_possessions INTEGER DEFAULT 0;
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_redzone_goals INTEGER DEFAULT 0;
