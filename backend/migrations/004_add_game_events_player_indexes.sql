-- Migration: Add indexes on game_events player foreign keys
-- Date: 2025-10-08
-- Purpose: Optimize queries involving game_events player lookups
-- Note: While the refactored play-by-play code no longer JOINs directly on these columns,
--       these indexes are still useful for data integrity and potential future queries

-- Add indexes on player ID foreign key columns
CREATE INDEX IF NOT EXISTS idx_game_events_thrower_id ON game_events(thrower_id);
CREATE INDEX IF NOT EXISTS idx_game_events_receiver_id ON game_events(receiver_id);
CREATE INDEX IF NOT EXISTS idx_game_events_defender_id ON game_events(defender_id);
CREATE INDEX IF NOT EXISTS idx_game_events_puller_id ON game_events(puller_id);
