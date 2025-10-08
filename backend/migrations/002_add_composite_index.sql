-- Migration: Add composite index on game_events(game_id, team)
-- Date: 2025-10-08
-- Purpose: Optimize game stats queries by replacing separate indexes with a composite index

-- Drop old separate indexes (if they exist)
DROP INDEX IF EXISTS idx_game_events_game;
DROP INDEX IF EXISTS idx_game_events_team;

-- Create new composite index that covers both columns
-- This will significantly speed up queries that filter by game_id AND team (most common pattern)
CREATE INDEX IF NOT EXISTS idx_game_events_game_team ON game_events(game_id, team);

-- Keep the event_type index as it's used separately
-- CREATE INDEX IF NOT EXISTS idx_game_events_type ON game_events(event_type);
-- (already exists, no need to recreate)
