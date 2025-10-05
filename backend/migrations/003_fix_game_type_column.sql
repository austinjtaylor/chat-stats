-- Migration: Increase game_type column length
-- Run this in Supabase SQL Editor before migrating data

-- Increase game_type column from VARCHAR(20) to VARCHAR(50)
ALTER TABLE games ALTER COLUMN game_type TYPE VARCHAR(50);
