-- User-Specific Tables for SaaS Features
-- Requires Supabase Auth to be enabled (auth.users table exists automatically)

-- User subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Subscription details
    tier VARCHAR(20) NOT NULL DEFAULT 'free', -- 'free', 'pro', 'enterprise'
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'canceled', 'past_due', 'incomplete'

    -- Stripe integration
    stripe_customer_id VARCHAR(100) UNIQUE,
    stripe_subscription_id VARCHAR(100) UNIQUE,
    stripe_price_id VARCHAR(100),

    -- Billing period
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMP,

    -- Usage tracking
    queries_this_month INTEGER DEFAULT 0,
    query_limit INTEGER DEFAULT 50, -- Free tier limit

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id)
);

-- User saved queries table (conversation history)
CREATE TABLE IF NOT EXISTS user_saved_queries (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Query details
    query TEXT NOT NULL,
    response TEXT NOT NULL,

    -- Metadata
    session_id VARCHAR(100), -- Group related queries
    tokens_used INTEGER,
    response_time_ms INTEGER,

    -- Organization
    is_favorite BOOLEAN DEFAULT FALSE,
    tags TEXT[], -- Array of tags for organization

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    CONSTRAINT user_saved_queries_user_id_created_at_idx
        CHECK (user_id IS NOT NULL)
);

-- User favorite players
CREATE TABLE IF NOT EXISTS user_favorite_players (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    player_id VARCHAR(50) NOT NULL,

    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, player_id)
);

-- User favorite teams
CREATE TABLE IF NOT EXISTS user_favorite_teams (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id VARCHAR(50) NOT NULL,

    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, team_id)
);

-- User preferences/settings
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Preferences
    theme VARCHAR(20) DEFAULT 'light', -- 'light', 'dark', 'auto'
    default_season INTEGER, -- Preferred season year
    notifications_enabled BOOLEAN DEFAULT TRUE,
    email_digest_frequency VARCHAR(20) DEFAULT 'weekly', -- 'daily', 'weekly', 'monthly', 'never'

    -- Display preferences
    favorite_stat_categories TEXT[], -- Array of preferred stats to highlight

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id)
);

-- Performance Indexes
CREATE INDEX idx_user_subscriptions_user ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_stripe_customer ON user_subscriptions(stripe_customer_id);
CREATE INDEX idx_user_saved_queries_user ON user_saved_queries(user_id);
CREATE INDEX idx_user_saved_queries_session ON user_saved_queries(session_id);
CREATE INDEX idx_user_saved_queries_created ON user_saved_queries(created_at DESC);
CREATE INDEX idx_user_favorite_players_user ON user_favorite_players(user_id);
CREATE INDEX idx_user_favorite_teams_user ON user_favorite_teams(user_id);
CREATE INDEX idx_user_preferences_user ON user_preferences(user_id);

-- Enable Row Level Security
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_saved_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorite_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_favorite_teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own data

-- user_subscriptions policies
CREATE POLICY "Users can view their own subscription"
  ON user_subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own subscription"
  ON user_subscriptions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "System can insert subscriptions"
  ON user_subscriptions FOR INSERT
  WITH CHECK (true); -- Service role will handle this

-- user_saved_queries policies
CREATE POLICY "Users can view their own saved queries"
  ON user_saved_queries FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own saved queries"
  ON user_saved_queries FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own saved queries"
  ON user_saved_queries FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own saved queries"
  ON user_saved_queries FOR DELETE
  USING (auth.uid() = user_id);

-- user_favorite_players policies
CREATE POLICY "Users can view their own favorite players"
  ON user_favorite_players FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own favorite players"
  ON user_favorite_players FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own favorite players"
  ON user_favorite_players FOR DELETE
  USING (auth.uid() = user_id);

-- user_favorite_teams policies
CREATE POLICY "Users can view their own favorite teams"
  ON user_favorite_teams FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own favorite teams"
  ON user_favorite_teams FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own favorite teams"
  ON user_favorite_teams FOR DELETE
  USING (auth.uid() = user_id);

-- user_preferences policies
CREATE POLICY "Users can view their own preferences"
  ON user_preferences FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own preferences"
  ON user_preferences FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
  ON user_preferences FOR UPDATE
  USING (auth.uid() = user_id);

-- Function to automatically create user_subscription and user_preferences on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  -- Create default subscription
  INSERT INTO public.user_subscriptions (user_id, tier, status, query_limit)
  VALUES (NEW.id, 'free', 'active', 50);

  -- Create default preferences
  INSERT INTO public.user_preferences (user_id)
  VALUES (NEW.id);

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to run the function when a new user signs up
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_user_subscriptions_updated_at
  BEFORE UPDATE ON user_subscriptions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at
  BEFORE UPDATE ON user_preferences
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Helpful view: User subscription summary
CREATE OR REPLACE VIEW user_subscription_summary AS
SELECT
    us.user_id,
    u.email,
    us.tier,
    us.status,
    us.queries_this_month,
    us.query_limit,
    us.current_period_end,
    us.cancel_at_period_end,
    (us.queries_this_month >= us.query_limit) AS at_query_limit,
    CASE
        WHEN us.tier = 'free' THEN 0
        WHEN us.tier = 'pro' THEN 9.99
        WHEN us.tier = 'enterprise' THEN 49.99
        ELSE 0
    END AS monthly_price
FROM user_subscriptions us
JOIN auth.users u ON us.user_id = u.id;
