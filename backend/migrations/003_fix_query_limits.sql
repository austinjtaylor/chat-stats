-- Fix Query Limits for Free Tier Users
-- This migration corrects the free tier query limit from 50 to 10
-- Date: 2025-10-09

-- Update all existing free tier users to have the correct query limit
UPDATE user_subscriptions
SET query_limit = 10
WHERE tier = 'free' AND query_limit = 50;

-- Update the table default (this is redundant with 002 fix, but ensures consistency)
ALTER TABLE user_subscriptions
ALTER COLUMN query_limit SET DEFAULT 10;

-- Recreate the trigger function with correct value
-- (This ensures new signups get the correct limit)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  -- Create default subscription with correct query limit
  INSERT INTO public.user_subscriptions (user_id, tier, status, query_limit)
  VALUES (NEW.id, 'free', 'active', 10);

  -- Create default preferences
  INSERT INTO public.user_preferences (user_id)
  VALUES (NEW.id);

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Verify the changes
-- SELECT tier, query_limit, COUNT(*)
-- FROM user_subscriptions
-- GROUP BY tier, query_limit
-- ORDER BY tier, query_limit;
