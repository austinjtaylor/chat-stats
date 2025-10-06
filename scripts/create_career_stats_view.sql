-- Create materialized view for player career stats
-- This pre-aggregates career statistics for instant loading

CREATE MATERIALIZED VIEW IF NOT EXISTS player_career_stats AS
WITH player_aggregates AS (
    SELECT
        pss.player_id,
        MAX(pss.year) as most_recent_year,
        SUM(pss.total_goals) as total_goals,
        SUM(pss.total_assists) as total_assists,
        SUM(pss.total_hockey_assists) as total_hockey_assists,
        SUM(pss.total_blocks) as total_blocks,
        SUM(pss.calculated_plus_minus) as calculated_plus_minus,
        SUM(pss.total_completions) as total_completions,
        SUM(pss.total_yards_thrown) as total_yards_thrown,
        SUM(pss.total_yards_received) as total_yards_received,
        SUM(pss.total_throwaways) as total_throwaways,
        SUM(pss.total_stalls) as total_stalls,
        SUM(pss.total_drops) as total_drops,
        SUM(pss.total_callahans) as total_callahans,
        SUM(pss.total_hucks_completed) as total_hucks_completed,
        SUM(pss.total_hucks_attempted) as total_hucks_attempted,
        SUM(pss.total_hucks_received) as total_hucks_received,
        SUM(pss.total_pulls) as total_pulls,
        SUM(pss.total_o_points_played) as total_o_points_played,
        SUM(pss.total_d_points_played) as total_d_points_played,
        SUM(pss.total_seconds_played) as total_seconds_played,
        SUM(pss.total_o_opportunities) as total_o_opportunities,
        SUM(pss.total_d_opportunities) as total_d_opportunities,
        SUM(pss.total_o_opportunity_scores) as total_o_opportunity_scores,
        COUNT(DISTINCT pgs.game_id) as games_played
    FROM player_season_stats pss
    LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
    WHERE pgs.game_id IS NULL OR (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
    GROUP BY pss.player_id
),
most_recent_info AS (
    SELECT DISTINCT ON (pss.player_id)
        pss.player_id,
        pss.team_id as most_recent_team_id,
        p.full_name,
        p.first_name,
        p.last_name,
        t.name as most_recent_team_name,
        t.full_name as most_recent_team_full_name
    FROM player_season_stats pss
    JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
    LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
    ORDER BY pss.player_id, pss.year DESC
)
SELECT
    pa.player_id,
    mri.most_recent_team_id,
    mri.full_name,
    mri.first_name,
    mri.last_name,
    mri.most_recent_team_name,
    mri.most_recent_team_full_name,
    pa.total_goals,
    pa.total_assists,
    pa.total_hockey_assists,
    pa.total_blocks,
    pa.calculated_plus_minus,
    pa.total_completions,
    pa.total_yards_thrown,
    pa.total_yards_received,
    pa.total_throwaways,
    pa.total_stalls,
    pa.total_drops,
    pa.total_callahans,
    pa.total_hucks_completed,
    pa.total_hucks_attempted,
    pa.total_hucks_received,
    pa.total_pulls,
    pa.total_o_points_played,
    pa.total_d_points_played,
    pa.total_seconds_played,
    pa.total_o_opportunities,
    pa.total_d_opportunities,
    pa.total_o_opportunity_scores,
    pa.games_played,
    pa.total_o_opportunities as possessions,
    (pa.total_goals + pa.total_assists) as score_total,
    (pa.total_o_points_played + pa.total_d_points_played) as total_points_played,
    (pa.total_yards_thrown + pa.total_yards_received) as total_yards,
    ROUND(pa.total_seconds_played / 60.0, 0) as minutes_played,
    CASE
        WHEN pa.total_hucks_attempted > 0
        THEN ROUND(pa.total_hucks_completed * 100.0 / pa.total_hucks_attempted, 1)
        ELSE 0
    END as huck_percentage,
    CASE
        WHEN pa.total_o_opportunities >= 20
        THEN ROUND(pa.total_o_opportunity_scores * 100.0 / pa.total_o_opportunities, 1)
        ELSE NULL
    END as offensive_efficiency,
    CASE
        WHEN (pa.total_throwaways + pa.total_stalls + pa.total_drops) > 0
        THEN ROUND((pa.total_yards_thrown + pa.total_yards_received) * 1.0 / (pa.total_throwaways + pa.total_stalls + pa.total_drops), 1)
        ELSE NULL
    END as yards_per_turn,
    CASE
        WHEN (pa.total_completions + pa.total_throwaways + pa.total_drops) > 0
        THEN ROUND((CAST(pa.total_completions AS NUMERIC) / (pa.total_completions + pa.total_throwaways + pa.total_drops)) * 100, 2)
        ELSE 0
    END as completion_percentage
FROM player_aggregates pa
JOIN most_recent_info mri ON pa.player_id = mri.player_id;

-- Create index on the materialized view for fast lookups
CREATE INDEX IF NOT EXISTS idx_career_stats_player ON player_career_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_career_stats_team ON player_career_stats(most_recent_team_id);

-- To refresh the view after data updates, run:
-- REFRESH MATERIALIZED VIEW player_career_stats;
