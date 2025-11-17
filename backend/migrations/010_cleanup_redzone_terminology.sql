-- Migration: Clean up redundant red zone terminology
-- Drop redzone_possessions columns which duplicate o_line_possessions + d_line_possessions
-- This resolves confusion where "redzone_possessions" actually meant "total possessions"

-- Drop redundant team redzone_possessions column
ALTER TABLE team_season_stats DROP COLUMN IF EXISTS redzone_possessions;

-- Drop redundant opponent redzone_possessions column
ALTER TABLE team_season_stats DROP COLUMN IF EXISTS opp_redzone_possessions;

-- Note: redzone_attempts and redzone_goals remain as the meaningful red zone stats:
-- - redzone_attempts = possessions that reached the red zone (80-100 yards)
-- - redzone_goals = goals scored from the red zone
-- - red_zone_conversion = (redzone_goals / redzone_attempts) * 100
