-- Fix completion_percentage calculation in player_career_stats materialized view
-- The previous formula incorrectly used (completions + throwaways + drops) where drops is receiver drops
-- The correct formula uses total_throw_attempts from player_season_stats which includes receiver drops on the thrower's passes

DROP MATERIALIZED VIEW IF EXISTS player_career_stats;

CREATE MATERIALIZED VIEW player_career_stats AS
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
        SUM(pss.total_throw_attempts) as total_throw_attempts,
        SUM(pss.total_yards_thrown) as total_yards_thrown,
        SUM(pss.total_yards_received) as total_yards_received,
        SUM(pss.total_throwaways) as total_throwaways,
        SUM(pss.total_stalls) as total_stalls,
        SUM(pss.total_drops) as total_drops,
        SUM(pss.total_callahans) as total_callahans,
        SUM(pss.total_hucks_completed) as total_hucks_completed,
        SUM(pss.total_hucks_attempted) as total_hucks_attempted,
        SUM(pss.total_hucks_received) as total_hucks_received,
        SUM(pss.total_catches) as total_catches,
        SUM(pss.total_pulls) as total_pulls,
        SUM(pss.total_o_points_played) as total_o_points_played,
        SUM(pss.total_d_points_played) as total_d_points_played,
        SUM(pss.total_seconds_played) as total_seconds_played,
        SUM(pss.total_o_opportunities) as total_o_opportunities,
        SUM(pss.total_d_opportunities) as total_d_opportunities,
        SUM(pss.total_o_opportunity_scores) as total_o_opportunity_scores
    FROM player_season_stats pss
    GROUP BY pss.player_id
),
games_played_count AS (
    SELECT
        pgs.player_id,
        COUNT(DISTINCT pgs.game_id) as games_played
    FROM player_game_stats pgs
    WHERE pgs.o_points_played > 0 OR pgs.d_points_played > 0
       OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0
    GROUP BY pgs.player_id
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
    pa.total_throw_attempts,
    pa.total_yards_thrown,
    pa.total_yards_received,
    pa.total_throwaways,
    pa.total_stalls,
    pa.total_drops,
    pa.total_callahans,
    pa.total_hucks_completed,
    pa.total_hucks_attempted,
    pa.total_hucks_received,
    pa.total_catches,
    pa.total_pulls,
    pa.total_o_points_played,
    pa.total_d_points_played,
    pa.total_seconds_played,
    pa.total_o_opportunities,
    pa.total_d_opportunities,
    pa.total_o_opportunity_scores,
    COALESCE(gpc.games_played, 0) as games_played,
    pa.total_o_opportunities as possessions,
    (pa.total_goals + pa.total_assists) as score_total,
    (pa.total_o_points_played + pa.total_d_points_played) as total_points_played,
    (pa.total_yards_thrown + pa.total_yards_received) as total_yards,
    ROUND(pa.total_seconds_played / 60.0, 0) as minutes_played,
    CASE WHEN pa.total_hucks_attempted > 0
        THEN ROUND(pa.total_hucks_completed * 100.0 / pa.total_hucks_attempted, 1)
        ELSE 0
    END as huck_percentage,
    CASE
        WHEN pa.total_o_opportunities >= 100
        THEN ROUND(pa.total_o_opportunity_scores * 100.0 / pa.total_o_opportunities, 1)
        ELSE NULL
    END as offensive_efficiency,
    CASE
        WHEN (pa.total_throwaways + pa.total_stalls + pa.total_drops) > 0
        THEN ROUND((pa.total_yards_thrown + pa.total_yards_received) * 1.0 / (pa.total_throwaways + pa.total_stalls + pa.total_drops), 1)
        WHEN (pa.total_yards_thrown + pa.total_yards_received) > 0
        THEN (pa.total_yards_thrown + pa.total_yards_received) * 1.0
        ELSE NULL
    END as yards_per_turn,
    CASE
        WHEN pa.total_completions > 0
        THEN ROUND(pa.total_yards_thrown * 1.0 / pa.total_completions, 1)
        ELSE NULL
    END as yards_per_completion,
    CASE
        WHEN pa.total_catches > 0
        THEN ROUND(pa.total_yards_received * 1.0 / pa.total_catches, 1)
        ELSE NULL
    END as yards_per_reception,
    CASE
        WHEN (pa.total_throwaways + pa.total_stalls + pa.total_drops) > 0
        THEN ROUND(pa.total_assists * 1.0 / (pa.total_throwaways + pa.total_stalls + pa.total_drops), 2)
        ELSE NULL
    END as assists_per_turnover,
    -- Fixed completion_percentage: uses total_throw_attempts instead of (completions + throwaways + drops)
    CASE
        WHEN pa.total_throw_attempts >= 100
        THEN ROUND(pa.total_completions * 100.0 / pa.total_throw_attempts, 1)
        ELSE NULL
    END as completion_percentage
FROM player_aggregates pa
JOIN most_recent_info mri ON pa.player_id = mri.player_id
LEFT JOIN games_played_count gpc ON pa.player_id = gpc.player_id;
