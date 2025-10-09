-- Add full_name column to user_preferences table
-- This allows users to set their display name and customize their initials

ALTER TABLE user_preferences
ADD COLUMN full_name VARCHAR(255);

-- Add comment for documentation
COMMENT ON COLUMN user_preferences.full_name IS 'User full name for display purposes and generating initials';
