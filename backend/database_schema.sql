-- Sports Statistics Database Schema
-- For Professional Sports League Stats Chatbot System

-- Teams table (UFA API compatible)
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id VARCHAR(50) NOT NULL,  -- UFA teamID
    year INTEGER NOT NULL,  -- Four digit year
    city VARCHAR(100) NOT NULL,  -- Team's current city
    name VARCHAR(100) NOT NULL,  -- Team's name
    full_name VARCHAR(200) NOT NULL,  -- Team's full name
    abbrev VARCHAR(10) NOT NULL,  -- Team's abbreviation
    wins INTEGER DEFAULT 0,  -- Number of wins
    losses INTEGER DEFAULT 0,  -- Number of losses
    ties INTEGER DEFAULT 0,  -- Number of ties
    standing INTEGER NOT NULL,  -- Team's current standing
    division_id VARCHAR(50),  -- Division ID
    division_name VARCHAR(100),  -- Division name
    UNIQUE(team_id, year)
);

-- Players table (UFA API compatible)
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id VARCHAR(50) NOT NULL,  -- UFA playerID
    first_name VARCHAR(100) NOT NULL,  -- Player's first name
    last_name VARCHAR(100) NOT NULL,  -- Player's last name
    full_name VARCHAR(200) NOT NULL,  -- Player's full name
    team_id VARCHAR(50),  -- UFA teamID
    active BOOLEAN DEFAULT TRUE,  -- Whether player is active
    year INTEGER,  -- Year for team association
    jersey_number INTEGER,  -- Player's jersey number
    UNIQUE(player_id, team_id, year)
);

-- Games table (UFA API compatible)
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id VARCHAR(100) NOT NULL UNIQUE,  -- UFA gameID
    away_team_id VARCHAR(50) NOT NULL,  -- UFA awayTeamID
    home_team_id VARCHAR(50) NOT NULL,  -- UFA homeTeamID
    away_score INTEGER,  -- Away team score
    home_score INTEGER,  -- Home team score
    status VARCHAR(50) NOT NULL,  -- Game status (Upcoming, Live, Final)
    start_timestamp TIMESTAMP,  -- Game start timestamp
    start_timezone VARCHAR(50),  -- Start timezone
    streaming_url VARCHAR(500),  -- Streaming URL
    update_timestamp TIMESTAMP,  -- Last update timestamp
    week VARCHAR(20),  -- Week identifier
    location VARCHAR(200),  -- Game location
    year INTEGER NOT NULL,  -- Four digit year
    game_type VARCHAR(20) DEFAULT 'regular'  -- Game type: regular, playoffs_r1, playoffs_div, playoffs_championship, allstar
);

-- Player game statistics table (UFA API compatible)
CREATE TABLE IF NOT EXISTS player_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id VARCHAR(50) NOT NULL,  -- UFA playerID
    game_id VARCHAR(100) NOT NULL,  -- UFA gameID
    team_id VARCHAR(50) NOT NULL,  -- UFA teamID
    year INTEGER NOT NULL,  -- Four digit year
    -- Core Ultimate Frisbee stats
    assists INTEGER DEFAULT 0,
    goals INTEGER DEFAULT 0,
    hockey_assists INTEGER DEFAULT 0,
    completions INTEGER DEFAULT 0,
    throw_attempts INTEGER DEFAULT 0,
    throwaways INTEGER DEFAULT 0,
    stalls INTEGER DEFAULT 0,
    callahans_thrown INTEGER DEFAULT 0,
    yards_received INTEGER DEFAULT 0,
    yards_thrown INTEGER DEFAULT 0,
    hucks_attempted INTEGER DEFAULT 0,
    hucks_completed INTEGER DEFAULT 0,
    catches INTEGER DEFAULT 0,
    drops INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    callahans INTEGER DEFAULT 0,
    pulls INTEGER DEFAULT 0,
    ob_pulls INTEGER DEFAULT 0,
    recorded_pulls INTEGER DEFAULT 0,
    recorded_pulls_hangtime INTEGER,
    o_points_played INTEGER DEFAULT 0,
    o_points_scored INTEGER DEFAULT 0,
    d_points_played INTEGER DEFAULT 0,
    d_points_scored INTEGER DEFAULT 0,
    seconds_played INTEGER DEFAULT 0,
    o_opportunities INTEGER DEFAULT 0,
    o_opportunity_scores INTEGER DEFAULT 0,
    d_opportunities INTEGER DEFAULT 0,
    d_opportunity_stops INTEGER DEFAULT 0,
    UNIQUE(player_id, game_id)
);

-- Season statistics (aggregated) UFA API compatible
CREATE TABLE IF NOT EXISTS player_season_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id VARCHAR(50) NOT NULL,  -- UFA playerID
    team_id VARCHAR(50) NOT NULL,  -- UFA teamID
    year INTEGER NOT NULL,  -- Four digit year
    -- Aggregated Ultimate Frisbee stats
    total_assists INTEGER DEFAULT 0,
    total_goals INTEGER DEFAULT 0,
    total_hockey_assists INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    total_throw_attempts INTEGER DEFAULT 0,
    total_throwaways INTEGER DEFAULT 0,
    total_stalls INTEGER DEFAULT 0,
    total_callahans_thrown INTEGER DEFAULT 0,
    total_yards_received INTEGER DEFAULT 0,
    total_yards_thrown INTEGER DEFAULT 0,
    total_hucks_attempted INTEGER DEFAULT 0,
    total_hucks_completed INTEGER DEFAULT 0,
    total_catches INTEGER DEFAULT 0,
    total_drops INTEGER DEFAULT 0,
    total_blocks INTEGER DEFAULT 0,
    total_callahans INTEGER DEFAULT 0,
    total_pulls INTEGER DEFAULT 0,
    total_ob_pulls INTEGER DEFAULT 0,
    total_recorded_pulls INTEGER DEFAULT 0,
    total_recorded_pulls_hangtime INTEGER,
    total_o_points_played INTEGER DEFAULT 0,
    total_o_points_scored INTEGER DEFAULT 0,
    total_d_points_played INTEGER DEFAULT 0,
    total_d_points_scored INTEGER DEFAULT 0,
    total_seconds_played INTEGER DEFAULT 0,
    total_o_opportunities INTEGER DEFAULT 0,
    total_o_opportunity_scores INTEGER DEFAULT 0,
    total_d_opportunities INTEGER DEFAULT 0,
    total_d_opportunity_stops INTEGER DEFAULT 0,
    -- Calculated fields
    calculated_plus_minus INTEGER GENERATED ALWAYS AS 
        (total_goals + total_assists + total_blocks - total_throwaways - total_stalls - total_drops) STORED,
    completion_percentage DECIMAL(5,2),
    UNIQUE(player_id, team_id, year)
);

-- Team season statistics (UFA API compatible)
CREATE TABLE IF NOT EXISTS team_season_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id VARCHAR(50) NOT NULL,  -- UFA teamID
    year INTEGER NOT NULL,  -- Four digit year
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    standing INTEGER,
    division_id VARCHAR(50),
    division_name VARCHAR(100),
    points_for INTEGER DEFAULT 0,
    points_against INTEGER DEFAULT 0,
    UNIQUE(team_id, year)
);

-- Indexes for performance (UFA API compatible)
CREATE INDEX idx_teams_team_id ON teams(team_id);
CREATE INDEX idx_teams_year ON teams(year);
CREATE INDEX idx_players_team ON players(team_id);
CREATE INDEX idx_players_player_id ON players(player_id);
CREATE INDEX idx_players_year ON players(year);
CREATE INDEX idx_games_year ON games(year);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX idx_games_game_id ON games(game_id);
CREATE INDEX idx_player_game_stats_player ON player_game_stats(player_id);
CREATE INDEX idx_player_game_stats_game ON player_game_stats(game_id);
CREATE INDEX idx_player_game_stats_year ON player_game_stats(year);
CREATE INDEX idx_player_season_stats ON player_season_stats(player_id, year);
CREATE INDEX idx_team_season_stats ON team_season_stats(team_id, year);

-- Views for common queries (UFA API compatible)
CREATE VIEW IF NOT EXISTS current_season_leaders AS
SELECT 
    p.full_name,
    p.first_name,
    p.last_name,
    t.name as team_name,
    t.full_name as team_full_name,
    pss.year,
    pss.total_goals,
    pss.total_assists,
    pss.total_blocks,
    pss.calculated_plus_minus,
    pss.completion_percentage
FROM player_season_stats pss
JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
WHERE pss.year = (SELECT MAX(year) FROM player_season_stats)
ORDER BY pss.calculated_plus_minus DESC;

CREATE VIEW IF NOT EXISTS team_standings AS
SELECT 
    t.name,
    t.full_name,
    t.city,
    t.division_name,
    t.year,
    t.wins,
    t.losses,
    t.ties,
    t.standing,
    ROUND(CAST(t.wins AS FLOAT) / NULLIF(t.wins + t.losses + t.ties, 0), 3) as win_percentage
FROM teams t
WHERE t.year = (SELECT MAX(year) FROM teams)
ORDER BY t.standing ASC;