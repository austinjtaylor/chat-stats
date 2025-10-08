-- Migration 006: Add logo_url column to teams table
-- This migration adds support for team logos stored in Supabase Storage

-- Add logo_url column to teams table
ALTER TABLE teams
ADD COLUMN IF NOT EXISTS logo_url TEXT;

-- Create index for faster lookups when filtering by teams with logos
CREATE INDEX IF NOT EXISTS idx_teams_logo_url ON teams(logo_url) WHERE logo_url IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN teams.logo_url IS 'Public URL to team logo image in Supabase Storage (team-logos bucket)';
