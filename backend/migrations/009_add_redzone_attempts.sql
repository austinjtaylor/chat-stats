-- Migration: Add redzone_attempts columns to team_season_stats
-- This migration adds columns to track possessions that reached the red zone (80-100 yards)
-- Required for accurate red zone conversion % calculation

-- Add team redzone attempts column
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS redzone_attempts INTEGER DEFAULT 0;

-- Add opponent redzone attempts column
ALTER TABLE team_season_stats ADD COLUMN IF NOT EXISTS opp_redzone_attempts INTEGER DEFAULT 0;
